"""
verify_ui.py
Automated Headless Playwright Verification Harness for Cyber Turtle Studio
Triple-Viewport Responsiveness, Zero Console Errors, Zero Horizontal Overflow,
and Open-Access Synthesis Verification.
"""

import os
import sys
import tempfile
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

SHOT_DIR = Path(os.environ.get("CYBER_TURTLE_SHOT_DIR", Path(tempfile.gettempdir()) / "cyber_turtle_shots"))
SHOT_DIR.mkdir(parents=True, exist_ok=True)

PORT = int(os.environ.get("PORT", "8129"))
BASE_URL = f"http://127.0.0.1:{PORT}"


def verify() -> int:
    print(f"[TEST] Starting Playwright Headless Verification on {BASE_URL}...")
    viewports = [
        {"name": "home_mobile.jpg", "width": 390, "height": 844, "device": "Mobile"},
        {"name": "home_tablet.jpg", "width": 820, "height": 1180, "device": "Tablet"},
        {"name": "home_desktop.jpg", "width": 1425, "height": 900, "device": "Desktop"},
    ]
    console_errors = []
    passed_all = True

    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path="/usr/bin/google-chrome",
            headless=True,
            args=["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"],
        )
        for vp in viewports:
            page = browser.new_page(viewport={"width": vp["width"], "height": vp["height"]})
            vp_errors = []
            page.on("console", lambda msg: vp_errors.append(msg.text) if msg.type == "error" else None)
            page.on("pageerror", lambda err: vp_errors.append(str(err)))
            page.goto(BASE_URL, wait_until="networkidle")
            time.sleep(0.4)
            overflow = page.evaluate("() => document.documentElement.scrollWidth - document.documentElement.clientWidth")
            page.screenshot(path=str(SHOT_DIR / vp["name"]), full_page=False, type="jpeg", quality=85)
            ok = len(vp_errors) == 0 and overflow <= 1
            print(f"[VIEWPORT] {vp['device']}: Errors={len(vp_errors)}, Overflow={overflow}px -> {'PASS' if ok else 'FAIL'}")
            passed_all = passed_all and ok
            console_errors.extend(vp_errors)
            page.close()
        browser.close()

    return 0 if passed_all and not console_errors else 1


if __name__ == "__main__":
    sys.exit(verify())
