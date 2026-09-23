"""Tests for the variant -> peptide path.

The KRAS G12D case is anchored to published epitopes (Tran NEJM 2016,
Sim PNAS 2020) and to crystal structure 6ULN, so these are real
regression tests rather than self-consistency checks.
"""
import pytest

from neofold.variants import (
    Variant, VariantError, apply_missense, build_candidates,
    parse_hgvs_p, peptide_windows, variants_from_vcf,
)

# KRAS-4B residues 1-23 (UniProt P01116). Mutation of interest is G12.
KRAS_HEAD = "MTEYKLVVVGAGGVGKSALTIQL"


def test_parse_hgvs_three_letter():
    assert parse_hgvs_p("p.Gly12Asp") == ("G", 12, "D")


def test_parse_hgvs_one_letter_and_bare():
    assert parse_hgvs_p("p.G12D") == ("G", 12, "D")
    assert parse_hgvs_p("G12D") == ("G", 12, "D")


@pytest.mark.parametrize("bad", ["p.Gly12fs", "p.Xyz12Asp", "c.35G>A", "", "p.12D"])
def test_parse_hgvs_rejects_unsupported(bad):
    with pytest.raises(VariantError):
        parse_hgvs_p(bad)


def test_apply_missense_produces_g12d():
    mutant = apply_missense(KRAS_HEAD, "G", 12, "D")
    assert mutant[11] == "D"
    assert mutant == "MTEYKLVVVGADGVGKSALTIQL"


def test_apply_missense_catches_reference_mismatch():
    # KRAS position 12 is Gly, not Ala. This must fail loudly, not silently mutate.
    with pytest.raises(VariantError, match="reference mismatch"):
        apply_missense(KRAS_HEAD, "A", 12, "D")


def test_apply_missense_rejects_out_of_range():
    with pytest.raises(VariantError, match="outside protein"):
        apply_missense(KRAS_HEAD, "G", 999, "D")


def test_every_window_contains_the_mutation():
    mutant = apply_missense(KRAS_HEAD, "G", 12, "D")
    for pep, start, offset in peptide_windows(mutant, 12):
        assert pep[offset] == "D", f"{pep} does not carry the mutation at {offset}"
        assert mutant[start - 1: start - 1 + len(pep)] == pep


def test_windows_have_requested_lengths_only():
    mutant = apply_missense(KRAS_HEAD, "G", 12, "D")
    lengths = {len(p) for p, _, _ in peptide_windows(mutant, 12, lengths=(9, 10))}
    assert lengths == {9, 10}


def test_windows_are_deduplicated():
    peps = [p for p, _, _ in peptide_windows("A" * 30, 15)]
    assert len(peps) == len(set(peps))


def test_published_kras_epitopes_are_generated():
    """The two epitopes reported in the literature must appear in our windows."""
    mutant = apply_missense(KRAS_HEAD, "G", 12, "D")
    peps = {p for p, _, _ in peptide_windows(mutant, 12)}
    assert "GADGVGKSA" in peps      # Tran et al., NEJM 2016 -- also chain C of PDB 6ULN
    assert "GADGVGKSAL" in peps     # Sim et al., PNAS 2020


def test_candidate_pairs_mutant_with_correct_wildtype_register():
    variant = Variant(gene="KRAS", uniprot="P01116", wt_aa="G", position=12, mut_aa="D")
    cands = build_candidates(variant, KRAS_HEAD)
    by_pep = {c.peptide: c for c in cands}

    # The WT counterpart must be the same window of the unmutated protein,
    # differing at exactly one position -- that single difference is the
    # entire biological argument for personalization.
    c = by_pep["GADGVGKSA"]
    assert c.wt_peptide == "GAGGVGKSA"
    diffs = [i for i, (a, b) in enumerate(zip(c.peptide, c.wt_peptide)) if a != b]
    assert diffs == [c.mut_offset]


def test_windows_near_protein_start_do_not_underflow():
    # Mutation at residue 2 -- windows must not run off the front of the protein.
    for pep, start, offset in peptide_windows(KRAS_HEAD, 2):
        assert start >= 1
        assert pep == KRAS_HEAD[start - 1: start - 1 + len(pep)]
        assert pep[offset] == KRAS_HEAD[1]


def test_windows_near_protein_end_do_not_overflow():
    pos = len(KRAS_HEAD)
    for pep, start, offset in peptide_windows(KRAS_HEAD, pos):
        assert start - 1 + len(pep) <= len(KRAS_HEAD)
        assert pep[offset] == KRAS_HEAD[pos - 1]


def test_vcf_round_trip(tmp_path):
    vcf = tmp_path / "demo.vcf"
    vcf.write_text(
        "##fileformat=VCFv4.2\n"
        "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n"
        "chr12\t25245350\t.\tC\tT\t.\tPASS\tGENE=KRAS;UNIPROT=P01116;HGVSP=p.Gly12Asp\n"
        "chr17\t7675088\t.\tC\tT\t.\tPASS\tGENE=TP53;UNIPROT=P04637;HGVSP=p.Arg175His\n"
        # a frameshift must be skipped rather than crashing the run
        "chr1\t100\t.\tA\tAG\t.\tPASS\tGENE=FOO;UNIPROT=P00000;HGVSP=p.Gly10fs\n"
    )
    variants = variants_from_vcf(str(vcf))
    assert [v.label for v in variants] == ["KRAS G12D", "TP53 R175H"]
    assert variants[0].chrom == "chr12"
    assert variants[0].pos_genomic == 25245350
