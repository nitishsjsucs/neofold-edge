"""Structural accuracy and ensemble-consistency measurement.

Two jobs, both answering "how much should we trust this pose?" without relying
on the model's own confidence -- which we measured to be unreliable here
(a deliberately wrong peptide/allele pairing scored ipTM 0.988 vs 0.987).

  1. `peptide_rmsd_vs_reference` -- accuracy against an experimental structure.
     This is the only measurement in the project that is ground truth.
  2. `ensemble_spread` -- reproducibility across random seeds. Cheap, needs no
     reference, but measures self-consistency, NOT correctness. A model can be
     consistently wrong.

Requires gemmi.
"""
from __future__ import annotations

import itertools
import math
from dataclasses import dataclass
from pathlib import Path

import gemmi

BACKBONE = ("N", "CA", "C", "O")


def _load(path: str | Path) -> gemmi.Structure:
    st = gemmi.read_structure(str(path))
    st.setup_entities()
    st.remove_ligands_and_waters()
    st.remove_hydrogens()
    return st


def _chain(st: gemmi.Structure, chain_id: str) -> gemmi.Chain:
    for ch in st[0]:
        if ch.name == chain_id:
            return ch
    raise KeyError(f"chain {chain_id!r} not found; have {[c.name for c in st[0]]}")


def _atoms(chain: gemmi.Chain, names: tuple[str, ...]) -> list[gemmi.Position]:
    out = []
    for res in chain:
        for name in names:
            atom = res.find_atom(name, "*")
            if atom:
                out.append(atom.pos)
    return out


def _rmsd(a: list[gemmi.Position], b: list[gemmi.Position]) -> tuple[float, int]:
    n = min(len(a), len(b))
    if n == 0:
        return float("nan"), 0
    total = sum(a[i].dist(b[i]) ** 2 for i in range(n))
    return math.sqrt(total / n), n


@dataclass
class AccuracyReport:
    mhc_rmsd: float
    mhc_atoms: int
    peptide_backbone_rmsd: float
    peptide_ca_rmsd: float
    per_residue_ca: list[float]

    def as_dict(self) -> dict:
        return {
            "mhc_superposition_ca_rmsd_a": round(self.mhc_rmsd, 3),
            "mhc_atoms_aligned": self.mhc_atoms,
            "peptide_backbone_rmsd_a": round(self.peptide_backbone_rmsd, 3),
            "peptide_ca_rmsd_a": round(self.peptide_ca_rmsd, 3),
            "per_residue_ca_deviation_a": [round(v, 2) for v in self.per_residue_ca],
        }


def peptide_rmsd_vs_reference(
    reference_cif: str | Path,
    predicted_cif: str | Path,
    ref_mhc: str = "A", ref_peptide: str = "C",
    pred_mhc: str = "A", pred_peptide: str = "C",
) -> AccuracyReport:
    """Superpose on the MHC heavy chain, then measure where the peptide landed.

    Superposing on the MHC rather than on everything is the point: it asks
    "given the groove, did we put the peptide in the right place?", which is
    the question that matters and the convention in the pMHC literature.
    """
    ref, pred = _load(reference_cif), _load(predicted_cif)

    superposition = gemmi.calculate_superposition(
        _chain(ref, ref_mhc).get_polymer(),
        _chain(pred, pred_mhc).get_polymer(),
        gemmi.PolymerType.PeptideL,
        gemmi.SupSelect.CaP,
    )
    pred[0].transform_pos_and_adp(superposition.transform)

    ref_pep, pred_pep = _chain(ref, ref_peptide), _chain(pred, pred_peptide)
    bb, _ = _rmsd(_atoms(ref_pep, BACKBONE), _atoms(pred_pep, BACKBONE))
    ca, _ = _rmsd(_atoms(ref_pep, ("CA",)), _atoms(pred_pep, ("CA",)))

    ref_ca, pred_ca = _atoms(ref_pep, ("CA",)), _atoms(pred_pep, ("CA",))
    per_res = [ref_ca[i].dist(pred_ca[i]) for i in range(min(len(ref_ca), len(pred_ca)))]

    return AccuracyReport(
        mhc_rmsd=superposition.rmsd, mhc_atoms=superposition.count,
        peptide_backbone_rmsd=bb, peptide_ca_rmsd=ca, per_residue_ca=per_res,
    )


@dataclass
class EnsembleReport:
    n_models: int
    mean_pairwise_peptide_rmsd: float
    max_pairwise_peptide_rmsd: float
    per_residue_spread: list[float]

    @property
    def consistency(self) -> str:
        """Bucket the spread into something a UI can show.

        Thresholds are conventions for judging whether independent samples
        agree on a 9-mer backbone, NOT validated decision rules.
        """
        if math.isnan(self.mean_pairwise_peptide_rmsd):
            return "unknown"
        if self.mean_pairwise_peptide_rmsd < 1.0:
            return "high"
        if self.mean_pairwise_peptide_rmsd < 2.5:
            return "medium"
        return "low"

    def as_dict(self) -> dict:
        return {
            "n_models": self.n_models,
            "mean_pairwise_peptide_rmsd_a": round(self.mean_pairwise_peptide_rmsd, 3),
            "max_pairwise_peptide_rmsd_a": round(self.max_pairwise_peptide_rmsd, 3),
            "per_residue_spread_a": [round(v, 2) for v in self.per_residue_spread],
            "consistency": self.consistency,
            "caveat": ("measures agreement between independent samples, not "
                       "correctness -- a model can be consistently wrong"),
        }


def ensemble_spread(
    cif_paths: list[str | Path],
    mhc_chain: str = "A",
    peptide_chain: str = "C",
) -> EnsembleReport:
    """How much do independent predictions of the same complex disagree?

    Each model is superposed onto the first on its MHC chain, so the spread
    reported is peptide placement disagreement, not whole-complex drift.
    """
    if len(cif_paths) < 2:
        raise ValueError("ensemble spread needs at least 2 models")

    structures = [_load(p) for p in cif_paths]
    anchor = structures[0]
    for st in structures[1:]:
        sup = gemmi.calculate_superposition(
            _chain(anchor, mhc_chain).get_polymer(),
            _chain(st, mhc_chain).get_polymer(),
            gemmi.PolymerType.PeptideL, gemmi.SupSelect.CaP)
        st[0].transform_pos_and_adp(sup.transform)

    peptides = [_atoms(_chain(st, peptide_chain), BACKBONE) for st in structures]
    pairwise = [_rmsd(a, b)[0] for a, b in itertools.combinations(peptides, 2)]

    ca_sets = [_atoms(_chain(st, peptide_chain), ("CA",)) for st in structures]
    n_res = min(len(s) for s in ca_sets)
    per_residue = []
    for i in range(n_res):
        pts = [s[i] for s in ca_sets]
        cx = sum(p.x for p in pts) / len(pts)
        cy = sum(p.y for p in pts) / len(pts)
        cz = sum(p.z for p in pts) / len(pts)
        centroid = gemmi.Position(cx, cy, cz)
        per_residue.append(
            math.sqrt(sum(p.dist(centroid) ** 2 for p in pts) / len(pts)))

    return EnsembleReport(
        n_models=len(structures),
        mean_pairwise_peptide_rmsd=sum(pairwise) / len(pairwise),
        max_pairwise_peptide_rmsd=max(pairwise),
        per_residue_spread=per_residue,
    )
