"""Cross-platform compatibility and system utility layer for cyber-turtle-studio.

Provides safe atomic file operations, cross-platform path normalization,
encoding fallbacks, and terminal/environment detection for Linux, macOS,
Windows, and Android (Termux).
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Sequence, Tuple, Union


@dataclass(frozen=True)
class PlatformInfo:
    """System platform and terminal capability metadata."""

    os_name: str
    is_windows: bool
    is_macos: bool
    is_linux: bool
    is_termux: bool
    python_version: Tuple[int, int, int]
    supports_ansi_color: bool
    supports_unicode: bool
    default_encoding: str


def is_windows() -> bool:
    return sys.platform.startswith("win") or os.name == "nt"


def is_macos() -> bool:
    return sys.platform.startswith("darwin")


def is_termux() -> bool:
    return "TERMUX_VERSION" in os.environ or "/data/data/com.termux" in os.environ.get("PREFIX", "")


def is_linux() -> bool:
    return (sys.platform.startswith("linux") or "linux" in sys.platform) and not is_termux()


def get_platform_info() -> PlatformInfo:
    """Detect platform details and terminal capabilities."""
    sys_platform = sys.platform.lower()
    is_win = is_windows()
    is_mac = is_macos()
    is_tmx = is_termux()
    is_lin = is_linux()

    os_label = "windows" if is_win else ("macos" if is_mac else ("termux" if is_tmx else "linux"))

    # ANSI color detection
    has_color = False
    if not is_win or "ANSICON" in os.environ or "WT_SESSION" in os.environ or os.environ.get("TERM_PROGRAM") == "vscode":
        has_color = True
    if os.environ.get("COLORTERM") in ("truecolor", "24bit"):
        has_color = True
    if os.environ.get("NO_COLOR"):
        has_color = False

    # Unicode capability
    enc = sys.getdefaultencoding().lower()
    supports_uni = "utf" in enc or not is_win or bool(os.environ.get("PYTHONIOENCODING", "").lower().startswith("utf"))

    return PlatformInfo(
        os_name=os_label,
        is_windows=is_win,
        is_macos=is_mac,
        is_linux=is_lin,
        is_termux=is_tmx,
        python_version=(sys.version_info.major, sys.version_info.minor, sys.version_info.micro),
        supports_ansi_color=has_color,
        supports_unicode=supports_uni,
        default_encoding=sys.getdefaultencoding(),
    )


def safe_path(raw_path: Union[str, Path]) -> Path:
    """Normalize and expand file paths across Linux, macOS, Windows, and Termux."""
    path_str = str(raw_path).strip()
    if not path_str:
        return Path.cwd()

    expanded = os.path.expandvars(path_str)
    expanded = os.path.expanduser(expanded)
    return Path(expanded).resolve()


def normalize_path(path: Union[str, Path]) -> Path:
    """Alias for safe_path for standard API compliance."""
    return safe_path(path)


def ensure_parent_dir(path: Union[str, Path]) -> Path:
    """Ensure that the parent directory for a target path exists."""
    p = safe_path(path)
    parent = p.parent
    if not parent.exists():
        parent.mkdir(parents=True, exist_ok=True)
    return p


def atomic_write_text(
    path: Union[str, Path],
    content: str,
    encoding: str = "utf-8",
    errors: str = "strict",
) -> Path:
    """Atomically write text content to a file."""
    target = safe_path(path)
    ensure_parent_dir(target)

    parent_dir = target.parent
    temp_prefix = f".tmp_{target.name}_"

    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding=encoding,
        errors=errors,
        dir=parent_dir,
        prefix=temp_prefix,
        delete=False,
    ) as tf:
        temp_path = Path(tf.name)
        tf.write(content)
        tf.flush()
        os.fsync(tf.fileno())

    try:
        os.replace(temp_path, target)
    except Exception:
        if temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass
        raise

    return target


def atomic_write_bytes(
    path: Union[str, Path],
    data: bytes,
) -> Path:
    """Atomically write binary bytes to a file."""
    target = safe_path(path)
    ensure_parent_dir(target)

    parent_dir = target.parent
    temp_prefix = f".tmp_{target.name}_"

    with tempfile.NamedTemporaryFile(
        mode="wb",
        dir=parent_dir,
        prefix=temp_prefix,
        delete=False,
    ) as tf:
        temp_path = Path(tf.name)
        tf.write(data)
        tf.flush()
        os.fsync(tf.fileno())

    try:
        os.replace(temp_path, target)
    except Exception:
        if temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass
        raise

    return target


def read_text_safe(
    path: Union[str, Path],
    default: str = "",
    primary_encoding: str = "utf-8",
    fallback_encodings: Sequence[str] = ("utf-8-sig", "latin-1", "cp1252"),
) -> str:
    """Read text from file safely with fallback encodings, returning default on missing file."""
    try:
        p = safe_path(path)
        if not p.is_file():
            return default
        raw = p.read_bytes()
        for enc in (primary_encoding, *fallback_encodings):
            try:
                return raw.decode(enc)
            except Exception:
                continue
        return raw.decode("utf-8", errors="replace")
    except Exception:
        return default


def read_text_with_fallback(
    path: Union[str, Path],
    primary_encoding: str = "utf-8",
    fallback_encodings: Sequence[str] = ("utf-8-sig", "latin-1", "cp1252"),
) -> str:
    """Read a text file trying the primary encoding, followed by fallback encodings."""
    p = safe_path(path)
    if not p.is_file():
        raise FileNotFoundError(f"File not found: {p}")

    encodings_to_try = [primary_encoding] + [e for e in fallback_encodings if e != primary_encoding]
    raw_bytes = p.read_bytes()

    for enc in encodings_to_try:
        try:
            return raw_bytes.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue

    return raw_bytes.decode("utf-8", errors="replace")


def read_json_safe(path: Union[str, Path], default: Any = None) -> Any:
    """Read and parse JSON from a file, returning default on error or missing file."""
    text = read_text_safe(path, default="")
    if not text.strip():
        return default if default is not None else {}
    try:
        return json.loads(text)
    except Exception:
        return default if default is not None else {}


def write_json_safe(path: Union[str, Path], data: Any, indent: int = 2) -> Path:
    """Atomically write JSON-serializable data to a file."""
    content = json.dumps(data, indent=indent, default=str) + "\n"
    return atomic_write_text(path, content)


def safe_delete(path: Union[str, Path]) -> bool:
    """Safely delete a file without raising if it does not exist."""
    try:
        p = safe_path(path)
        if p.is_file() or p.is_symlink():
            p.unlink()
            return True
        return False
    except Exception:
        return False
