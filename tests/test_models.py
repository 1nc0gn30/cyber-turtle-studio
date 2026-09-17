"""Unit tests for geometric data models, vector AST, and fractal configuration classes."""

from __future__ import annotations

import math

import pytest
from cyber_turtle_studio.models import (
    BoundingBox,
    DrawingAST,
    LSystemConfig,
    LSystemRule,
    PathSegment,
    PathSegmentType,
    PatternPreset,
    Point2D,
    TurtleState,
)


def test_point2d_arithmetic_and_transforms():
    """Verify Point2D vector math, distance, rotation, scaling, and serialization."""
    p1 = Point2D(0.0, 0.0)
    p2 = Point2D(3.0, 4.0)

    # Distance
    assert math.isclose(p1.distance_to(p2), 5.0)

    # Translation
    p3 = p1.translate(10.0, -5.0)
    assert p3.x == 10.0
    assert p3.y == -5.0

    # Rotation (90 degrees around origin)
    p_rot = Point2D(10.0, 0.0).rotate(math.pi / 2.0)
    assert math.isclose(p_rot.x, 0.0, abs_tol=1e-6)
    assert math.isclose(p_rot.y, 10.0, abs_tol=1e-6)

    # Scaling
    p_scale = Point2D(5.0, 10.0).scale(2.0)
    assert p_scale.x == 10.0
    assert p_scale.y == 20.0

    # Polar creation
    p_polar = Point2D.from_polar(10.0, 0.0)
    assert math.isclose(p_polar.x, 10.0)
    assert math.isclose(p_polar.y, 0.0, abs_tol=1e-6)

    # Serialization
    d = p2.to_dict()
    assert d == {"x": 3.0, "y": 4.0}
    p_deser = Point2D.from_dict(d)
    assert p_deser == p2


def test_bounding_box_calculations():
    """Verify AABB bounds, dimensions, center point, and containment."""
    bb = BoundingBox(min_x=-50.0, min_y=-50.0, max_x=50.0, max_y=50.0)
    assert bb.width == 100.0
    assert bb.height == 100.0
    assert bb.center.x == 0.0
    assert bb.center.y == 0.0

    # Serialization
    d = bb.to_dict()
    assert d["min_x"] == -50.0
    assert d["max_x"] == 50.0
    bb_deser = BoundingBox.from_dict(d)
    assert bb_deser.min_x == bb.min_x


def test_path_segment_properties():
    """Verify PathSegment calculations and dictionary roundtrip."""
    p1 = Point2D(0.0, 0.0)
    p2 = Point2D(10.0, 0.0)
    seg = PathSegment(
        start=p1,
        end=p2,
        color="#ff0055",
        stroke_width=2.5,
        opacity=0.9,
        segment_type=PathSegmentType.LINE,
    )

    assert seg.length == 10.0
    assert seg.is_draw is True

    seg_dict = seg.to_dict()
    assert seg_dict["stroke_width"] == 2.5
    seg_restored = PathSegment.from_dict(seg_dict)
    assert seg_restored.start == p1
    assert seg_restored.end == p2
    assert seg_restored.color == "#ff0055"


def test_turtle_state_cloning():
    """Verify state snapshot deep copying."""
    st = TurtleState(
        position=Point2D(10.0, 20.0),
        heading=45.0,
        pen_down=False,
        pen_color="#1a73e8",
        stroke_width=3.0,
    )
    cloned = st.clone()
    assert cloned.position.x == 10.0
    assert cloned.heading == 45.0
    assert cloned.pen_down is False

    # Modifying clone must not mutate original
    cloned.position = Point2D(99.0, 20.0)
    assert st.position.x == 10.0


def test_drawing_ast_geometry_ops(sample_drawing_ast: DrawingAST):
    """Verify DrawingAST bounds calculation, scaling, centering, and stats."""
    ast = sample_drawing_ast
    bb = ast.bounds()
    assert bb.min_x == 0.0
    assert bb.max_y == 100.0
    assert bb.width == 100.0
    assert bb.height == 100.0

    # Center drawing at origin (0, 0)
    ast = ast.center_at(0.0, 0.0)
    bb_centered = ast.bounds()
    assert math.isclose(bb_centered.center.x, 0.0, abs_tol=1e-5)
    assert math.isclose(bb_centered.center.y, 0.0, abs_tol=1e-5)

    # Scale drawing
    ast = ast.scale(2.0)
    bb_scaled = ast.bounds()
    assert math.isclose(bb_scaled.width, 200.0, abs_tol=1e-5)


    # Stats
    stats = ast.stats()
    assert stats["total_segments"] == 4
    assert stats.get("drawing_segments", stats.get("draw_segments", 0)) == 4
    assert stats.get("total_drawing_length", stats.get("total_draw_length", 0)) > 0

    # Serialization roundtrip
    ast_dict = ast.to_dict()
    ast_restored = DrawingAST.from_dict(ast_dict)
    assert len(ast_restored.segments) == 4
    assert ast_restored.title == ast.title


def test_lsystem_config_and_rules():
    """Verify LSystemConfig and rule serialization."""
    rule = LSystemRule(predecessor="F", successor="F+F-F", probability=1.0)
    assert rule.predecessor == "F"
    assert rule.successor == "F+F-F"

    cfg = LSystemConfig(
        name="Dragon Curve",
        axiom="FX",
        rules={"X": "X+YF+", "Y": "-FX-Y"},
        angle=90.0,
        iterations=4,
    )
    d = cfg.to_dict()
    assert d["axiom"] == "FX"
    assert "X" in d["rules"]

    cfg_restored = LSystemConfig.from_dict(d)
    assert cfg_restored.name == "Dragon Curve"
    assert cfg_restored.angle == 90.0

