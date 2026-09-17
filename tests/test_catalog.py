"""Tests for the fractal and geometric design catalog registry."""

from __future__ import annotations

import pytest
from cyber_turtle_studio.catalog import (
    generate_pattern,
    get_catalog_summary,
    get_preset,
    list_categories,
    list_presets,
    list_tags,
    register_preset,
)
from cyber_turtle_studio.models import DrawingAST, LSystemConfig, PatternPreset


def test_catalog_list_and_summary():
    """Verify listing all presets and catalog telemetry summary."""
    presets = list_presets()
    assert len(presets) >= 25

    summary = get_catalog_summary()
    assert summary["total_presets"] >= 25
    assert "categories" in summary
    assert "difficulty_breakdown" in summary


def test_get_preset_by_id_and_alias():
    """Verify preset lookup by exact ID, aliases, and hyphenation."""
    p_exact = get_preset("koch_snowflake")
    assert p_exact.id == "koch_snowflake"
    assert p_exact.category == "Fractals"

    # Hyphenated lookup
    p_hyphen = get_preset("koch-snowflake")
    assert p_hyphen.id == "koch_snowflake"

    # Name lookup
    p_name = get_preset("Koch Snowflake")
    assert p_name.id == "koch_snowflake"


def test_get_preset_unknown_raises_keyerror():
    """Verify unknown preset ID raises KeyError with informative message."""
    with pytest.raises(KeyError) as exc_info:
        get_preset("non_existent_fractal_xyz")
    assert "not found in catalog" in str(exc_info.value)


def test_filter_presets_by_category_and_tags():
    """Verify filtering presets by category, tags, and search query."""
    fractals = list_presets(category="Fractals")
    assert len(fractals) > 0
    assert all(p.category == "Fractals" for p in fractals)

    # Search filter
    search_results = list_presets(search="snowflake")
    assert len(search_results) >= 1
    assert any(p.id == "koch_snowflake" for p in search_results)


def test_categories_and_tags():
    """Verify categories and tags listing."""
    cats = list_categories()
    assert "Fractals" in cats
    assert len(cats) >= 3

    tags = list_tags()
    assert len(tags) >= 5


def test_generate_pattern_direct():
    """Verify direct pattern generation from preset ID."""
    drawing = generate_pattern("dragon_curve", iterations=4)
    assert isinstance(drawing, DrawingAST)
    assert len(drawing.segments) > 0
    assert drawing.title == "Dragon Curve" or "Dragon" in drawing.title


def test_register_custom_preset():
    """Verify dynamic registration of custom preset."""
    custom = PatternPreset(
        id="unit_test_custom_preset",
        name="Unit Test Custom Fractal",
        category="Experimental",
        description="Dynamic test preset",
        config=LSystemConfig(axiom="F", rules={"F": "F+F"}, angle=90.0, iterations=2),
        tags=["test", "custom"],
        difficulty="Beginner",
    )
    register_preset(custom)

    retrieved = get_preset("unit_test_custom_preset")
    assert retrieved.name == "Unit Test Custom Fractal"
    assert "Experimental" in list_categories()
