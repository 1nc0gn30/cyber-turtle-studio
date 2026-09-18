"""Model Context Protocol (MCP) Server for Cyber Turtle Studio.

Pure Python standard library implementation of the MCP JSON-RPC 2.0 protocol over stdio.
Exposes Turtle execution, L-System fractal synthesis, multi-format vector/CNC exporters,
catalog queries, diagnostics, and interactive AI prompts.
"""

from __future__ import annotations

import io
import json
import logging
import os
import sys
import traceback
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Union

from .catalog import (
    GLOBAL_REGISTRY,
    generate_pattern,
    get_catalog_summary,
    get_preset,
    list_categories,
    list_presets,
    list_tags,
)
from .compat import (
    PlatformInfo,
    atomic_write_text,
    get_platform_info,
    normalize_path,
    read_text_safe,
    safe_path,
)
from .exporters import (
    ASCIIExporter,
    ASCIIRenderMode,
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
from .models import DrawingAST, LSystemConfig, LSystemRule, PatternPreset
from .toolpath_optimizer import ToolpathOptimizer, render_toolpath_comparison_svg
from .turtle_engine import LogoParser, TurtleEngine, execute_logo

logger = logging.getLogger("cyber_turtle_mcp")

PRESETS = GLOBAL_REGISTRY._presets


# =============================================================================
# Grammar Guide & Resource Payloads
# =============================================================================

GRAMMAR_GUIDE_TEXT = """# Cyber Turtle Studio & L-System Grammar Guide

## 1. Logo DSL Commands Reference
Cyber Turtle Studio includes a high-precision Logo interpreter supporting standard and extended graphics instructions:

| Command | Aliases | Arguments | Description | Example |
| :--- | :--- | :--- | :--- | :--- |
| `forward` | `fd` | `<distance>` | Move forward along heading | `fd 100` |
| `backward` | `bk`, `back` | `<distance>` | Move backward along heading | `bk 50` |
| `left` | `lt` | `<degrees>` | Turn counter-clockwise | `lt 90` |
| `right` | `rt` | `<degrees>` | Turn clockwise | `rt 45` |
| `penup` | `pu` | *none* | Lift drawing pen | `pu` |
| `pendown` | `pd` | *none* | Lower drawing pen | `pd` |
| `goto` | `setpos` | `<x> <y>` | Move directly to (x, y) | `goto 100 -50` |
| `setheading`| `seth` | `<degrees>` | Set absolute heading (0=E, 90=N) | `seth 90` |
| `color` | `setcolor` | `<hex/name>` | Set stroke color | `color #00ffcc` |
| `width` | `pensize` | `<pixels>` | Set stroke width | `width 2.5` |
| `opacity` | *none* | `<0.0 - 1.0>` | Set stroke opacity | `opacity 0.8` |
| `circle` | *none* | `<radius> [deg] [steps]` | Draw circular arc | `circle 50 180` |
| `dot` | *none* | `<size> [color]` | Draw filled circular dot | `dot 10 #ff007f` |
| `push` | `push_state`| *none* | Save position & heading to stack | `push` |
| `pop` | `pop_state` | *none* | Restore position & heading | `pop` |
| `begin_fill`| *none* | `[color]` | Begin recording polygon fill | `begin_fill #39ff14` |
| `end_fill` | *none* | *none* | Close and fill polygon | `end_fill` |
| `repeat` | `loop` | `<n> [ <body> ]` | Repeat commands n times | `repeat 8 [ fd 50 rt 45 ]` |
| `make` | `set`, `let` | `"var <value>` | Assign variable | `make "len 80` |
| `to` ... `end`| *none* | `to <name> [:args] ... end` | Define custom procedure | `to square :s repeat 4 [ fd :s rt 90 ] end` |

---

## 2. Lindenmayer System (L-System) Rewriting Rules
Formal grammar symbol semantics for fractal growth:

- `F`, `G`: Move forward by current `step_size` with pen down.
- `f`: Move forward by current `step_size` with pen UP (travel move).
- `+`: Turn right (clockwise) by `turn_angle`.
- `-`: Turn left (counter-clockwise) by `turn_angle`.
- `[`: Push turtle state (position, heading, scale) onto stack (branch start).
- `]`: Pop turtle state from stack (branch end).
- `|`: Turn 180 degrees (reverse heading).
- `<`: Multiply step size by scale factor (0.8x default).
- `>`: Divide step size by scale factor (1.25x default).
- `(`: Decrease turn angle.
- `)`: Increase turn angle.
- `C`: Cycle stroke color from palette.
- `{` / `}`: Begin and end polygon fill.
- `X`, `Y`, `L`, `R`, `A`, `B`: Non-terminal syntactic variables guiding fractal recursion.

### Canonical Fractal Formulas:
- **Koch Snowflake**: Axiom: `F--F--F`, Rule: `F=F+F--F+F`, Angle: `60°`
- **Dragon Curve**: Axiom: `FX`, Rules: `X=X+YF+, Y=-FX-Y`, Angle: `90°`
- **Hilbert Curve**: Axiom: `L`, Rules: `L=+RF-LFL-FR+, R=-LF+RFR+FL-`, Angle: `90°`
- **Barnsley Fern**: Axiom: `X`, Rules: `X=F+[[X]-X]-F[-FX]+X, F=FF`, Angle: `25°`

---

## 3. Multi-Format Exporters
- **SVG**: Scalable vector paths, dark cyberpunk glow filters, CSS stroke animations.
- **CNC G-Code**: High-precision toolpaths with rapid travel (`G0`), linear cutting (`G1`), Z-axis pen lift or laser (`M3/M5`).
- **Terminal ASCII & Braille**: High-resolution 2x4 subpixel Unicode Braille patterns (U+2800..U+28FF).
"""


def _parse_rules_input(raw_rules: Union[str, Dict[str, Any]]) -> Dict[str, str]:
    """Normalize rule input from either a dictionary or delimited string."""
    if isinstance(raw_rules, dict):
        return {str(k).strip(): str(v).strip() for k, v in raw_rules.items()}

    rules_dict: Dict[str, str] = {}
    rule_str = str(raw_rules).strip()
    if not rule_str:
        return rules_dict

    if rule_str.startswith("{") and rule_str.endswith("}"):
        try:
            parsed = json.loads(rule_str)
            if isinstance(parsed, dict):
                return {str(k).strip(): str(v).strip() for k, v in parsed.items()}
        except Exception:
            pass

    delimiters = [",", "\n", ";"]
    tokens = [rule_str]
    for delim in delimiters:
        new_tokens = []
        for t in tokens:
            new_tokens.extend(t.split(delim))
        tokens = new_tokens

    for token in tokens:
        token = token.strip()
        if not token:
            continue
        if "->" in token:
            parts = token.split("->", 1)
        elif "=" in token:
            parts = token.split("=", 1)
        elif ":" in token:
            parts = token.split(":", 1)
        else:
            continue
        pred = parts[0].strip()
        succ = parts[1].strip()
        if pred:
            rules_dict[pred] = succ

    return rules_dict


# =============================================================================
# Model Context Protocol (MCP) Server
# =============================================================================

class MCPServer:
    """Complete Model Context Protocol stdio server for Cyber Turtle Studio."""

    def __init__(self) -> None:
        self.name = "cyber-turtle-studio"
        self.version = "0.1.0"
        self.protocol_version = "2024-11-05"
        self.running = False

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Return MCP tool catalog metadata."""
        return [
            {
                "name": "turtle_execute_logo",
                "description": (
                    "Execute a Logo DSL script (e.g. 'repeat 8 [ fd 80 rt 45 ]', 'color #ff007f repeat 36 [ circle 40 rt 10 ]') "
                    "and return drawing geometry AST metrics, bounding box, and rendered SVG vector markup."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "script": {
                            "type": "string",
                            "description": "Logo language code to execute (supports fd, bk, lt, rt, circle, dot, repeat, push, pop, make, color, width).",
                        },
                        "theme": {
                            "type": "string",
                            "description": "Color theme palette: 'cyber_matrix', 'retro_amber', 'blueprint_cyan', 'sacred_gold', 'light_minimal', 'monochrome'.",
                            "default": "cyber_matrix",
                        },
                        "animate": {
                            "type": "boolean",
                            "description": "Generate animated SVG with CSS keyframe stroke-dashoffset animation.",
                            "default": False,
                        },
                        "stroke_width": {
                            "type": "number",
                            "description": "Stroke line width in pixels.",
                            "default": 1.5,
                        },
                        "include_svg": {
                            "type": "boolean",
                            "description": "Include full SVG markup in response payload.",
                            "default": True,
                        },
                        "include_ascii": {
                            "type": "boolean",
                            "description": "Include Unicode Braille/ASCII terminal art preview in response.",
                            "default": False,
                        },
                        "include_gcode": {
                            "type": "boolean",
                            "description": "Include CNC pen-plotter G-Code in response.",
                            "default": False,
                        },
                        "output_path": {
                            "type": "string",
                            "description": "Optional file path to save SVG file atomically.",
                        },
                    },
                    "required": ["script"],
                },
            },
            {
                "name": "turtle_generate_lsystem",
                "description": (
                    "Generate a fractal from Lindenmayer System (L-System) formal grammar rules. "
                    "Expands axiom through iterative replacement and interprets geometric turtle instructions."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "axiom": {
                            "type": "string",
                            "description": "Initial axiom string (e.g. 'F--F--F', 'FX', 'L', 'X', 'F+F+F+F').",
                        },
                        "rules": {
                            "type": ["object", "string"],
                            "description": "Production rewriting rules as object {'F': 'F+F--F+F'} or string 'F=F+F--F+F, X=X+YF+'.",
                        },
                        "iterations": {
                            "type": "integer",
                            "description": "Number of rewrite recursion levels (typically 1-8).",
                            "default": 3,
                        },
                        "angle": {
                            "type": "number",
                            "description": "Turning angle in degrees for '+' and '-' symbols.",
                            "default": 90.0,
                        },
                        "step_size": {
                            "type": "number",
                            "description": "Forward step length in pixels.",
                            "default": 10.0,
                        },
                        "theme": {
                            "type": "string",
                            "description": "Color theme palette name ('cyber_matrix', 'blueprint_cyan', 'sacred_gold', etc.).",
                            "default": "cyber_matrix",
                        },
                        "animate": {
                            "type": "boolean",
                            "description": "Enable CSS keyframe stroke animation in SVG output.",
                            "default": False,
                        },
                        "export_format": {
                            "type": "string",
                            "description": "Output representation format: 'svg', 'gcode', 'ascii', 'ast', or 'all'.",
                            "default": "svg",
                        },
                        "output_path": {
                            "type": "string",
                            "description": "Optional target file path to save output atomically.",
                        },
                    },
                    "required": ["axiom", "rules"],
                },
            },
            {
                "name": "turtle_export_svg",
                "description": (
                    "Export drawing commands or a catalog preset to Scalable Vector Graphics (SVG) "
                    "with customizable themes, glow filters, dimensions, and CSS stroke animation."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "preset_id": {
                            "type": "string",
                            "description": "Built-in preset ID (e.g. 'koch_snowflake', 'dragon_curve', 'hilbert_curve', 'barnsley_fern', 'sierpinski_triangle').",
                        },
                        "logo_script": {
                            "type": "string",
                            "description": "Logo script to execute if preset_id is not specified.",
                        },
                        "theme": {
                            "type": "string",
                            "description": "Color theme palette name ('cyber_matrix', 'retro_amber', 'blueprint_cyan', 'sacred_gold', 'light_minimal', 'monochrome').",
                            "default": "cyber_matrix",
                        },
                        "animate": {
                            "type": "boolean",
                            "description": "Enable smooth stroke drawing CSS animation.",
                            "default": False,
                        },
                        "duration_sec": {
                            "type": "number",
                            "description": "Animation duration in seconds.",
                            "default": 4.0,
                        },
                        "width": {
                            "type": "number",
                            "description": "SVG canvas viewport width in pixels.",
                            "default": 1000.0,
                        },
                        "height": {
                            "type": "number",
                            "description": "SVG canvas viewport height in pixels.",
                            "default": 1000.0,
                        },
                        "padding": {
                            "type": "number",
                            "description": "Padding margin in pixels around drawing bounding box.",
                            "default": 40.0,
                        },
                        "output_path": {
                            "type": "string",
                            "description": "Optional file path to save generated SVG file.",
                        },
                    },
                },
            },
            {
                "name": "turtle_export_gcode",
                "description": (
                    "Export drawing commands or a catalog preset to CNC Pen Plotter or Laser Cutter G-Code. "
                    "Generates standard G0 rapid travel, G1 linear feed, Z-axis pen lift, and laser M3/M5 commands."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "preset_id": {
                            "type": "string",
                            "description": "Built-in preset ID to render as G-Code.",
                        },
                        "logo_script": {
                            "type": "string",
                            "description": "Logo script to execute if preset_id is not specified.",
                        },
                        "bed_width": {
                            "type": "number",
                            "description": "CNC physical work bed width in millimeters.",
                            "default": 210.0,
                        },
                        "bed_height": {
                            "type": "number",
                            "description": "CNC physical work bed height in millimeters.",
                            "default": 297.0,
                        },
                        "feed_draw": {
                            "type": "number",
                            "description": "Drawing feedrate in mm/min (e.g. 1200).",
                            "default": 1200.0,
                        },
                        "feed_travel": {
                            "type": "number",
                            "description": "Rapid travel feedrate in mm/min (e.g. 3000).",
                            "default": 3000.0,
                        },
                        "z_up": {
                            "type": "number",
                            "description": "Z height in mm for pen-up travel moves.",
                            "default": 5.0,
                        },
                        "z_down": {
                            "type": "number",
                            "description": "Z height in mm for pen-down drawing.",
                            "default": 0.0,
                        },
                        "laser_mode": {
                            "type": "boolean",
                            "description": "Enable laser mode using M3 S255 / M5 commands instead of Z-axis travel.",
                            "default": False,
                        },
                        "output_path": {
                            "type": "string",
                            "description": "Optional file path to save the .gcode file.",
                        },
                    },
                },
            },
            {
                "name": "turtle_presets",
                "description": (
                    "Query the complete catalog of 28+ built-in Logo geometric patterns and L-System fractal presets "
                    "with category filtering, tags, difficulty levels, and metadata."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "category": {
                            "type": "string",
                            "description": "Filter by category: 'Fractal Curves', 'Space-Filling Curves', 'Sierpinski Family', 'Botanical Branching', 'Sacred & Cultural', or 'all'.",
                        },
                        "tag": {
                            "type": "string",
                            "description": "Filter by tag keyword (e.g. 'dragon', 'hilbert', 'tree', 'mandala', 'space_filling').",
                        },
                        "difficulty": {
                            "type": "string",
                            "description": "Filter by difficulty ('Beginner', 'Intermediate', 'Advanced', 'Master').",
                        },
                        "detailed": {
                            "type": "boolean",
                            "description": "Return full parameter configurations and descriptions.",
                            "default": False,
                        },
                    },
                },
            },
            {
                "name": "turtle_diagnostics",
                "description": (
                    "Execute system diagnostic suite, verifying multi-OS compatibility (Linux, macOS, Windows, Termux), "
                    "Python runtime version, terminal ANSI color support, Unicode encoding, and directory write permissions."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "detailed": {
                            "type": "boolean",
                            "description": "Include environment variable audit and detailed platform telemetry.",
                            "default": True,
                        },
                    },
                },
            },
            {
                "name": "turtle_optimize_toolpath",
                "description": (
                    "Optimize pen-plotter / CNC toolpaths by solving the Traveling Salesperson Problem (TSP) "
                    "with 2-Opt local search to minimize non-drawing rapid pen-up air travel moves."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "script": {
                            "type": "string",
                            "description": "Logo script to execute and optimize.",
                        },
                        "preset": {
                            "type": "string",
                            "description": "Or preset pattern ID (e.g. 'sierpinski_triangle', 'dragon_curve').",
                        },
                        "draw_feedrate": {
                            "type": "number",
                            "default": 1200.0,
                            "description": "Drawing feedrate in mm/min.",
                        },
                        "travel_feedrate": {
                            "type": "number",
                            "default": 3000.0,
                            "description": "Rapid air travel feedrate in mm/min.",
                        },
                        "include_comparison_svg": {
                            "type": "boolean",
                            "default": True,
                            "description": "Generate side-by-side SVG comparison highlighting air travel.",
                        },
                    },
                },
            },
            {
                "name": "turtle_generate_truchet",
                "description": "Generate generative Truchet tiling vector patterns (Smith quarter-circle arcs, diagonal slashes, concentric ribbons) for SVG and pen plotting.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "rows": {"type": "integer", "default": 10, "description": "Number of tile rows."},
                        "cols": {"type": "integer", "default": 10, "description": "Number of tile columns."},
                        "tile_size": {"type": "number", "default": 40.0, "description": "Tile dimension size."},
                        "style": {
                            "type": "string",
                            "enum": ["arcs", "diagonal", "concentric_arcs", "cross_line"],
                            "default": "arcs",
                            "description": "Truchet tiling variation.",
                        },
                        "seed": {"type": "integer", "description": "Optional RNG seed for deterministic generation."},
                        "theme": {"type": "string", "default": "cyber_matrix", "description": "Color theme for SVG rendering."},
                        "stroke_width": {"type": "number", "default": 2.0, "description": "Vector stroke width."},
                    },
                },
            },
            {
                "name": "turtle_generate_maze",
                "description": "Generate algorithmic labyrinth mazes (Recursive Backtracker, Wilson uniform spanning tree, or Braided) with optional solved pathfinding trail.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "rows": {"type": "integer", "default": 12, "description": "Number of maze rows."},
                        "cols": {"type": "integer", "default": 12, "description": "Number of maze columns."},
                        "cell_size": {"type": "number", "default": 30.0, "description": "Cell dimension in canvas units."},
                        "algorithm": {
                            "type": "string",
                            "enum": ["backtracker", "wilson", "braided"],
                            "default": "backtracker",
                            "description": "Maze generation algorithm.",
                        },
                        "solve": {"type": "boolean", "default": True, "description": "Whether to draw the solved route."},
                        "seed": {"type": "integer", "description": "Optional RNG seed for reproducibility."},
                        "wall_color": {"type": "string", "default": "#00e5ff", "description": "Hex color for maze walls."},
                        "path_color": {"type": "string", "default": "#ff007f", "description": "Hex color for solved route."},
                    },
                },
            },
        ]

    def get_resource_definitions(self) -> List[Dict[str, Any]]:
        """Return MCP resource catalog metadata."""
        return [
            {
                "uri": "turtle://presets",
                "name": "Built-in Preset Catalog",
                "description": "Comprehensive JSON database of all Logo & L-System fractal presets, metadata, and default parameters.",
                "mimeType": "application/json",
            },
            {
                "uri": "turtle://grammar-guide",
                "name": "Turtle & L-System Grammar Guide",
                "description": "Complete reference manual for Logo DSL commands, L-System rewriting symbols, and CNC G-Code instructions.",
                "mimeType": "text/markdown",
            },
        ]

    def get_prompt_definitions(self) -> List[Dict[str, Any]]:
        """Return MCP prompt catalog metadata."""
        return [
            {
                "name": "turtle_create_fractal",
                "description": "Interactive assistant for designing custom L-System growth patterns, space-filling curves, and fractal geometry.",
                "arguments": [
                    {
                        "name": "style",
                        "description": "Desired geometry aesthetic: 'nature' (botanical ferns, trees), 'geometric' (crystals, snowflakes), 'space_filling' (curves), 'cyber' (mandalas, labyrinths).",
                        "required": False,
                    },
                    {
                        "name": "complexity",
                        "description": "Complexity tier: 'simple' (1-3 rules), 'medium' (4-6 rules), 'intricate' (branching stack with stochastic rules).",
                        "required": False,
                    },
                ],
            },
            {
                "name": "turtle_plotter_workflow",
                "description": "Step-by-step guidance for setting up physical pen-plotters (AxiDraw, GRBL, CNC) with generated G-Code, coordinate scaling, and tool paths.",
                "arguments": [
                    {
                        "name": "machine_type",
                        "description": "Plotter hardware type: 'pen-plotter', 'laser-cutter', '3d-printer-cnc'.",
                        "required": False,
                    },
                    {
                        "name": "bed_size",
                        "description": "Work area dimensions: 'A4', 'A3', '200x200', '300x300'.",
                        "required": False,
                    },
                ],
            },
        ]

    def handle_tool_call(self, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tool by name and return JSON-RPC content array."""
        try:
            if name == "turtle_execute_logo":
                return self._tool_execute_logo(args)
            elif name == "turtle_generate_lsystem":
                return self._tool_generate_lsystem(args)
            elif name == "turtle_export_svg":
                return self._tool_export_svg(args)
            elif name == "turtle_export_gcode":
                return self._tool_export_gcode(args)
            elif name == "turtle_presets":
                return self._tool_presets(args)
            elif name == "turtle_diagnostics":
                return self._tool_diagnostics(args)
            elif name == "turtle_optimize_toolpath":
                return self._tool_optimize_toolpath(args)
            elif name == "turtle_generate_truchet":
                return self._tool_generate_truchet(args)
            elif name == "turtle_generate_maze":
                return self._tool_generate_maze(args)
            else:
                return {
                    "content": [{"type": "text", "text": f"Error: Unknown tool name '{name}'."}],
                    "isError": True,
                }
        except Exception as exc:
            err_msg = f"Tool '{name}' execution error: {type(exc).__name__}: {str(exc)}\n{traceback.format_exc()}"
            logger.error(err_msg)
            return {
                "content": [{"type": "text", "text": err_msg}],
                "isError": True,
            }

    def _tool_execute_logo(self, args: Dict[str, Any]) -> Dict[str, Any]:
        script = str(args.get("script", "")).strip()
        if not script:
            return {"content": [{"type": "text", "text": "Error: 'script' argument cannot be empty."}], "isError": True}

        theme = str(args.get("theme", "cyber_matrix"))
        animate = bool(args.get("animate", False))
        stroke_width = float(args.get("stroke_width", 1.5))
        include_svg = bool(args.get("include_svg", True))
        include_ascii = bool(args.get("include_ascii", False))
        include_gcode = bool(args.get("include_gcode", False))
        output_path = args.get("output_path")

        ast = execute_logo(script)
        ast.title = "Logo Execution"
        stats = ast.stats()

        svg_content = export_svg(
            ast,
            theme=theme,
            animated=animate,
            stroke_width=stroke_width,
            file_path=output_path,
        )

        res_blocks = [
            f"=== Cyber Turtle Logo Execution ===\n"
            f"Title: {ast.title}\n"
            f"Total Segments: {stats['total_segments']} (Drawing: {stats['drawing_segments']}, Travel: {stats['travel_count']})\n"
            f"Bounding Box: Width={stats['width']:.2f}, Height={stats['height']:.2f}, Aspect={stats['aspect_ratio']:.2f}\n"
            f"Total Path Length: {stats['total_path_length']:.2f} px (Drawing: {stats['total_drawing_length']:.2f} px)\n"
        ]

        if output_path:
            res_blocks.append(f"Saved SVG to: {normalize_path(output_path)}\n")

        if include_ascii:
            ascii_text = export_ascii(ast, width=50, height=25, mode="braille")
            res_blocks.append(f"Terminal Braille Preview:\n{ascii_text}\n")

        if include_gcode:
            gcode_text, _ = export_gcode(ast)
            res_blocks.append(f"CNC G-Code ({len(gcode_text.splitlines())} lines):\n{gcode_text[:500]}...\n")

        if include_svg:
            res_blocks.append(f"Generated SVG Markup ({len(svg_content)} bytes):\n```xml\n{svg_content}\n```")

        return {"content": [{"type": "text", "text": "\n".join(res_blocks)}]}

    def _tool_generate_lsystem(self, args: Dict[str, Any]) -> Dict[str, Any]:
        axiom = str(args.get("axiom", "")).strip()
        if not axiom:
            return {"content": [{"type": "text", "text": "Error: 'axiom' argument cannot be empty."}], "isError": True}

        raw_rules = args.get("rules", {})
        rules = _parse_rules_input(raw_rules)
        if not rules:
            return {"content": [{"type": "text", "text": "Error: 'rules' mapping could not be parsed."}], "isError": True}

        iterations = int(args.get("iterations", 3))
        angle = float(args.get("angle", 90.0))
        step_size = float(args.get("step_size", 10.0))
        theme = str(args.get("theme", "cyber_matrix"))
        animate = bool(args.get("animate", False))
        export_fmt = str(args.get("export_format", "svg")).lower()
        output_path = args.get("output_path")

        from .lsystem_engine import generate_lsystem as _raw_gen
        cfg = LSystemConfig(
            axiom=axiom,
            rules=rules,
            angle=angle,
            iterations=iterations,
            step_size=step_size,
            name="L-System Fractal",
        )
        ast = _raw_gen(cfg, iterations=iterations)
        stats = ast.stats()

        res_blocks = [
            f"=== L-System Fractal Generated ===\n"
            f"Axiom: {axiom}\n"
            f"Rules: {json.dumps(rules)}\n"
            f"Iterations: {iterations} | Angle: {angle}° | Step: {step_size}px\n"
            f"Total Segments: {stats['total_segments']} | Path Length: {stats['total_path_length']:.2f}px\n"
            f"Bounding Box: {stats['width']:.2f} x {stats['height']:.2f}\n"
        ]

        if export_fmt in ("svg", "all"):
            svg_content = export_svg(ast, theme=theme, animated=animate, file_path=output_path if export_fmt == "svg" else None)
            res_blocks.append(f"SVG Markup ({len(svg_content)} bytes):\n```xml\n{svg_content}\n```\n")

        if export_fmt in ("ascii", "all"):
            ascii_text = export_ascii(ast, width=54, height=26, mode="braille", file_path=output_path if export_fmt == "ascii" else None)
            res_blocks.append(f"Terminal Braille Preview:\n{ascii_text}\n")

        if export_fmt in ("gcode", "all"):
            gcode_text, _ = export_gcode(ast, file_path=output_path if export_fmt == "gcode" else None)
            res_blocks.append(f"CNC G-Code Program ({len(gcode_text.splitlines())} lines):\n{gcode_text[:600]}...\n")

        if export_fmt in ("ast", "json", "all"):
            res_blocks.append(f"Drawing AST JSON:\n```json\n{ast.to_json(indent=2)}\n```\n")

        if output_path and export_fmt != "svg":
            res_blocks.append(f"Saved output to: {normalize_path(output_path)}\n")

        return {"content": [{"type": "text", "text": "\n".join(res_blocks)}]}

    def _tool_export_svg(self, args: Dict[str, Any]) -> Dict[str, Any]:
        preset_id = args.get("preset_id")
        logo_script = args.get("logo_script")
        theme = str(args.get("theme", "cyber_matrix"))
        animate = bool(args.get("animate", False))
        duration_sec = float(args.get("duration_sec", 4.0))
        width = int(args.get("width", 1000))
        height = int(args.get("height", 1000))
        padding = float(args.get("padding", 40.0))
        output_path = args.get("output_path")

        if preset_id:
            ast = generate_pattern(str(preset_id))
        elif logo_script:
            ast = execute_logo(str(logo_script))
            ast.title = "Custom SVG Export"
        else:
            ast = generate_pattern("dragon_curve")

        svg_markup = export_svg(
            ast,
            theme=theme,
            width=width,
            height=height,
            padding=padding,
            animated=animate,
            animation_duration=duration_sec,
            file_path=output_path,
        )

        resp = f"Successfully generated SVG for '{ast.title}' (Theme: {theme}, Animated: {animate}).\n"
        if output_path:
            resp += f"Saved to file: {normalize_path(output_path)}\n"
        resp += f"\n```xml\n{svg_markup}\n```"

        return {"content": [{"type": "text", "text": resp}]}

    def _tool_export_gcode(self, args: Dict[str, Any]) -> Dict[str, Any]:
        preset_id = args.get("preset_id")
        logo_script = args.get("logo_script")
        bed_width = float(args.get("bed_width", 210.0))
        bed_height = float(args.get("bed_height", 297.0))
        feed_draw = float(args.get("feed_draw", 1200.0))
        feed_travel = float(args.get("feed_travel", 3000.0))
        z_up = float(args.get("z_up", 5.0))
        z_down = float(args.get("z_down", 0.0))
        laser_mode = bool(args.get("laser_mode", False))
        output_path = args.get("output_path")

        if preset_id:
            ast = generate_pattern(str(preset_id))
        elif logo_script:
            ast = execute_logo(str(logo_script))
            ast.title = "Custom GCode Export"
        else:
            ast = generate_pattern("koch_snowflake")

        tool_mode = "laser" if laser_mode else "pen_z"
        cfg = GCodeConfig(
            tool_mode=GCodeToolMode(tool_mode),
            draw_feedrate=feed_draw,
            travel_feedrate=feed_travel,
            pen_up_z=z_up,
            pen_down_z=z_down,
            bed_width=bed_width,
            bed_height=bed_height,
        )
        gcode_text, stats = export_gcode(
            ast,
            config=cfg,
            file_path=output_path,
        )

        resp = (
            f"CNC G-Code generated for '{ast.title}'.\n"
            f"Bed Size: {bed_width}x{bed_height} mm | Feed: {feed_draw} mm/min | Laser Mode: {laser_mode}\n"
            f"Total Lines: {stats.get('total_lines', len(gcode_text.splitlines()))} | Drawing Distance: {stats.get('drawing_distance_mm', 0)} mm\n"
        )
        if output_path:
            resp += f"Saved to file: {normalize_path(output_path)}\n"
        resp += f"\n```gcode\n{gcode_text}\n```"

        return {"content": [{"type": "text", "text": resp}]}

    def _tool_presets(self, args: Dict[str, Any]) -> Dict[str, Any]:
        category = args.get("category")
        tag = args.get("tag")
        difficulty = args.get("difficulty")
        detailed = bool(args.get("detailed", False))

        presets = list_presets(category=category, tag=tag, difficulty=difficulty)
        summary = get_catalog_summary()

        if detailed:
            data = {
                "summary": summary,
                "count": len(presets),
                "presets": [p.to_dict() for p in presets],
            }
            text = json.dumps(data, indent=2)
        else:
            rows = [
                f"=== Cyber Turtle Studio Preset Catalog ({len(presets)} presets) ===",
                f"Categories: {', '.join(list_categories())}\n",
            ]
            for p in presets:
                rows.append(f"• [{p.id}] {p.name} ({p.category}, {p.difficulty}) - {p.description}")
            text = "\n".join(rows)

        return {"content": [{"type": "text", "text": text}]}

    def _tool_diagnostics(self, args: Dict[str, Any]) -> Dict[str, Any]:
        detailed = bool(args.get("detailed", True))
        plat = get_platform_info()

        test_file = safe_path(".diag_write_test.tmp")
        write_ok = False
        try:
            atomic_write_text(test_file, "ok")
            if test_file.is_file():
                write_ok = True
                test_file.unlink()
        except Exception:
            write_ok = False

        diag_data = {
            "application": self.name,
            "version": self.version,
            "mcp_protocol_version": self.protocol_version,
            "platform": {
                "os_name": plat.os_name,
                "is_windows": plat.is_windows,
                "is_macos": plat.is_macos,
                "is_linux": plat.is_linux,
                "is_termux": plat.is_termux,
                "python_version": f"{plat.python_version[0]}.{plat.python_version[1]}.{plat.python_version[2]}",
                "supports_ansi_color": plat.supports_ansi_color,
                "supports_unicode": plat.supports_unicode,
                "default_encoding": plat.default_encoding,
            },
            "environment": {
                "cwd": str(os.getcwd()),
                "write_permission": write_ok,
                "catalog_presets_loaded": len(GLOBAL_REGISTRY.list()),
                "available_themes": list(THEMES.keys()),
            },
        }

        if detailed:
            diag_data["env_vars"] = {
                k: os.environ[k]
                for k in ["TERM", "COLORTERM", "NO_COLOR", "TERMUX_VERSION", "SHELL", "LANG"]
                if k in os.environ
            }

        text = json.dumps(diag_data, indent=2)
        return {"content": [{"type": "text", "text": text}]}

    def _tool_optimize_toolpath(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Run toolpath optimization and return telemetry metrics and comparison SVG."""
        script = str(args.get("script", "")).strip()
        preset_id = str(args.get("preset", "")).strip()
        draw_feed = float(args.get("draw_feedrate", 1200.0))
        travel_feed = float(args.get("travel_feedrate", 3000.0))
        include_svg = bool(args.get("include_comparison_svg", True))

        if script:
            ast = execute_logo(script)
        elif preset_id:
            ast = generate_pattern(preset_id)
        else:
            # Default star burst test pattern
            ast = execute_logo("REPEAT 8 [ FD 50 PU HOME RT REPCOUNT * 45 PD ]")

        optimizer = ToolpathOptimizer(draw_feedrate_mm_min=draw_feed, travel_feedrate_mm_min=travel_feed)
        opt_ast, report = optimizer.optimize_toolpath(ast)

        res_dict = report.to_dict()
        if include_svg:
            res_dict["comparison_svg"] = render_toolpath_comparison_svg(ast, opt_ast)

        return {
            "content": [{"type": "text", "text": json.dumps(res_dict, indent=2)}]
        }

    def _tool_generate_truchet(self, args: Dict[str, Any]) -> Dict[str, Any]:
        from .truchet_maze import TruchetStyle, generate_truchet_tiling
        rows = int(args.get("rows", 10))
        cols = int(args.get("cols", 10))
        tile_size = float(args.get("tile_size", 40.0))
        style_str = str(args.get("style", "arcs")).lower()
        seed = args.get("seed")
        theme = str(args.get("theme", "cyber_matrix"))
        stroke_width = float(args.get("stroke_width", 2.0))

        try:
            style = TruchetStyle(style_str)
        except ValueError:
            style = TruchetStyle.ARCS

        ast, stats_meta = generate_truchet_tiling(
            rows=rows,
            cols=cols,
            tile_size=tile_size,
            style=style,
            seed=int(seed) if seed is not None else None,
            stroke_width=stroke_width,
        )
        svg_str = export_svg(ast, theme=theme)
        stats = ast.stats()
        draw_len = stats.get("total_draw_length", stats.get("total_drawing_length", 0.0))

        res_data = {
            "success": True,
            "style": style.value,
            "rows": rows,
            "cols": cols,
            "total_segments": stats["total_segments"],
            "total_draw_length": draw_len,
            "stats": stats_meta,
            "svg": svg_str,
        }
        return {"content": [{"type": "text", "text": json.dumps(res_data, indent=2)}], "isError": False}

    def _tool_generate_maze(self, args: Dict[str, Any]) -> Dict[str, Any]:
        from .truchet_maze import MazeAlgorithm, generate_maze_labyrinth, render_ascii_maze
        rows = int(args.get("rows", 12))
        cols = int(args.get("cols", 12))
        cell_size = float(args.get("cell_size", 30.0))
        algo_str = str(args.get("algorithm", "backtracker")).lower()
        solve = bool(args.get("solve", True))
        seed = args.get("seed")
        wall_color = str(args.get("wall_color", "#00e5ff"))
        path_color = str(args.get("path_color", "#ff007f"))

        try:
            algo = MazeAlgorithm(algo_str)
        except ValueError:
            algo = MazeAlgorithm.RECURSIVE_BACKTRACKER

        ast, meta = generate_maze_labyrinth(
            rows=rows,
            cols=cols,
            cell_size=cell_size,
            algorithm=algo,
            solve=solve,
            seed=int(seed) if seed is not None else None,
            wall_color=wall_color,
            path_color=path_color,
        )
        svg_str = export_svg(ast, theme="cyber_matrix")
        ascii_art = render_ascii_maze(meta)
        stats = ast.stats()
        draw_len = stats.get("total_draw_length", stats.get("total_drawing_length", 0.0))

        res_data = {
            "success": True,
            "algorithm": algo.value,
            "rows": rows,
            "cols": cols,
            "solved": meta["solved"],
            "solution_length": meta["solution_length"],
            "wall_segments_count": meta["wall_segments_count"],
            "total_draw_length": draw_len,
            "meta": meta,
            "svg": svg_str,
            "ascii": ascii_art,
        }
        return {"content": [{"type": "text", "text": json.dumps(res_data, indent=2)}], "isError": False}

    def handle_resource_read(self, uri: str) -> Dict[str, Any]:
        """Read and return registered MCP resource content."""
        if uri == "turtle://presets":
            catalog_dump = {
                "summary": get_catalog_summary(),
                "categories": list_categories(),
                "tags": list_tags(),
                "themes": list(THEMES.keys()),
                "presets": [p.to_dict() for p in GLOBAL_REGISTRY.list()],
            }
            return {
                "contents": [
                    {
                        "uri": uri,
                        "mimeType": "application/json",
                        "text": json.dumps(catalog_dump, indent=2),
                    }
                ]
            }
        elif uri == "turtle://grammar-guide":
            return {
                "contents": [
                    {
                        "uri": uri,
                        "mimeType": "text/markdown",
                        "text": GRAMMAR_GUIDE_TEXT,
                    }
                ]
            }
        else:
            raise ValueError(f"Resource URI '{uri}' not found.")

    def handle_prompt_get(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate structured prompt instructions for AI assistant."""
        args = arguments or {}

        if name == "turtle_create_fractal":
            style = args.get("style", "nature")
            complexity = args.get("complexity", "medium")

            return {
                "description": f"Design custom {style} L-System fractal",
                "messages": [
                    {
                        "role": "user",
                        "content": {
                            "type": "text",
                            "text": (
                                f"Please help me design a custom {style} L-System with {complexity} complexity. "
                                f"Explain the geometric concept, provide the axiom and rules, and demonstrate how to execute it."
                            ),
                        },
                    }
                ],
            }

        elif name == "turtle_plotter_workflow":
            machine = args.get("machine_type", "pen-plotter")
            bed = args.get("bed_size", "A4")

            return {
                "description": f"CNC Pen Plotter setup guide for {machine} ({bed})",
                "messages": [
                    {
                        "role": "user",
                        "content": {
                            "type": "text",
                            "text": (
                                f"I need to prepare a drawing for physical plotting on a {machine} with a {bed} bed size. "
                                f"Guide me through generating G-Code, setting safe travel feedrates, pen heights, "
                                f"and zeroing the machine coordinates."
                            ),
                        },
                    }
                ],
            }

        else:
            raise ValueError(f"Prompt '{name}' not found.")

    def handle_jsonrpc_request(self, request_bytes_or_dict: Union[str, bytes, Dict[str, Any]]) -> Union[str, Dict[str, Any]]:
        """Handle raw JSON string, bytes, or parsed dictionary for JSON-RPC 2.0."""
        if isinstance(request_bytes_or_dict, (str, bytes)):
            try:
                req_obj = json.loads(request_bytes_or_dict)
            except Exception as e:
                return json.dumps({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": str(e)}})
            resp = self.process_request(req_obj)
            return json.dumps(resp) if resp is not None else ""
        return self.process_request(request_bytes_or_dict)

    def process_request(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process an incoming JSON-RPC 2.0 request or notification."""

        req_id = request.get("id")
        method = request.get("method")
        params = request.get("params", {})

        if method == "notifications/initialized":
            logger.info("Client completed MCP initialization.")
            return None

        if method == "ping":
            return {"jsonrpc": "2.0", "id": req_id, "result": {}}

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": self.protocol_version,
                    "capabilities": {
                        "tools": {},
                        "resources": {},
                        "prompts": {},
                    },
                    "serverInfo": {
                        "name": self.name,
                        "version": self.version,
                    },
                },
            }

        if method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"tools": self.get_tool_definitions()},
            }

        if method == "tools/call":
            tool_name = params.get("name", "")
            tool_args = params.get("arguments", {})
            call_result = self.handle_tool_call(tool_name, tool_args)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": call_result,
            }

        if method == "resources/list":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"resources": self.get_resource_definitions()},
            }

        if method == "resources/templates/list":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"resourceTemplates": []},
            }

        if method == "resources/read":
            uri = params.get("uri", "")
            try:
                res_data = self.handle_resource_read(uri)
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": res_data,
                }
            except Exception as exc:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32602, "message": f"Invalid params: {str(exc)}"},
                }

        if method == "prompts/list":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"prompts": self.get_prompt_definitions()},
            }

        if method == "prompts/get":
            prompt_name = params.get("name", "")
            prompt_args = params.get("arguments", {})
            try:
                prompt_data = self.handle_prompt_get(prompt_name, prompt_args)
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": prompt_data,
                }
            except Exception as exc:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32602, "message": f"Invalid params: {str(exc)}"},
                }

        if req_id is not None:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"Method '{method}' not found."},
            }

        return None

    handle_jsonrpc_request = process_request


    def run_stdio(self) -> None:
        """Run the MCP JSON-RPC 2.0 loop over standard input/output."""
        self.running = True
        logger.info(f"Starting {self.name} MCP Server v{self.version} over stdio.")

        while self.running:
            try:
                line = sys.stdin.readline()
                if not line:
                    break

                line_str = line.strip()
                if not line_str:
                    continue

                if line_str.lower().startswith("content-length:"):
                    parts = line_str.split(":", 1)
                    length = int(parts[1].strip())
                    sys.stdin.readline()
                    raw_body = sys.stdin.read(length)
                    request = json.loads(raw_body)
                else:
                    request = json.loads(line_str)

                response = self.process_request(request)
                if response is not None:
                    out_json = json.dumps(response)
                    sys.stdout.write(out_json + "\n")
                    sys.stdout.flush()

            except json.JSONDecodeError as err:
                err_resp = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32700, "message": f"Parse error: {str(err)}"},
                }
                sys.stdout.write(json.dumps(err_resp) + "\n")
                sys.stdout.flush()

            except (KeyboardInterrupt, BrokenPipeError):
                break
            except Exception as exc:
                logger.error(f"Unexpected stdio loop error: {traceback.format_exc()}")


def run_stdio_server() -> None:
    """Entry point to start the MCP server over stdio."""
    logging.basicConfig(
        stream=sys.stderr,
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    server = MCPServer()
    server.run_stdio()


if __name__ == "__main__":
    run_stdio_server()
