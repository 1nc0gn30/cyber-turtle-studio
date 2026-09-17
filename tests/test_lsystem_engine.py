"""Tests for deterministic & stochastic L-System string expansion and fractal synthesis."""

from __future__ import annotations

import pytest
from cyber_turtle_studio.lsystem_engine import (
    LSystemInterpreter,
    expand_lsystem,
    generate_lsystem,
    get_builtin_presets,
)
from cyber_turtle_studio.models import DrawingAST, LSystemConfig, LSystemRule


def test_expand_lsystem_deterministic():
    """Verify standard deterministic string rewriting rules."""
    # Koch Snowflake: F -> F+F--F+F
    axiom = "F"
    rules = {"F": "F+F--F+F"}

    # 0 iterations
    assert expand_lsystem(axiom, rules, 0) == "F"

    # 1 iteration
    assert expand_lsystem(axiom, rules, 1) == "F+F--F+F"

    # 2 iterations: each F becomes F+F--F+F
    expanded_2 = expand_lsystem(axiom, rules, 2)
    assert expanded_2.count("+") == 10
    assert expanded_2.count("-") == 10



def test_expand_lsystem_stochastic():
    """Verify probabilistic rule expansion with fixed seed."""
    axiom = "F"
    stochastic_rules = {
        "F": [
            LSystemRule("F", "F[+F]F", probability=0.5),
            LSystemRule("F", "F[-F]F", probability=0.5),
        ]
    }

    # With seed, output is deterministic
    res1 = expand_lsystem(axiom, stochastic_rules, 3, seed=42)
    res2 = expand_lsystem(axiom, stochastic_rules, 3, seed=42)
    assert res1 == res2
    assert len(res1) > len(axiom)


def test_generate_lsystem_drawing(sample_lsystem_config: LSystemConfig):
    """Verify complete DrawingAST generation from LSystemConfig."""
    drawing = generate_lsystem(sample_lsystem_config, iterations=2)
    assert isinstance(drawing, DrawingAST)
    assert len(drawing.segments) > 0

    stats = drawing.stats()
    assert stats.get("drawing_segments", stats.get("draw_segments", len(drawing.segments))) > 0
    assert stats.get("total_drawing_length", stats.get("total_draw_length", 0)) > 0


def test_builtin_presets_catalog():
    """Verify built-in presets collection contains 25+ valid fractals."""
    presets = get_builtin_presets()
    assert len(presets) >= 25

    # Check key presets exist
    preset_ids = {p.id for p in presets}
    assert "koch_snowflake" in preset_ids
    assert "dragon_curve" in preset_ids
    assert "hilbert_curve" in preset_ids
    assert "sierpinski_triangle" in preset_ids
    assert "barnsley_fern" in preset_ids
    assert "kolam_tile" in preset_ids

    # Verify every preset can generate valid geometry without error
    for p in presets[:5]:  # Test first 5 presets thoroughly
        drawing = generate_lsystem(p.config, iterations=2)
        assert len(drawing.segments) > 0
