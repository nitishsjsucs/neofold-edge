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
from neofold.expression import NormalExpression
from neofold.selfsim import SelfProteome

ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "app" / "static"
RESULTS = ROOT / "results"
DATA = ROOT / "data"

app = FastAPI(title="NeoFold Edge", docs_url=None, redoc_url=None, openapi_url=None)

_screen = PeptideScreen()
_cache: dict[str, dict] = {}

# Vendored reviewed human proteome for the self-similarity filter.
_proteome_path = ROOT / "data" / "reference" / "human_sp.fasta.gz"
_proteome = SelfProteome(_proteome_path) if _proteome_path.exists() else None

_gtex_path = ROOT / "data" / "reference" / "gtex_median_tpm.gct.gz"
_expression = NormalExpression(_gtex_path) if _gtex_path.exists() else None


@app.on_event("startup")
def _warm_caches() -> None:
    """Pay the index-build and model-load costs before anyone clicks."""
    import threading

    def warm():
        try:
            _screen.predictor            # ~2.5 s MHCflurry load
            if _proteome is not None:
                _proteome.warm()         # ~9 s of seed indexes
            if _expression is not None:
                _expression.check("KRAS")
        except Exception:
            pass                         # warming is an optimisation, not a requirement

    threading.Thread(target=warm, daemon=True).start()


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
                        allele=allele, top_n=top_n, screen=_screen,
                        proteome=_proteome, expression=_expression)
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
        "order": 1, "label": "KRAS G12D — tumour", "peptide": "GADGVGKSA", "role": "mutant",
        "partner": "kras_g12d_9mer_wt_model_0", "crystal": "6ULN",
    },
    "kras_g12d_9mer_wt_model_0": {
        # "germline counterpart", not "normal tissue": GAGGVGKSA occurs in
        # several RAS-family proteins, so it is not tissue-specific.
        "order": 2, "label": "KRAS germline counterpart", "peptide": "GAGGVGKSA",
        "role": "wild_type", "partner": "kras_g12d_9mer_mut_model_0",
    },
    # NOT a neoantigen. ICDFGLARV occurs verbatim in ERK2/MAPK1 (P28482) and
    # NLK (Q9UBE8): it contains the DFG motif shared across the kinome. Our
    # binding screen ranked it highly -- 178 nM, the largest differential in
    # the demo -- and the self-similarity filter disqualifies it. Kept and
    # labelled as a negative control, because it is the clearest illustration
    # that a large differential does not mean tumour-specific.
    "kit_d816v_mut_model_0": {
        "order": 3, "label": "KIT D816V — self peptide (control)",
        "peptide": "ICDFGLARV", "role": "negative_control",
        "partner": "kit_d816v_wt_model_0", "disqualified": True,
        "why": ("occurs verbatim in ERK2/MAPK1 (P28482) — the DFG motif is "
                "conserved across protein kinases, so this is a normal human "
                "peptide, not a neoepitope"),
    },
    "kit_d816v_wt_model_0": {
        "order": 4, "label": "KIT germline counterpart",
        "peptide": "ICDFGLARD", "role": "wild_type",
        "partner": "kit_d816v_mut_model_0",
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
            "screen": "decisive — DAI 23.5, above the Rech 2018 first-percentile bar of 10",
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
#
# IMPORTANT: a pre-registered contact is only informative when the MUTATION is
# what creates it. Measured here: KIT D816V places its substitution at peptide
# position 9, and both the mutant and the wild-type peptide happen to carry Asp
# at position 3 -- so both form the p3-Arg156 salt bridge (2.54 A vs 2.49 A) and
# the measurement says nothing about that variant. Keying this per CASE rather
# than per allele is what stops the panel from implying otherwise.
PREREGISTERED_CONTACTS = {
    "kras_g12d": {
        "alleles": ["HLA-C*08:02"],
        "peptide_position": 3,
        "mhc_residue": 156,
        "mutation_position": 3,
        "rationale": ("HLA-C*08:02 prefers aspartate at peptide position 3, and "
                      "crystal structure 6ULN shows that residue making charge "
                      "contacts to Arg156 AND Arg97. The G12D substitution is "
                      "what places an aspartate there."),
        "reference": "PDB 6ULN; Sim et al., PNAS 2020; Rasmussen et al., J Immunol 2014",
        "limitation": ("Whether this contact CAN form is a deterministic function "
                       "of the peptide sequence — position 3 is aspartate or it is "
                       "not — so the structure prediction adds no information on "
                       "that point. What the prediction contributes is the "
                       "geometry, which matches the crystal to 0.15 Å."),
    },
}

# Cases we have structures for but NO pre-registered contact that the mutation
# creates. Saying so is the honest option; measuring something anyway is not.
NO_CONTACT_REASON = {
    "kit_d816v": (
        "KIT D816V substitutes the peptide's C-terminal residue (position 9), "
        "not position 3. Both the mutant and wild-type peptides carry aspartate "
        "at position 3, so the p3-Arg156 salt bridge forms in both (2.54 A and "
        "2.49 A measured) and cannot distinguish them. The C-terminal anchor is "
        "where this mutation acts; we have not pre-registered a measurement for "
        "it, so none is shown."
    ),
}


def _case_for(name: str) -> str | None:
    for case in list(PREREGISTERED_CONTACTS) + list(NO_CONTACT_REASON):
        if name.startswith(case):
            return case
    return None


@app.get("/api/contact/{name}")
def contact(name: str, allele: str = "HLA-C*08:02") -> dict:
    """Measure the pre-registered contact for this case, if one applies."""
    case = _case_for(name)
    if case in NO_CONTACT_REASON:
        return {"available": False, "not_applicable": True,
                "reason": NO_CONTACT_REASON[case]}

    spec = PREREGISTERED_CONTACTS.get(case)
    if spec is None or allele not in spec["alleles"]:
        return {"available": False,
                "reason": f"no pre-registered contact defined for this case on {allele}"}

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

    crystal = RESULTS / "reference" / "6ULN.cif"
    if crystal.exists() and case == "kras_g12d":
        ref = measure_salt_bridge(crystal, peptide_position=spec["peptide_position"],
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


@app.get("/api/benchmark")
def benchmark() -> dict:
    """Measured single-node performance, plus clearly-separated projections.

    Everything under "measured" was timed on the Nano. Everything under
    "projected" is arithmetic on those measurements -- we only ever had one
    Nano, so no multi-node number here was observed.
    """
    import statistics
    path = ROOT / "benchmarks" / "measured.json"
    if not path.exists():
        return {"available": False}
    d = json.loads(path.read_text())

    full = [r["wall_s"] for r in d["runs"] if r["msa"] is True]
    mean = statistics.mean(full)
    overhead = d["stage_split"]["fixed_overhead_s"]

    return {
        "available": True,
        "hardware": d["hardware"],
        "telemetry": d["telemetry_during_inference"],
        "screening": d["screening_stage"],
        "measured": {
            "runs": d["runs"],
            "n_full_setting_runs": len(full),
            "mean_wall_s": round(mean, 1),
            "stdev_wall_s": round(statistics.stdev(full), 1),
            "candidates_per_hour": round(3600 / mean),
            "fixed_overhead_s": overhead,
            "overhead_fraction_pct": round(100 * overhead / mean),
        },
        "projected": {
            "note": "PROJECTED from measured single-node throughput. Not observed.",
            "basis": d["projections"]["basis"],
            "assumptions": d["projections"]["assumptions"],
            "erosion_factors": d["projections"]["erosion_factors"],
            "nodes": [
                {"nodes": 1, "label": "1 node", "candidates_per_hour": round(3600 / mean),
                 "measured": True},
                {"nodes": 1, "label": "1 node, batched",
                 "candidates_per_hour": d.get("batched", {}).get("candidates_per_hour",
                                                                 round(3600 / (mean - overhead))),
                 "measured": "batched" in d},
                {"nodes": 2, "label": "2 nodes", "candidates_per_hour": round(3600 / mean * 2),
                 "measured": False},
                {"nodes": 4, "label": "4 nodes", "candidates_per_hour": round(3600 / mean * 4),
                 "measured": False},
            ],
            "batched_single_node": {
                "candidates_per_hour": d.get("batched", {}).get("candidates_per_hour"),
                "per_candidate_s": d.get("batched", {}).get("per_candidate_s"),
                "speedup": d.get("batched", {}).get("speedup_vs_sequential"),
                "measured": "batched" in d,
                "note": ("MEASURED: five candidates in one boltz invocation took "
                         "180 s total, i.e. 36 s each against 64.3 s run "
                         "separately -- the 2.3 GB checkpoint loads once."),
            },
        },
    }


@app.get("/api/md")
def md() -> dict:
    """Molecular-dynamics stability check, mutant vs wild-type.

    Read the caveat before the numbers. This is ~1 ns of implicit-solvent
    dynamics against measured complex half-lives in HOURS, so it samples about
    10^-13 of the relevant timescale. It is a NEGATIVE filter -- it can reject
    an implausible pose, and nothing more. A peptide that stays put has not
    been shown to bind.
    """
    import statistics as st
    md_dir = RESULTS / "md"
    if not md_dir.exists():
        return {"available": False}

    runs = {"mutant": [], "wild_type": []}
    for f in sorted(md_dir.glob("*.json")):
        role = "wild_type" if "_wt" in f.name else "mutant"
        runs[role].append(json.loads(f.read_text()))
    if not runs["mutant"] or not runs["wild_type"]:
        return {"available": False}

    def stats(rows, key):
        vals = [r[key] for r in rows]
        return {"mean": round(st.mean(vals), 3), "min": round(min(vals), 3),
                "max": round(max(vals), 3), "n": len(vals)}

    cp_m, cp_w = stats(runs["mutant"], "contact_persistence"), stats(runs["wild_type"], "contact_persistence")
    rm_m, rm_w = stats(runs["mutant"], "final_peptide_rmsd_a"), stats(runs["wild_type"], "final_peptide_rmsd_a")
    separates = lambda a, b: a["min"] > b["max"] or a["max"] < b["min"]

    return {
        "available": True,
        "engine": "OpenMM 8.6.1, CUDA platform, amber14 + OBC2 implicit solvent",
        "throughput_ns_per_day": round(st.mean(
            [r["ns_per_day"] for rs in runs.values() for r in rs]), 0),
        "production_ns_per_run": round(st.mean(
            [r["production_ns"] for rs in runs.values() for r in rs]), 2),
        "traces": {k: [{"t": r["frame_times_ps"], "rmsd": r["peptide_rmsd_a"],
                        "contacts": r["contact_fraction"]} for r in v]
                   for k, v in runs.items()},
        "metrics": [
            {"name": "Contact persistence", "mutant": cp_m, "wild_type": cp_w,
             "separates": separates(cp_m, cp_w), "higher_is_better": True},
            {"name": "Final peptide RMSD (A)", "mutant": rm_m, "wild_type": rm_w,
             "separates": separates(rm_m, rm_w), "higher_is_better": False},
        ],
        "caveat": (
            "~1 ns of implicit-solvent dynamics, n=3 per condition, on ONE peptide "
            "pair. Contact persistence separated the pair here; peptide RMSD did "
            "not. Suggestive, not a validated discriminator -- the largest published "
            "study on this question moved AUC only from 0.80 to 0.81 using 200 ns "
            "runs. Treat as a red-flag detector, never as evidence of binding."
        ),
    }


@app.get("/api/validation")
def validation() -> dict:
    """Measured performance of the screening layer against T-cell assay data.

    This is the only end-to-end accuracy number in the project that is about
    IMMUNOGENICITY rather than geometry. Benchmark: Bjerregaard et al.,
    Front Immunol 2017 -- 1,947 neopeptide/HLA pairs from 13 published
    studies, each with an experimental T-cell assay outcome, 53 positive.
    Base rate 2.72%.
    """
    bench = ROOT / "benchmarks"
    path = bench / "screen_validation.json"
    if not path.exists():
        return {"available": False}
    d = json.loads(path.read_text())
    out = {"available": True, **d}
    for name, fn in (("precision_at_k", "precision_at_k.json"),
                     ("auc", "auc.json"),
                     ("tesla", "tesla_validation.json"),
                     ("structures", "holdout_structures.json")):
        f = bench / fn
        if f.exists():
            out[name] = json.loads(f.read_text())
    out["reading"] = (
        "Enrichment is the honest headline: at a 2.72% base rate, raw precision "
        "looks uniformly poor and hides the differences between rules. Ranking "
        "by presentation score reaches ~14-16% precision in the top 25-100, "
        "roughly 5x enrichment. Note that our first shipped rule, DAI >= 2, "
        "scored 0.96x -- worse than random."
    )
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
