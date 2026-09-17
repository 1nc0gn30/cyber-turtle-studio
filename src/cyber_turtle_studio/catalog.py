"""Catalog and Preset Registry for cyber-turtle-studio.

Provides catalog query, filtering, search, preset lookup, dynamic registration,
and fast generation wrappers for all 28+ built-in geometric fractals.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Union

from cyber_turtle_studio.lsystem_engine import (
    generate_lsystem,
    get_builtin_presets,
)
from cyber_turtle_studio.models import DrawingAST, PatternPreset


class PresetRegistry:
    """In-memory registry managing all fractal presets."""

    def __init__(self) -> None:
        self._presets: Dict[str, PatternPreset] = {}
        self._aliases: Dict[str, str] = {}
        self.reload_builtins()

    def reload_builtins(self) -> None:
        """Load or reload all built-in presets."""
        self._presets.clear()
        self._aliases.clear()
        for preset in get_builtin_presets():
            self.register(preset)

    def register(self, preset: PatternPreset) -> None:
        """Register a new preset or overwrite existing."""
        pid = preset.id.lower().strip()
        self._presets[pid] = preset
        # Register name alias
        name_alias = preset.name.lower().replace(" ", "_").strip()
        self._aliases[name_alias] = pid
        # Register hyphen alias
        hyphen_alias = pid.replace("_", "-")
        self._aliases[hyphen_alias] = pid

    def get(self, preset_id_or_name: str) -> PatternPreset:
        """Retrieve preset by ID, name, or alias (case-insensitive)."""
        clean_key = preset_id_or_name.lower().strip()
        if clean_key in self._presets:
            return self._presets[clean_key]

        normalized_alias = clean_key.replace(" ", "_").replace("-", "_")
        if normalized_alias in self._aliases:
            return self._presets[self._aliases[normalized_alias]]

        # Fuzzy search fallback
        for pid, p in self._presets.items():
            if clean_key == pid or clean_key in p.name.lower() or clean_key in pid:
                return p

        available = ", ".join(sorted(self._presets.keys()))
        raise KeyError(f"Preset '{preset_id_or_name}' not found in catalog. Available: {available}")

    def list(
        self,
        category: Optional[str] = None,
        tag: Optional[str] = None,
        search: Optional[str] = None,
        difficulty: Optional[str] = None,
    ) -> List[PatternPreset]:
        """Search and filter presets by category, tag, search query, or difficulty."""
        results: List[PatternPreset] = []
        q = search.lower().strip() if search else None
        cat = category.lower().strip() if category else None
        tg = tag.lower().strip() if tag else None
        diff = difficulty.lower().strip() if difficulty else None

        for preset in self._presets.values():
            if cat and preset.category.lower() != cat:
                continue
            if diff and preset.difficulty.lower() != diff:
                continue
            if tg and not any(tg == t.lower() for t in preset.tags):
                continue
            if q:
                match_name = q in preset.name.lower()
                match_id = q in preset.id.lower()
                match_desc = q in preset.description.lower()
                match_tags = any(q in t.lower() for t in preset.tags)
                match_cat = q in preset.category.lower()
                if not (match_name or match_id or match_desc or match_tags or match_cat):
                    continue
            results.append(preset)

        return sorted(results, key=lambda p: (p.category, p.name))

    def categories(self) -> List[str]:
        """List all unique preset categories."""
        cats = {p.category for p in self._presets.values()}
        return sorted(list(cats))

    def tags(self) -> List[str]:
        """List all unique preset tags."""
        all_tags = set()
        for p in self._presets.values():
            all_tags.update(p.tags)
        return sorted(list(all_tags))

    def summary(self) -> Dict[str, Any]:
        """Return catalog telemetry and summary statistics."""
        presets = list(self._presets.values())
        cat_counts: Dict[str, int] = {}
        diff_counts: Dict[str, int] = {}

        for p in presets:
            cat_counts[p.category] = cat_counts.get(p.category, 0) + 1
            diff_counts[p.difficulty] = diff_counts.get(p.difficulty, 0) + 1

        return {
            "total_presets": len(presets),
            "categories": cat_counts,
            "difficulty_breakdown": diff_counts,
            "total_tags": len(self.tags()),
        }


# Global default catalog registry instance
GLOBAL_REGISTRY = PresetRegistry()
PRESETS: Dict[str, PatternPreset] = GLOBAL_REGISTRY._presets


def list_presets(
    category: Optional[str] = None,
    tag: Optional[str] = None,
    search: Optional[str] = None,
    difficulty: Optional[str] = None,
    drawing_type: Optional[str] = None,
) -> List[PatternPreset]:
    """List and filter presets from the global catalog."""
    return GLOBAL_REGISTRY.list(category=category, tag=tag, search=search, difficulty=difficulty)


def get_preset(preset_id_or_name: str) -> PatternPreset:
    """Get a preset from the global catalog by ID or name."""
    return GLOBAL_REGISTRY.get(preset_id_or_name)


def register_preset(preset: PatternPreset) -> None:
    """Register a custom preset in the global catalog."""
    GLOBAL_REGISTRY.register(preset)


def list_categories() -> List[str]:
    """List all categories available in the catalog."""
    return GLOBAL_REGISTRY.categories()


def list_tags() -> List[str]:
    """List all tags available in the catalog."""
    return GLOBAL_REGISTRY.tags()


def get_catalog_summary() -> Dict[str, Any]:
    """Get catalog metrics and category breakdown."""
    return GLOBAL_REGISTRY.summary()


def generate_pattern(
    preset_id_or_name: str,
    iterations: Optional[int] = None,
    step_size: Optional[float] = None,
    seed: Optional[int] = None,
) -> DrawingAST:
    """Generate DrawingAST directly for any catalog preset."""
    preset = get_preset(preset_id_or_name)
    cfg = preset.config
    iters = iterations if iterations is not None else preset.recommended_iterations

    # Apply optional step size override
    if step_size is not None:
        cfg.step_size = float(step_size)

    drawing = generate_lsystem(cfg, iterations=iters, seed=seed)
    drawing.title = preset.name
    drawing.metadata.update({
        "preset_id": preset.id,
        "category": preset.category,
        "difficulty": preset.difficulty,
        "default_theme": preset.default_theme,
    })
    return drawing
