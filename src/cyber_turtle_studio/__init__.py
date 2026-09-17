"""Cyber Turtle Studio - Sovereign Multi-OS Turtle Graphics, L-System Fractal Engine, and Exporters.

Pure Python standard library toolkit for algorithmic art, fractal synthesis,
Logo execution, pen-plotter G-Code, dynamic SVGs, terminal ASCII/Braille art,
and Model Context Protocol (MCP) integration.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Union

from .catalog import (
    GLOBAL_REGISTRY,
    PresetRegistry,
    generate_pattern,
    get_catalog_summary,
    get_preset,
    list_categories,
    list_presets,
    list_tags,
    register_preset,
)
from .compat import (
    PlatformInfo,
    atomic_write_bytes,
    atomic_write_text,
    ensure_parent_dir,
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
from .exporters import (
    ASCIIExporter,
    ASCIIRenderMode,
    BedOrigin,
    ColorTheme,
    GCodeConfig,
    GCodeExporter,
    GCodeToolMode,
    SVGExporter,
    THEMES,
    export_animated_svg,
    export_ascii,
    export_gcode,
    export_svg,
)
from .lsystem_engine import (
    LSystemInterpreter,
    expand_lsystem,
    generate_lsystem as _raw_generate_lsystem,
    get_builtin_presets,
)
from .models import (
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
from .turtle_engine import (
    LogoParser,
    TurtleEngine,
    execute_logo,
)
from .spirograph import (
    generate_harmonograph,
    generate_spirograph,
)

# Canonical class aliases
Turtle = TurtleEngine
LSystemEngine = LSystemInterpreter
SVG_THEMES = THEMES
PRESETS = GLOBAL_REGISTRY._presets


def generate_lsystem(
    config_or_axiom: Union[LSystemConfig, str],
    rules: Optional[Union[Dict[str, Any], Sequence[LSystemRule], str]] = None,
    iterations: Optional[int] = None,
    angle: Optional[float] = None,
    angle_deg: Optional[float] = None,
    step_size: Optional[float] = None,
    seed: Optional[int] = None,
    palette: Optional[List[str]] = None,
    name: str = "L-System",
    **kwargs: Any,
) -> DrawingAST:
    """Flexible generator for L-Systems supporting both LSystemConfig objects and raw parameters."""
    if isinstance(config_or_axiom, LSystemConfig):
        return _raw_generate_lsystem(
            config_or_axiom,
            iterations=iterations,
            seed=seed,
            palette=palette,
        )

    # Construct LSystemConfig from raw parameters
    eff_angle = angle_deg if angle_deg is not None else (angle if angle is not None else 90.0)
    eff_step = step_size if step_size is not None else 10.0
    eff_rules: Dict[str, Any] = {}

    if isinstance(rules, dict):
        eff_rules = rules
    elif isinstance(rules, str):
        # Parse string rule format "F=F+F-F, X=X+YF+"
        for part in rules.replace("\n", ",").split(","):
            part = part.strip()
            if "=" in part:
                k, v = part.split("=", 1)
                eff_rules[k.strip()] = v.strip()
            elif "->" in part:
                k, v = part.split("->", 1)
                eff_rules[k.strip()] = v.strip()
    elif isinstance(rules, (list, tuple)):
        for r in rules:
            if isinstance(r, LSystemRule):
                eff_rules[r.predecessor] = r
            elif isinstance(r, dict):
                pred = str(r.get("predecessor", ""))
                if pred:
                    eff_rules[pred] = r

    cfg = LSystemConfig(
        axiom=str(config_or_axiom),
        rules=eff_rules,
        angle=float(eff_angle),
        iterations=int(iterations if iterations is not None else 3),
        step_size=float(eff_step),
        name=name,
        seed=seed,
    )
    return _raw_generate_lsystem(cfg, iterations=iterations, seed=seed, palette=palette)


__version__ = "0.1.0"
__author__ = "Cyber Turtle Studio Team"
__license__ = "MIT"

__all__ = [
    # Version & Metadata
    "__version__",
    "__author__",
    "__license__",
    # Core Domain Models & AST
    "Point2D",
    "BoundingBox",
    "PathSegmentType",
    "PathSegment",
    "TurtleState",
    "DrawingAST",
    "LSystemRule",
    "LSystemConfig",
    "PatternPreset",
    # Engines & Interpreters
    "Turtle",
    "TurtleEngine",
    "LogoParser",
    "LSystemEngine",
    "LSystemInterpreter",
    # Generator Functions
    "execute_logo",
    "generate_lsystem",
    "generate_pattern",
    "expand_lsystem",
    "get_builtin_presets",
    "generate_spirograph",
    "generate_harmonograph",
    # Exporters
    "SVGExporter",
    "export_svg",
    "export_animated_svg",
    "ColorTheme",
    "THEMES",
    "SVG_THEMES",
    "GCodeExporter",
    "export_gcode",
    "GCodeConfig",
    "GCodeToolMode",
    "BedOrigin",
    "ASCIIExporter",
    "export_ascii",
    "ASCIIRenderMode",
    # Catalog & Preset Management
    "PRESETS",
    "GLOBAL_REGISTRY",
    "PresetRegistry",
    "get_preset",
    "list_presets",
    "register_preset",
    "list_categories",
    "list_tags",
    "get_catalog_summary",
    # Platform & File I/O Compatibility
    "PlatformInfo",
    "get_platform_info",
    "is_windows",
    "is_macos",
    "is_linux",
    "is_termux",
    "safe_path",
    "normalize_path",
    "ensure_parent_dir",
    "atomic_write_text",
    "atomic_write_bytes",
    "read_text_safe",
    "read_text_with_fallback",
    "read_json_safe",
    "write_json_safe",
    "safe_delete",
]
