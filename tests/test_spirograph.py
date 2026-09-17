"""Unit tests for spirograph and harmonograph generators in Cyber Turtle Studio."""

import math
import pytest

from cyber_turtle_studio import (
    DrawingAST,
    PathSegmentType,
    export_svg,
    generate_harmonograph,
    generate_spirograph,
)


def test_generate_spirograph_hypotrochoid():
    ast = generate_spirograph(R=120.0, r=45.0, d=30.0, curve_type="hypotrochoid", num_points=500)
    assert isinstance(ast, DrawingAST)
    assert ast.title.startswith("Spirograph_hypotrochoid")
    assert len(ast.segments) > 0
    assert all(s.segment_type == PathSegmentType.LINE for s in ast.segments)
    # Check bounding box
    bbox = ast.bounding_box()
    assert bbox.width > 0
    assert bbox.height > 0
    # Check SVG export compatibility
    svg = export_svg(ast)
    assert "<svg" in svg
    assert "</svg>" in svg


def test_generate_spirograph_epitrochoid():
    ast = generate_spirograph(R=100.0, r=35.0, d=25.0, curve_type="epitrochoid", num_points=600)
    assert isinstance(ast, DrawingAST)
    assert len(ast.segments) == 599
    svg = export_svg(ast)
    assert "<svg" in svg


def test_generate_spirograph_invalid():
    with pytest.raises(ValueError, match="Invalid curve_type"):
        generate_spirograph(curve_type="unknown")

    with pytest.raises(ValueError, match="must be positive"):
        generate_spirograph(R=0, r=20, d=10)


def test_generate_harmonograph():
    ast = generate_harmonograph(
        f1=2.001, f2=3.0, f3=3.002, f4=2.0,
        d1=0.002, d2=0.002, d3=0.002, d4=0.002,
        t_max=60.0,
        num_points=1000
    )
    assert isinstance(ast, DrawingAST)
    assert ast.title.startswith("Harmonograph")
    assert len(ast.segments) == 999
    bbox = ast.bounding_box()
    assert bbox.width > 0
    assert bbox.height > 0
    svg = export_svg(ast)
    assert "<svg" in svg
