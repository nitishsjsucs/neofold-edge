"""Validate the screening layer against measured T-cell responses.

Benchmark: Bjerregaard et al., Front Immunol 2017 (PMC5694748) -- 1,948
neopeptide/HLA pairs assembled from 13 published studies, each with an
experimental T-cell assay outcome and its wild-type counterpart. 53 positives,
so the base rate is 2.7%.

This is the validation the pipeline never had. Structure accuracy was measured
against crystals; the SCREEN -- the layer that actually decides what gets
shortlisted -- was only ever argued about.

Metrics reported per rule:
  recall      fraction of true responders retained
  precision   fraction of retained candidates that are responders (PPV)
  enrichment  precision / base rate. 1.0 = no better than random.

Enrichment is the headline: with a 2.7% base rate, precision alone looks
uniformly terrible and hides the differences between rules.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def normalise_allele(a: str) -> str:
    """'HLA-A03:01' -> 'HLA-A*03:01'."""
    return f"HLA-{a[4]}*{a[5:]}" if a.startswith("HLA-") else a


def load_rows():
    path = ROOT / "data" / "benchmark" / "bjerregaard2017.csv"
    rows = []
    for r in csv.DictReader(open(path)):
        if r["Removed_from_study"] != "FALSE":
            continue
        if not (8 <= len(r["Mutant_peptide"]) <= 11):
            continue
        if r["Mismatches"] != "1":
            continue
        rows.append(r)
    return rows


def score_all(rows):
    """Run MHCflurry on mutant and wild-type, grouped by allele."""
    from mhcflurry import Class1PresentationPredictor
    predictor = Class1PresentationPredictor.load()
    supported = set(predictor.supported_alleles)

    by_allele: dict[str, list] = {}
    for r in rows:
        allele = normalise_allele(r["HLA_allele"])
        if allele in supported:
            by_allele.setdefault(allele, []).append(r)

    scored = []
    for allele, group in sorted(by_allele.items()):
        peptides = sorted({r["Mutant_peptide"] for r in group} |
                          {r["Normal_peptide"] for r in group})
        peptides = [p for p in peptides if 8 <= len(p) <= 15]
        df = predictor.predict(peptides=peptides, alleles={"s": [allele]},
                               verbose=0, include_affinity_percentile=True)
        lut = {row.peptide: row for row in df.itertuples()}
        for r in group:
            m, w = lut.get(r["Mutant_peptide"]), lut.get(r["Normal_peptide"])
            if m is None or w is None:
                continue
            scored.append({
                "peptide": r["Mutant_peptide"],
                "wt_peptide": r["Normal_peptide"],
                "allele": allele,
                "responder": r["Tcell_response"] == "YES",
                "anchor": r["Anchor"] == "YES",
                "affinity": float(m.affinity),
                "wt_affinity": float(w.affinity),
                "rank": float(getattr(m, "affinity_percentile", float("nan"))),
                "presentation": float(m.presentation_score),
            })
        print(f"  {allele:14} {len(group):4} pairs", flush=True)
    return scored


def evaluate(scored, rules):
    n = len(scored)
    pos = sum(s["responder"] for s in scored)
    base = pos / n
    print(f"\nbenchmark: {n} pairs, {pos} responders, base rate {base:.2%}\n")
    print(f"{'rule':44}{'kept':>7}{'found':>7}{'recall':>9}{'prec':>8}{'enrich':>9}")
    print("-" * 84)
    out = []
    for name, fn in rules:
        kept = [s for s in scored if fn(s)]
        found = sum(s["responder"] for s in kept)
        recall = found / pos if pos else 0.0
        prec = found / len(kept) if kept else 0.0
        enrich = prec / base if base else 0.0
        print(f"{name:44}{len(kept):>7}{found:>7}{recall:>8.1%}{prec:>8.1%}{enrich:>8.2f}x")
        out.append({"rule": name, "kept": len(kept), "found": found,
                    "recall": round(recall, 4), "precision": round(prec, 4),
                    "enrichment": round(enrich, 3)})
    return out, base, pos, n


def main():
    from neofold.screen import damped_dai

    rows = load_rows()
    print(f"loaded {len(rows)} usable rows; scoring with MHCflurry by allele...")
    scored = score_all(rows)
    for s in scored:
        s["dai"] = damped_dai(s["wt_affinity"], s["affinity"])

    rules = [
        ("random (base rate)", lambda s: True),
        ("affinity <= 500 nM", lambda s: s["affinity"] <= 500),
        ("affinity <= 50 nM", lambda s: s["affinity"] <= 50),
        ("%rank < 2.0 (weak binder)", lambda s: s["rank"] < 2.0),
        ("%rank < 0.5 (strong binder)", lambda s: s["rank"] < 0.5),
        ("presentation >= 0.10", lambda s: s["presentation"] >= 0.10),
        ("presentation >= 0.50", lambda s: s["presentation"] >= 0.50),
        # The rule we shipped, then removed:
        ("DAI >= 10 ALONE", lambda s: s["dai"] >= 10),
        ("DAI >= 2 ALONE", lambda s: s["dai"] >= 2),
        ("affinity <= 500 AND DAI >= 10", lambda s: s["affinity"] <= 500 and s["dai"] >= 10),
        ("affinity <= 500 AND DAI >= 2", lambda s: s["affinity"] <= 500 and s["dai"] >= 2),
        # What we ship now:
        ("OURS: presentation >= 0.10 AND <= 500 nM",
         lambda s: s["presentation"] >= 0.10 and s["affinity"] <= 500),
    ]
    results, base, pos, n = evaluate(scored, rules)

    # Does DAI help at all, conditional on presentation?
    presented = [s for s in scored if s["presentation"] >= 0.10 and s["affinity"] <= 500]
    if presented:
        p_pos = sum(s["responder"] for s in presented)
        print(f"\nwithin the {len(presented)} presented candidates ({p_pos} responders):")
        for label, fn in [("DAI >= 10", lambda s: s["dai"] >= 10),
                          ("DAI >= 2", lambda s: s["dai"] >= 2),
                          ("anchor mutation", lambda s: s["anchor"]),
                          ("TCR-facing mutation", lambda s: not s["anchor"])]:
            sub = [s for s in presented if fn(s)]
            f = sum(s["responder"] for s in sub)
            print(f"   {label:24} {len(sub):4} kept, {f:3} responders, "
                  f"precision {f/len(sub) if sub else 0:.1%} "
                  f"(vs {p_pos/len(presented):.1%} for all presented)")

    out = ROOT / "benchmarks" / "screen_validation.json"
    out.write_text(json.dumps(
        {"benchmark": "Bjerregaard 2017 (PMC5694748)", "n_pairs": n,
         "n_responders": pos, "base_rate": round(base, 5), "rules": results},
        indent=2))
    print(f"\nwrote {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
