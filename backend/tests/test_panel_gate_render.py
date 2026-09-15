"""Tests for deploy/app/render-panel-gate.sh."""

from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "deploy" / "app" / "render-panel-gate.sh"


def _run(tmp_path: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    map_path = tmp_path / "map.conf"
    check_path = tmp_path / "check.conf"
    loc_path = tmp_path / "locations.conf"
    auth_check_path = tmp_path / "auth-check.conf"
    full_env = {
        **os.environ,
        "PANEL_GATE_MAP": str(map_path),
        "PANEL_GATE_CHECK": str(check_path),
        "PANEL_AUTH_CHECK": str(auth_check_path),
        "PANEL_GATE_LOCATIONS": str(loc_path),
        **env,
    }
    return subprocess.run(
        ["bash", str(SCRIPT)],
        env=full_env,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.fixture(autouse=True)
def _executable():
    if not SCRIPT.is_file():
        pytest.skip("render-panel-gate.sh missing")
    SCRIPT.chmod(SCRIPT.stat().st_mode | stat.S_IXUSR)


def test_empty_entrance_unlocks(tmp_path: Path):
    result = _run(tmp_path, {"PANEL_ENTRANCE": "", "JWT_SECRET": "test-secret"})
    assert result.returncode == 0, result.stderr
    assert "default 1" in (tmp_path / "map.conf").read_text()
    assert (tmp_path / "check.conf").read_text() == ""
    assert (tmp_path / "auth-check.conf").read_text() == ""
    assert (tmp_path / "locations.conf").read_text() == ""


def test_enabled_entrance_writes_cookie_redirect(tmp_path: Path):
    result = _run(
        tmp_path,
        {"PANEL_ENTRANCE": "a1b2c3d4e5f6", "JWT_SECRET": "test-secret"},
    )
    assert result.returncode == 0, result.stderr
    locations = (tmp_path / "locations.conf").read_text()
    assert "location = /a1b2c3d4e5f6 {" in locations
    assert "return 302 /login;" in locations
    assert "waf_panel_gate=" in locations
    check = (tmp_path / "check.conf").read_text()
    assert "return 404;" in check
    assert "$panel_gate_ok" in check
    auth_check = (tmp_path / "auth-check.conf").read_text()
    assert "$panel_app_ok" in auth_check
    mapping = (tmp_path / "map.conf").read_text()
    assert "cookie_waf_panel_gate" in mapping
    assert "cookie_waf_panel_session" in mapping
    assert "panel_app_ok" in mapping
    assert "default 0" in mapping


def test_strips_slashes_and_whitespace(tmp_path: Path):
    result = _run(
        tmp_path,
        {"PANEL_ENTRANCE": "  /gate_ok/  ", "JWT_SECRET": "test-secret"},
    )
    assert result.returncode == 0, result.stderr
    assert "location = /gate_ok {" in (tmp_path / "locations.conf").read_text()


def test_rejects_reserved_path(tmp_path: Path):
    result = _run(tmp_path, {"PANEL_ENTRANCE": "login", "JWT_SECRET": "test-secret"})
    assert result.returncode != 0
    assert "保留路径" in result.stderr


def test_rejects_invalid_characters(tmp_path: Path):
    result = _run(tmp_path, {"PANEL_ENTRANCE": "../etc", "JWT_SECRET": "test-secret"})
    assert result.returncode != 0
    assert "无效" in result.stderr


def test_requires_jwt_secret_when_enabled(tmp_path: Path):
    result = _run(tmp_path, {"PANEL_ENTRANCE": "secretpath", "JWT_SECRET": ""})
    assert result.returncode != 0
    assert "JWT_SECRET" in result.stderr
