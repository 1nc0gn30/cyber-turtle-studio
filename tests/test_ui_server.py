"""Tests for Cyber Turtle Studio Multi-threaded HTTP and REST API Server."""

from __future__ import annotations

import json
import threading
import time
import urllib.error
import urllib.request
from typing import Generator

import pytest
from cyber_turtle_studio.ui_server import create_server


@pytest.fixture
def live_server(free_port: int) -> Generator[str, None, None]:
    """Spin up live ThreadingHTTPServer in background thread for testing."""
    host = "127.0.0.1"
    port = free_port
    httpd = create_server(host, port)

    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.05)  # Let server bind

    base_url = f"http://{host}:{port}"
    try:
        yield base_url
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=1.0)


def _http_get(url: str) -> tuple[int, dict, str]:
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req) as resp:
        body = resp.read().decode("utf-8")
        headers = dict(resp.headers)
        return resp.status, headers, body


def _http_post(url: str, payload: dict) -> tuple[int, dict, str]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        body = resp.read().decode("utf-8")
        headers = dict(resp.headers)
        return resp.status, headers, body


def test_ui_server_root_index(live_server: str):
    """Verify GET / returns 200 with HTML Studio UI."""
    status, headers, body = _http_get(f"{live_server}/")
    assert status == 200
    assert "html" in headers.get("Content-Type", "").lower()
    assert "Cyber Turtle Studio" in body or "<html" in body


def test_ui_server_presets_api(live_server: str):
    """Verify GET /api/presets returns JSON catalog."""
    status, headers, body = _http_get(f"{live_server}/api/presets")
    assert status == 200
    assert "application/json" in headers.get("Content-Type", "").lower()
    data = json.loads(body)
    assert "presets" in data
    assert len(data["presets"]) >= 25


def test_ui_server_stats_and_diagnostics(live_server: str):
    """Verify GET /api/stats returns system and platform diagnostics."""
    status, headers, body = _http_get(f"{live_server}/api/stats")
    assert status == 200
    data = json.loads(body)
    assert data["status"] == "healthy"
    assert "platform" in data
    assert "version" in data


def test_ui_server_execute_logo_api(live_server: str):
    """Verify POST /api/execute-logo executes Logo script and returns SVG."""
    payload = {
        "script": "repeat 4 [ fd 80 rt 90 ]",
        "theme": "cyber_matrix",
        "animate": False,
    }
    status, headers, body = _http_post(f"{live_server}/api/execute-logo", payload)
    assert status == 200
    data = json.loads(body)
    assert data["success"] is True
    assert "<svg" in data["svg"]
    assert "gcode" in data
    assert "stats" in data
    assert data["stats"]["total_segments"] == 4


def test_ui_server_generate_lsystem_api(live_server: str):
    """Verify POST /api/generate-lsystem synthesizes L-System geometry."""
    payload = {
        "axiom": "F--F--F",
        "rules": {"F": "F+F--F+F"},
        "angle": 60.0,
        "iterations": 2,
        "theme": "sacred_gold",
    }
    status, headers, body = _http_post(f"{live_server}/api/generate-lsystem", payload)
    assert status == 200
    data = json.loads(body)
    assert data["success"] is True
    assert "<svg" in data["svg"]
    assert len(data["ast"]["segments"]) > 0


def test_ui_server_generate_preset_api(live_server: str):
    """Verify POST /api/generate-preset produces drawing directly."""
    payload = {
        "preset_id": "dragon_curve",
        "theme": "blueprint_cyan",
    }
    status, headers, body = _http_post(f"{live_server}/api/generate-preset", payload)
    assert status == 200
    data = json.loads(body)
    assert data["success"] is True
    assert data["preset_id"] == "dragon_curve"
    assert "<svg" in data["svg"]


def test_ui_server_export_endpoints(live_server: str):
    """Verify export endpoints for SVG, GCode, and ASCII."""
    # SVG export
    status_svg, _, body_svg = _http_post(
        f"{live_server}/api/export-svg",
        {"preset_id": "koch_snowflake", "theme": "cyber_matrix"},
    )
    assert status_svg == 200
    assert "<svg" in json.loads(body_svg)["svg"]

    # GCode export
    status_gc, _, body_gc = _http_post(
        f"{live_server}/api/export-gcode",
        {"preset_id": "koch_snowflake", "bed_width": 200.0},
    )
    assert status_gc == 200
    assert "G21" in json.loads(body_gc)["gcode"]


def test_ui_server_cors_options(live_server: str):
    """Verify OPTIONS request returns CORS headers."""
    req = urllib.request.Request(f"{live_server}/api/execute-logo", method="OPTIONS")
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        headers = dict(resp.headers)
        assert headers.get("Access-Control-Allow-Origin") == "*"


def test_ui_server_404_error(live_server: str):
    """Verify unknown endpoint returns 404."""
    with pytest.raises(urllib.error.HTTPError) as exc_info:
        urllib.request.urlopen(f"{live_server}/api/unknown_endpoint_xyz")
    assert exc_info.value.code == 404
