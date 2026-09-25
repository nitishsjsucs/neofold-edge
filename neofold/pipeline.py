"""End-to-end triage: variant file -> ranked, explained candidate shortlist.

This module owns the funnel and nothing else. Structure prediction is a
separate stage (see `structure.py`) because it needs a GPU and takes ~1000x
longer per candidate.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from neofold.screen import (MIN_PRESENTATION, WEAK_BINDER_NM, PeptideScreen,
                            ScreenResult, rank_for_structure, triage)
from neofold.expression import NormalExpression
from neofold.selfsim import SelfProteome
from neofold.variants import Candidate, Variant, build_candidates, read_fasta, variants_from_vcf

DISCLAIMER = (
    "Research prioritisation only. Predicted values are hypotheses, not "
    "measurements. Expert review and laboratory validation required. "
    "Not a diagnostic, treatment recommendation, or vaccine design."
)


@dataclass
class TriageReport:
    allele: str
    variants: list[Variant]
    candidates: list[Candidate]
    results: list[ScreenResult]
    shortlist: list[ScreenResult]
    self_matches: dict = field(default_factory=dict)
    expression_flags: dict = field(default_factory=dict)
    timings: dict[str, float] = field(default_factory=dict)
    skipped_variants: list[str] = field(default_factory=list)

    @property
    def funnel(self) -> dict[str, int]:
        return {
            "variants": len(self.variants),
            "candidate_peptides": len(self.candidates),
            "scored": len(self.results),
            "self_peptides": sum(1 for r in self.results
                                 if triage(r, self.self_matches.get(r.peptide))[0] == "self peptide"),
            "presented": sum(1 for r in self.results
                             if triage(r, self.self_matches.get(r.peptide))[0] == "presented"),
            "shortlist": len(self.shortlist),
        }

    def as_dict(self) -> dict:
        rows = []
        for r in self.results:
            sm = self.self_matches.get(r.peptide)
            tier, reason = triage(r, sm)
            row = r.as_dict()
            row["tier"] = tier
            row["reason"] = reason
            gene = r.candidate_id.split("-")[0]
            if gene in self.expression_flags:
                row["expression"] = self.expression_flags[gene].as_dict()
            if sm is not None:
                row["self_verdict"] = sm.verdict
                row["self_protein"] = sm.nearest_protein
                row["self_explanation"] = sm.explanation
                row["nearest_self_peptide"] = sm.nearest_self_peptide
            rows.append(row)
        return {
            "allele": self.allele,
            "funnel": self.funnel,
            "timings": {k: round(v, 3) for k, v in self.timings.items()},
            "skipped_variants": self.skipped_variants,
            "results": rows,
            "shortlist": [r.candidate_id for r in self.shortlist],
            "disclaimer": DISCLAIMER,
        }


def run_triage(
    vcf_path: str,
    fasta_path: str,
    allele: str,
    top_n: int = 5,
    screen: PeptideScreen | None = None,
    proteome: SelfProteome | None = None,
    expression: NormalExpression | None = None,
) -> TriageReport:
    timings: dict[str, float] = {}

    t0 = time.perf_counter()
    reference = read_fasta(fasta_path)
    variants = variants_from_vcf(vcf_path)
    timings["parse"] = time.perf_counter() - t0

    t0 = time.perf_counter()
    candidates: list[Candidate] = []
    skipped: list[str] = []
    for v in variants:
        ref = reference.get(v.uniprot)
        if ref is None:
            skipped.append(f"{v.label}: no reference sequence for {v.uniprot}")
            continue
        try:
            candidates.extend(build_candidates(v, ref))
        except Exception as exc:            # reference mismatch etc.
            skipped.append(f"{v.label}: {exc}")
    timings["expand"] = time.perf_counter() - t0

    screen = screen or PeptideScreen()
    t0 = time.perf_counter()
    results = screen.score(candidates, allele)
    timings["screen"] = time.perf_counter() - t0

    # Self-similarity runs in two passes, ordered by cost and by consequence.
    #
    # Pass 1 (cheap, over everything): exact proteome matches. A peptide that
    # IS a human peptide is disqualified outright.
    #
    # Pass 2 (~1.3 s each, over presented candidates only): the 1-mismatch
    # search that supplies the FOREIGNNESS term. It has to run before the
    # recognition rule, because TESLA's rule is "low agretopicity OR high
    # foreignness" -- so foreignness can qualify a candidate on its own and
    # cannot be deferred to the shortlist.
    self_matches: dict = {}
    if proteome is not None:
        t0 = time.perf_counter()
        for r in results:
            self_matches[r.peptide] = proteome.check(r.peptide, near=False)
        timings["self_exact"] = time.perf_counter() - t0

        # Only the shortlist needs the 1-mismatch search. It used to run over
        # every presented candidate, from when dissimilarity-to-self was part
        # of the qualification rule. It is now a flag on the shortlist, so
        # scoring 22 candidates at ~1.3 s each was ~11 s of wasted demo time.
        for_near = rank_for_structure(results, top_n, self_matches)
        t0 = time.perf_counter()
        for r in for_near:
            # Exclude the candidate's own wild-type: every missense neoepitope
            # is trivially one mismatch from it, so counting it would make the
            # flag meaningless.
            self_matches[r.peptide] = proteome.check(
                r.peptide, near=True, wild_type=r.wt_peptide)
        timings["self_near"] = time.perf_counter() - t0
        timings["_n_near_searched"] = len(for_near)

    # Off-tumour safety annotation on the shortlist. A FLAG, never a gate:
    # high normal-tissue expression warns, low expression never qualifies.
    expression_flags: dict = {}
    if expression is not None:
        t0 = time.perf_counter()
        for r in shortlist_candidates(results, top_n, self_matches):
            gene = r.candidate_id.split("-")[0]
            if gene not in expression_flags:
                expression_flags[gene] = expression.check(gene)
        timings["expression"] = time.perf_counter() - t0

    shortlist = rank_for_structure(results, top_n, self_matches)
    return TriageReport(
        allele=allele, variants=variants, candidates=candidates,
        results=results, shortlist=shortlist, timings=timings,
        skipped_variants=skipped, self_matches=self_matches,
        expression_flags=expression_flags,
    )


def shortlist_candidates(results, top_n, self_matches):
    """The candidates that will be shortlisted, without re-ranking twice."""
    return rank_for_structure(results, top_n, self_matches)
