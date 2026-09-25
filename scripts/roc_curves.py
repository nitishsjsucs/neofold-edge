"""ROC curves for both screening benchmarks, for the dashboard.

AUC is a single number, and a single number hides the shape. A rule can reach
0.75 by being excellent on the top 5% and useless elsewhere, or by being
mediocre everywhere -- and those are different tools. The curve shows which.

It also makes the DAI failure visible rather than merely stated: a curve that
tracks the diagonal, and on TESLA crosses BELOW it, is an argument no bar
chart makes as well.

Writes benchmarks/roc.json. Curves are decimated to ~<=80 points because the
dashboard draws them as SVG paths and 1,947 vertices per curve is wasteful.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

MAX_POINTS = 80


def roc(values, labels, higher_is_better=True):
    """Return (points, auc). Points are [fpr, tpr] including (0,0) and (1,1).

    Ties are handled by advancing through a whole tied block before emitting a
    vertex -- otherwise a predictor with many identical scores traces a
    staircase whose area depends on input order rather than on the predictor.
    """
    sign = -1.0 if higher_is_better else 1.0
    pairs = sorted(zip((sign * float(v) for v in values), labels))
    P = sum(1 for _, y in pairs if y)
    N = len(pairs) - P
    if not P or not N:
        return [], float("nan")

    pts = [(0.0, 0.0)]
    area = tp = fp = 0
    i = 0
    while i < len(pairs):
        j = i
        while j + 1 < len(pairs) and pairs[j + 1][0] == pairs[i][0]:
            j += 1
        dtp = sum(1 for k in range(i, j + 1) if pairs[k][1])
        dfp = (j - i + 1) - dtp
        # Trapezoid across the tied block: a vertical-then-horizontal staircase
        # would over-count ties, which is exactly how AUC and a drawn ROC
        # disagree if you are careless.
        area += dfp * (tp + dtp / 2)
        tp += dtp
        fp += dfp
        pts.append((fp / N, tp / P))
        i = j + 1

    if len(pts) > MAX_POINTS:
        step = (len(pts) - 1) / (MAX_POINTS - 1)
        keep = {0, len(pts) - 1}
        keep |= {round(k * step) for k in range(MAX_POINTS)}
        pts = [pts[k] for k in sorted(keep) if k < len(pts)]
    return [[round(a, 4), round(b, 4)] for a, b in pts], area / (P * N)


def bjerregaard():
    from validate_screen import load_rows, score_all
    from neofold.screen import damped_dai

    scored = score_all(load_rows())
    for s in scored:
        s["dai"] = damped_dai(s["wt_affinity"], s["affinity"])
    y = [s["responder"] for s in scored]

    series = []
    for label, key, hib, colour in [
        ("presentation score", "presentation", True, "#2a78d6"),
        ("predicted affinity", "affinity", False, "#6da7ec"),
        ("predicted %rank", "rank", False, "#86b6ef"),
        ("DAI (mutant vs germline)", "dai", True, "#d03b3b"),
    ]:
        vals = [s[key] for s in scored]
        ok = [k for k, v in enumerate(vals) if v == v]        # drop NaN
        pts, a = roc([vals[k] for k in ok], [y[k] for k in ok], hib)
        series.append({"label": label, "colour": colour,
                       "auc": round(a, 4), "points": pts,
                       "ours": key != "dai"})
        print(f"  {label:28} AUC {a:.4f}  ({len(pts)} vertices)")
    return {"benchmark": "Bjerregaard 2017", "n": len(scored),
            "positives": sum(y), "base_rate": round(sum(y) / len(scored), 5),
            "series": series}


def tesla():
    from validate_tesla import load, score_with_mhcflurry

    rows = load()
    scored = score_with_mhcflurry(rows)
    y = [s["validated"] for s in scored]

    series = []
    for label, key, hib, colour, ours in [
        ("OUR presentation score", "our_presentation", True, "#2a78d6", True),
        ("OUR %rank", "our_rank", False, "#86b6ef", True),
        ("TESLA MEASURED affinity", "measured_affinity", False, "#fab219", False),
        ("TESLA agretopicity", "agretopicity", False, "#d03b3b", False),
    ]:
        vals = [s.get(key) for s in scored]
        ok = [k for k, v in enumerate(vals)
              if v is not None and isinstance(v, (int, float)) and v == v]
        if len(ok) < 20:
            print(f"  {label:28} SKIPPED ({len(ok)} usable)")
            continue
        pts, a = roc([vals[k] for k in ok], [y[k] for k in ok], hib)
        series.append({"label": label, "colour": colour, "auc": round(a, 4),
                       "points": pts, "ours": ours, "n": len(ok)})
        print(f"  {label:28} AUC {a:.4f}  (n={len(ok)}, {len(pts)} vertices)")
    return {"benchmark": "TESLA 2020", "n": len(scored),
            "positives": sum(y), "base_rate": round(sum(y) / len(scored), 5),
            "series": series}


def main():
    out = {}
    print("Bjerregaard 2017:")
    out["bjerregaard"] = bjerregaard()
    print("\nTESLA 2020:")
    try:
        out["tesla"] = tesla()
    except Exception as exc:                      # openpyxl / column drift
        print(f"  TESLA skipped: {exc}")
    dest = ROOT / "benchmarks" / "roc.json"
    dest.write_text(json.dumps(out, indent=2) + "\n")
    print(f"\nwrote {dest.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
