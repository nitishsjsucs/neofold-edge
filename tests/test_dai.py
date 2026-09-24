"""Differential agretopicity index: direction, damping, and thresholds.

The field uses at least four incompatible formulas under the name "DAI", and
TESLA's "agretopicity" is the reciprocal of everyone else's. A sign error here
silently inverts the filter, so the convention is asserted, not assumed.
"""
import math

import pytest

from neofold.screen import (LUKSZA_EPSILON, MIN_DAI, ScreenResult, damped_dai,
                            triage)


def make(mt_nm, wt_nm, presentation=0.5):
    return ScreenResult(candidate_id="X-Y-PEP", peptide="PEPTIDEXX",
                        wt_peptide="PEPTIDEYY", allele="HLA-C*08:02",
                        affinity_nm=mt_nm, wt_affinity_nm=wt_nm,
                        presentation_score=presentation,
                        wt_presentation_score=0.1, processing_score=0.5)


def test_direction_is_wt_over_mt():
    """Rech 2018 and the pVACtools SOURCE use WT/MT: higher = mutation
    improved binding. (The pVACtools docs state this backwards.)"""
    improved = damped_dai(wt_affinity_nm=5000.0, mt_affinity_nm=50.0)
    worsened = damped_dai(wt_affinity_nm=50.0, mt_affinity_nm=5000.0)
    assert improved > 1.0
    assert worsened < 1.0


def test_agretopicity_is_the_reciprocal_of_dai():
    """TESLA's convention. agretopicity < 0.1 must equal DAI > 10."""
    r = make(mt_nm=50.0, wt_nm=5000.0)
    assert r.agretopicity == pytest.approx(1.0 / r.dai, rel=1e-6)
    assert (r.dai >= 10.0) == (r.agretopicity <= 0.1)


def test_damping_suppresses_inflation_from_weak_wild_types():
    """A wild-type predicted at 30,000 nM is in the regime where predictors are
    least reliable; the raw ratio would be wildly inflated."""
    raw = 30000.0 / 100.0
    damped = damped_dai(30000.0, 100.0)
    assert damped < raw
    assert damped == pytest.approx(raw / (1 + LUKSZA_EPSILON * 30000.0), rel=1e-9)


def test_damping_barely_affects_reliable_wild_types():
    """A wild-type at 200 nM is well within the trained range, so the
    correction should be small."""
    raw, damped = 200.0 / 20.0, damped_dai(200.0, 20.0)
    assert damped == pytest.approx(raw, rel=0.07)


def test_threshold_is_ten_not_two():
    """Rech 2018's first percentile. We previously used 2, which sits near the
    null: Rech measured the MEDIAN DAI of ordinary neoantigens as 1.183."""
    assert MIN_DAI == 10.0


def test_presentation_gate_comes_before_agretopicity():
    """TESLA: prioritising agretopicity WITHOUT accounting for presentation
    performed no better, or worse. A huge DAI must not rescue a non-binder."""
    huge_dai_but_unpresented = make(mt_nm=40000.0, wt_nm=50000.0, presentation=0.9)
    tier, reason = triage(huge_dai_but_unpresented)
    assert tier == "not presented"


def test_comparable_wild_type_binding_is_not_qualified():
    """The EGFR L858R case: binds well, but so does its wild-type."""
    tier, reason = triage(make(mt_nm=36.0, wt_nm=34.0))
    assert tier == "presented, not distinguished"
    assert "binds comparably" in reason


def test_strong_differential_qualifies():
    tier, reason = triage(make(mt_nm=74.0, wt_nm=3656.0))
    assert tier == "investigate"
    assert "DAI" in reason and "Rech" in reason


def test_self_peptide_beats_every_other_signal():
    class FakeSelf:
        exact_self = True
        nearest_protein = "MK01_HUMAN (P28482)"
        min_mismatches = 0
    tier, _ = triage(make(mt_nm=10.0, wt_nm=50000.0), FakeSelf())
    assert tier == "self peptide"
