"""Embedded Multi-threaded HTTP and REST API Server for Cyber Turtle Studio.

Serves the Cyber Turtle Studio web application (design influenced by Material 3 tokens) and exposes high-performance
REST APIs for executing Logo scripts, synthesizing L-System fractals, and exporting
vector SVGs, CNC G-Code, and terminal ASCII art.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import urllib.parse
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from . import __version__
from .catalog import (
    PRESETS,
    generate_pattern,
    get_catalog_summary,
    get_preset,
    list_categories,
    list_presets,
    list_tags,
)
from .compat import get_platform_info, read_text_safe
from .exporters import (
    ASCIIExporter,
    GCodeExporter,
    SVGExporter,
    export_ascii,
    export_gcode,
    export_svg,
)
from .lsystem_engine import generate_lsystem
from .models import DrawingAST
from .toolpath_optimizer import ToolpathOptimizer, render_toolpath_comparison_svg
from .turtle_engine import execute_logo

EMBEDDED_HTML_FALLBACK = """<!DOCTYPE html>
<html lang="en" data-theme="light">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Cyber Turtle Studio (Fallback)</title>
  <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&family=Google+Sans:wght@400;500;700&family=Roboto+Mono:wght@400;500&display=swap" rel="stylesheet">
  <style>
    :root {
      --md-primary: #1a73e8;
      --md-surface: #ffffff;
      --md-bg: #f8f9fa;
      --md-outline: #dadce0;
    }
    body { font-family: 'Google Sans', Roboto, sans-serif; background: var(--md-bg); margin: 0; padding: 20px; }
    .card { background: var(--md-surface); border: 1px solid var(--md-outline); border-radius: 16px; padding: 24px; max-width: 800px; margin: 0 auto; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
    h1 { color: var(--md-primary); margin-bottom: 12px; }
    textarea { width: 100%; height: 120px; font-family: 'Roboto Mono', monospace; padding: 10px; border-radius: 8px; border: 1px solid var(--md-outline); box-sizing: border-box; }
    button { background: var(--md-primary); color: #fff; border: none; border-radius: 20px; padding: 10px 20px; font-weight: 500; cursor: pointer; margin-top: 10px; }
    #view { margin-top: 20px; background: #050805; padding: 16px; border-radius: 8px; min-height: 200px; display: flex; align-items: center; justify-content: center; }
  </style>
</head>
<body>
  <div class="card">
    <h1>🐢 Cyber Turtle Studio</h1>
    <p>Embedded server is operational. Public assets directory not found; serving fallback interface.</p>
    <textarea id="code">repeat 36 [ repeat 4 [ fd 100 rt 90 ] rt 10 ]</textarea>
    <button onclick="run()">Synthesize Logo</button>
    <div id="view"></div>
  </div>
  <script>
    async function run() {
      const script = document.getElementById('code').value;
      const res = await fetch('/api/execute-logo', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ script, theme: 'cyber_matrix' })
      });
      const data = await res.json();
      document.getElementById('view').innerHTML = data.svg;
    }
    run();
  </script>
</body>
</html>
"""


class StudioHTTPRequestHandler(SimpleHTTPRequestHandler):
    """Custom HTTP Request Handler with REST API routes, CORS headers, and static UI serving."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.public_dir = self._find_public_dir()
        super().__init__(*args, directory=str(self.public_dir) if self.public_dir.exists() else None, **kwargs)

    @staticmethod
    def _find_public_dir() -> Path:
        """Locate the public assets folder across package installs, development trees, and current working dir."""
        candidates = [
            Path(__file__).parent.parent.parent / "public",
            Path.cwd() / "public",
            Path(__file__).parent / "public",
        ]
        for c in candidates:
            if c.is_dir() and (c / "index.html").is_file():
                return c.resolve()
        for c in candidates:
            if c.is_dir():
                return c.resolve()
        return Path.cwd() / "public"

    def _set_cors_headers(self) -> None:
        """Set cross-origin resource sharing headers for web clients and MCP bridges."""
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS, HEAD")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Requested-With")

    def do_OPTIONS(self) -> None:
        """Handle CORS pre-flight requests."""
        self.send_response(200)
        self._set_cors_headers()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self) -> None:
        """Route GET requests for static UI files, presets catalog, and diagnostics."""
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query_params = urllib.parse.parse_qs(parsed.query)

        if path in ("/", "/index.html"):
            index_file = self.public_dir / "index.html"
            if index_file.is_file():
                content = index_file.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(content)))
                self._set_cors_headers()
                self.end_headers()
                self.wfile.write(content)
                return
            else:
                fallback = EMBEDDED_HTML_FALLBACK.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(fallback)))
                self._set_cors_headers()
                self.end_headers()
                self.wfile.write(fallback)
                return

        elif path in ("/api/presets", "/api/catalog"):
            category_filter = query_params.get("category", [None])[0]
            type_filter = query_params.get("type", [None])[0]
            tag_filter = query_params.get("tag", [None])[0]

            presets_list = list_presets(category=category_filter, drawing_type=type_filter, tag=tag_filter)
            presets_dicts = [
                {
                    "id": p.id,
                    "title": p.title,
                    "category": p.category,
                    "type": p.type,
                    "description": p.description,
                    "difficulty": p.difficulty,
                    "default_parameters": p.default_parameters,
                    "tags": p.tags,
                }
                for p in presets_list
            ]
            response = {
                "summary": get_catalog_summary(),
                "categories": list_categories(),
                "tags": list_tags(),
                "presets": presets_dicts,
                "count": len(presets_dicts),
            }
            self._send_json(response)
            return

        elif path in ("/api/stats", "/api/diagnostics", "/api/health"):
            stats = {
                "status": "healthy",
                "version": __version__,
                "server": "Cyber Turtle Studio ThreadingHTTPServer",
                "summary": get_catalog_summary(),
                "platform": get_platform_info().__dict__,
            }
            self._send_json(stats)
            return

        # Fallback to standard static file server
        super().do_GET()

    def do_POST(self) -> None:
        """Route POST requests for Logo execution, L-System synthesis, and exporters."""
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        content_length = int(self.headers.get("Content-Length", 0))
        body_bytes = self.rfile.read(content_length)
        try:
            req_data = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
        except Exception as e:
            self._send_error(400, f"Invalid JSON payload: {e}")
            return

        try:
            if path == "/api/execute-logo":
                script = req_data.get("script", "repeat 4 [ fd 100 rt 90 ]")
                color = req_data.get("color", "#00f0ff")
                width = float(req_data.get("width", 1.5))
                theme = req_data.get("theme", "cyber_matrix")
                animate = bool(req_data.get("animate", False))

                ast = execute_logo(script)
                svg_str = export_svg(ast, theme=theme, animate=animate)
                gcode_str = export_gcode(ast)

                response = {
                    "success": True,
                    "title": ast.title,
                    "ast": ast.to_dict(),
                    "stats": ast.stats(),
                    "svg": svg_str,
                    "gcode": gcode_str,
                }
                self._send_json(response)

            elif path == "/api/generate-lsystem":
                axiom = req_data.get("axiom", "F--F--F")
                rules = req_data.get("rules", {"F": "F+F--F+F"})
                iterations = int(req_data.get("iterations", 3))
                angle_deg = float(req_data.get("angle_deg", req_data.get("angle", 60.0)))
                step_size = float(req_data.get("step_size", req_data.get("step", 10.0)))
                initial_heading = float(req_data.get("initial_heading", req_data.get("heading", 0.0)))
                theme = req_data.get("theme", "cyber_matrix")
                animate = bool(req_data.get("animate", False))

                ast = generate_lsystem(
                    axiom=axiom,
                    rules=rules,
                    iterations=iterations,
                    angle_deg=angle_deg,
                    step_size=step_size,
                    initial_heading_deg=initial_heading,
                )
                svg_str = export_svg(ast, theme=theme, animate=animate)
                gcode_str = export_gcode(ast)

                response = {
                    "success": True,
                    "title": ast.title,
                    "ast": ast.to_dict(),
                    "stats": ast.stats(),
                    "svg": svg_str,
                    "gcode": gcode_str,
                }
                self._send_json(response)

            elif path == "/api/generate-preset":
                preset_id = req_data.get("preset_id", "koch_snowflake")
                theme = req_data.get("theme", "cyber_matrix")
                animate = bool(req_data.get("animate", False))

                ast = generate_pattern(preset_id)
                svg_str = export_svg(ast, theme=theme, animate=animate)
                gcode_str = export_gcode(ast)

                response = {
                    "success": True,
                    "preset_id": preset_id,
                    "title": ast.title,
                    "ast": ast.to_dict(),
                    "stats": ast.stats(),
                    "svg": svg_str,
                    "gcode": gcode_str,
                }
                self._send_json(response)

            elif path == "/api/export-svg":
                ast = self._extract_or_generate_ast(req_data)
                theme = req_data.get("theme", "cyber_matrix")
                animate = bool(req_data.get("animate", False))
                duration = float(req_data.get("duration", 4.0))

                svg_content = export_svg(ast, theme=theme, animate=animate, duration_sec=duration)
                if req_data.get("as_download", False):
                    raw = svg_content.encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "image/svg+xml")
                    self.send_header("Content-Disposition", 'attachment; filename="drawing.svg"')
                    self.send_header("Content-Length", str(len(raw)))
                    self._set_cors_headers()
                    self.end_headers()
                    self.wfile.write(raw)
                else:
                    self._send_json({"success": True, "svg": svg_content})

            elif path == "/api/export-gcode":
                ast = self._extract_or_generate_ast(req_data)
                bed_w = float(req_data.get("bed_width", 200.0))
                bed_h = float(req_data.get("bed_height", 200.0))
                feed_draw = float(req_data.get("feed_draw", 1200.0))
                feed_travel = float(req_data.get("feed_travel", 3000.0))
                z_up = float(req_data.get("z_up", 5.0))
                z_down = float(req_data.get("z_down", 0.0))
                laser_mode = bool(req_data.get("laser_mode", False))

                gcode_content = export_gcode(
                    ast,
                    bed_width=bed_w,
                    bed_height=bed_h,
                    feed_draw=feed_draw,
                    feed_travel=feed_travel,
                    z_up=z_up,
                    z_down=z_down,
                    laser_mode=laser_mode,
                )
                if req_data.get("as_download", False):
                    raw = gcode_content.encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "text/plain")
                    self.send_header("Content-Disposition", 'attachment; filename="drawing.gcode"')
                    self.send_header("Content-Length", str(len(raw)))
                    self._set_cors_headers()
                    self.end_headers()
                    self.wfile.write(raw)
                else:
                    self._send_json({"success": True, "gcode": gcode_content})

            elif path == "/api/export-ascii":
                ast = self._extract_or_generate_ast(req_data)
                width = int(req_data.get("width", 80))
                height = int(req_data.get("height", 40))
                ascii_text = export_ascii(ast, width=width, height=height)
                self._send_json({"success": True, "ascii": ascii_text})

            elif path == "/api/optimize-toolpath":
                ast = self._extract_or_generate_ast(req_data)
                draw_feed = float(req_data.get("draw_feedrate", 1200.0))
                travel_feed = float(req_data.get("travel_feedrate", 3000.0))

                optimizer = ToolpathOptimizer(draw_feedrate_mm_min=draw_feed, travel_feedrate_mm_min=travel_feed)
                opt_ast, report = optimizer.optimize_toolpath(ast)

                comp_svg = render_toolpath_comparison_svg(ast, opt_ast)
                opt_gcode = export_gcode(opt_ast)

                self._send_json({
                    "success": True,
                    "report": report.to_dict(),
                    "comparison_svg": comp_svg,
                    "optimized_gcode": opt_gcode,
                })

            else:
                self._send_error(404, f"API endpoint not found: {path}")

        except Exception as err:
            self._send_error(500, f"Error processing {path}: {str(err)}")

    def _extract_or_generate_ast(self, data: Dict[str, Any]) -> DrawingAST:
        """Helper to resolve a DrawingAST from payload or preset."""
        if "ast" in data and isinstance(data["ast"], dict):
            return DrawingAST.from_dict(data["ast"])
        if "preset_id" in data:
            return generate_pattern(data["preset_id"])
        if "script" in data:
            return execute_logo(data["script"])
        if "axiom" in data and "rules" in data:
            return generate_lsystem(
                axiom=data["axiom"],
                rules=data["rules"],
                iterations=int(data.get("iterations", 3)),
                angle_deg=float(data.get("angle_deg", 60.0)),
            )
        return generate_pattern("koch_snowflake")

    def _send_json(self, data: Any, status: int = 200) -> None:
        """Serialize and send JSON response with CORS headers."""
        body = json.dumps(data, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._set_cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def _send_error(self, status: int, message: str) -> None:
        """Send standardized JSON error response."""
        self._send_json({"success": False, "error": message, "status": status}, status=status)

    def log_message(self, format: str, *args: Any) -> None:
        """Quiet standard request logging in production unless explicitly debugging."""
        if os.environ.get("CYBER_TURTLE_DEBUG"):
            super().log_message(format, *args)


def create_server(host: str = "127.0.0.1", port: int = 8080) -> ThreadingHTTPServer:
    """Create and return configured ThreadingHTTPServer instance."""
    server_addr = (host, port)
    return ThreadingHTTPServer(server_addr, StudioHTTPRequestHandler)


def start_server(
    host: str = "127.0.0.1",
    port: int = 8080,
    open_browser: bool = False,
    auto_port: bool = True,
) -> None:
    """Start the multi-threaded Cyber Turtle Studio UI server (design influenced by Material 3 tokens)."""
    current_port = port
    max_attempts = 10 if auto_port else 1
    httpd: Optional[ThreadingHTTPServer] = None

    for attempt in range(max_attempts):
        try:
            httpd = create_server(host, current_port)
            break
        except OSError:
            if not auto_port:
                raise
            current_port += 1

    if httpd is None:
        raise RuntimeError(f"Could not bind server to {host}:{port}-{current_port}")

    url = f"http://{host}:{current_port}/"
    print(f"🚀 Cyber Turtle Studio running at: {url}")
    print("   Press Ctrl+C to stop.")

    if open_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Cyber Turtle Studio server...")
    finally:
        httpd.server_close()


def main() -> None:
    """CLI entry point for running ui_server directly."""
    parser = argparse.ArgumentParser(description="Cyber Turtle Studio UI Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host address to bind (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8080, help="Port to listen on (default: 8080)")
    parser.add_argument("--no-browser", action="store_true", help="Do not open web browser automatically")
    args = parser.parse_args()

    start_server(host=args.host, port=args.port, open_browser=not args.no_browser)


if __name__ == "__main__":
    main()
