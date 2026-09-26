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
