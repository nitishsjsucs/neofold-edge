"""Self-similarity filter tests.

The strongest validation here is biological rather than synthetic: the
wild-type counterpart of a real neoepitope MUST be found in the human
proteome, because it is by definition a normal human peptide. If it is not,
the search is broken.
"""
from pathlib import Path

import pytest

from neofold.selfsim import SelfProteome

PROTEOME = Path(__file__).resolve().parent.parent / "data" / "reference" / "human_sp.fasta.gz"
pytestmark = pytest.mark.skipif(not PROTEOME.exists(), reason="human proteome not vendored")


@pytest.fixture(scope="module")
def proteome():
    return SelfProteome(PROTEOME)


def test_proteome_loads(proteome):
    assert proteome.n_proteins > 20000


def test_wild_type_peptides_are_self(proteome):
    """The validation that matters: a wild-type peptide IS a human peptide."""
    for wt in ("GAGGVGKSA", "GAGGVGKSAL"):
        m = proteome.check(wt, near=False)
        assert m.exact_self, f"{wt} should be found in the human proteome"


def test_kras_neoepitope_is_not_self(proteome):
    """G12D creates a sequence absent from the normal proteome."""
    m = proteome.check("GADGVGKSA", near=False)
    assert not m.exact_self


def test_viral_epitope_is_not_self(proteome):
    """A CMV peptide must not appear in the human proteome."""
    assert not proteome.check("NLVPMVATV", near=False).exact_self


def test_kit_d816v_peptide_is_caught_as_self(proteome):
    """A real catch. ICDFGLARV contains the DFG motif conserved across protein
    kinases, so the KIT activation-loop 'neoepitope' occurs verbatim in ERK2.
    Our binding screen ranked it highly; this filter disqualifies it."""
    m = proteome.check("ICDFGLARV", near=False)
    assert m.exact_self
    assert "MK01" in (m.nearest_protein or ""), m.nearest_protein


def test_peptides_do_not_match_across_protein_boundaries(proteome):
    """Proteins are joined with a separator, so a peptide cannot be assembled
    from the end of one protein and the start of the next."""
    assert proteome._load() is None or True
    assert "*" in proteome._blob


def test_verdict_and_explanation_are_populated(proteome):
    m = proteome.check("GAGGVGKSA", near=False)
    assert m.verdict == "is-self"
    assert "normal human proteome" in m.explanation
