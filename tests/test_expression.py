"""Normal-tissue expression as a safety flag, never a gate.

These tests encode why the obvious filter is backwards.
"""
from pathlib import Path

import pytest

from neofold.expression import NormalExpression

GTEX = Path(__file__).resolve().parent.parent / "data" / "reference" / "gtex_median_tpm.gct.gz"
pytestmark = pytest.mark.skipif(not GTEX.exists(), reason="GTEx atlas not vendored")


@pytest.fixture(scope="module")
def gtex():
    return NormalExpression(GTEX)


def test_titin_is_flagged_elevated(gtex):
    """TTN is abundant in cardiac muscle. In the MAGE-A3 TCR trials an
    engineered receptor cross-reacted with a titin peptide and patients died
    of cardiac toxicity. This is the case the flag exists for."""
    f = gtex.check("TTN")
    assert f.found and f.risk == "elevated"
    assert "Heart" in (f.critical_tissue or "")
    assert "MAGE-A3" in f.note


def test_ny_eso_1_would_be_deleted_by_the_naive_filter(gtex):
    """CTAG1B (NY-ESO-1) is one of the best-studied cancer-testis antigens and
    its median normal expression is near zero. A 'require TPM >= 1' inclusion
    gate would discard it. Silence in normal tissue is the defining property
    of this antigen class, not a defect."""
    f = gtex.check("CTAG1B")
    assert f.found
    assert f.max_tpm < 1.0, "NY-ESO-1 should be essentially silent in normal tissue"
    assert f.risk == "low", "low normal expression must never be a disqualification"


def test_low_expression_note_refuses_to_endorse(gtex):
    """A low-risk result removes one safety concern; it is not evidence the
    candidate is good, and the wording must say so."""
    assert "NOT evidence the candidate is good" in gtex.check("CTAG1B").note


def test_housekeeping_gene_is_elevated(gtex):
    f = gtex.check("ACTB")
    assert f.risk == "elevated" and f.max_tpm > 1000


def test_flag_is_never_a_gate(gtex):
    """Structural assertion: the result advertises that it does not filter."""
    for gene in ("TTN", "CTAG1B", "KRAS"):
        assert gtex.check(gene).as_dict()["is_gate"] is False


def test_unknown_gene_declines_to_assess(gtex):
    f = gtex.check("NOT_A_REAL_GENE_XYZ")
    assert not f.found and f.risk == "unknown"
    assert "no off-tumour assessment" in f.note


def test_demo_genes_are_all_present(gtex):
    for gene in ("KRAS", "TP53", "PIK3CA", "EGFR", "KIT", "BRAF"):
        assert gtex.check(gene).found, gene
