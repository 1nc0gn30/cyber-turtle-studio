"""Tests for cross-platform compatibility and safe atomic file utilities."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from cyber_turtle_studio.compat import (
    PlatformInfo,
    atomic_write_bytes,
    atomic_write_text,
    get_platform_info,
    is_linux,
    is_macos,
    is_termux,
    is_windows,
    normalize_path,
    read_json_safe,
    read_text_safe,
    read_text_with_fallback,
    safe_delete,
    safe_path,
    write_json_safe,
)


def test_platform_detection():
    """Verify platform detection functions return boolean flags."""
    info = get_platform_info()
    assert isinstance(info, PlatformInfo)
    assert info.os_name in ("linux", "macos", "windows", "termux")
    assert isinstance(info.is_windows, bool)
    assert isinstance(info.is_macos, bool)
    assert isinstance(info.is_linux, bool)
    assert isinstance(info.is_termux, bool)
    assert len(info.python_version) == 3
    assert isinstance(info.supports_ansi_color, bool)
    assert isinstance(info.supports_unicode, bool)


def test_safe_path_normalization(temp_dir: Path):
    """Verify path expansion and normalization."""
    p = safe_path(str(temp_dir))
    assert isinstance(p, Path)
    assert p.is_dir()
    assert normalize_path(str(temp_dir)) == p

    # Test empty string returns cwd
    assert safe_path("").resolve() == Path.cwd().resolve()


def test_atomic_write_text_and_read(temp_dir: Path):
    """Verify atomic text writing and safe reading with fallbacks."""
    target_file = temp_dir / "subdir" / "test_file.txt"
    content = "Hello Cyber Turtle Studio! 🐢⚡"

    # Write text atomically (should auto-create parent directory)
    res_path = atomic_write_text(target_file, content)
    assert res_path.exists()
    assert res_path.is_file()

    # Read back with safe reader
    read_back = read_text_safe(target_file)
    assert read_back == content

    # Read with fallback
    read_fb = read_text_with_fallback(target_file)
    assert read_fb == content


def test_atomic_write_bytes(temp_dir: Path):
    """Verify atomic binary data writing."""
    target_file = temp_dir / "binary.dat"
    data = b"\x00\x01\x02\x03\xff\xfe\xfd"

    res_path = atomic_write_bytes(target_file, data)
    assert res_path.exists()
    assert res_path.read_bytes() == data


def test_read_missing_file_fallback(temp_dir: Path):
    """Verify missing file handling in safe reader."""
    missing = temp_dir / "non_existent.txt"
    assert read_text_safe(missing, default="DEFAULT") == "DEFAULT"

    with pytest.raises(FileNotFoundError):
        read_text_with_fallback(missing)


def test_json_safe_read_write(temp_dir: Path):
    """Verify atomic JSON read and write utilities."""
    json_path = temp_dir / "data.json"
    payload = {"name": "Koch Snowflake", "iterations": 4, "active": True}

    write_json_safe(json_path, payload)
    assert json_path.exists()

    loaded = read_json_safe(json_path)
    assert loaded == payload

    # Test corrupted JSON returns default
    atomic_write_text(json_path, "INVALID JSON {{{")
    assert read_json_safe(json_path, default={"fallback": 1}) == {"fallback": 1}


def test_safe_delete(temp_dir: Path):
    """Verify safe file deletion without exceptions on missing paths."""
    test_file = temp_dir / "to_delete.txt"
    atomic_write_text(test_file, "goodbye")
    assert test_file.exists()

    assert safe_delete(test_file) is True
    assert not test_file.exists()

    # Deleting non-existent file returns False safely
    assert safe_delete(test_file) is False
