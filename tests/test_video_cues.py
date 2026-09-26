"""The demo video's pointer contract.

Every callout in the film is placed from a measured getBoundingClientRect and
must land under a phrase the narration actually says. Both halves drift easily:
a reworded line silently orphans a marker, and a re-captured screenshot silently
invalidates a region. This pins them.
"""
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"


@pytest.fixture(scope="module")
def plates():
    sys.path.insert(0, str(SCRIPTS))
    try:
        import video_plates
        return video_plates
    except SystemExit as exc:            # video_theme refuses to load without RAQM
        pytest.skip(f"video toolchain unavailable: {exc}")


def test_every_cue_resolves(plates):
    assert plates.check() == 0, "see the ✗ lines above"


def test_check_is_reachable_from_the_cli():
    """The command scripts/measure_regions.md tells a contributor to run."""
    r = subprocess.run([sys.executable, "video_plates.py", "--check"],
                       cwd=SCRIPTS, capture_output=True, text=True)
    if "RAQM" in r.stderr:
        pytest.skip("video toolchain unavailable")
    assert r.returncode == 0, r.stdout + r.stderr


def test_check_actually_fails_on_a_broken_region(plates):
    """A green check is only worth something if red is reachable."""
    import video_scenes as scenes
    capture, cues = scenes.CUES["dashboard"]
    scenes.CUES["dashboard"] = (capture, [
        dict(region="no_such_element", phrase=cues[0]["phrase"], caption="x")])
    try:
        assert plates.check() == 1, "check() passed an unmeasured region"
    finally:
        scenes.CUES["dashboard"] = (capture, cues)


def test_documented_commands_exist():
    doc = (SCRIPTS / "measure_regions.md").read_text()
    for cmd in ["scripts/video_plates.py --check", "scripts/make_video.py",
                "./scripts/serve.sh"]:
        assert cmd in doc
    for path in ["scripts/video_plates.py", "scripts/make_video.py",
                 "scripts/serve.sh", "video/app-regions.json"]:
        assert (ROOT / path).exists(), f"{path} is referenced but missing"
