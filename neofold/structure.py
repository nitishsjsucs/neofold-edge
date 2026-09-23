"""Boltz-2 structure prediction: input construction and invocation.

Runs on the Nano. The install quirks this depends on are documented in
BUILD-GUIDE.md; the ones that matter here are:

  * `--num_workers 0` is MANDATORY. The default multiprocess dataloader
    deadlocks silently on this ARM64 setup -- 0% GPU, no error, forever.
  * Triton needs Python headers on PATH via CPATH (no sudo available).
  * `msa: empty` per chain is what makes offline operation possible.
"""
from __future__ import annotations

import json
import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

# Reference chains for a class I peptide-MHC complex. The peptide is chain C.
HLA_CHAIN, B2M_CHAIN, PEPTIDE_CHAIN = "A", "B", "C"

B2M_MATURE = (
    "IQRTPKIQVYSRHPAENGKSNFLNCYVSGFHPSDIEVDLLKNGERIEKVEHSDLSFSKDW"
    "SFYLLYYTEFTPTEKDEYACRVNHVTLSQPKIVKWDRDM"
)

# IMGT/HLA ectodomains, mature residues 1-275 (signal peptide removed,
# transmembrane and cytoplasmic tails removed) -- the construct crystallographers
# use, and the one that matches PDB depositions chain-for-chain.
HLA_ECTODOMAIN = {
    # HLA:HLA00446 C*08:02:01:01 -- the KRAS G12D case, ground truth PDB 6ULN
    "HLA-C*08:02": (
        "CSHSMRYFYTAVSRPGRGEPRFIAVGYVDDTQFVQFDSDAASPRGEPRAPWVEQEGPEYWDRETQKYKRQAQTDRVSLRNLRGYYNQSEA"
        "GSHTLQRMYGCDLGPDGRLLRGYNQFAYDGKDYIALNEDLRSWTAADKAAQITQRKWEAAREAEQRRAYLEGTCVEWLRRYLENGKKTLQ"
        "RAEHPKTHVTHHPVSDHEATLRCWALGFYPAEITLTWQRDGEDQTQDTELVETRPAGDGTFQKWAAVVVPSGEEQRYTCHVQHEGLPEPLTLRWG"
    ),
    # HLA:HLA00005 A*02:01:01:01
    "HLA-A*02:01": (
        "GSHSMRYFFTSVSRPGRGEPRFIAVGYVDDTQFVRFDSDAASQRMEPRAPWIEQEGPEYWDGETRKVKAHSQTHRVDLGTLRGYYNQSEA"
        "GSHTVQRMYGCDVGSDWRFLRGYHQYAYDGKDYIALKEDLRSWTAADMAAQTTKHKWEAAHVAEQLRAYLEGTCVEWLRRYLENGKETLQ"
        "RTDAPKTHMTHHAVSDHEATLRCWALSFYPAEITLTWQRDGEDQTQDTELVETRPAGDGTFQKWAAVVVPSGQEQRYTCHVQHEGLPKPLTLRWE"
    ),
}


@dataclass
class PredictionJob:
    name: str
    peptide: str
    allele: str
    msa_hla: str | None = None      # path to a cached MSA csv/a3m, or None
    msa_b2m: str | None = None
    include_b2m: bool = True
    gdomain_only: bool = False      # crop the heavy chain to alpha1+alpha2 (1-180)

    def yaml(self) -> str:
        heavy = HLA_ECTODOMAIN.get(self.allele)
        if heavy is None:
            raise KeyError(
                f"no stored ectodomain for {self.allele}; add it from IMGT/HLA "
                f"(known: {sorted(HLA_ECTODOMAIN)})")
        if self.gdomain_only:
            heavy = heavy[:180]

        def block(cid: str, seq: str, msa: str | None) -> str:
            # An explicit `msa:` key is required for offline operation. Omitting
            # it makes Boltz want the MSA server; `empty` is single-sequence mode.
            return (f"  - protein:\n"
                    f"      id: {cid}\n"
                    f"      sequence: {seq}\n"
                    f"      msa: {msa or 'empty'}\n")

        out = "version: 1\nsequences:\n"
        out += block(HLA_CHAIN, heavy, self.msa_hla)
        if self.include_b2m and not self.gdomain_only:
            out += block(B2M_CHAIN, B2M_MATURE, self.msa_b2m)
        # A 9-mer has no meaningful MSA; always single-sequence.
        out += block(PEPTIDE_CHAIN, self.peptide, None)
        return out


@dataclass
class PredictionResult:
    name: str
    cif_path: Path
    confidence: dict
    seed: int
    wall_seconds: float


def boltz_env() -> dict:
    """Environment a Boltz run needs on the Nano."""
    env = dict(os.environ)
    home = Path.home()
    env["PATH"] = f"/usr/local/cuda/bin:{env.get('PATH','')}"
    # Triton compiles a CUDA shim at runtime and needs Python.h. We cannot
    # apt-install python3.12-dev (sudo needs a password), so the headers are
    # unpacked into $HOME and exposed here.
    cpath = [str(home / "pylocal/usr/include/python3.12"),
             str(home / "pylocal/usr/include")]
    if env.get("CPATH"):
        cpath.append(env["CPATH"])
    env["CPATH"] = ":".join(cpath)
    return env


def predict(
    job: PredictionJob,
    out_dir: Path,
    seed: int = 0,
    recycling_steps: int = 3,
    diffusion_samples: int = 1,
    sampling_steps: int = 200,
    boltz_bin: str = "boltz",
) -> PredictionResult:
    """Run one Boltz-2 prediction and return the parsed result."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    yaml_path = out_dir / f"{job.name}.yaml"
    yaml_path.write_text(job.yaml())

    cmd = [
        boltz_bin, "predict", str(yaml_path),
        "--out_dir", str(out_dir),
        "--accelerator", "gpu",
        "--num_workers", "0",          # MANDATORY -- see module docstring
        "--recycling_steps", str(recycling_steps),
        "--diffusion_samples", str(diffusion_samples),
        "--sampling_steps", str(sampling_steps),
        "--seed", str(seed),
        "--output_format", "mmcif",
        "--override",
    ]
    t0 = time.perf_counter()
    proc = subprocess.run(cmd, env=boltz_env(), capture_output=True, text=True)
    wall = time.perf_counter() - t0
    if proc.returncode != 0:
        tail = "\n".join(proc.stdout.splitlines()[-15:])
        raise RuntimeError(f"boltz failed ({proc.returncode}):\n{tail}")

    cifs = sorted(out_dir.glob(f"**/{job.name}_model_0.cif"))
    if not cifs:
        raise FileNotFoundError(f"no cif produced for {job.name} under {out_dir}")
    conf_files = sorted(out_dir.glob(f"**/confidence_{job.name}_model_0.json"))
    confidence = json.loads(conf_files[0].read_text()) if conf_files else {}

    return PredictionResult(name=job.name, cif_path=cifs[0], confidence=confidence,
                            seed=seed, wall_seconds=wall)
