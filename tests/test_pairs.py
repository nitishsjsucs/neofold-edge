"""Regression tests for the mutant/wild-type structure pairs.

These lock in two things that are easy to get wrong and expensive to get wrong
in public: that the structural contact discriminates where it should, and that
it honestly does NOT where it shouldn't.
"""
from pathlib import Path

import pytest

from neofold.contacts import measure_salt_bridge, peptide_sequence

S = Path(__file__).resolve().parent.parent / "results" / "shortlist"

PAIRS = {
    "kras_g12d_9mer":  ("GADGVGKSA", "GAGGVGKSA"),
    "kras_g12d_10mer": ("GADGVGKSAL", "GAGGVGKSAL"),
    "kit_d816v":       ("ICDFGLARV", "ICDFGLARD"),
}

pytestmark = pytest.mark.skipif(
    not (S / "kras_g12d_9mer_mut_model_0.cif").exists(),
    reason="predicted structures not present")


def cif(case: str, role: str) -> Path:
    return S / f"{case}_{role}_model_0.cif"


@pytest.mark.parametrize("case,expected", PAIRS.items())
def test_predicted_peptides_match_intent(case, expected):
    mut, wt = expected
    assert peptide_sequence(cif(case, "mut")) == mut
    assert peptide_sequence(cif(case, "wt")) == wt


def test_mutant_and_wildtype_differ_at_exactly_one_position():
    for case, (mut, wt) in PAIRS.items():
        diffs = [i for i, (a, b) in enumerate(zip(mut, wt)) if a != b]
        assert len(diffs) == 1, f"{case}: expected a single substitution"


@pytest.mark.parametrize("case", ["kras_g12d_9mer", "kras_g12d_10mer"])
def test_kras_contact_discriminates(case):
    """For KRAS G12D the mutation CREATES the p3 aspartate, so the contact
    forms in the mutant and is chemically impossible in the wild-type."""
    m = measure_salt_bridge(cif(case, "mut"), peptide_position=3, mhc_residue_number=156)
    w = measure_salt_bridge(cif(case, "wt"), peptide_position=3, mhc_residue_number=156)
    assert m.peptide_residue.startswith("ASP") and m.is_salt_bridge
    assert w.peptide_residue.startswith("GLY")
    assert not w.possible, "wild-type glycine cannot form this contact"


def test_kit_contact_does_not_discriminate_and_we_must_not_claim_it_does():
    """KIT D816V mutates peptide position 9, not 3. Both peptides carry Asp at
    p3, so this contact forms in BOTH and is uninformative for this variant.

    This test exists to stop the panel from ever presenting it as evidence."""
    m = measure_salt_bridge(cif("kit_d816v", "mut"), peptide_position=3, mhc_residue_number=156)
    w = measure_salt_bridge(cif("kit_d816v", "wt"), peptide_position=3, mhc_residue_number=156)
    assert m.is_salt_bridge and w.is_salt_bridge
    assert abs(m.min_distance_a - w.min_distance_a) < 0.5


def test_confidence_does_not_separate_any_pair():
    """The central measured finding: Boltz confidence gives the wild-type
    essentially the same score as the mutant, in every pair we predicted."""
    import json
    for case in PAIRS:
        conf = {}
        for role in ("mut", "wt"):
            p = S / f"confidence_{case}_{role}_model_0.json"
            conf[role] = json.loads(p.read_text())["iptm"]
        delta = abs(conf["mut"] - conf["wt"])
        assert delta < 0.02, (
            f"{case}: ipTM delta {delta:.4f}. If this ever grows, the claim that "
            f"confidence does not discriminate needs revisiting.")
