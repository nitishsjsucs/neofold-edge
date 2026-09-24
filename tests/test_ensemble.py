"""The ensemble-spread experiment: a pre-registered NEGATIVE result.

We proposed using agreement between Boltz diffusion samples as a confidence
signal. Reading the architecture suggested it could not work -- the trunk runs
once per input and only diffusion noise varies between samples -- so we ran a
2x2 allele swap to settle it by measurement rather than by argument.

These tests pin the negative result in place. If someone later revives the
feature, these fail and force them to re-derive it.
"""
import json
from pathlib import Path

import pytest

SUMMARY = Path(__file__).resolve().parent.parent / "results" / "ensemble" / "summary.json"
pytestmark = pytest.mark.skipif(not SUMMARY.exists(), reason="ensemble results not present")


def rows():
    return json.loads(SUMMARY.read_text())


def test_design_is_balanced_two_by_two():
    r = rows()
    assert len(r) == 4
    assert sum(x["kind"] == "cognate" for x in r) == 2
    assert sum(x["kind"] == "swapped" for x in r) == 2


def test_ensemble_spread_does_not_separate_cognate_from_swapped():
    r = rows()
    cog = [x["spread"] for x in r if x["kind"] == "cognate"]
    swp = [x["spread"] for x in r if x["kind"] == "swapped"]
    overlap = not (min(cog) > max(swp) or max(cog) < min(swp))
    assert overlap, (
        "Ensemble spread now separates the groups. That contradicts the recorded "
        "negative result -- re-run the experiment before claiming the feature works.")


def test_the_tightest_ensemble_is_a_wrong_pairing():
    """The sharpest form of the negative result: ranking by self-consistency
    puts a non-cognate peptide/allele pair FIRST. Spread is not merely
    uninformative here, it is actively misleading."""
    best = min(rows(), key=lambda x: x["spread"])
    assert best["kind"] == "swapped", (
        f"expected the tightest ensemble to be a swapped pairing, got {best['label']}")


def test_all_four_complexes_score_confidently_regardless():
    """Every pairing, correct or not, comes back with high ipTM -- consistent
    with the wrong-allele control measured earlier."""
    for x in rows():
        assert x["iptm_mean"] > 0.97, f"{x['label']} scored {x['iptm_mean']}"
