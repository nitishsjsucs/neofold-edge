"""Fast peptide-MHC binding screen (MHCflurry).

This is the layer that actually DISCRIMINATES. We measured that Boltz-2's
structural confidence does not: a deliberately wrong peptide/allele pairing
scored ipTM 0.988 against 0.987 for the correct one. So ranking lives here,
and structure prediction is reserved for explaining the survivors.

Runs on CPU by design, leaving the GPU free for structure prediction.
"""
from __future__ import annotations

import time
from dataclasses import dataclass

from neofold.variants import Candidate

# MHCflurry reports affinity in nM. Lower is stronger. These thresholds are the
# conventional reporting bands in the epitope literature, not decision rules.
STRONG_BINDER_NM = 50.0
WEAK_BINDER_NM = 500.0


@dataclass
class ScreenResult:
    candidate_id: str
    peptide: str
    wt_peptide: str
    allele: str
    affinity_nm: float
    wt_affinity_nm: float
    presentation_score: float
    wt_presentation_score: float
    processing_score: float

    @property
    def fold_change(self) -> float:
        """How much stronger the mutant binds than its wild-type counterpart.

        This is the personalization signal: a large value means the mutation
        created a presentable peptide where the normal protein had none.
        """
        if self.affinity_nm <= 0:
            return float("inf")
        return self.wt_affinity_nm / self.affinity_nm

    @property
    def binder_class(self) -> str:
        if self.affinity_nm <= STRONG_BINDER_NM:
            return "strong"
        if self.affinity_nm <= WEAK_BINDER_NM:
            return "weak"
        return "non-binder"

    def as_dict(self) -> dict:
        return {
            "candidate_id": self.candidate_id,
            "peptide": self.peptide,
            "wt_peptide": self.wt_peptide,
            "allele": self.allele,
            "affinity_nm": round(self.affinity_nm, 2),
            "wt_affinity_nm": round(self.wt_affinity_nm, 2),
            "fold_change": round(self.fold_change, 1),
            "presentation_score": round(self.presentation_score, 4),
            "wt_presentation_score": round(self.wt_presentation_score, 4),
            "processing_score": round(self.processing_score, 4),
            "binder_class": self.binder_class,
        }


class PeptideScreen:
    """Thin wrapper over MHCflurry's presentation predictor.

    Loading the predictor takes a few seconds, so hold one instance for the
    lifetime of the process.
    """

    def __init__(self, predictor=None):
        self._predictor = predictor
        self.load_seconds: float | None = None

    @property
    def predictor(self):
        if self._predictor is None:
            from mhcflurry import Class1PresentationPredictor
            t0 = time.perf_counter()
            self._predictor = Class1PresentationPredictor.load()
            self.load_seconds = time.perf_counter() - t0
        return self._predictor

    @property
    def supported_alleles(self) -> list[str]:
        return list(self.predictor.supported_alleles)

    def supports(self, allele: str) -> bool:
        return allele in set(self.predictor.supported_alleles)

    def score(self, candidates: list[Candidate], allele: str) -> list[ScreenResult]:
        """Score mutant peptides and their wild-type counterparts together.

        Scoring both in one pass is deliberate: the mutant number alone is not
        evidence of anything. The contrast against the wild-type at the same
        register is what makes a candidate tumour-specific.
        """
        if not candidates:
            return []
        if not self.supports(allele):
            raise ValueError(
                f"allele {allele!r} is not supported by this MHCflurry build; "
                f"{len(self.supported_alleles)} alleles available")

        mut_peps = [c.peptide for c in candidates]
        wt_peps = [c.wt_peptide for c in candidates]

        mut_df = self._predict(mut_peps, allele)
        wt_df = self._predict(wt_peps, allele)

        results = []
        for cand in candidates:
            m = mut_df[cand.peptide]
            w = wt_df.get(cand.wt_peptide)
            results.append(ScreenResult(
                candidate_id=cand.candidate_id,
                peptide=cand.peptide,
                wt_peptide=cand.wt_peptide,
                allele=allele,
                affinity_nm=m["affinity"],
                wt_affinity_nm=w["affinity"] if w else float("nan"),
                presentation_score=m["presentation_score"],
                wt_presentation_score=w["presentation_score"] if w else float("nan"),
                processing_score=m["processing_score"],
            ))
        results.sort(key=lambda r: r.presentation_score, reverse=True)
        return results

    def _predict(self, peptides: list[str], allele: str) -> dict[str, dict]:
        # MHCflurry class I supports 8-15mers; anything else would raise.
        usable = sorted({p for p in peptides if 8 <= len(p) <= 15})
        if not usable:
            return {}
        df = self.predictor.predict(
            peptides=usable, alleles={"sample": [allele]}, verbose=0)
        return {
            row.peptide: {
                "affinity": float(row.affinity),
                "presentation_score": float(row.presentation_score),
                "processing_score": float(row.processing_score),
            }
            for row in df.itertuples()
        }


def top_k(results: list[ScreenResult], k: int) -> list[ScreenResult]:
    """The survivors that earn expensive structure prediction."""
    return results[:k]


# A candidate must clear BOTH bars to be worth a researcher's attention:
# it has to be presentable at all, and it has to be more presentable than the
# wild-type peptide the same person's healthy cells already display.
#
# The affinity gate matters independently of presentation score: a peptide can
# score respectably on presentation while its predicted affinity is in the
# thousands of nM, which nobody in the field would call a binder.
MIN_PRESENTATION = 0.10
MIN_FOLD_CHANGE = 2.0


def triage(result: ScreenResult, self_match=None) -> tuple[str, str]:
    """Classify a candidate and say why, in plain language.

    Returns (tier, reason). Kept as explicit rules rather than a blended score
    so that every row in the UI can explain itself, and so a reviewer can
    disagree with a specific threshold rather than a black box.

    `self_match` is an optional SelfMatch from neofold.selfsim. A peptide that
    occurs verbatim in the normal human proteome is disqualified regardless of
    how well it binds: T-cells against it are subject to central tolerance and
    would be autoreactive. This check is applied FIRST because binding
    strength is irrelevant if the peptide is not tumour-specific at all.
    """
    if self_match is not None and self_match.exact_self:
        return ("self peptide", (
            f"disqualified: this exact sequence occurs in the normal human "
            f"proteome ({self_match.nearest_protein}), so it is not a "
            f"tumour-specific target regardless of predicted binding"))

    presentable = (result.presentation_score >= MIN_PRESENTATION
                   and result.affinity_nm <= WEAK_BINDER_NM)
    specific = result.fold_change >= MIN_FOLD_CHANGE

    if presentable and specific:
        return ("investigate", (
            f"predicted presentable ({result.affinity_nm:.0f} nM) and "
            f"{result.fold_change:.0f}x stronger than the wild-type peptide"))
    if presentable and not specific:
        return ("not tumour-specific", (
            f"binds well ({result.affinity_nm:.0f} nM) but the wild-type peptide "
            f"binds comparably ({result.wt_affinity_nm:.0f} nM), so healthy cells "
            f"are predicted to present it too"))
    if specific and not presentable:
        return ("weak presentation", (
            f"{result.fold_change:.0f}x tumour-enriched but weakly presented "
            f"({result.affinity_nm:.0f} nM)"))
    return ("deprioritised",
            f"neither strongly presented nor tumour-enriched ({result.affinity_nm:.0f} nM)")


def rank_for_structure(results: list[ScreenResult], k: int,
                       self_matches: dict | None = None) -> list[ScreenResult]:
    """Pick the candidates that earn a GPU structure prediction.

    Only 'investigate' candidates qualify. Binding strength alone is not
    enough: a peptide whose wild-type counterpart binds just as well is not a
    tumour-specific hypothesis, however good its affinity looks -- and a
    peptide that IS a normal human peptide is not a target at all.
    """
    sm = self_matches or {}
    qualified = [r for r in results
                 if triage(r, sm.get(r.peptide))[0] == "investigate"]
    return qualified[:k]
