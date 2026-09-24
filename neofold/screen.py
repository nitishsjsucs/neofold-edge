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

# Percentile-rank bands, the NetMHCpan convention and now the field default.
# Ranks are preferred to raw nM because allele-specific affinity distributions
# differ: 500 nM is a very different thing on HLA-A*02:01 than on HLA-C*08:02.
STRONG_RANK = 0.5
WEAK_RANK = 2.0


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
    affinity_percentile: float = float("nan")
    wt_affinity_percentile: float = float("nan")

    @property
    def dai(self) -> float:
        """Differential agretopicity index (Łuksza-damped).

        How much better the mutant binds than its wild-type counterpart at the
        same register. See `damped_dai` for the direction convention and why
        the damping matters.
        """
        return damped_dai(self.wt_affinity_nm, self.affinity_nm)

    @property
    def raw_fold_change(self) -> float:
        """Undamped WT/MT ratio. Reported for transparency; ranking uses `dai`."""
        if self.affinity_nm <= 0:
            return float("inf")
        return self.wt_affinity_nm / self.affinity_nm

    @property
    def agretopicity(self) -> float:
        """TESLA's convention: MT/WT, so LOWER is better. The reciprocal of DAI."""
        d = self.dai
        return float("inf") if d == 0 else 1.0 / d

    @property
    def binder_class(self) -> str:
        """Band by PERCENTILE RANK where available, which is the convention the
        field has moved to: raw nM is not comparable across alleles, because
        different alleles have systematically different affinity distributions.
        Falls back to nM bands when a rank is unavailable."""
        pct = self.affinity_percentile
        if pct == pct:                       # not NaN
            if pct < STRONG_RANK:
                return "strong"
            if pct < WEAK_RANK:
                return "weak"
            return "non-binder"
        if self.affinity_nm <= STRONG_BINDER_NM:
            return "strong"
        if self.affinity_nm <= WEAK_BINDER_NM:
            return "weak"
        return "non-binder"

    @property
    def wt_binder_class(self) -> str:
        """The wild-type's own band. Reporting this stops us claiming the
        germline peptide is 'invisible' when it is in fact a weak binder."""
        pct = self.wt_affinity_percentile
        if pct == pct:
            return "strong" if pct < STRONG_RANK else "weak" if pct < WEAK_RANK else "non-binder"
        return ("strong" if self.wt_affinity_nm <= STRONG_BINDER_NM
                else "weak" if self.wt_affinity_nm <= WEAK_BINDER_NM else "non-binder")

    def as_dict(self) -> dict:
        return {
            "candidate_id": self.candidate_id,
            "peptide": self.peptide,
            "wt_peptide": self.wt_peptide,
            "allele": self.allele,
            "affinity_nm": round(self.affinity_nm, 2),
            "wt_affinity_nm": round(self.wt_affinity_nm, 2),
            "dai": round(self.dai, 1),
            "raw_fold_change": round(self.raw_fold_change, 1),
            "agretopicity": round(self.agretopicity, 4),
            "presentation_score": round(self.presentation_score, 4),
            "wt_presentation_score": round(self.wt_presentation_score, 4),
            "processing_score": round(self.processing_score, 4),
            "affinity_percentile": (None if self.affinity_percentile != self.affinity_percentile
                                    else round(self.affinity_percentile, 3)),
            "wt_affinity_percentile": (None if self.wt_affinity_percentile != self.wt_affinity_percentile
                                       else round(self.wt_affinity_percentile, 3)),
            "binder_class": self.binder_class,
            "wt_binder_class": self.wt_binder_class,
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
                affinity_percentile=m.get("affinity_percentile", float("nan")),
                wt_affinity_percentile=(w.get("affinity_percentile", float("nan"))
                                        if w else float("nan")),
            ))
        results.sort(key=lambda r: r.presentation_score, reverse=True)
        return results

    def _predict(self, peptides: list[str], allele: str) -> dict[str, dict]:
        # MHCflurry class I supports 8-15mers; anything else would raise.
        usable = sorted({p for p in peptides if 8 <= len(p) <= 15})
        if not usable:
            return {}
        df = self.predictor.predict(
            peptides=usable, alleles={"sample": [allele]}, verbose=0,
            include_affinity_percentile=True)
        return {
            row.peptide: {
                "affinity": float(row.affinity),
                "affinity_percentile": float(getattr(row, "affinity_percentile", float("nan"))),
                "presentation_score": float(row.presentation_score),
                "processing_score": float(row.processing_score),
            }
            for row in df.itertuples()
        }


def top_k(results: list[ScreenResult], k: int) -> list[ScreenResult]:
    """The survivors that earn expensive structure prediction."""
    return results[:k]


# --------------------------------------------------------------------------
# Triage rule, structured after Wells et al., Cell 2020 (TESLA).
#
# TESLA tested 608 peptides across 25 pipelines and found only 37 (6%)
# immunogenic. Two findings shape this rule:
#
#   1. PRESENTATION FIRST. "Submissions that explicitly prioritized peptide
#      foreignness, agretopicity, or both, WITHOUT accounting for presentation,
#      either had no difference in performance or performed worse." So the
#      mutant-vs-wildtype differential is applied only to peptides that already
#      look presentable -- never as a standalone gate.
#   2. RECOGNITION IS A DISJUNCTION. TESLA defines recognition as "the presence
#      of either low agretopicity OR high foreignness" (OR, not AND). A highly
#      foreign peptide qualifies even with unremarkable agretopicity.
#
# THRESHOLD PROVENANCE, because ours were previously invented:
#   affinity <= 500 nM   conventional weak-binder band (pVACtools default).
#                        NOTE: TESLA's 34 nM is on MEASURED affinity from a
#                        competitive binding assay, not a predicted value, so
#                        it cannot be transplanted onto MHCflurry output.
#   DAI >= 10            Rech et al., Cancer Immunol Res 2018 -- the first
#                        percentile of the empirical DAI distribution. Exactly
#                        equivalent to TESLA's "agretopicity < 0.1", which is
#                        the reciprocal convention.
#
# We previously used DAI >= 2. That was arbitrary and close to the null: Rech
# measured the MEDIAN DAI of ordinary neoantigens as 1.183, so a 2x cut sits
# near the middle of the null distribution and enriches for almost nothing.
MIN_PRESENTATION = 0.10
MIN_DAI = 10.0

# Łuksza et al., Nature 2017: the wild-type peptide is usually a weak binder,
# which is exactly the regime where predictors are least reliable, so a small
# denominator can inflate the ratio arbitrarily. Damping with this pseudocount
# (1/3687 nM, "the outer range of predictability for the assays upon which
# NetMHC is trained") is standard and adopted verbatim by antigen.garnish.
LUKSZA_EPSILON = 0.0003


def damped_dai(wt_affinity_nm: float, mt_affinity_nm: float) -> float:
    """Differential agretopicity index, Łuksza-damped.

    DIRECTION CONVENTION, asserted in tests because the field is inconsistent
    and a sign error here silently inverts the filter:

        DAI = affinity_WT / affinity_MT      higher = mutation improved binding

    This matches Rech 2018 and the pVACtools source. Note that TESLA's
    "agretopicity" is the RECIPROCAL (MT/WT), so TESLA's `agretopicity < 0.1`
    and `DAI > 10` are the same filter. The pVACtools *documentation* states
    the direction backwards; its code does not.
    """
    if mt_affinity_nm <= 0:
        return float("inf")
    raw = wt_affinity_nm / mt_affinity_nm
    return raw / (1.0 + LUKSZA_EPSILON * wt_affinity_nm)


def triage(result: ScreenResult, self_match=None) -> tuple[str, str]:
    """Classify a candidate and say why, in plain language.

    Explicit rules rather than a blended score, so every row in the UI explains
    itself and a reviewer can disagree with a named threshold rather than a
    black box.
    """
    # Step 0. A peptide that IS a normal human peptide is not a target at all,
    # however well it binds -- T-cells against it face central tolerance.
    if self_match is not None and self_match.exact_self:
        return ("self peptide", (
            f"disqualified: this exact sequence occurs in the normal human "
            f"proteome ({self_match.nearest_protein}), so it is not a "
            f"tumour-specific target regardless of predicted binding"))

    # Step 1. Presentation gate. Everything downstream is conditional on this,
    # which is the TESLA finding.
    presentable = (result.presentation_score >= MIN_PRESENTATION
                   and result.affinity_nm <= WEAK_BINDER_NM)
    if not presentable:
        return ("not presented", (
            f"predicted affinity {result.affinity_nm:.0f} nM and presentation "
            f"score {result.presentation_score:.2f} — below the bar for being "
            f"displayed at all, so downstream evidence does not apply"))

    # Step 2. Recognition.
    #
    # TESLA's recognition rule is a disjunction: "low agretopicity OR high
    # foreignness". We implement ONLY the agretopicity half, deliberately.
    #
    # TESLA's "foreignness" is similarity to known pathogen epitopes -- the
    # Łuksza R term, a BLOSUM62 alignment score against ~2,500 IEDB epitopes.
    # Our self-similarity search measures something DIFFERENT: distance from
    # the human proteome (closer to Richman et al., Cell Syst 2019
    # "dissimilarity"). Substituting one for the other would be wrong, and
    # when we tried it the disjunction admitted candidates with DAI ~0.9 that
    # the differential had correctly rejected. So dissimilarity-to-self is
    # reported as a FLAG and never qualifies a candidate on its own.
    dai = result.dai
    if dai >= MIN_DAI:
        note = ""
        if self_match is not None and self_match.min_mismatches is not None:
            note = (" and has no human peptide within one substitution"
                    if self_match.min_mismatches > 1
                    else f" (note: resembles {self_match.nearest_protein}, "
                         f"one substitution away)")
        return ("investigate", (
            f"presented ({result.affinity_nm:.0f} nM) and binds {dai:.0f}x better "
            f"than the wild-type peptide, above the DAI ≥ {MIN_DAI:.0f} bar "
            f"(Rech 2018){note}"))

    return ("presented, not distinguished", (
        f"presented ({result.affinity_nm:.0f} nM) but the wild-type peptide binds "
        f"comparably ({result.wt_affinity_nm:.0f} nM, DAI {dai:.1f}) — below the "
        f"DAI ≥ {MIN_DAI:.0f} bar, so healthy cells are predicted to present it too"))


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
