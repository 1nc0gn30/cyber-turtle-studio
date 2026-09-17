"""Tests for Turtle graphics interpreter and Logo DSL script parser."""

from __future__ import annotations

import math

import pytest
from cyber_turtle_studio.models import DrawingAST, PathSegmentType, Point2D
from cyber_turtle_studio.turtle_engine import LogoParser, TurtleEngine, execute_logo


def test_turtle_movement_and_heading():
    """Verify forward, backward, left, right, and coordinate tracking."""
    t = TurtleEngine(start_pos=(0.0, 0.0), start_heading=0.0)  # Heading 0 = East
    assert t.x == 0.0
    assert t.y == 0.0
    assert t.heading == 0.0

    t.forward(100.0)
    assert math.isclose(t.x, 100.0, abs_tol=1e-5)
    assert math.isclose(t.y, 0.0, abs_tol=1e-5)

    t.left(90.0)  # Now heading North (90 deg)
    assert math.isclose(t.heading, 90.0, abs_tol=1e-5)

    t.forward(50.0)
    assert math.isclose(t.x, 100.0, abs_tol=1e-5)
    assert math.isclose(t.y, 50.0, abs_tol=1e-5)

    t.backward(25.0)
    assert math.isclose(t.y, 25.0, abs_tol=1e-5)

    t.goto(0.0, 0.0)
    assert math.isclose(t.x, 0.0, abs_tol=1e-5)
    assert math.isclose(t.y, 0.0, abs_tol=1e-5)


def test_turtle_pen_state_and_styles():
    """Verify pen up/down, colors, stroke width, and opacity."""
    t = TurtleEngine()
    t.set_color("#ff007f")
    assert t.pen_color == "#ff007f"

    t.set_width(3.5)
    assert t.stroke_width == 3.5

    t.set_opacity(0.75)
    assert t.opacity == 0.75

    t.pen_up()
    assert t.is_pen_down is False
    t.forward(50.0)

    t.pen_down()
    assert t.is_pen_down is True
    t.forward(50.0)

    drawing = t.get_drawing()
    assert len(drawing.segments) == 2
    # First was move (pen up), second was line (pen down)
    assert drawing.segments[0].segment_type == PathSegmentType.MOVE
    assert drawing.segments[1].segment_type == PathSegmentType.LINE


def test_turtle_state_stack():
    """Verify push_state and pop_state tree branching behavior."""
    t = TurtleEngine(start_pos=(10.0, 20.0), start_heading=45.0)
    t.set_color("#1a73e8")

    t.push_state()
    t.forward(100.0)
    t.right(90.0)
    t.set_color("#ff0000")

    # Pop state should restore original position and heading
    t.pop_state()
    assert math.isclose(t.x, 10.0, abs_tol=1e-5)
    assert math.isclose(t.y, 20.0, abs_tol=1e-5)
    assert math.isclose(t.heading, 45.0, abs_tol=1e-5)
    assert t.pen_color == "#1a73e8"


def test_turtle_circle_and_dot():
    """Verify circle arc generation and dot commands."""
    t = TurtleEngine()
    t.circle(radius=50.0, extent=360.0, steps=36)
    t.dot(size=12.0, color="#ffd700")

    drawing = t.get_drawing()
    assert len(drawing.segments) > 10
    dot_segs = [s for s in drawing.segments if s.segment_type == PathSegmentType.DOT]
    assert len(dot_segs) == 1
    assert dot_segs[0].color == "#ffd700"


def test_logo_parser_square_and_repeats(sample_logo_scripts: dict):
    """Verify standard Logo script execution and nested loops."""
    script = sample_logo_scripts["square"]
    drawing = execute_logo(script)
    assert isinstance(drawing, DrawingAST)
    assert len(drawing.segments) == 4

    # Nested loop test
    nested_script = sample_logo_scripts["nested_repeat"]
    drawing_nested = execute_logo(nested_script)
    assert len(drawing_nested.segments) == 24


def test_logo_variables_and_procedures(sample_logo_scripts: dict):
    """Verify variable assignments and custom procedure definitions."""
    var_script = sample_logo_scripts["variables"]
    drawing_var = execute_logo(var_script)
    assert len(drawing_var.segments) == 4

    proc_script = sample_logo_scripts["procedures"]
    drawing_proc = execute_logo(proc_script)
    assert len(drawing_proc.segments) == 4


def test_logo_error_handling_and_comments():
    """Verify comment stripping and resilient parsing."""
    script_with_comments = """
    ; This is a header comment
    color #34a853 ; Google green
    repeat 3 [
        fd 60 ; forward
        rt 120 ; right turn
    ]
    """
    drawing = execute_logo(script_with_comments)
    assert len(drawing.segments) == 3
