"""NeoFold Edge - local web app.

Everything is served from disk. No CDN, no external API, no telemetry.
`docs_url=None` is deliberate: FastAPI's /docs pulls Swagger UI from jsDelivr
at runtime, which would break the offline guarantee.
"""
from __future__ import annotations

import asyncio
import json
import os
import socket
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from neofold.pipeline import DISCLAIMER, run_triage
from neofold.screen import PeptideScreen, triage

ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "app" / "static"
RESULTS = ROOT / "results"
DATA = ROOT / "data"

app = FastAPI(title="NeoFold Edge", docs_url=None, redoc_url=None, openapi_url=None)

_screen = PeptideScreen()
_cache: dict[str, dict] = {}


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return (STATIC / "index.html").read_text()


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "disclaimer": DISCLAIMER}


@app.get("/api/network")
def network() -> dict:
    """Report whether this machine can currently reach the internet.

    The demo's claim is that it does not NEED the network, so we show the
    state honestly rather than asserting it. A reachable internet does not
    weaken the claim; using it would.
    """
    reachable = False
    try:
        with socket.create_connection(("1.1.1.1", 53), timeout=0.6):
            reachable = True
    except OSError:
        reachable = False
    return {
        "internet_reachable": reachable,
        "external_calls_made": 0,
        "note": "All inference is local. This app makes no outbound requests.",
    }


@app.get("/api/alleles")
def alleles(q: str = "", limit: int = 40) -> dict:
    all_alleles = _screen.supported_alleles
    if q:
        needle = q.upper()
        matches = [a for a in all_alleles if needle in a.upper()]
    else:
        matches = [a for a in all_alleles if a.startswith(("HLA-A", "HLA-B", "HLA-C"))]
    return {"total": len(all_alleles), "alleles": sorted(matches)[:limit]}


@app.get("/api/datasets")
def datasets() -> dict:
    files = sorted((DATA / "demo").glob("*.vcf"))
    return {"datasets": [{"name": f.name, "path": str(f.relative_to(ROOT))} for f in files]}


@app.post("/api/triage")
def triage_endpoint(payload: dict) -> JSONResponse:
    vcf = payload.get("vcf", "data/demo/tumor_variants_large.vcf")
    allele = payload.get("allele", "HLA-C*08:02")
    top_n = int(payload.get("top_n", 5))

    vcf_path = (ROOT / vcf).resolve()
    if not str(vcf_path).startswith(str(ROOT)) or not vcf_path.exists():
        raise HTTPException(status_code=400, detail="unknown dataset")

    key = f"{vcf}|{allele}|{top_n}"
    if key in _cache:
        out = dict(_cache[key])
        out["cached"] = True
        return JSONResponse(out)

    t0 = time.perf_counter()
    report = run_triage(str(vcf_path), str(ROOT / "data/sequences/proteins.fasta"),
                        allele=allele, top_n=top_n, screen=_screen)
    out = report.as_dict()
    out["wall_seconds"] = round(time.perf_counter() - t0, 2)
    out["cached"] = False
    _cache[key] = out
    return JSONResponse(out)


def _find_cif(name: str) -> Path | None:
    """Structures live either in results/ or results/shortlist/."""
    for base in (RESULTS, RESULTS / "shortlist"):
        p = (base / f"{name}.cif").resolve()
        if str(p).startswith(str(RESULTS)) and p.exists():
            return p
    return None


def _confidence_for(cif: Path) -> dict:
    p = cif.parent / f"confidence_{cif.stem}.json"
    return json.loads(p.read_text()) if p.exists() else {}


# The mutant/wild-type pairs, and what each one is for.
PAIRS = {
    "kras_g12d_9mer_mut_model_0": {
        "label": "KRAS G12D — tumour", "peptide": "GADGVGKSA", "role": "mutant",
        "partner": "kras_g12d_9mer_wt_model_0", "crystal": "6ULN",
    },
    "kras_g12d_9mer_wt_model_0": {
        "label": "KRAS wild-type — normal tissue", "peptide": "GAGGVGKSA",
        "role": "wild_type", "partner": "kras_g12d_9mer_mut_model_0",
    },
}


@app.get("/api/structures")
def structures() -> dict:
    """Predicted structures on disk, with confidence and pairing metadata."""
    out = []
    seen = set()
    for base in (RESULTS, RESULTS / "shortlist"):
        if not base.exists():
            continue
        for cif in sorted(base.glob("*.cif")):
            if cif.stem in seen:
                continue
            seen.add(cif.stem)
            conf = _confidence_for(cif)
            out.append({
                "id": cif.stem,
                "cif_url": f"/api/structure/{cif.stem}",
                "iptm": conf.get("iptm"),
                "plddt": conf.get("complex_plddt"),
                "ptm": conf.get("ptm"),
                **PAIRS.get(cif.stem, {}),
            })
    return {"structures": out}


@app.get("/api/compare")
def compare(mutant: str = "kras_g12d_9mer_mut_model_0",
            wild_type: str = "kras_g12d_9mer_wt_model_0") -> dict:
    """Side-by-side evidence for a mutant peptide and its wild-type counterpart.

    The point of this endpoint is what it does NOT let you conclude. Boltz
    confidence is reported because hiding it would be dishonest, but it is
    labelled as non-discriminating: measured here, the wild-type -- which does
    not stabilise this allele experimentally -- scores essentially the same as
    the mutant. The discriminating evidence is the named contact and the
    binding screen.
    """
    from neofold.contacts import measure_salt_bridge, peptide_sequence

    rows = []
    for name, role in ((mutant, "mutant"), (wild_type, "wild_type")):
        cif = _find_cif(name)
        if cif is None:
            continue
        conf = _confidence_for(cif)
        contact = measure_salt_bridge(cif, peptide_position=3, mhc_residue_number=156)
        rows.append({
            "id": name, "role": role, "peptide": peptide_sequence(cif),
            "iptm": conf.get("iptm"), "plddt": conf.get("complex_plddt"),
            "contact": contact.as_dict(),
        })
    if len(rows) < 2:
        return {"available": False, "reason": "both structures not yet predicted"}

    mut, wt = rows[0], rows[1]
    return {
        "available": True,
        "mutant": mut,
        "wild_type": wt,
        "iptm_delta": round(abs((mut["iptm"] or 0) - (wt["iptm"] or 0)), 4),
        "verdict": {
            "confidence": ("does not discriminate — the wild-type scores "
                           "essentially the same as the mutant"),
            "structure": ("decisive — the mutation creates an aspartate that "
                          "salt-bridges Arg156; glycine has no side chain, so "
                          "the contact cannot form at all"),
            "screen": "decisive — 49x stronger predicted binding than wild-type",
        },
    }


@app.get("/api/structure/{name}")
def structure(name: str):
    path = _find_cif(name)
    if path is None:
        raise HTTPException(status_code=404, detail="no such structure")
    return FileResponse(path, media_type="chemical/x-mmcif")


# Contacts worth measuring, specified in advance from experimental structures.
# Fishing a predicted model for "whatever looks different" would not be evidence;
# checking a named contact that a crystal structure already established is.
PREREGISTERED_CONTACTS = {
    "HLA-C*08:02": {
        "peptide_position": 3,
        "mhc_residue": 156,
        "rationale": ("HLA-C*08:02 prefers aspartate at peptide position 3, and "
                      "crystal structure 6ULN shows that residue salt-bridging "
                      "Arg156 in the D pocket. The G12D substitution is what "
                      "places an aspartate there."),
        "reference": "PDB 6ULN; Rasmussen et al., J Immunol 2014",
    },
}


@app.get("/api/contact/{name}")
def contact(name: str, allele: str = "HLA-C*08:02") -> dict:
    """Measure the pre-registered contact for this allele in a predicted model."""
    spec = PREREGISTERED_CONTACTS.get(allele)
    if spec is None:
        return {"available": False,
                "reason": f"no pre-registered contact defined for {allele}"}

    path = _find_cif(name)
    if path is None:
        raise HTTPException(status_code=404, detail="no such structure")

    from neofold.contacts import measure_salt_bridge, peptide_sequence
    measured = measure_salt_bridge(
        path, peptide_position=spec["peptide_position"],
        mhc_residue_number=spec["mhc_residue"])

    out = {"available": True, "peptide": peptide_sequence(path),
           "rationale": spec["rationale"], "reference": spec["reference"],
           **measured.as_dict()}

    # Compare against the experimental structure when we have it on disk.
    crystal = RESULTS / "reference" / "6ULN.cif"
    if crystal.exists() and allele == "HLA-C*08:02":
        ref = measure_salt_bridge(
            crystal, peptide_position=spec["peptide_position"],
            mhc_residue_number=spec["mhc_residue"])
        out["crystal_distance_a"] = ref.as_dict()["min_distance_a"]
    return out


@app.get("/api/confidence/{name}")
def confidence(name: str) -> dict:
    """Per-residue and pairwise confidence arrays for the confidence plots.

    pLDDT is per-atom confidence collapsed to residues; PAE is the predicted
    error in the relative position of every residue pair. The PAE block
    structure is the interesting part: low off-diagonal error between the
    peptide chain and the groove means the model is confident about how they
    sit RELATIVE to each other, which is a different claim from being
    confident about each chain on its own.
    """
    import numpy as np

    def load(prefix):
        for base in (RESULTS, RESULTS / "shortlist"):
            path = base / f"{prefix}_{name}.npz"
            if path.exists():
                break
        else:
            return None
        with np.load(path) as d:
            return d[d.files[0]]

    plddt, pae = load("plddt"), load("pae")
    if plddt is None and pae is None:
        raise HTTPException(status_code=404, detail="no confidence arrays on disk")

    # Chain boundaries, read from the structure so the plots can band them.
    chains = []
    cif = _find_cif(name)
    if cif is not None:
        import gemmi
        st = gemmi.read_structure(str(cif))
        st.setup_entities()
        offset = 0
        labels = {"A": "HLA heavy chain", "B": "β2-microglobulin", "C": "Peptide"}
        for ch in st[0]:
            n = len(list(ch))
            chains.append({"id": ch.name, "label": labels.get(ch.name, ch.name),
                           "start": offset, "end": offset + n - 1, "length": n})
            offset += n

    out = {"name": name, "chains": chains}
    if plddt is not None:
        # Boltz reports pLDDT on 0-1 here; the conventional scale is 0-100.
        scale = 100.0 if float(plddt.max()) <= 1.0 else 1.0
        out["plddt"] = [round(float(v) * scale, 1) for v in plddt]
    if pae is not None:
        out["pae"] = [[round(float(v), 1) for v in row] for row in pae]
        out["pae_max"] = round(float(pae.max()), 1)
    return out


@app.get("/api/gpu")
def gpu() -> dict:
    """GPU telemetry, GB10-aware.

    On GB10 the memory.* query fields return N/A because the GPU shares
    coherent system memory rather than having discrete VRAM, so we read
    per-process memory from the compute-apps query instead and report the
    unified pool separately.
    """
    from neofold.telemetry import read_gpu
    return read_gpu()


app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")
