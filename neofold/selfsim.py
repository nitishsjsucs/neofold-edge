"""Self-similarity filter: is this "neoepitope" actually a normal human peptide?

Two reasons a candidate that resembles self is a bad candidate:

  1. Central tolerance. T-cells reactive to self peptides are largely deleted
     in the thymus, so a peptide indistinguishable from self is unlikely to
     have an available repertoire.
  2. Autoimmunity risk. A T-cell raised against a neoepitope that closely
     resembles a self peptide could attack healthy tissue.

WHAT THIS DOES NOT ESTABLISH. Absence from the proteome does not make a
peptide immunogenic; it only removes one specific reason it would not be.
Tolerance also depends on thymic expression levels, which we do not model,
and sequence identity is a crude proxy for TCR cross-reactivity, which
depends on which residues point up toward the receptor rather than on overall
similarity.

The reference is the reviewed (Swiss-Prot) human proteome, which is the
curated set rather than every predicted isoform -- so a peptide unique to a
rare isoform could be missed.
"""
from __future__ import annotations

import gzip
from dataclasses import dataclass
from pathlib import Path

AA = "ACDEFGHIKLMNPQRSTVWY"


@dataclass
class SelfMatch:
    peptide: str
    exact_self: bool
    min_mismatches: int | None      # None when not searched beyond exact
    nearest_self_peptide: str | None
    nearest_protein: str | None

    @property
    def verdict(self) -> str:
        if self.exact_self:
            return "is-self"
        if self.min_mismatches == 1:
            return "near-self"
        return "not-self"

    @property
    def explanation(self) -> str:
        if self.exact_self:
            return ("this exact sequence occurs in the normal human proteome "
                    f"({self.nearest_protein}) — it is a self peptide, not a neoepitope")
        if self.min_mismatches == 1:
            return (f"differs at a single position from {self.nearest_self_peptide} in "
                    f"{self.nearest_protein}, a DIFFERENT human protein from the one "
                    f"this candidate came from — elevated cross-reactivity risk")
        return ("no human peptide within one mismatch, excluding the candidate's own "
                "wild-type counterpart")

    def as_dict(self) -> dict:
        return {"peptide": self.peptide, "verdict": self.verdict,
                "exact_self": self.exact_self,
                "min_mismatches": self.min_mismatches,
                "nearest_self_peptide": self.nearest_self_peptide,
                "nearest_protein": self.nearest_protein,
                "explanation": self.explanation}


class SelfProteome:
    """Reviewed human proteome, searchable for exact and near-exact peptides.

    Exact search uses substring matching over one concatenated sequence, which
    is both fast and low-memory. Near matches use a seed index built lazily,
    because a 1-mismatch search over every k-mer would otherwise cost more
    memory than the rest of the pipeline combined.
    """

    def __init__(self, fasta_path: str | Path):
        self.path = Path(fasta_path)
        self._blob: str | None = None
        self._offsets: list[tuple[int, str]] = []
        self._starts: list[int] = []
        self._seed_index: dict[int, dict[str, list[int]]] = {}

    def _load(self) -> None:
        if self._blob is not None:
            return
        opener = gzip.open if self.path.suffix == ".gz" else open
        parts, offsets, pos = [], [], 0
        name = None
        buf: list[str] = []
        with opener(self.path, "rt") as fh:
            for line in fh:
                if line.startswith(">"):
                    if name is not None and buf:
                        seq = "".join(buf)
                        offsets.append((pos, name))
                        parts.append(seq)
                        pos += len(seq) + 1
                    # sp|P01116|RASK_HUMAN ... -> "RASK_HUMAN (P01116)"
                    f = line[1:].split("|")
                    name = (f"{f[2].split()[0]} ({f[1]})" if len(f) >= 3
                            else line[1:].strip()[:40])
                    buf = []
                else:
                    buf.append(line.strip())
        if name is not None and buf:
            seq = "".join(buf)
            offsets.append((pos, name))
            parts.append(seq)
        # "*" separators stop peptides spanning two proteins.
        self._blob = "*".join(parts)
        self._offsets = offsets
        # Precomputed once: rebuilding this per lookup made the whole-set scan
        # O(n_proteins) per peptide instead of O(log n).
        self._starts = [o for o, _ in offsets]

    @property
    def n_proteins(self) -> int:
        self._load()
        return len(self._offsets)

    def _protein_at(self, index: int) -> str:
        import bisect
        i = bisect.bisect_right(self._starts, index) - 1
        return self._offsets[i][1] if 0 <= i < len(self._offsets) else "?"

    def find_exact(self, peptide: str) -> str | None:
        """Protein name containing this exact peptide, or None."""
        self._load()
        idx = self._blob.find(peptide)
        return self._protein_at(idx) if idx >= 0 else None

    def _seeds(self, k: int) -> dict[str, list[int]]:
        """Index of half-length seeds. A 1-mismatch match must match one half
        exactly, so indexing halves makes the search tractable."""
        if k in self._seed_index:
            return self._seed_index[k]
        self._load()
        half = k // 2
        index: dict[str, list[int]] = {}
        blob = self._blob
        for i in range(len(blob) - k + 1):
            seed = blob[i:i + half]
            if "*" in seed:
                continue
            index.setdefault(seed, []).append(i)
        self._seed_index[k] = index
        return index

    def find_near(self, peptide: str, max_mismatches: int = 1,
                  exclude: str | None = None) -> tuple[int, str, str] | None:
        """Closest self peptide within `max_mismatches`, as (n, seq, protein).

        `exclude` suppresses one sequence, and it is essential rather than
        optional. Every missense neoepitope is by construction ONE mismatch
        from its own wild-type counterpart, which is a self peptide -- so
        without excluding it, every candidate trivially reports "near-self"
        and the metric carries no information. The question worth asking is
        whether the peptide resembles some OTHER human protein.
        """
        self._load()
        k = len(peptide)
        half = k // 2
        index = self._seeds(k)
        best: tuple[int, str, str] | None = None
        # Either the first half or the second half must be mismatch-free.
        for offset, seed in ((0, peptide[:half]), (half, peptide[half:half * 2])):
            for pos in index.get(seed, ()):
                start = pos - offset
                if start < 0 or start + k > len(self._blob):
                    continue
                cand = self._blob[start:start + k]
                if "*" in cand:
                    continue
                if exclude is not None and cand == exclude:
                    continue
                mism = sum(1 for a, b in zip(cand, peptide) if a != b)
                if mism <= max_mismatches and (best is None or mism < best[0]):
                    best = (mism, cand, self._protein_at(start))
                    if mism == 0:
                        return best
        return best

    def check(self, peptide: str, near: bool = True,
              wild_type: str | None = None) -> SelfMatch:
        """Classify a peptide against the human proteome.

        Pass `wild_type` so the candidate's own unmutated counterpart is not
        counted as a near-self hit -- see `find_near`.
        """
        protein = self.find_exact(peptide)
        if protein is not None:
            return SelfMatch(peptide, True, 0, peptide, protein)
        if not near:
            return SelfMatch(peptide, False, None, None, None)
        hit = self.find_near(peptide, max_mismatches=1, exclude=wild_type)
        if hit is None:
            return SelfMatch(peptide, False, 2, None, None)
        mism, seq, prot = hit
        return SelfMatch(peptide, False, mism, seq, prot)
