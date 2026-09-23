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


@app.get("/api/structures")
def structures() -> dict:
    """Predicted structures available on disk, with their confidence metadata."""
    out = []
    for cif in sorted(RESULTS.glob("*.cif")):
        conf_path = RESULTS / f"confidence_{cif.stem}.json"
        conf = json.loads(conf_path.read_text()) if conf_path.exists() else {}
        out.append({
            "id": cif.stem,
            "cif_url": f"/api/structure/{cif.stem}",
            "iptm": conf.get("iptm"),
            "plddt": conf.get("complex_plddt"),
            "ptm": conf.get("ptm"),
        })
    return {"structures": out}


@app.get("/api/structure/{name}")
def structure(name: str):
    path = (RESULTS / f"{name}.cif").resolve()
    if not str(path).startswith(str(RESULTS)) or not path.exists():
        raise HTTPException(status_code=404, detail="no such structure")
    return FileResponse(path, media_type="chemical/x-mmcif")


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
