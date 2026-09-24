"""Differential agretopicity index: direction, damping, and thresholds.

The field uses at least four incompatible formulas under the name "DAI", and
TESLA's "agretopicity" is the reciprocal of everyone else's. A sign error here
silently inverts the filter, so the convention is asserted, not assumed.
"""
import math

import pytest

from neofold.screen import LUKSZA_EPSILON, ScreenResult, damped_dai, triage


def make(mt_nm, wt_nm, presentation=0.5, mut_offset=4):
    return ScreenResult(candidate_id="X-Y-PEP", peptide="PEPTIDEXX",
                        wt_peptide="PEPTIDEYY", allele="HLA-C*08:02",
                        affinity_nm=mt_nm, wt_affinity_nm=wt_nm,
                        presentation_score=presentation,
                        wt_presentation_score=0.1, processing_score=0.5,
                        mut_offset=mut_offset)


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


def test_dai_is_reported_not_gated_on():
    """DAI is an anchor-creation detector, so gating on it selects for anchor
    mutations and DISCARDS TCR-facing ones -- the opposite of what
    immunogenicity needs. A low-DAI peptide that is well presented must still
    reach the shortlist."""
    low_dai_well_presented = make(mt_nm=36.0, wt_nm=34.0)
    tier, _ = triage(low_dai_well_presented)
    assert tier == "presented", "a low DAI must not exclude a presented peptide"


def test_presentation_gate_comes_before_agretopicity():
    """TESLA: prioritising agretopicity WITHOUT accounting for presentation
    performed no better, or worse. A huge DAI must not rescue a non-binder."""
    huge_dai_but_unpresented = make(mt_nm=40000.0, wt_nm=50000.0, presentation=0.9)
    tier, reason = triage(huge_dai_but_unpresented)
    assert tier == "not presented"


def test_tcr_facing_mutation_is_not_penalised_for_low_dai():
    """EGFR L858R is the motivating case: its mutation sits at peptide
    position 6, so a DAI near 1 is expected. We previously excluded it."""
    r = make(mt_nm=36.0, wt_nm=34.0, mut_offset=5)
    assert r.mutation_site == "TCR-facing"
    tier, reason = triage(r)
    assert tier == "presented"
    assert "TCR-facing" in reason and "not evidence against" in reason


def test_anchor_mutation_is_flagged_so_a_large_dai_is_not_over_read():
    """An anchor mutation produces a large DAI by changing MHC binding. The
    reason string must say so, or the number invites the wrong conclusion."""
    r = make(mt_nm=74.0, wt_nm=3656.0, mut_offset=1)      # P2 = anchor
    assert r.mutation_site == "anchor"
    tier, reason = triage(r)
    assert tier == "presented"
    assert "anchor" in reason and "improved MHC binding" in reason


def test_anchor_detection_covers_both_primary_anchors():
    assert make(1.0, 1.0, mut_offset=1).mutation_site == "anchor"     # P2
    assert make(1.0, 1.0, mut_offset=8).mutation_site == "anchor"     # P-omega
    assert make(1.0, 1.0, mut_offset=0).mutation_site == "P1"
    assert make(1.0, 1.0, mut_offset=4).mutation_site == "TCR-facing"


def test_self_peptide_beats_every_other_signal():
    class FakeSelf:
        exact_self = True
        nearest_protein = "MK01_HUMAN (P28482)"
        min_mismatches = 0
    tier, _ = triage(make(mt_nm=10.0, wt_nm=50000.0), FakeSelf())
    assert tier == "self peptide"
