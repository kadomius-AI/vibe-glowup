"""End-to-end Glow Up on synthetic footage: plan + QA files are written, layout and format are right."""
import json
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def _run(*args):
    return subprocess.run([sys.executable, str(SCRIPTS / "glowup.py"), *map(str, args)], capture_output=True, text=True)


def test_glowup_webcam_to_vertical(tmp_path, webcam_closeup, wide_talking_head):
    out = tmp_path / "g.mp4"
    r = _run("apply", webcam_closeup, "--ref", wide_talking_head, "--out", out, "--format", "vertical",
             "--captions", "none", "--upscale", "off", "--restore-faces", "0", "--tighten", "0", "--allow-qa-fail")
    assert r.returncode == 0, r.stderr[-2000:]
    plan = json.loads(Path(str(out) + ".plan.json").read_text())
    qa = json.loads(Path(str(out) + ".qa.json").read_text())
    assert plan["schema"] == "vibekit.plan/1" and plan["decisions"]["layout"] == "fill"
    assert "grade" in plan["decisions"] and plan["inputs"]["source"]["sha256"]
    for k in ("render", "dimensions", "fps", "black"):
        assert qa["checks"][k]["ok"], (k, qa["checks"][k])


def test_render_plan_reproduces(tmp_path, webcam_closeup, wide_talking_head):
    out = tmp_path / "g.mp4"
    _run("apply", webcam_closeup, "--ref", wide_talking_head, "--out", out, "--format", "vertical", "--captions", "none",
         "--upscale", "off", "--restore-faces", "0", "--tighten", "0", "--allow-qa-fail")
    out2 = tmp_path / "g2.mp4"
    r = _run("render-plan", str(out) + ".plan.json", "--out", out2)
    assert out2.exists(), r.stderr[-2000:]
    a = json.loads(Path(str(out) + ".plan.json").read_text())["decisions"]["grade"]
    b = json.loads(Path(str(out2) + ".plan.json").read_text())["decisions"]["grade"]
    assert a == b, "same plan must give the same grade decisions"
