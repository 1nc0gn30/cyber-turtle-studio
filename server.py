#!/usr/bin/env python3
"""
Cyber Turtle Studio — Sovereign Server Launcher.
Generative Turtle Graphics, L-Systems & AxiDraw Pen Plotter Studio on port 8129.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
SRC_DIR = BASE_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from cyber_turtle_studio.ui_server import start_server

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cyber Turtle Studio Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface (default: 127.0.0.1)")
    parser.add_argument("--port", "-p", type=int, default=8129, help="Port to listen on (default: 8129)")
    args = parser.parse_args()

    print(f"✦ Starting Cyber Turtle Studio on http://{args.host}:{args.port}")
    start_server(host=args.host, port=args.port, open_browser=False)
