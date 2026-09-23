"""Tests for structural validation and contact measurement.

These run against real files: crystal structure 6ULN and a Boltz-2 prediction
produced on the Nano. They are regression tests for numbers quoted in
BUILD-GUIDE.md, so if the analysis code drifts, the documented claims fail.
"""
from pathlib import Path

import pytest

from neofold.contacts import measure_salt_bridge, peptide_sequence
from neofold.validate import peptide_rmsd_vs_reference

RESULTS = Path(__file__).resolve().parent.parent / "results"
CRYSTAL = RESULTS / "reference" / "6ULN.cif"
PREDICTION = RESULTS / "kras_g12d_c0802_model_0.cif"

pytestmark = pytest.mark.skipif(
    not (CRYSTAL.exists() and PREDICTION.exists()),
    reason="reference structures not present")


def test_both_structures_contain_the_kras_neoepitope():
    assert peptide_sequence(CRYSTAL) == "GADGVGKSA"
    assert peptide_sequence(PREDICTION) == "GADGVGKSA"


def test_predicted_peptide_is_sub_angstrom_against_crystal():
    """The headline accuracy claim in BUILD-GUIDE section 6A."""
    report = peptide_rmsd_vs_reference(CRYSTAL, PREDICTION)
    assert report.peptide_backbone_rmsd < 1.0
    assert report.peptide_ca_rmsd < 1.0
    # Guard the specific documented value so drift is caught, not just "small".
    assert report.peptide_backbone_rmsd == pytest.approx(0.56, abs=0.05)
    assert report.mhc_atoms == 273


def test_peptide_termini_are_the_least_certain_positions():
    """Expected physical pattern: anchored middle, floppier ends."""
    dev = peptide_rmsd_vs_reference(CRYSTAL, PREDICTION).per_residue_ca
    assert len(dev) == 9
    middle = sum(dev[2:7]) / 5
    ends = (dev[0] + dev[-1]) / 2
    assert ends > middle


def test_p3_asp_arg156_salt_bridge_present_in_crystal():
    """Pre-registered contact: HLA-C*08:02 prefers Asp at p3, and 6ULN shows
    it salt-bridging Arg156. G12D is what puts Asp there."""
    m = measure_salt_bridge(CRYSTAL, peptide_position=3, mhc_residue_number=156)
    assert m.peptide_residue == "ASP3"
    assert m.mhc_residue == "ARG156"
    assert m.is_salt_bridge
    assert m.min_distance_a < 4.0


def test_prediction_reproduces_the_salt_bridge():
    m = measure_salt_bridge(PREDICTION, peptide_position=3, mhc_residue_number=156)
    assert m.is_salt_bridge
    crystal = measure_salt_bridge(CRYSTAL, peptide_position=3, mhc_residue_number=156)
    # Agreeing on a named contact to within half an Angstrom is a far stronger
    # statement than agreeing on a self-reported confidence score.
    assert abs(m.min_distance_a - crystal.min_distance_a) < 0.5


def test_glycine_makes_the_contact_chemically_impossible():
    """The wild-type residue at p3 is Gly. The point is not that the contact is
    weak -- it is that Gly has no side chain, so it cannot exist at all."""
    m = measure_salt_bridge(CRYSTAL, peptide_position=1, mhc_residue_number=156)
    assert m.peptide_residue == "GLY1"
    assert not m.possible
    assert "no charged side-chain group" in m.note
