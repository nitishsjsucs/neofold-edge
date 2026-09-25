"""Polyepitope construct assembly, with junction screening.

WHAT THIS IS. Deterministic assembly of selected epitopes into an amino-acid
construct, following the published BioNTech "pentatope" architecture. It
arranges sequences a researcher has already chosen; it does not design
anything.

WHAT THIS IS NOT. Not a vaccine, not a therapeutic, not manufacturable
output. We emit AMINO ACIDS ONLY, never nucleotides, because a nucleotide
sequence implies a manufacturing artefact and this is not one. Between this
output and a medicine sit GMP manufacture, release testing, toxicology, an
IND and dose-finding.

THE PROBLEM THIS SOLVES. Joining two epitopes creates a new sequence across
the seam, and that seam can encode an epitope nobody intended. This is
demonstrated, not hypothetical:

  * Livingston et al., J Immunol 2002;168:5499 -- an arrangement created a
    high-affinity class II junction epitope, that epitope raised its own
    response, ALL FOUR intended responses were lost, and adding a spacer
    restored them.
  * Cornet et al., Vaccine 2006 -- across all six orderings of three
    epitopes, only ONE produced the intended responses.

So ordering is not cosmetic. With five epitopes there are only 120
arrangements, which we enumerate EXHAUSTIVELY -- pvacvector has to anneal
because it targets larger sets; at this size we can simply be exact.

LINKERS ARE NOT FREE AND ARE NOT THE DEFAULT. No primary study establishes
AAY; its citation chain runs through a review containing no AAY data, and
Schubert & Kohlbacher (2016) scored it BELOW using no spacer at all. Gurung
et al. (2024) compared linker against no-linker with mass-spec readout across
47 antigens: no-linker recovered MORE epitopes, and glycine/serine linkers
caused translation to collapse past roughly twenty antigens. We therefore
join directly by default and insert a spacer only at junctions that no
reordering can clean.
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass, field

# Published in the BNT122 phase 1 Methods (Nat Med 2025), and independently
# consistent with patent base counts (26 aa x 3 = 78 bp; 55 aa x 3 + stop = 168 bp).
SEC_SIGNAL = "MRVMAPRTLILLLSGALALTETWAGS"
MITD_ANCHOR = ("IVGIVAGLAVLAVVVIGAVVATVMCRRKSSGGKGGSYSQAASSDSAQGSDVSLTA")

# BioNTech's constructs carry 27-residue stretches with the mutation at
# position 14, rather than minimal epitopes -- this lets the proteasome pick
# the register instead of committing to a predicted one.
STRETCH_LENGTH = 27
MUTATION_OFFSET = 13          # 0-based, so position 14

# A 10-residue glycine/serine spacer. The BNT122 Methods confirm 30 bp
# linkers (= 10 aa); the exact residue string is not published, so this is a
# conventional G/S composition and is labelled as such.
DEFAULT_SPACER = "GGSGGGGSGG"
SPACER_IS_PUBLISHED = False

# Junction k-mer lengths to screen, and the binder thresholds used to call a
# junction "contaminated". Matches pvacvector's test.
JUNCTION_LENGTHS = (8, 9, 10, 11)
JUNCTION_AFFINITY_NM = 500.0
JUNCTION_RANK = 2.0


@dataclass
class Epitope:
    """One selected candidate, expanded to a 27-mer stretch."""
    candidate_id: str
    core_peptide: str           # the 9-11mer that was shortlisted
    stretch: str                # the 27-mer actually placed in the construct
    gene: str
    mutation: str

    def __len__(self) -> int:
        return len(self.stretch)


@dataclass
class Junction:
    left: str                   # candidate_id
    right: str
    spacer: str
    peptides: list[str] = field(default_factory=list)
    binders: list[dict] = field(default_factory=list)

    @property
    def clean(self) -> bool:
        return not self.binders


@dataclass
class Construct:
    epitopes: list[Epitope]
    order: list[int]
    junctions: list[Junction]
    sequence: str
    n_junctional_binders: int
    orderings_evaluated: int
    worst_ordering_binders: int = 0
    shortlist_order_binders: int = 0

    def as_dict(self) -> dict:
        return {
            "sequence": self.sequence,
            "length_aa": len(self.sequence),
            "architecture": ["sec signal (26 aa)",
                             f"{len(self.epitopes)} x {STRETCH_LENGTH} aa epitope stretch",
                             "MITD anchor (55 aa)"],
            "order": [self.epitopes[i].candidate_id for i in self.order],
            "orderings_evaluated": self.orderings_evaluated,
            "n_junctional_binders": self.n_junctional_binders,
            "worst_ordering_binders": self.worst_ordering_binders,
            "shortlist_order_binders": self.shortlist_order_binders,
            "junctions": [
                {"left": j.left, "right": j.right,
                 "spacer": j.spacer or "(none — direct fusion)",
                 "binders": j.binders, "clean": j.clean}
                for j in self.junctions
            ],
            "amino_acids_only": True,
            "disclaimer": (
                "Research construct assembly for expert review. Amino acid "
                "sequence only — deliberately not nucleotides. This is not a "
                "vaccine, not a therapeutic, and not manufacturable output."
            ),
        }


def build_stretch(mutant_protein: str, position: int,
                  length: int = STRETCH_LENGTH,
                  offset: int = MUTATION_OFFSET) -> str:
    """Extract the 27-mer around a mutation, clamped at protein boundaries.

    `position` is 1-based in the mutated protein.
    """
    idx = position - 1
    start = idx - offset
    if start < 0:
        start = 0
    if start + length > len(mutant_protein):
        start = max(0, len(mutant_protein) - length)
    return mutant_protein[start:start + length]


def junction_peptides(left: str, right: str, spacer: str = "",
                      lengths=JUNCTION_LENGTHS) -> list[str]:
    """Every k-mer that SPANS the seam between two stretches.

    Takes k-1 residues from the left, the spacer, and k-1 from the right, so
    that every window of length k crosses the join and none lies wholly
    inside either original epitope.
    """
    out: list[str] = []
    seen: set[str] = set()
    for k in lengths:
        window = left[-(k - 1):] + spacer + right[:k - 1]
        for i in range(len(window) - k + 1):
            pep = window[i:i + k]
            # Skip anything entirely contained in one parent, which is not a
            # junction artefact -- it was already screened as a candidate.
            if pep in left or pep in right:
                continue
            if pep not in seen:
                seen.add(pep)
                out.append(pep)
    return out


def screen_junction(left: Epitope, right: Epitope, allele: str, screen,
                    spacer: str = "") -> Junction:
    """Score the seam between two epitopes for accidentally-created binders."""
    peps = junction_peptides(left.stretch, right.stretch, spacer)
    j = Junction(left=left.candidate_id, right=right.candidate_id,
                 spacer=spacer, peptides=peps)
    if not peps:
        return j
    scored = screen._predict(peps, allele)
    for pep, vals in scored.items():
        rank = vals.get("affinity_percentile", float("nan"))
        is_binder = (vals["affinity"] <= JUNCTION_AFFINITY_NM
                     or (rank == rank and rank < JUNCTION_RANK))
        if is_binder:
            j.binders.append({
                "peptide": pep,
                "affinity_nm": round(vals["affinity"], 1),
                "affinity_percentile": (None if rank != rank else round(rank, 3)),
            })
    j.binders.sort(key=lambda b: b["affinity_nm"])
    return j


def assemble(epitopes: list[Epitope], allele: str, screen,
             spacer: str = DEFAULT_SPACER,
             exhaustive_limit: int = 7) -> Construct:
    """Choose the ordering that creates the fewest junctional binders.

    With n <= `exhaustive_limit` every permutation is evaluated, so the result
    is optimal rather than heuristic. Junction scores are cached, because the
    seam between two epitopes is the same in every ordering that puts them
    adjacent -- which collapses 120 orderings of 5 epitopes into 20 distinct
    junction evaluations.
    """
    # Two shortlisted peptides from the SAME variant expand to the same 27-mer
    # stretch, so they would be placed twice. Deduplicate by stretch, keeping
    # the first (highest-ranked) occurrence.
    seen: set[str] = set()
    deduped = []
    for e in epitopes:
        if e.stretch not in seen:
            seen.add(e.stretch)
            deduped.append(e)
    epitopes = deduped

    n = len(epitopes)
    if n < 2:
        raise ValueError("need at least two distinct epitope stretches")

    cache: dict[tuple[int, int, str], Junction] = {}

    def junction(i: int, k: int, sp: str) -> Junction:
        key = (i, k, sp)
        if key not in cache:
            cache[key] = screen_junction(epitopes[i], epitopes[k], allele, screen, sp)
        return cache[key]

    orders = (list(itertools.permutations(range(n))) if n <= exhaustive_limit
              else [tuple(range(n))])

    best_order, best_junctions, best_score = None, None, None
    for order in orders:
        js, score = [], 0
        for a, b in zip(order, order[1:]):
            # Prefer a direct fusion; fall back to a spacer only if the direct
            # join is contaminated.
            j = junction(a, b, "")
            if j.binders:
                with_spacer = junction(a, b, spacer)
                if len(with_spacer.binders) < len(j.binders):
                    j = with_spacer
            js.append(j)
            score += len(j.binders)
        if best_score is None or score < best_score:
            best_order, best_junctions, best_score = list(order), js, score
            if score == 0:
                break

    parts = [SEC_SIGNAL]
    for pos, idx in enumerate(best_order):
        parts.append(epitopes[idx].stretch)
        if pos < len(best_order) - 1:
            parts.append(best_junctions[pos].spacer)
    parts.append(MITD_ANCHOR)

    # What the search actually bought: the worst ordering is the honest
    # comparator, because a naive pipeline would take the shortlist order.
    worst = best_score
    naive = None
    for order in orders:
        score = sum(len(junction(a, b, "").binders) for a, b in zip(order, order[1:]))
        worst = max(worst, score)
        if naive is None:
            naive = score
    return Construct(epitopes=epitopes, order=best_order,
                     junctions=best_junctions, sequence="".join(parts),
                     n_junctional_binders=best_score,
                     orderings_evaluated=len(orders),
                     worst_ordering_binders=worst,
                     shortlist_order_binders=naive)
