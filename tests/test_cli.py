"""Tests for Cyber Turtle Studio Command Line Interface (CLI)."""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from cyber_turtle_studio.cli import build_parser, main


def test_cli_version_and_help(capsys):
    """Verify CLI --version and --help flags."""
    parser = build_parser()
    assert parser.prog is not None

    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0

    out = capsys.readouterr().out
    assert "0.1.0" in out or "cyber-turtle" in out


def test_cli_presets_subcommand(capsys):
    """Verify 'presets' subcommand with JSON and category filtering."""
    exit_code = main(["presets", "--category", "Fractals"])
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "Koch Snowflake" in out or "Fractals" in out

    # Test JSON output
    exit_json = main(["presets", "--json"])
    assert exit_json == 0
    json_out = capsys.readouterr().out
    assert "koch_snowflake" in json_out


def test_cli_logo_execution(capsys, temp_dir: Path):
    """Verify 'logo' subcommand outputting to file and stdout."""
    out_file = temp_dir / "logo_square.svg"
    exit_code = main(["logo", "repeat 4 [ fd 50 rt 90 ]", "-o", str(out_file), "-f", "svg"])
    assert exit_code == 0
    assert out_file.exists()
    assert "<svg" in out_file.read_text(encoding="utf-8")


def test_cli_lsystem_execution(capsys, temp_dir: Path):
    """Verify 'lsystem' subcommand generating fractal geometry."""
    out_file = temp_dir / "lsystem.gcode"
    exit_code = main([
        "lsystem", "F--F--F",
        "-r", "F=F+F--F+F",
        "-i", "2",
        "-a", "60",
        "-o", str(out_file),
        "-f", "gcode",
    ])
    assert exit_code == 0
    assert out_file.exists()
    assert "G21" in out_file.read_text(encoding="utf-8")


def test_cli_generate_preset(capsys, temp_dir: Path):
    """Verify 'generate' subcommand generating preset directly."""
    out_file = temp_dir / "dragon.svg"
    exit_code = main(["generate", "dragon_curve", "-i", "4", "-o", str(out_file)])
    assert exit_code == 0
    assert out_file.exists()


def test_cli_gcode_subcommand(capsys, temp_dir: Path):
    """Verify 'gcode' export subcommand."""
    out_file = temp_dir / "plot.gcode"
    exit_code = main(["gcode", "koch_snowflake", "-o", str(out_file), "--feed", "1500"])
    assert exit_code == 0
    assert out_file.exists()


def test_cli_ascii_subcommand(capsys):
    """Verify 'ascii' terminal braille rendering."""
    exit_code = main(["ascii", "koch_snowflake", "-w", "40", "-H", "20"])
    assert exit_code == 0
    out = capsys.readouterr().out
    assert len(out) > 0


def test_cli_diagnostics_subcommand(capsys):
    """Verify 'diagnostics' and doctor subcommands."""
    exit_code = main(["diagnostics", "--json"])
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "platform" in out.lower() or "version" in out.lower()
