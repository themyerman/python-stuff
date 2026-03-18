"""Smoke tests for examples/developer-journey/ascp_pr_checks.py."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "examples" / "developer-journey" / "ascp_pr_checks.py"


def test_pr_checks_exits_2_without_required_env(tmp_path):
    r = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        env={"PATH": __import__("os").environ.get("PATH", "")},
    )
    assert r.returncode == 2
    assert "ASCP_BASE_URL" in r.stderr or "ASCP_TOKEN" in r.stderr or "ASCP_TENANT_ID" in r.stderr


def test_pr_checks_exits_2_without_target_when_assurance(tmp_path):
    env = {
        **__import__("os").environ,
        "ASCP_BASE_URL": "http://127.0.0.1:9",
        "ASCP_TOKEN": "x",
        "ASCP_TENANT_ID": "t",
    }
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "--assurance-only"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        env=env,
    )
    assert r.returncode == 2
    assert "ASCP_ASSURANCE_TARGET_URL" in r.stderr


def test_supply_only_skips_assurance(tmp_path, monkeypatch):
    env = {
        **__import__("os").environ,
        "ASCP_BASE_URL": "http://127.0.0.1:9",
        "ASCP_TOKEN": "x",
        "ASCP_TENANT_ID": "t",
    }
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "--supply-only"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        env=env,
    )
    assert r.returncode == 0
    assert "Supply-only" in r.stdout or "done" in r.stdout
