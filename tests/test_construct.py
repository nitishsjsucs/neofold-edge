"""Polyepitope construct assembly and junction screening.

The safety-relevant assertions here are the ones about what we DON'T emit.
"""
import itertools

import pytest

from neofold.construct import (DEFAULT_SPACER, MITD_ANCHOR, MUTATION_OFFSET,
                               SEC_SIGNAL, SPACER_IS_PUBLISHED, STRETCH_LENGTH,
                               Epitope, assemble, build_stretch,
                               junction_peptides)

PROTEIN = "MTEYKLVVVGADGVGKSALTIQLIQNHFVDEYDPTIEDSYRKQVVIDGETCLLDILDTAGQEEY"


def test_stretch_places_the_mutation_at_position_14():
    """Only when the mutation is far enough from both termini to be centred."""
    pos = 30                       # comfortably central in PROTEIN
    s = build_stretch(PROTEIN, position=pos)
    assert len(s) == STRETCH_LENGTH
    assert s[MUTATION_OFFSET] == PROTEIN[pos - 1]


def test_stretch_clamps_at_the_protein_start():
    """A mutation near the N-terminus cannot be centred; it must not underflow."""
    s = build_stretch(PROTEIN, position=3)
    assert len(s) == STRETCH_LENGTH
    assert s == PROTEIN[:STRETCH_LENGTH]


def test_stretch_clamps_at_the_protein_end():
    s = build_stretch(PROTEIN, position=len(PROTEIN) - 1)
    assert len(s) == STRETCH_LENGTH
    assert s == PROTEIN[-STRETCH_LENGTH:]


def test_junction_peptides_all_span_the_seam():
    left, right = "A" * 27, "C" * 27
    for pep in junction_peptides(left, right):
        assert "A" in pep and "C" in pep, f"{pep} does not cross the join"


def test_junction_peptides_exclude_windows_inside_one_parent():
    """A k-mer lying wholly in one epitope is not a junction artefact -- it was
    already screened as a candidate."""
    left, right = "ACDEFGHIKLMNPQRSTVWYACDEFGH", "WYTVSRQPNMLKIHGFEDCAYWVTSR"
    for pep in junction_peptides(left, right):
        assert pep not in left and pep not in right


def test_spacer_changes_the_junction_peptides():
    a = set(junction_peptides("A" * 27, "C" * 27, ""))
    b = set(junction_peptides("A" * 27, "C" * 27, DEFAULT_SPACER))
    assert a != b


def test_spacer_is_flagged_as_not_published():
    """The BNT122 Methods confirm a 30 bp (10 aa) linker but do not print the
    residues. Ours is a conventional G/S composition and must say so."""
    assert SPACER_IS_PUBLISHED is False
    assert len(DEFAULT_SPACER) == 10


class FakeScreen:
    """Calls any peptide containing 'WW' a strong binder."""
    def _predict(self, peptides, allele):
        return {p: {"affinity": 10.0 if "WW" in p else 30000.0,
                    "affinity_percentile": 0.05 if "WW" in p else 50.0,
                    "presentation_score": 0.9 if "WW" in p else 0.001,
                    "processing_score": 0.5} for p in peptides}


def make(name, stretch):
    assert set(stretch) <= set("ACDEFGHIKLMNPQRSTVWY"), stretch
    return Epitope(candidate_id=name, core_peptide=stretch[10:19],
                   stretch=stretch, gene=name, mutation="X1Y")


def test_assembly_picks_an_ordering_that_avoids_junction_binders():
    """Two epitopes end/start such that one adjacency creates 'XX'. The search
    must place them so that it does not."""
    # "X" here is a placeholder residue the FakeScreen keys on; use W, which
    # is a real amino acid and rare enough not to collide.
    a = make("A", "A" * 26 + "W")                  # ends W
    b = make("B", "W" + "C" * 26)                  # starts W -> A|B makes WW
    c = make("C", "D" * 27)
    out = assemble([a, b, c], "HLA-C*08:02", FakeScreen(), spacer=DEFAULT_SPACER)
    order = [out.epitopes[i].candidate_id for i in out.order]
    assert out.n_junctional_binders == 0, order
    # Either it avoided the A->B adjacency, or it kept it and inserted a
    # spacer. Both are valid solutions; what is not valid is keeping the
    # adjacency bare.
    if order.index("A") + 1 == order.index("B"):
        ab = next(j for j in out.junctions if j.left == "A" and j.right == "B")
        assert ab.spacer, "kept the contaminated adjacency with no spacer"


def test_search_is_exhaustive_for_small_sets():
    eps = [make(ch, ch * 27) for ch in "ACDE"]
    out = assemble(eps, "HLA-C*08:02", FakeScreen())
    assert out.orderings_evaluated == len(list(itertools.permutations(range(4))))  # 24


def test_duplicate_stretches_are_deduplicated():
    """Two shortlisted peptides from the same variant expand to one stretch."""
    dup = "D" * 27
    eps = [make("A", "A" * 27), make("D1", dup), make("D2", dup)]
    out = assemble(eps, "HLA-C*08:02", FakeScreen())
    assert len(out.epitopes) == 2


def test_construct_has_the_published_flanks():
    eps = [make(ch, ch * 27) for ch in "AC"]
    out = assemble(eps, "HLA-C*08:02", FakeScreen())
    assert out.sequence.startswith(SEC_SIGNAL)
    assert out.sequence.endswith(MITD_ANCHOR)


def test_output_is_amino_acids_only_never_nucleotides():
    """A nucleotide sequence would imply a manufacturing artefact. This is not
    one, and the output must not be mistakable for one."""
    eps = [make(ch, ch * 27) for ch in "AC"]
    out = assemble(eps, "HLA-C*08:02", FakeScreen())
    d = out.as_dict()
    assert d["amino_acids_only"] is True
    assert set(out.sequence) - set("ACDEFGHIKLMNPQRSTVWY") == set()
    assert "not a vaccine" in d["disclaimer"]


def test_direct_fusion_is_preferred_over_a_spacer():
    """Linkers are not free: no primary study establishes AAY, Schubert 2016
    scored it below no spacer, and Gurung 2024 found no-linker recovered more
    epitopes. A spacer must only appear where it actually helps."""
    eps = [make(ch, ch * 27) for ch in "AC"]
    out = assemble(eps, "HLA-C*08:02", FakeScreen())
    assert all(j.spacer == "" for j in out.junctions)
