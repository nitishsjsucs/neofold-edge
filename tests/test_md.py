"""Tests for the molecular-dynamics stability check.

The most important test here is the one asserting what MD does NOT show.
"""
import json
from pathlib import Path

import pytest

MD = Path(__file__).resolve().parent.parent / "results" / "md"
pytestmark = pytest.mark.skipif(not MD.exists() or not list(MD.glob("*.json")),
                                reason="MD results not present")


def load(role: str) -> list[dict]:
    return [json.loads(f.read_text()) for f in sorted(MD.glob("*.json"))
            if (("_wt" in f.name) == (role == "wild_type"))]


def test_three_replicates_per_condition():
    assert len(load("mutant")) == 3
    assert len(load("wild_type")) == 3


def test_no_run_is_outright_rejected():
    """MD is a negative filter, and here it rejects nothing. Neither peptide
    flies out of the groove, so MD cannot be used to call one a non-binder."""
    for role in ("mutant", "wild_type"):
        for r in load(role):
            assert not r["verdict"].startswith("REJECTED"), \
                f"{role} unexpectedly rejected: {r['verdict']}"


def test_only_wild_type_runs_are_ever_flagged_unstable():
    """1 of 3 wild-type replicates drifted enough to be flagged; 0 of 3 mutant.

    Directionally consistent with the contact-persistence separation, but a
    1-in-3 flag rate is not a discriminator and must not be presented as one.
    """
    flagged = {role: sum(r["verdict"].startswith("UNSTABLE") for r in load(role))
               for role in ("mutant", "wild_type")}
    assert flagged["mutant"] == 0
    assert flagged["wild_type"] >= 1


def test_contact_persistence_separates_the_pair():
    m = [r["contact_persistence"] for r in load("mutant")]
    w = [r["contact_persistence"] for r in load("wild_type")]
    assert min(m) > max(w), (
        f"ranges overlap: mutant {min(m)}-{max(m)} vs wild-type {min(w)}-{max(w)}. "
        f"If this ever fails, the UI claim that contact persistence separates "
        f"this pair must be withdrawn.")


def test_peptide_rmsd_does_NOT_separate_the_pair():
    """Guards against quietly promoting RMSD to a discriminator later."""
    m = [r["final_peptide_rmsd_a"] for r in load("mutant")]
    w = [r["final_peptide_rmsd_a"] for r in load("wild_type")]
    overlap = not (min(m) > max(w) or max(m) < min(w))
    assert overlap, "RMSD ranges no longer overlap -- re-check before claiming it separates"


def test_rmsd_is_superposition_corrected():
    """Without superposing on the MHC, rigid-body tumbling inflates peptide
    RMSD to ~7 A even for a crystallographically-validated pose. Values in
    that range mean the Kabsch alignment regressed."""
    for role in ("mutant", "wild_type"):
        for r in load(role):
            assert r["max_peptide_rmsd_a"] < 5.0, (
                f"{role} max RMSD {r['max_peptide_rmsd_a']} A looks like "
                f"uncorrected rigid-body drift")
