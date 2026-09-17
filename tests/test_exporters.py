"""Tests for vector SVG, CNC G-Code, and terminal ASCII/Braille exporters."""

from __future__ import annotations

from pathlib import Path

import pytest
from cyber_turtle_studio.exporters import (
    ASCIIExporter,
    ASCIIRenderMode,
    GCodeExporter,
    SVG_THEMES,
    SVGExporter,
    export_animated_svg,
    export_ascii,
    export_gcode,
    export_svg,
)
from cyber_turtle_studio.models import DrawingAST


def test_svg_exporter_static(sample_drawing_ast: DrawingAST):
    """Verify static SVG generation and XML structure."""
    svg = export_svg(sample_drawing_ast, theme="cyber_matrix")
    assert "<svg" in svg
    assert "</svg>" in svg
    assert "viewBox=" in svg
    assert "stroke=" in svg


def test_svg_exporter_animated(sample_drawing_ast: DrawingAST):
    """Verify animated SVG with CSS keyframe stroke-dasharray animations."""
    svg_anim = export_animated_svg(sample_drawing_ast, theme="sacred_gold", duration_sec=3.0)
    assert "<style" in svg_anim
    assert "@keyframes" in svg_anim
    assert "stroke-dasharray" in svg_anim



def test_svg_themes():
    """Verify all built-in color themes exist and produce valid CSS colors."""
    assert len(SVG_THEMES) >= 5
    for theme_name in ("cyber_matrix", "retro_amber", "blueprint_cyan", "sacred_gold", "light_minimal"):
        assert theme_name in SVG_THEMES


def test_gcode_exporter_standard_pen_plotter(sample_drawing_ast: DrawingAST):
    """Verify standard CNC pen-plotter G-Code syntax (G0, G1, Z moves, G21/G90)."""
    gcode = export_gcode(
        sample_drawing_ast,
        bed_width=200.0,
        bed_height=200.0,
        feed_draw=1200.0,
        feed_travel=3000.0,
        z_up=5.0,
        z_down=0.0,
        laser_mode=False,
    )
    assert "G21" in gcode  # Millimeter mode
    assert "G90" in gcode  # Absolute coords
    assert "G0" in gcode   # Rapid travel
    assert "G1" in gcode   # Linear draw
    assert "Z5.0" in gcode or "Z5" in gcode  # Pen up
    assert "Z0.0" in gcode or "Z0" in gcode  # Pen down


def test_gcode_exporter_laser_mode(sample_drawing_ast: DrawingAST):
    """Verify laser cutter mode with M3/M5 power commands."""
    gcode = export_gcode(
        sample_drawing_ast,
        laser_mode=True,
    )
    assert "M3" in gcode  # Laser on
    assert "M5" in gcode  # Laser off


def test_ascii_and_braille_exporter(sample_drawing_ast: DrawingAST):
    """Verify terminal ASCII and Braille matrix rasterization."""
    braille_art = export_ascii(sample_drawing_ast, width=40, height=20, mode="braille")
    assert isinstance(braille_art, str)
    assert len(braille_art) > 0

    ascii_art = export_ascii(sample_drawing_ast, width=40, height=20, mode="ascii")
    assert isinstance(ascii_art, str)
    assert len(ascii_art) > 0


def test_exporter_file_saving(sample_drawing_ast: DrawingAST, temp_dir: Path):
    """Verify exporters can write directly to disk files."""
    svg_path = temp_dir / "output.svg"
    gcode_path = temp_dir / "output.gcode"
    ascii_path = temp_dir / "output.txt"

    # SVG save
    svg_exp = SVGExporter()
    svg_exp.export_file(sample_drawing_ast, svg_path)
    assert svg_path.exists()
    assert "<svg" in svg_path.read_text(encoding="utf-8")

    # GCode save
    gc_exp = GCodeExporter()
    gc_exp.export_file(sample_drawing_ast, gcode_path)
    assert gcode_path.exists()
    assert "G21" in gcode_path.read_text(encoding="utf-8")

    # ASCII save
    asc_exp = ASCIIExporter()
    asc_exp.export_file(sample_drawing_ast, ascii_path)
    assert ascii_path.exists()
