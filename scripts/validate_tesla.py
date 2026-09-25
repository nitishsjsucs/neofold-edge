"""Independent validation on TESLA (Wells et al., Cell 2020).

Why this set and not just Bjerregaard:

  * Its negatives are SAME-PATIENT hard negatives -- peptides that a real
    pipeline nominated and a real assay rejected -- rather than a mixture of
    negatives from different studies.
  * Prevalence is 6.1% (37/608), close to what a clinical pipeline actually
    faces.
  * It carries MEASURED binding affinity alongside predicted, so we can
    separate "our predictor is wrong" from "affinity is not the signal".
  * It carries tumour abundance, so we can quantify the omission we have
    documented but not implemented.

We do NOT tune anything on this set. Bjerregaard was the development
benchmark; TESLA is reported as-is.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def auc(values, labels):
    """Rank-based AUC with ties averaged."""
    pairs = sorted(zip(values, labels))
    ranks = [0.0] * len(pairs)
    i = 0
    while i < len(pairs):
        j = i
        while j + 1 < len(pairs) and pairs[j + 1][0] == pairs[i][0]:
            j += 1
        avg = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[k] = avg
        i = j + 1
    pos_ranks = [ranks[k] for k in range(len(pairs)) if pairs[k][1]]
    n1, n0 = len(pos_ranks), len(pairs) - len(pos_ranks)
    if not n1 or not n0:
        return float("nan")
    return (sum(pos_ranks) - n1 * (n1 + 1) / 2) / (n1 * n0)


def load():
    import openpyxl
    ws = openpyxl.load_workbook(ROOT / "data/benchmark/tesla_mmc4.xlsx",
                                read_only=True)["master-bindings-selected"]
    rows = list(ws.iter_rows(values_only=True))
    hdr = list(rows[0])
    out = []
    for r in rows[1:]:
        if not r[0]:
            continue
        d = dict(zip(hdr, r))
        def num(k):
            v = d.get(k)
            try:
                return float(v)
            except (TypeError, ValueError):
                return None
        out.append({
            "peptide": d["ALT_EPI_SEQ"],
            "allele": "HLA-" + str(d["MHC"]).replace("_", ""),
            "validated": bool(d["VALIDATED"]),
            "measured_affinity": num("MEASURED_BINDING_AFFINITY"),
            "netmhcpan": num("NETMHC_PAN_BINDING_AFFINITY"),
            "abundance": num("TUMOR_ABUNDANCE"),
            "stability": num("BINDING_STABILITY"),
            "agretopicity": num("AGRETOPICITY"),
            "foreignness": num("FOREIGNNESS"),
        })
    return out


def score_with_mhcflurry(rows):
    """Add OUR predictions, so this is a test of our pipeline and not just a
    re-analysis of TESLA's own columns."""
    from mhcflurry import Class1PresentationPredictor
    predictor = Class1PresentationPredictor.load()
    supported = set(predictor.supported_alleles)

    by_allele: dict[str, list] = {}
    for r in rows:
        if r["allele"] in supported and 8 <= len(r["peptide"]) <= 15:
            by_allele.setdefault(r["allele"], []).append(r)

    for allele, group in sorted(by_allele.items()):
        peps = sorted({r["peptide"] for r in group})
        df = predictor.predict(peptides=peps, alleles={"s": [allele]}, verbose=0,
                               include_affinity_percentile=True)
        lut = {row.peptide: row for row in df.itertuples()}
        for r in group:
            hit = lut.get(r["peptide"])
            if hit is None:
                continue
            r["our_presentation"] = float(hit.presentation_score)
            r["our_affinity"] = float(hit.affinity)
            r["our_rank"] = float(getattr(hit, "affinity_percentile", float("nan")))
    return [r for r in rows if "our_presentation" in r]


def main():
    rows = load()
    print(f"TESLA: {len(rows)} peptides, {sum(r['validated'] for r in rows)} immunogenic")
    scored = score_with_mhcflurry(rows)
    labels = [r["validated"] for r in scored]
    pos, n = sum(labels), len(scored)
    base = pos / n
    print(f"scored by MHCflurry: {n} peptides, {pos} immunogenic, base rate {base:.2%}\n")

    print(f"{'score':40}{'AUC':>8}")
    print("-" * 50)
    candidates = [
        ("OUR presentation score", lambda r: r["our_presentation"], False),
        ("OUR predicted affinity (nM)", lambda r: r["our_affinity"], True),
        ("OUR %rank", lambda r: r["our_rank"], True),
        ("TESLA: MEASURED affinity (nM)", lambda r: r["measured_affinity"], True),
        ("TESLA: NetMHCpan affinity (nM)", lambda r: r["netmhcpan"], True),
        ("TESLA: tumour abundance (TPM)", lambda r: r["abundance"], False),
        ("TESLA: binding stability (h)", lambda r: r["stability"], False),
        ("TESLA: agretopicity (lower=better)", lambda r: r["agretopicity"], True),
        ("TESLA: foreignness", lambda r: r["foreignness"], False),
    ]
    results = {}
    for name, fn, invert in candidates:
        sub = [(r, fn(r)) for r in scored if fn(r) is not None]
        if len(sub) < 20:
            print(f"{name:40}{'n/a':>8}  (only {len(sub)} values)")
            continue
        vals = [(-v if invert else v) for _, v in sub]
        labs = [r["validated"] for r, _ in sub]
        a = auc(vals, labs)
        results[name] = {"auc": round(a, 4), "n": len(sub),
                         "positives": sum(labs)}
        print(f"{name:40}{a:8.3f}   n={len(sub)}")

    # Precision at shortlist depth, ranked by our screen.
    print(f"\nprecision at depth, ranked by OUR presentation score "
          f"(base rate {base:.1%}):")
    ranked = sorted(scored, key=lambda r: r["our_presentation"], reverse=True)
    pk = {}
    for k in (10, 25, 50, 100):
        hits = sum(r["validated"] for r in ranked[:k])
        pk[k] = {"hits": hits, "precision": round(hits / k, 4),
                 "enrichment": round((hits / k) / base, 2)}
        print(f"   P@{k:<4} {hits:3}/{k:<4} = {hits/k:5.1%}   "
              f"{(hits/k)/base:.2f}x enrichment")

    out = ROOT / "benchmarks" / "tesla_validation.json"
    out.write_text(json.dumps(
        {"benchmark": "TESLA, Wells et al. Cell 2020", "n_scored": n,
         "n_immunogenic": pos, "base_rate": round(base, 5),
         "auc": results, "precision_at_k": pk}, indent=2))
    print(f"\nwrote {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
