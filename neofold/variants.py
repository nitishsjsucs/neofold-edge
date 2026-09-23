"""Variant -> mutated protein -> candidate peptide windows.

Scope is deliberately narrow: missense SNVs mapped onto canonical UniProt
sequences. That covers the demo cases and nothing else. Frameshifts, indels,
splice variants and fusion neoantigens are NOT handled -- see `UNSUPPORTED`.
Being explicit about that is part of the project's honesty story.

Everything here is pure Python and runs offline.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

AA3TO1 = {
    "Ala": "A", "Arg": "R", "Asn": "N", "Asp": "D", "Cys": "C", "Gln": "Q",
    "Glu": "E", "Gly": "G", "His": "H", "Ile": "I", "Leu": "L", "Lys": "K",
    "Met": "M", "Phe": "F", "Pro": "P", "Ser": "S", "Thr": "T", "Trp": "W",
    "Tyr": "Y", "Val": "V",
}

UNSUPPORTED = (
    "frameshift, in-frame indel, splice-site, stop-gain/loss and fusion "
    "variants are not modelled; only missense SNVs are converted to peptides"
)

# Peptide lengths presented by MHC class I. 9-mers dominate.
DEFAULT_LENGTHS = (8, 9, 10, 11)


class VariantError(ValueError):
    """Raised when a variant cannot be mapped onto a reference protein."""


@dataclass(frozen=True)
class Variant:
    gene: str
    uniprot: str
    wt_aa: str
    position: int          # 1-based residue position in the canonical protein
    mut_aa: str
    chrom: str | None = None
    pos_genomic: int | None = None
    ref: str | None = None
    alt: str | None = None

    @property
    def label(self) -> str:
        return f"{self.gene} {self.wt_aa}{self.position}{self.mut_aa}"


@dataclass
class Candidate:
    """One peptide window spanning a mutated residue, with its WT counterpart."""
    peptide: str
    wt_peptide: str
    variant: Variant
    start: int             # 1-based start position in the protein
    mut_offset: int        # 0-based index of the mutated residue within the peptide
    scores: dict = field(default_factory=dict)

    @property
    def length(self) -> int:
        return len(self.peptide)

    @property
    def candidate_id(self) -> str:
        return f"{self.variant.gene}-{self.variant.wt_aa}{self.variant.position}" \
               f"{self.variant.mut_aa}-{self.peptide}"


def parse_hgvs_p(hgvsp: str) -> tuple[str, int, str]:
    """'p.Gly12Asp' or 'p.G12D' -> ('G', 12, 'D'). Missense only."""
    text = hgvsp.strip()
    if text.startswith("p."):
        text = text[2:]

    m = re.fullmatch(r"([A-Z][a-z]{2})(\d+)([A-Z][a-z]{2})", text)
    if m:
        wt, pos, mut = m.group(1), int(m.group(2)), m.group(3)
        if wt not in AA3TO1 or mut not in AA3TO1:
            raise VariantError(f"unknown amino acid in {hgvsp!r}")
        return AA3TO1[wt], pos, AA3TO1[mut]

    m = re.fullmatch(r"([A-Z])(\d+)([A-Z])", text)
    if m:
        return m.group(1), int(m.group(2)), m.group(3)

    raise VariantError(f"not a simple missense HGVS.p: {hgvsp!r} ({UNSUPPORTED})")


def read_fasta(path: str) -> dict[str, str]:
    """UniProt-style FASTA -> {accession: sequence}. Falls back to the whole
    header token when the header is not in UniProt's sp|ACC|NAME form."""
    seqs: dict[str, str] = {}
    acc: str | None = None
    buf: list[str] = []
    with open(path) as fh:
        for line in fh:
            if line.startswith(">"):
                if acc is not None:
                    seqs[acc] = "".join(buf)
                header = line[1:].strip()
                parts = header.split("|")
                acc = parts[1] if len(parts) >= 2 else header.split()[0]
                buf = []
            else:
                buf.append(line.strip())
    if acc is not None:
        seqs[acc] = "".join(buf)
    return seqs


def apply_missense(seq: str, wt: str, position: int, mut: str) -> str:
    """Substitute one residue, verifying the reference agrees.

    The WT check is the single most valuable line in this module: it catches
    wrong isoform, wrong accession and off-by-one errors, which otherwise
    produce plausible-looking nonsense peptides.
    """
    if position < 1 or position > len(seq):
        raise VariantError(
            f"position {position} outside protein of length {len(seq)}")
    found = seq[position - 1]
    if found != wt:
        raise VariantError(
            f"reference mismatch at position {position}: sequence has {found!r}, "
            f"variant claims {wt!r} -- wrong isoform or wrong accession?")
    return seq[: position - 1] + mut + seq[position:]


def peptide_windows(
    protein: str,
    position: int,
    lengths: tuple[int, ...] = DEFAULT_LENGTHS,
) -> list[tuple[str, int, int]]:
    """Every k-mer containing the residue at `position` (1-based).

    Returns (peptide, start_1based, offset_of_mutation_within_peptide).
    """
    idx = position - 1
    out: list[tuple[str, int, int]] = []
    seen: set[str] = set()
    for length in lengths:
        first = max(0, idx - length + 1)
        last = min(len(protein) - length, idx)
        for start in range(first, last + 1):
            pep = protein[start: start + length]
            if len(pep) != length or pep in seen:
                continue
            seen.add(pep)
            out.append((pep, start + 1, idx - start))
    return out


def build_candidates(
    variant: Variant,
    reference: str,
    lengths: tuple[int, ...] = DEFAULT_LENGTHS,
) -> list[Candidate]:
    """Full path: variant + canonical protein -> candidate peptides.

    Each candidate carries its wild-type counterpart at the same register, so
    the screen can show the mutant/WT contrast that justifies personalization.
    """
    mutant = apply_missense(reference, variant.wt_aa, variant.position, variant.mut_aa)
    candidates = []
    for pep, start, offset in peptide_windows(mutant, variant.position, lengths):
        wt_pep = reference[start - 1: start - 1 + len(pep)]
        candidates.append(
            Candidate(peptide=pep, wt_peptide=wt_pep, variant=variant,
                      start=start, mut_offset=offset)
        )
    return candidates


def parse_vcf(path: str) -> list[dict]:
    """Minimal VCF reader. Returns raw records; protein consequence must come
    from the INFO field (we expect GENE, UNIPROT and HGVSP keys, which our
    demo VCF carries explicitly rather than requiring a VEP cache)."""
    records = []
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            cols = line.split("\t")
            if len(cols) < 8:
                continue
            info = {}
            for item in cols[7].split(";"):
                if "=" in item:
                    k, v = item.split("=", 1)
                    info[k] = v
            records.append({
                "chrom": cols[0], "pos": int(cols[1]), "id": cols[2],
                "ref": cols[3], "alt": cols[4], "info": info,
            })
    return records


def variants_from_vcf(path: str) -> list[Variant]:
    """VCF -> Variant objects, skipping anything that is not a simple missense."""
    out = []
    for rec in parse_vcf(path):
        info = rec["info"]
        if not {"GENE", "UNIPROT", "HGVSP"} <= info.keys():
            continue
        try:
            wt, pos, mut = parse_hgvs_p(info["HGVSP"])
        except VariantError:
            continue          # non-missense consequence: out of scope, skip quietly
        out.append(Variant(
            gene=info["GENE"], uniprot=info["UNIPROT"],
            wt_aa=wt, position=pos, mut_aa=mut,
            chrom=rec["chrom"], pos_genomic=rec["pos"],
            ref=rec["ref"], alt=rec["alt"],
        ))
    return out
