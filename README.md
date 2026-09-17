<div align="center">

# 🐢 Google Cyber Turtle Studio
### High-Precision Turtle Graphics, L-System Fractal Synthesizer, CNC G-Code Plotter & Google Material 3 Studio

[![CI Matrix](https://github.com/1nc0gn30/cyber-turtle-studio/actions/workflows/ci.yml/badge.svg)](https://github.com/1nc0gn30/cyber-turtle-studio/actions)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Zero Dependencies](https://img.shields.io/badge/dependencies-0%20runtime-success.svg)](https://github.com/1nc0gn30/cyber-turtle-studio)
[![MCP Protocol](https://img.shields.io/badge/MCP-JSON--RPC%202.0-8a2be2.svg)](https://modelcontextprotocol.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

*A sovereign, zero-dependency, pure Python geometry engine and Google Material 3 Studio for recursive generative art, Lindenmayer system botany, mathematical fractals, animated vector SVGs, and physical CNC pen-plotter G-Code manufacturing.*

---

</div>

## 🌟 Highlights & Capabilities

- **Zero Runtime Dependencies**: 100% Pure Python standard library implementation compatible with Python 3.9 through 3.13 on Linux, macOS, Windows, and Termux.
- **High-Precision 2D Vector Turtle Interpreter**: Arbitrary step precision, heading calculations, state stacks, circle/arc interpolations, dot primitives, and polygon fills.
- **Extensible Logo DSL Script Engine**: Full mini-language interpreter supporting loops (`repeat`), nested blocks, variables (`make`), custom procedures (`to ... end`), mathematical expressions, and comment syntax.
- **Lindenmayer System (L-System) Fractal Synthesizer**: Deterministic and stochastic production rules, parametric branching stack trees (`[` and `]`), step scaling (`<` and `>`), and 28+ built-in mathematical fractals.
- **Multi-Format Exporters**:
  - **Animated Vector SVG**: Interactive CSS keyframe stroke-dasharray animations and 6 visual palettes (`cyber_matrix`, `retro_amber`, `blueprint_cyan`, `sacred_gold`, `light_minimal`, `monochrome`).
  - **CNC Pen-Plotter & Laser G-Code**: High-speed G0 travel, G1 drawing feeds, Z-axis servo/stepper heights, laser power modulation (`M3`/`M5`), bed auto-fitting, and motor controls.
  - **High-Resolution Terminal Braille**: 2x4 subpixel Unicode Braille matrix rendering (`U+2800`..`U+28FF`) with 24-bit TrueColor ANSI styling.
- **Google Material 3 Web Studio**: Responsive dual-mode editor, real-time SVG viewport, zoom/pan controls, animated step-scrubber playback engine, and CNC plotter drawer.
- **Model Context Protocol (MCP) Server**: Full JSON-RPC 2.0 stdio server providing AI agents (Claude Desktop, Cursor, Cline, Roo Code) with direct tool calls, grammar documentation, and plotter workflow prompts.

---

## 📐 Mathematical Foundations of L-Systems

A **Lindenmayer System (L-System)** is a parallel string rewriting formal grammar introduced by biologist Astrid Lindenmayer in 1968 to model the growth processes of plant cells and fractal geometry.

An L-System is formally defined as a tuple:

$$G = (V, \omega, P)$$

where:
1. **$V$ (Alphabet)**: The set of formal symbols containing terminal symbols (e.g. `F`, `+`, `-`, `[`, `]`) and non-terminal variables (e.g. `X`, `Y`).
2. **$\omega \in V^+$ (Axiom / Seed)**: An initial non-empty string defining the starting state of the system.
3. **$P \subset V \times V^*$ (Production Rules)**: A mapping specifying how predecessor symbols are replaced in parallel across successive iteration generations $N$.

### Turtle Interpretation Mapping

| Symbol | Turtle Graphics Action |
| :--- | :--- |
| `F`, `G`, `A`, `B` | Move forward by `step_size` drawing a line segment ($\text{pen\_down} = \text{True}$). |
| `f` | Move forward by `step_size` without drawing ($\text{pen\_down} = \text{False}$). |
| `+` | Turn right (clockwise) by branching angle $\theta$. |
| `-` | Turn left (counter-clockwise) by branching angle $\theta$. |
| `[` | **Push State**: Save current coordinate $(x, y)$, heading angle, and stroke style onto state stack. |
| `]` | **Pop State**: Restore saved position, heading angle, and stroke style from state stack. |
| `\|` | Turn 180° around (reverse heading direction). |
| `<` | Multiply step length by scaling factor (e.g. $0.8\times$). |
| `>` | Divide step length by scaling factor (e.g. $1.25\times$). |

---

## 🎨 Built-In 28+ Fractal Catalog Presets

| Category | Presets Included |
| :--- | :--- |
| **Fractals** | Koch Snowflake, Koch Anti-Snowflake, Heighway Dragon Curve, Terdragon, Lévy C Curve, Sierpiński Triangle, Sierpiński Arrowhead, Sierpiński Carpet, Quadratic Koch Island, Box Fractal, Cantor Dust |
| **Space-Filling Curves** | Hilbert Curve, Moore Curve, Gosper Hexagonal Flowsnake, Peano Curve, E-Curve |
| **Botany & Plant Growth** | Barnsley Fern, Axial Branching Plant, Delicate Weed Shrub, Pythagoras Tree, Symmetric Bush, 3D Monopodial Tree |
| **Sacred Geometry & Tiles** | Kolam Vedic Floor Tile, Islamic Star Lattice, Crystal Lattice, Flower of Life Mandala |
| **Classic Logo DSL** | Star Mandala, Spiral Vortex, Hexagon Matrix, Concentric Polygons |

---

## ⌨️ Logo DSL Command Reference

The built-in Logo interpreter parses and executes standard and extended Logo commands:

```logo
; Google Cyber Turtle Studio - Star Mandala Sample
color #00f0ff
width 2.0
make "size 100

repeat 36 [
  repeat 4 [
    fd :size
    rt 90
  ]
  rt 10
]
```

### Supported Syntax:
- **Movement**: `fd <dist>`, `bk <dist>`, `goto <x> <y>`
- **Rotation**: `rt <angle_deg>`, `lt <angle_deg>`, `setheading <deg>`
- **Pen Controls**: `pu` (penup), `pd` (pendown), `color #hex`, `width <px>`, `opacity <0.0-1.0>`
- **Shapes & Primitives**: `circle <radius> [extent] [steps]`, `dot <size> [color]`
- **State Branching**: `push` / `pop` (position and heading stack)
- **Fills**: `begin_fill [color]`, `end_fill`
- **Control Flow**: `repeat <n> [ <commands> ]` (supports arbitrary nesting)
- **Variables**: `make "var_name <value>`, `set <var_name> <value>`, `:var_name`
- **Procedures**: `to <name> [:param1 :param2] ... end`

---

## 🖨️ CNC Pen Plotter & Laser Cutter Guidelines

Cyber Turtle Studio generates industrial-grade **RS-274 / ISO G-Code** compatible with GRBL, Marlin, AxiDraw, EleksMaker, and Universal G-Code Sender.

```gcode
; --------------------------------------------------
; Generated by Google Cyber Turtle Studio CNC Engine
; Title: Koch Snowflake
; Bed Size: 200.0x200.0 mm
; --------------------------------------------------
G21 ; Set units to millimeters
G90 ; Set positioning to absolute mode
G28 ; Home all axes
G0 Z5.000 F3000.0 ; Pen Up Travel
G0 X10.000 Y10.000 F3000.0
G1 Z0.000 F1200.0 ; Pen Down Drawing
G1 X190.000 Y10.000 F1200.0
G0 Z5.000 F3000.0 ; Pen Up Travel
G0 X0 Y0 ; Return Home
M84 ; Disable steppers
M30 ; Program End
```

### CNC Plotting Parameters:
- **`--feed <mm/min>`**: Linear drawing feedrate (default `1200 mm/min`).
- **`--travel-feed <mm/min>`**: Rapid non-drawing travel feedrate (default `3000 mm/min`).
- **`--z-up <mm>`**: Pen lift height for safe rapid moves (default `5.0 mm`).
- **`--z-down <mm>`**: Pen surface contact height (default `0.0 mm`).
- **`--laser`**: Enables Laser mode (`M3 S255` laser on / `M5` laser off) instead of physical Z-axis pen motions.
- **`--bed-width <mm>` & `--bed-height <mm>`**: Work envelope constraints (e.g. `200x200 mm`, `300x300 mm`, `A4`, `A3`).

---

## 💻 Command Line Interface (CLI) Guide

Install locally in editable mode:
```bash
pip install -e .
```

Both `cyber-turtle-studio` and `cyber-turtle` entry points are available.

### CLI Subcommands Overview:

```bash
# 1. Execute Logo DSL code directly
cyber-turtle logo "repeat 36 [ repeat 4 [ fd 100 rt 90 ] rt 10 ]" -o mandala.svg --theme sacred_gold

# 2. Synthesize custom L-System fractal
cyber-turtle lsystem "F--F--F" -r "F=F+F--F+F" -i 4 -a 60 -o snowflake.svg --theme cyber_matrix --animate

# 3. Generate catalog preset directly
cyber-turtle generate dragon_curve -i 10 -o dragon.gcode -f gcode

# 4. List all 28+ presets with filtering
cyber-turtle presets -c Fractals
cyber-turtle presets --json

# 5. Export CNC G-Code with custom feedrates
cyber-turtle gcode koch_snowflake -o plot.gcode --feed 1500 --z-up 6.0

# 6. Render direct terminal ASCII / Braille art
cyber-turtle ascii barnsley_fern -w 80 -H 40 -m braille

# 7. Launch Google Material 3 Studio Web App
cyber-turtle serve --port 8080 --browser

# 8. Run Model Context Protocol (MCP) Server
cyber-turtle mcp

# 9. System diagnostics report
cyber-turtle doctor
```

---

## 🤖 Model Context Protocol (MCP) Integration

Cyber Turtle Studio natively integrates with AI environments via standard JSON-RPC 2.0 over `stdio`.

### Configuration for Claude Desktop

Add to your `claude_desktop_config.json` (`~/.config/Claude/claude_desktop_config.json` on Linux/macOS or `%APPDATA%\Claude\claude_desktop_config.json` on Windows):

```json
{
  "mcpServers": {
    "cyber-turtle-studio": {
      "command": "python3",
      "args": [
        "-m",
        "cyber_turtle_studio.mcp_server"
      ]
    }
  }
}
```

### Configuration for Cursor / Cline / Roo Code

Add to `.cursor/mcp.json` or `.cline/mcp_settings.json`:

```json
{
  "mcpServers": {
    "cyber-turtle": {
      "command": "cyber-turtle",
      "args": ["mcp"]
    }
  }
}
```

### Registered MCP Capabilities:
- **Tools**:
  - `turtle_execute_logo`: Execute Logo code and return Drawing AST, statistics, and SVG.
  - `turtle_generate_lsystem`: Synthesize fractals from axiom, rules, iterations, and turning angle.
  - `turtle_export_svg`: Generate vector SVG with animated CSS stroke effects.
  - `turtle_export_gcode`: Generate CNC pen-plotter or laser G-Code.
  - `turtle_presets`: Query catalog presets, categories, and parameters.
  - `turtle_diagnostics`: Verify multi-OS compatibility and engine health.
- **Resources**:
  - `turtle://presets`: Complete catalog metadata and mathematical rules.
  - `turtle://grammar-guide`: Full grammar symbol reference and Logo cheatsheet.
- **Prompts**:
  - `turtle_create_fractal`: Interactive assistant for designing custom growth patterns.
  - `turtle_plotter_workflow`: Step-by-step setup guidance for physical CNC plotters.

---

## 🌐 Google Material 3 Web Studio

Launch the built-in local studio:
```bash
python3 -m cyber_turtle_studio.ui_server --port 8080
```

### Studio Features:
- **Google Material 3 Light Mode Palette**: Google Blue (`#1a73e8`), elevation cards, filter chips, and dark mode toggle.
- **Dual Mode Editor**: Instant switching between Logo DSL live editor and L-System rule table form.
- **Real-time Canvas & Animated Playback**: Zoom, pan, grid overlay, playback scrubber, and speed controls.
- **G-Code Plotter Deck**: Live G-Code syntax preview, feedrate inputs, and 1-click `.gcode` / animated `.svg` downloads.
- **REST APIs**:
  - `GET /api/presets`: Returns all catalog presets and categories.
  - `POST /api/execute-logo`: Executes Logo code.
  - `POST /api/generate-lsystem`: Synthesizes L-System geometry.
  - `POST /api/generate-preset`: Generates preset drawing.
  - `POST /api/export-svg`: Exports static or animated SVG.
  - `POST /api/export-gcode`: Exports CNC G-Code.
  - `GET /api/stats`: Diagnostics and system health.

---

## 🧪 Comprehensive Test Suite

Run the full pytest suite:
```bash
pytest tests/ -v
```

### Test Coverage:
- `test_compat.py`: Platform detection, atomic text/byte I/O, path normalization, JSON helpers.
- `test_models.py`: `Point2D`, `BoundingBox`, `PathSegment`, `TurtleState`, `DrawingAST`, `LSystemConfig`.
- `test_turtle_engine.py`: Movement, heading, pen styles, state stack, circles/dots, loops, procedures.
- `test_lsystem_engine.py`: Deterministic & stochastic rewriting, fractal rendering, 28+ built-in presets.
- `test_exporters.py`: Vector SVG (static/animated), G-Code (plotter/laser), ASCII/Braille renderers.
- `test_catalog.py`: Preset registry queries, fuzzy lookup, category filtering, dynamic registration.
- `test_mcp_server.py`: JSON-RPC 2.0 lifecycle, tools, resources, and prompt templates.
- `test_cli.py`: All command-line subcommands, argument flags, and format outputs.
- `test_ui_server.py`: Multi-threaded HTTP server, REST endpoints, CORS headers, 404 handling.

---

## 📂 Project Architecture

```
cyber-turtle-studio/
├── .github/
│   └── workflows/
│       └── ci.yml                 # Multi-OS CI matrix across Python 3.9-3.13
├── public/
│   └── index.html                 # Google Material 3 Web Studio UI
├── src/
│   └── cyber_turtle_studio/
│       ├── __init__.py            # Package root & public exports
│       ├── catalog.py             # 28+ fractal preset registry & query engine
│       ├── cli.py                 # Sovereign multi-OS CLI interface
│       ├── compat.py              # Cross-platform atomic file I/O & OS detection
│       ├── lsystem_engine.py      # L-System string rewriter & turtle interpreter
│       ├── mcp_server.py          # Model Context Protocol stdio server
│       ├── models.py              # Geometry AST, Point2D, BoundingBox models
│       ├── turtle_engine.py       # High-precision Turtle interpreter & Logo parser
│       ├── ui_server.py           # Multi-threaded HTTP REST API server
│       └── exporters/
│           ├── __init__.py        # Exporter package interfaces
│           ├── ascii_exporter.py  # Terminal Braille / ASCII canvas renderer
│           ├── gcode_exporter.py  # CNC Pen-plotter & Laser G-Code generator
│           └── svg_exporter.py    # Static & animated SVG vector generator
├── tests/
│   ├── conftest.py                # Pytest configuration & test fixtures
│   ├── test_catalog.py            # Preset catalog tests
│   ├── test_cli.py                # CLI tests
│   ├── test_compat.py             # Platform & compat tests
│   ├── test_exporters.py          # SVG, G-Code, ASCII exporter tests
│   ├── test_lsystem_engine.py     # L-System synthesis tests
│   ├── test_mcp_server.py         # MCP server tests
│   ├── test_models.py             # Data models & geometry tests
│   ├── test_turtle_engine.py      # Turtle engine & Logo parser tests
│   └── test_ui_server.py          # UI & REST API server tests
├── pyproject.toml                 # Modern PEP 621 packaging metadata
└── README.md                      # Comprehensive documentation
```

---

## 📜 License

Distributed under the **MIT License**. See `LICENSE` for details.

Developed with 💙 by **1nc0gn30** for generative mathematics, computer science education, and CNC pen-plotting craft.
