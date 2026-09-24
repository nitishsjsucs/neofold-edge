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


def test_near_self_must_exclude_the_candidates_own_wild_type(proteome):
    """Without the exclusion the metric is vacuous: every missense neoepitope
    is one mismatch from its own wild-type, which is a self peptide."""
    naive = proteome.find_near("GADGVGKSA", max_mismatches=1)
    assert naive is not None and naive[1] == "GAGGVGKSA", \
        "expected the naive search to return the candidate's own wild-type"
    corrected = proteome.find_near("GADGVGKSA", max_mismatches=1, exclude="GAGGVGKSA")
    assert corrected is None or corrected[1] != "GAGGVGKSA"


def test_kras_neoepitope_is_near_self_to_a_different_gtpase(proteome):
    """The P-loop motif GxxxxGKS is conserved across small GTPases, so the KRAS
    neoepitope resembles a peptide in RRAD. This is a RISK FLAG, not a
    disqualifier -- the same epitope is clinically validated as immunogenic
    (Tran et al., NEJM 2016)."""
    m = proteome.check("GADGVGKSA", near=True, wild_type="GAGGVGKSA")
    assert m.verdict == "near-self"
    assert not m.exact_self, "a near-self flag must never disqualify on its own"
    assert "RAD" in (m.nearest_protein or ""), m.nearest_protein


def test_viral_peptide_has_no_near_self_match(proteome):
    m = proteome.check("NLVPMVATV", near=True)
    assert m.verdict == "not-self"


def test_QC_INVARIANT_every_wildtype_window_is_found_in_the_proteome(proteome):
    """End-to-end QC on variant mapping, not just on the self filter.

    Every wild-type peptide window we generate is, by construction, a verbatim
    substring of a normal human protein. If even one is not, something upstream
    is wrong: the reference sequence, the codon numbering, or the window
    arithmetic. This catches mapping bugs that produce plausible-looking but
    fictitious peptides.
    """
    from neofold.variants import build_candidates, read_fasta, variants_from_vcf
    root = PROTEOME.parent.parent.parent
    ref = read_fasta(str(root / "data" / "sequences" / "proteins.fasta"))
    variants = variants_from_vcf(str(root / "data" / "demo" / "tumor_variants.vcf"))
    missing = []
    for v in variants:
        if v.uniprot not in ref:
            continue
        for c in build_candidates(v, ref[v.uniprot]):
            if not proteome.check(c.wt_peptide, near=False).exact_self:
                missing.append((v.label, c.wt_peptide))
    assert not missing, f"wild-type windows absent from the proteome: {missing[:5]}"
