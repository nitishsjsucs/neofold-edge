"""The agent briefing is a document other agents will quote verbatim.

A number that drifts out of sync with benchmarks/ is worse there than anywhere
else in the repo, because the whole point of docs/AGENT-BRIEF.md is that a
reader never has to go and check. So the headline figures are pinned here: if a
benchmark is regenerated and a figure moves, this fails and the brief gets
updated rather than quietly becoming wrong.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
BRIEF = ROOT / "docs" / "AGENT-BRIEF.md"


def load(name):
    return json.loads((ROOT / "benchmarks" / name).read_text())


@pytest.fixture(scope="module")
def brief():
    return BRIEF.read_text()


def test_brief_exists(brief):
    assert len(brief) > 10_000, "the brief should be substantial"


@pytest.mark.parametrize("needle", [
    "0.777", "0.759", "1.41 Å", "0.965×", "2.224×",
    "2.58 Å", "2.73 Å", "53.4 TFLOPS", "38 W", "r = −0.23",
])
def test_headline_figures_present(brief, needle):
    assert needle in brief, f"{needle!r} missing from the brief"


def test_auc_matches_source(brief):
    auc = load("auc.json")["auc_overall"]
    assert f'{auc["presentation_score"]}' in brief
    assert f'{auc["dai"]}' in brief


def test_holdout_median_matches_source(brief):
    post = sorted(s["bb"] for s in load("holdout_structures.json") if s["post"])
    median = post[len(post) // 2]
    assert f"{median:.2f}" in brief, "held-out median has drifted from the brief"
    assert str(len(post)) in brief


def test_failed_filter_is_still_disclosed(brief):
    """The below-random rule must stay in the brief -- volunteering it is the
    project's differentiator, and an agent that cannot see it will omit it."""
    rules = {r["rule"]: r for r in load("screen_validation.json")["rules"]}
    dai2 = rules["DAI >= 2 ALONE"]
    assert dai2["enrichment"] < 1.0, "source data changed; revisit the claim"
    assert f'{dai2["enrichment"]}' in brief


def test_forbidden_phrasings_section_exists(brief):
    assert "Forbidden phrasings" in brief
    for banned in ["Sub-Ångström", "the box", "1 PFLOP"]:
        assert banned in brief, f"the brief should warn against {banned!r}"


def test_no_stale_accuracy_claim(brief):
    """0.42 A is the memorised-set number. It may appear only where the brief is
    explicitly telling the reader not to quote it."""
    for m in re.finditer(r"0\.42 Å", brief):
        window = brief[max(0, m.start() - 320):m.end() + 320]
        guard = r"never|not\b|training-set|memorised|memorized|do not|3. optimistic"
        assert re.search(guard, window, re.I), (
            "0.42 Å appears without the warning that it is a training-set figure")


# --------------------------------------------------- docs vs the live dashboard
# These two disagreed by 2x once (docs said ~400 candidates/hour at four nodes,
# the dashboard computed 367) because each derived the projection independently.
# A judge reading the README next to the screen would have seen it. Pinned.
def _node_rows():
    import sys
    sys.path.insert(0, str(ROOT))
    import app.main as main
    return {r["label"]: r for r in main.benchmark()["projected"]["nodes"]}


def test_hardware_doc_matches_the_dashboard_projection():
    rows = _node_rows()
    hw = (ROOT / "docs" / "HARDWARE.md").read_text()
    four = rows["4 nodes"]
    assert str(four["candidates_per_hour"]) in hw, (
        f"docs/HARDWARE.md does not state the dashboard's 4-node figure "
        f"({four['candidates_per_hour']}/hour)")
    assert f"{four['efficiency_pct']}%" in hw
    assert "~400" not in hw, "the old unreconciled projection is back"


def test_no_doc_still_quotes_the_unreconciled_projection():
    """HARDWARE.md was not the only place that said ~400."""
    rows = _node_rows()
    good = str(rows["4 nodes"]["candidates_per_hour"])
    for doc in ["README.md", "docs/HARDWARE.md", "docs/BENCHMARKS.md",
                "docs/AGENT-BRIEF.md", "docs/ARCHITECTURE.md"]:
        text = (ROOT / doc).read_text()
        for bad in ["~400", "400 candidates/hour", "400/hour"]:
            assert bad not in text, (
                f"{doc} quotes {bad}; the reconciled figure is {good}/hour")


def test_multi_node_rows_are_labelled_projections():
    for label, row in _node_rows().items():
        if row["nodes"] > 1:
            assert row["measured"] is False, (
                f"{label} is not marked a projection — we had one Nano")


def test_test_count_claims_match_reality():
    """The README badge is the first number a judge reads."""
    import re
    import subprocess
    import sys
    # -o addopts= resets the pyproject default; without it the inherited -q
    # makes this -qq, which prints per-file counts and NO total -- the regex
    # then misses, the test skips, and the drift it exists to catch sails through.
    r = subprocess.run([sys.executable, "-m", "pytest", "--collect-only",
                        "-o", "addopts=", "-q", "-p", "no:warnings"],
                       cwd=ROOT, capture_output=True, text=True)
    m = re.search(r"(\d+) tests? collected", r.stdout)
    assert m, ("could not count collected tests -- fix this rather than skipping, "
               f"or the count claims go unchecked.\n{r.stdout[-500:]}")
    n = int(m.group(1))
    for doc in ["README.md", "docs/ARCHITECTURE.md", "docs/BENCHMARKS.md",
                "docs/AGENT-BRIEF.md"]:
        for stale in re.findall(r"(\d+)[ _]tests?[ _]?(?:passing|collected)?",
                               (ROOT / doc).read_text()):
            if stale.isdigit() and 50 < int(stale) < 1000:
                assert int(stale) == n, (
                    f"{doc} claims {stale} tests, pytest collects {n}")
