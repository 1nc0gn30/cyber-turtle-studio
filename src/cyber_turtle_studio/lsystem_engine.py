"""Deterministic and stochastic Lindenmayer System (L-System) synthesizer.

Provides fast string rewriting, stochastic production rule evaluation,
turtle interpreter mapping, and 28+ built-in fractal & sacred geometry presets.
"""

from __future__ import annotations

import random
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from cyber_turtle_studio.models import (
    DrawingAST,
    LSystemConfig,
    LSystemRule,
    PatternPreset,
    Point2D,
    TurtleState,
)
from cyber_turtle_studio.turtle_engine import TurtleEngine


def expand_lsystem(
    axiom: str,
    rules: Union[Dict[str, Any], Sequence[LSystemRule]],
    iterations: int,
    seed: Optional[int] = None,
) -> str:
    """Expand an L-System axiom string according to production rules over N iterations.

    Supports deterministic and stochastic rules with probability weights.
    """
    if iterations <= 0:
        return axiom

    rng = random.Random(seed) if seed is not None else random.Random()

    # Normalize rules map: char -> list of (successor_str, cumulative_probability)
    rule_map: Dict[str, List[Tuple[str, float]]] = {}

    if isinstance(rules, dict):
        for pred, val in rules.items():
            options: List[Tuple[str, float]] = []
            if isinstance(val, str):
                options.append((val, 1.0))
            elif isinstance(val, list):
                total_prob = 0.0
                for item in val:
                    if isinstance(item, str):
                        options.append((item, 1.0))
                        total_prob += 1.0
                    elif isinstance(item, LSystemRule):
                        options.append((item.successor, item.probability))
                        total_prob += item.probability
                    elif isinstance(item, dict):
                        options.append((str(item.get("successor", "")), float(item.get("probability", 1.0))))
                        total_prob += float(item.get("probability", 1.0))
            rule_map[pred] = options
    elif isinstance(rules, (list, tuple)):
        for r in rules:
            if isinstance(r, LSystemRule):
                rule_map.setdefault(r.predecessor, []).append((r.successor, r.probability))

    current = axiom
    for _ in range(iterations):
        next_chars: List[str] = []
        for ch in current:
            if ch in rule_map:
                choices = rule_map[ch]
                if len(choices) == 1:
                    next_chars.append(choices[0][0])
                else:
                    # Weighted stochastic selection
                    weights = [w for _, w in choices]
                    selected = rng.choices(choices, weights=weights, k=1)[0][0]
                    next_chars.append(selected)
            else:
                next_chars.append(ch)
        current = "".join(next_chars)

    return current


class LSystemInterpreter:
    """Interprets expanded L-System symbol strings into 2D Turtle drawings."""

    DEFAULT_PALETTE = [
        "#00ffcc",  # Neon Cyan
        "#39ff14",  # Matrix Green
        "#ff007f",  # Cyber Magenta
        "#ffd700",  # Sacred Gold
        "#00d2ff",  # Electric Blue
        "#ff7700",  # Retro Amber
        "#b026ff",  # Synth Violet
        "#ffffff",  # Pure White
    ]

    def __init__(
        self,
        config: LSystemConfig,
        engine: Optional[TurtleEngine] = None,
        palette: Optional[List[str]] = None,
    ) -> None:
        self.config = config
        self.engine = engine if engine is not None else TurtleEngine(
            start_pos=config.start_pos,
            start_heading=config.start_heading,
            pen_down=True,
            pen_color="#00ffcc",
            stroke_width=1.0,
            opacity=1.0,
        )
        self.palette = palette or list(self.DEFAULT_PALETTE)
        self._palette_idx = 0
        self._step_size = config.step_size
        self._angle = config.angle

    def interpret(self, lstring: str) -> DrawingAST:
        """Execute turtle instructions corresponding to the L-System symbol stream."""
        engine = self.engine
        angle = self._angle
        step = self._step_size
        step_scale = self.config.step_scale if self.config.step_scale > 0 else 1.0
        angle_scale = self.config.angle_scale if self.config.angle_scale > 0 else 1.0

        for ch in lstring:
            # Move forward drawing
            if ch in ("F", "G"):
                engine.forward(step)
            # Move forward without drawing (pen up)
            elif ch == "f":
                engine.pen_up()
                engine.forward(step)
                engine.pen_down()
            # Turn Right (Clockwise)
            elif ch == "+":
                engine.right(angle)
            # Turn Left (Counter-Clockwise)
            elif ch == "-":
                engine.left(angle)
            # Push state
            elif ch == "[":
                engine.push_state()
            # Pop state
            elif ch == "]":
                engine.pop_state()
            # Reverse direction (180 deg)
            elif ch == "|":
                engine.left(180.0)
            # Scale step smaller
            elif ch == "<":
                step *= step_scale
            # Scale step larger
            elif ch == ">":
                step /= step_scale if step_scale != 0 else 1.0
            # Scale angle smaller
            elif ch == "(":
                angle *= angle_scale
            # Scale angle larger
            elif ch == ")":
                angle /= angle_scale if angle_scale != 0 else 1.0
            # Cycle color
            elif ch == "C":
                self._palette_idx = (self._palette_idx + 1) % len(self.palette)
                engine.set_color(self.palette[self._palette_idx])
            # Begin fill
            elif ch == "{":
                engine.begin_fill()
            # End fill
            elif ch == "}":
                engine.end_fill()
            # Increase stroke width
            elif ch == "#":
                engine.set_width(engine.stroke_width + 0.5)
            # Decrease stroke width
            elif ch == "!":
                engine.set_width(max(0.2, engine.stroke_width - 0.5))
            else:
                # Non-terminal / catalyst characters (A, B, X, Y, Z, M, N, L, R, W)
                # These guide the production rules without directly moving the pen.
                pass

        return engine.get_drawing()


def generate_lsystem(
    config: Optional[Union[LSystemConfig, str]] = None,
    iterations: Optional[int] = None,
    seed: Optional[int] = None,
    palette: Optional[List[str]] = None,
    axiom: Optional[str] = None,
    rules: Optional[Union[Dict[str, Any], Sequence[LSystemRule]]] = None,
    angle_deg: Optional[float] = None,
    angle: Optional[float] = None,
    step_size: Optional[float] = None,
    initial_heading_deg: Optional[float] = None,
    **kwargs: Any,
) -> DrawingAST:
    """Generate a complete DrawingAST from an L-System configuration or raw parameters."""
    if isinstance(config, LSystemConfig):
        cfg = config
    elif isinstance(config, str):
        # config is axiom string
        ax = config
        rul = rules or {}
        ang = angle_deg if angle_deg is not None else (angle if angle is not None else 60.0)
        stp = step_size if step_size is not None else 10.0
        iters = iterations if iterations is not None else 3
        heading = initial_heading_deg if initial_heading_deg is not None else 0.0
        cfg = LSystemConfig(
            axiom=ax,
            rules=rul if isinstance(rul, dict) else {},
            angle=ang,
            iterations=iters,
            step_size=stp,
            start_heading=heading,
        )
    else:
        ax = axiom or "F"
        rul = rules or {}
        ang = angle_deg if angle_deg is not None else (angle if angle is not None else 60.0)
        stp = step_size if step_size is not None else 10.0
        iters = iterations if iterations is not None else 3
        heading = initial_heading_deg if initial_heading_deg is not None else 0.0
        cfg = LSystemConfig(
            axiom=ax,
            rules=rul if isinstance(rul, dict) else {},
            angle=ang,
            iterations=iters,
            step_size=stp,
            start_heading=heading,
        )

    iters = iterations if iterations is not None else cfg.iterations
    s = seed if seed is not None else cfg.seed

    expanded = expand_lsystem(cfg.axiom, cfg.rules, iters, seed=s)
    interpreter = LSystemInterpreter(cfg, palette=palette)
    drawing = interpreter.interpret(expanded)
    drawing.title = cfg.name or "L-System"
    drawing.metadata.update({
        "iterations": iters,
        "axiom": cfg.axiom,
        "angle": cfg.angle,
        "seed": s,
        "symbol_length": len(expanded),
    })
    return drawing


LSystemEngine = LSystemInterpreter



# ---------------------------------------------------------------------------
# 28+ Built-in L-System Fractal & Sacred Geometry Presets
# ---------------------------------------------------------------------------

PRESETS_DATA: List[Dict[str, Any]] = [
    # 1. Koch Snowflake
    {
        "id": "koch_snowflake",
        "name": "Koch Snowflake",
        "category": "Fractals",
        "description": "Classic Helge von Koch tri-symmetric snowflake fractal.",
        "difficulty": "Beginner",
        "recommended_iterations": 4,
        "default_theme": "cyber_matrix",
        "tags": ["fractal", "classic", "snowflake", "symmetry"],
        "credit": "Niels Fabian Helge von Koch (1904)",
        "config": {
            "name": "Koch Snowflake",
            "axiom": "F--F--F",
            "rules": {"F": "F+F--F+F"},
            "angle": 60.0,
            "iterations": 4,
            "step_size": 10.0,
            "start_heading": 0.0,
        },
    },
    # 2. Koch Anti-Snowflake
    {
        "id": "koch_anti_snowflake",
        "name": "Koch Anti-Snowflake",
        "category": "Fractals",
        "description": "Inverted Koch snowflake with inward-facing fractal indentations.",
        "difficulty": "Beginner",
        "recommended_iterations": 4,
        "default_theme": "blueprint_cyan",
        "tags": ["fractal", "inverted", "snowflake"],
        "credit": "Helge von Koch",
        "config": {
            "name": "Koch Anti-Snowflake",
            "axiom": "F--F--F",
            "rules": {"F": "F-F++F-F"},
            "angle": 60.0,
            "iterations": 4,
            "step_size": 10.0,
            "start_heading": 0.0,
        },
    },
    # 3. Dragon Curve (Heighway)
    {
        "id": "dragon_curve",
        "name": "Heighway Dragon Curve",
        "category": "Space-Filling Curves",
        "description": "Self-similar dragon fractal generated by repeated 90-degree folding.",
        "difficulty": "Intermediate",
        "recommended_iterations": 10,
        "default_theme": "synthwave_neon",
        "tags": ["space-filling", "dragon", "heighway", "origami"],
        "credit": "John Heighway, Bruce Banks, William Harter (1966)",
        "config": {
            "name": "Heighway Dragon Curve",
            "axiom": "FX",
            "rules": {"X": "X+YF+", "Y": "-FX-Y"},
            "angle": 90.0,
            "iterations": 10,
            "step_size": 8.0,
            "start_heading": 0.0,
        },
    },
    # 4. Terdragon
    {
        "id": "terdragon",
        "name": "Terdragon Curve",
        "category": "Space-Filling Curves",
        "description": "3-fold dragon curve with 120-degree angular turns.",
        "difficulty": "Intermediate",
        "recommended_iterations": 6,
        "default_theme": "sacred_gold",
        "tags": ["dragon", "terdragon", "tiling", "triangular"],
        "credit": "Benoit Mandelbrot / Davis & Knuth",
        "config": {
            "name": "Terdragon Curve",
            "axiom": "F",
            "rules": {"F": "F-F+F"},
            "angle": 120.0,
            "iterations": 6,
            "step_size": 10.0,
            "start_heading": 0.0,
        },
    },
    # 5. Levy C Curve
    {
        "id": "levy_c_curve",
        "name": "Lévy C Curve",
        "category": "Fractals",
        "description": "Isosceles right triangle perimeter fractal forming ornate leafy lace.",
        "difficulty": "Intermediate",
        "recommended_iterations": 10,
        "default_theme": "cyber_matrix",
        "tags": ["fractal", "levy", "lace", "self-similar"],
        "credit": "Paul Lévy (1938)",
        "config": {
            "name": "Lévy C Curve",
            "axiom": "F",
            "rules": {"F": "+F--F+"},
            "angle": 45.0,
            "iterations": 10,
            "step_size": 8.0,
            "start_heading": 0.0,
        },
    },
    # 6. Hilbert Curve
    {
        "id": "hilbert_curve",
        "name": "Hilbert Space-Filling Curve",
        "category": "Space-Filling Curves",
        "description": "Continuous space-filling fractal mapping 1D interval into 2D plane.",
        "difficulty": "Intermediate",
        "recommended_iterations": 5,
        "default_theme": "blueprint_cyan",
        "tags": ["space-filling", "hilbert", "locality", "matrix"],
        "credit": "David Hilbert (1891)",
        "config": {
            "name": "Hilbert Space-Filling Curve",
            "axiom": "X",
            "rules": {"X": "-YF+XFX+FY-", "Y": "+XF-YFY-FX+"},
            "angle": 90.0,
            "iterations": 5,
            "step_size": 10.0,
            "start_heading": 0.0,
        },
    },
    # 7. Moore Curve
    {
        "id": "moore_curve",
        "name": "Moore Space-Filling Curve",
        "category": "Space-Filling Curves",
        "description": "Loop version of the Hilbert curve forming a closed continuous perimeter.",
        "difficulty": "Intermediate",
        "recommended_iterations": 4,
        "default_theme": "retro_amber",
        "tags": ["space-filling", "moore", "hilbert", "loop"],
        "credit": "E. H. Moore (1900)",
        "config": {
            "name": "Moore Space-Filling Curve",
            "axiom": "LFL+F+LFL",
            "rules": {"L": "-RF+LFL+FR-", "R": "+LF-RFR-FL+"},
            "angle": 90.0,
            "iterations": 4,
            "step_size": 10.0,
            "start_heading": 0.0,
        },
    },
    # 8. Gosper Hexagonal Curve (Flowsnake)
    {
        "id": "gosper_curve",
        "name": "Gosper Flowsnake Curve",
        "category": "Space-Filling Curves",
        "description": "Hexagonal space-filling curve forming intricate interlocking fractal tiles.",
        "difficulty": "Advanced",
        "recommended_iterations": 4,
        "default_theme": "sacred_gold",
        "tags": ["space-filling", "gosper", "flowsnake", "hexagonal"],
        "credit": "Bill Gosper (1973)",
        "config": {
            "name": "Gosper Flowsnake Curve",
            "axiom": "X",
            "rules": {
                "X": "X+YF++YF-FX--FXFX-YF+",
                "Y": "-FX+YFYF++YF+FX--FX-Y",
            },
            "angle": 60.0,
            "iterations": 4,
            "step_size": 8.0,
            "start_heading": 0.0,
        },
    },
    # 9. Sierpinski Triangle (Gasket)
    {
        "id": "sierpinski_triangle",
        "name": "Sierpiński Triangle",
        "category": "Fractals",
        "description": "Triangular fractal subdivided recursively into smaller equilateral triangles.",
        "difficulty": "Beginner",
        "recommended_iterations": 5,
        "default_theme": "cyber_matrix",
        "tags": ["fractal", "sierpinski", "triangle", "gasket"],
        "credit": "Wacław Sierpiński (1915)",
        "config": {
            "name": "Sierpiński Triangle",
            "axiom": "F-G-G",
            "rules": {"F": "F-G+F+G-F", "G": "GG"},
            "angle": 120.0,
            "iterations": 5,
            "step_size": 10.0,
            "start_heading": 0.0,
        },
    },
    # 10. Sierpinski Carpet
    {
        "id": "sierpinski_carpet",
        "name": "Sierpiński Carpet",
        "category": "Fractals",
        "description": "Square-based fractal formed by removing center square recursively.",
        "difficulty": "Advanced",
        "recommended_iterations": 3,
        "default_theme": "blueprint_cyan",
        "tags": ["fractal", "sierpinski", "carpet", "square"],
        "credit": "Wacław Sierpiński (1916)",
        "config": {
            "name": "Sierpiński Carpet",
            "axiom": "F",
            "rules": {"F": "F+F-F-F-G+F+F+F-F", "G": "GGG"},
            "angle": 90.0,
            "iterations": 3,
            "step_size": 8.0,
            "start_heading": 0.0,
        },
    },
    # 11. Sierpinski Arrowhead
    {
        "id": "sierpinski_arrowhead",
        "name": "Sierpiński Arrowhead Curve",
        "category": "Fractals",
        "description": "Continuous fractal curve whose limit set is the Sierpiński triangle.",
        "difficulty": "Intermediate",
        "recommended_iterations": 6,
        "default_theme": "synthwave_neon",
        "tags": ["fractal", "sierpinski", "arrowhead", "curve"],
        "credit": "Wacław Sierpiński",
        "config": {
            "name": "Sierpiński Arrowhead Curve",
            "axiom": "XF",
            "rules": {"X": "YF+XF+Y", "Y": "XF-YF-X"},
            "angle": 60.0,
            "iterations": 6,
            "step_size": 8.0,
            "start_heading": 0.0,
        },
    },
    # 12. Peano Curve
    {
        "id": "peano_curve",
        "name": "Peano Space-Filling Curve",
        "category": "Space-Filling Curves",
        "description": "First discovered space-filling curve mapping 1D interval into 2D unit square.",
        "difficulty": "Advanced",
        "recommended_iterations": 3,
        "default_theme": "retro_amber",
        "tags": ["space-filling", "peano", "classic", "grid"],
        "credit": "Giuseppe Peano (1890)",
        "config": {
            "name": "Peano Space-Filling Curve",
            "axiom": "X",
            "rules": {
                "X": "XFYFX+F+YFXFY-F-XFYFX",
                "Y": "YFXFY-F-XFYFX+F+YFXFY",
            },
            "angle": 90.0,
            "iterations": 3,
            "step_size": 8.0,
            "start_heading": 0.0,
        },
    },
    # 13. Pythagoras Tree
    {
        "id": "pythagoras_tree",
        "name": "Pythagoras Tree",
        "category": "Plants & Trees",
        "description": "Geometric tree constructed from nested right-angled triangles and squares.",
        "difficulty": "Intermediate",
        "recommended_iterations": 6,
        "default_theme": "sacred_gold",
        "tags": ["tree", "pythagoras", "botany", "harmonic"],
        "credit": "Albert E. Bosman (1942)",
        "config": {
            "name": "Pythagoras Tree",
            "axiom": "X",
            "rules": {"X": "F[+X][-X]", "F": "FF"},
            "angle": 45.0,
            "iterations": 6,
            "step_size": 6.0,
            "start_heading": 90.0,
        },
    },
    # 14. Barnsley Fern
    {
        "id": "barnsley_fern",
        "name": "Barnsley Fern (L-System)",
        "category": "Plants & Trees",
        "description": "Biological fern frond pattern modeled as an iterated branching system.",
        "difficulty": "Intermediate",
        "recommended_iterations": 6,
        "default_theme": "cyber_matrix",
        "tags": ["plants", "fern", "barnsley", "botanical"],
        "credit": "Michael Barnsley (1988)",
        "config": {
            "name": "Barnsley Fern (L-System)",
            "axiom": "X",
            "rules": {
                "X": "F[+X]F[-X]+X",
                "F": "FF",
            },
            "angle": 25.0,
            "iterations": 6,
            "step_size": 5.0,
            "start_heading": 90.0,
        },
    },
    # 15. Fractal Plant A (Prusinkiewicz Classic)
    {
        "id": "fractal_plant_a",
        "name": "Prusinkiewicz Classic Plant",
        "category": "Plants & Trees",
        "description": "Delicate natural weed and stem branching system with multi-tier leaf clusters.",
        "difficulty": "Intermediate",
        "recommended_iterations": 5,
        "default_theme": "cyber_matrix",
        "tags": ["plants", "prusinkiewicz", "classic", "botany"],
        "credit": "Przemyslaw Prusinkiewicz (1986)",
        "config": {
            "name": "Prusinkiewicz Classic Plant",
            "axiom": "X",
            "rules": {
                "X": "F+[[X]-X]-F[-FX]+X",
                "F": "FF",
            },
            "angle": 25.0,
            "iterations": 5,
            "step_size": 6.0,
            "start_heading": 65.0,
        },
    },
    # 16. Fractal Plant B (Simple Bush)
    {
        "id": "fractal_plant_b",
        "name": "Fractal Bush",
        "category": "Plants & Trees",
        "description": "Dense leafy bush with balanced symmetric sub-branches.",
        "difficulty": "Intermediate",
        "recommended_iterations": 5,
        "default_theme": "cyber_matrix",
        "tags": ["plants", "bush", "shrub", "symmetric"],
        "credit": "The Algorithmic Beauty of Plants",
        "config": {
            "name": "Fractal Bush",
            "axiom": "F",
            "rules": {"F": "FF+[+F-F-F]-[-F+F+F]"},
            "angle": 22.5,
            "iterations": 4,
            "step_size": 8.0,
            "start_heading": 90.0,
        },
    },
    # 17. Fractal Plant C (Wheat / Wild Weed)
    {
        "id": "fractal_plant_c",
        "name": "Wild Wheat / Grass Frond",
        "category": "Plants & Trees",
        "description": "Slender grass blades and grain-like side branching structures.",
        "difficulty": "Intermediate",
        "recommended_iterations": 5,
        "default_theme": "retro_amber",
        "tags": ["plants", "wheat", "grass", "slender"],
        "credit": "L-System Botanical Archives",
        "config": {
            "name": "Wild Wheat / Grass Frond",
            "axiom": "F",
            "rules": {"F": "F[+F]F[-F][F]"},
            "angle": 20.0,
            "iterations": 5,
            "step_size": 8.0,
            "start_heading": 90.0,
        },
    },
    # 18. Fractal Plant D (Stochastic Canopy Tree)
    {
        "id": "fractal_plant_d",
        "name": "Stochastic Branching Tree",
        "category": "Plants & Trees",
        "description": "Stochastic naturalistic tree model with varied branch angles and density.",
        "difficulty": "Advanced",
        "recommended_iterations": 5,
        "default_theme": "sacred_gold",
        "tags": ["plants", "stochastic", "tree", "canopy", "nature"],
        "credit": "cyber-turtle-studio",
        "config": {
            "name": "Stochastic Branching Tree",
            "axiom": "X",
            "rules": {
                "X": [
                    {"successor": "F[+X][-X]FX", "probability": 0.35},
                    {"successor": "F[+X]F[-X]+X", "probability": 0.35},
                    {"successor": "F[-X]F[+X]-X", "probability": 0.30},
                ],
                "F": "FF",
            },
            "angle": 22.5,
            "iterations": 5,
            "step_size": 6.0,
            "start_heading": 90.0,
            "seed": 42,
        },
    },
    # 19. Fractal Plant E (Vines / Tendrils)
    {
        "id": "fractal_plant_e",
        "name": "Cyber Vines & Tendrils",
        "category": "Plants & Trees",
        "description": "Curving tendrils and crawling vine structures.",
        "difficulty": "Intermediate",
        "recommended_iterations": 4,
        "default_theme": "synthwave_neon",
        "tags": ["plants", "vines", "tendrils", "spiral"],
        "credit": "cyber-turtle-studio",
        "config": {
            "name": "Cyber Vines & Tendrils",
            "axiom": "X",
            "rules": {
                "X": "F-[[X]+X]+F[+FX]-X",
                "F": "FF",
            },
            "angle": 22.5,
            "iterations": 4,
            "step_size": 8.0,
            "start_heading": 90.0,
        },
    },
    # 20. Kolam Tile (Anklets of Krishna / Indian Floor Art)
    {
        "id": "kolam_tile",
        "name": "Kolam Sacred Tile (Krishna Anklets)",
        "category": "Tiles & Kolam",
        "description": "Sacred Indian geometric floor art with endless loops and harmonic symmetry.",
        "difficulty": "Advanced",
        "recommended_iterations": 4,
        "default_theme": "sacred_gold",
        "tags": ["kolam", "sacred-geometry", "indian-art", "symmetry", "loops"],
        "credit": "Traditional South Indian Kolam / Prusinkiewicz & Lindenmayer",
        "config": {
            "name": "Kolam Sacred Tile (Krishna Anklets)",
            "axiom": "-X--X",
            "rules": {"X": "XFX--XFX"},
            "angle": 45.0,
            "iterations": 4,
            "step_size": 10.0,
            "start_heading": 0.0,
        },
    },
    # 21. Quadratic Koch Island (Minkowski Sausage)
    {
        "id": "quadratic_koch_island",
        "name": "Quadratic Koch Island (Minkowski)",
        "category": "Fractals",
        "description": "Square perimeter fractal with 90-degree square recursive bays.",
        "difficulty": "Intermediate",
        "recommended_iterations": 3,
        "default_theme": "blueprint_cyan",
        "tags": ["fractal", "koch", "minkowski", "island", "square"],
        "credit": "Hermann Minkowski / Benoit Mandelbrot",
        "config": {
            "name": "Quadratic Koch Island (Minkowski)",
            "axiom": "F-F-F-F",
            "rules": {"F": "F+FF-FF-F-F+F+FF-F"},
            "angle": 90.0,
            "iterations": 3,
            "step_size": 8.0,
            "start_heading": 0.0,
        },
    },
    # 22. Crystal Lattice (Hexagonal Snowflake Crystal)
    {
        "id": "crystal_lattice",
        "name": "Hexagonal Crystal Lattice",
        "category": "Sacred Geometry",
        "description": "Six-fold crystalline lattice with nested hexagonal molecular motifs.",
        "difficulty": "Intermediate",
        "recommended_iterations": 4,
        "default_theme": "blueprint_cyan",
        "tags": ["crystal", "lattice", "hexagonal", "sacred-geometry"],
        "credit": "cyber-turtle-studio",
        "config": {
            "name": "Hexagonal Crystal Lattice",
            "axiom": "F+F+F+F+F+F",
            "rules": {"F": "F-F++F-F"},
            "angle": 60.0,
            "iterations": 4,
            "step_size": 8.0,
            "start_heading": 0.0,
        },
    },
    # 23. Cross Curve / Greek Cross
    {
        "id": "cross_curve",
        "name": "Fractal Greek Cross",
        "category": "Sacred Geometry",
        "description": "Four-fold symmetric cross fractal expanding outward in quadratic steps.",
        "difficulty": "Beginner",
        "recommended_iterations": 4,
        "default_theme": "sacred_gold",
        "tags": ["cross", "greek-cross", "symmetry", "sacred-geometry"],
        "credit": "Classic L-System Collection",
        "config": {
            "name": "Fractal Greek Cross",
            "axiom": "F+F+F+F",
            "rules": {"F": "F+F-F-FF+F+F-F"},
            "angle": 90.0,
            "iterations": 3,
            "step_size": 10.0,
            "start_heading": 0.0,
        },
    },
    # 24. Quadratic Gosper Curve (E-Curve)
    {
        "id": "quadratic_gosper",
        "name": "Quadratic Gosper (E-Curve)",
        "category": "Space-Filling Curves",
        "description": "Grid-aligned space-filling curve forming intricate square labyrinth patterns.",
        "difficulty": "Advanced",
        "recommended_iterations": 3,
        "default_theme": "cyber_matrix",
        "tags": ["space-filling", "labyrinth", "gosper", "grid"],
        "credit": "Bill Gosper",
        "config": {
            "name": "Quadratic Gosper (E-Curve)",
            "axiom": "-YF",
            "rules": {
                "X": "XFX-YF-YF+FX+FX-YF-YFFX+YF+FXFXYF-FX+YF+FXFX+YF-FXYF-YF-FX+FX+YFYF-",
                "Y": "+FXFX-YF-YF+FX+FXYF+FX-YFYF-FX-YF+FXYFYF-FX-YFFX+FX+YF-YF-FX+FX+YFY",
            },
            "angle": 90.0,
            "iterations": 2,
            "step_size": 8.0,
            "start_heading": 0.0,
        },
    },
    # 25. Pentaplexity (Penrose Tile Motif)
    {
        "id": "pentaplexity",
        "name": "Pentaplexity (Penrose 5-Fold)",
        "category": "Sacred Geometry",
        "description": "5-fold rotational symmetry fractal tile based on Penrose aperiodic tiling.",
        "difficulty": "Master",
        "recommended_iterations": 4,
        "default_theme": "sacred_gold",
        "tags": ["penrose", "pentagonal", "sacred-geometry", "aperiodic", "5-fold"],
        "credit": "Roger Penrose (1974)",
        "config": {
            "name": "Pentaplexity (Penrose 5-Fold)",
            "axiom": "F++F++F++F++F",
            "rules": {"F": "F++F++F+++++F-F++F"},
            "angle": 36.0,
            "iterations": 4,
            "step_size": 10.0,
            "start_heading": 0.0,
        },
    },
    # 26. Cesaro Fractal (Torn Square)
    {
        "id": "cesaro_fractal",
        "name": "Cesàro Torn Square",
        "category": "Fractals",
        "description": "Self-similar torn square curve with subtle non-orthogonal 85-degree angles.",
        "difficulty": "Intermediate",
        "recommended_iterations": 4,
        "default_theme": "retro_amber",
        "tags": ["cesaro", "fractal", "torn-square", "geometry"],
        "credit": "Ernesto Cesàro (1906)",
        "config": {
            "name": "Cesàro Torn Square",
            "axiom": "F+F+F+F",
            "rules": {"F": "F+F--F+F"},
            "angle": 85.0,
            "iterations": 4,
            "step_size": 10.0,
            "start_heading": 0.0,
        },
    },
    # 27. Mango Tree / Canopy
    {
        "id": "mango_canopy",
        "name": "Mango Canopy Tree",
        "category": "Plants & Trees",
        "description": "Full rounded fruit tree canopy with dense spreading crown foliage.",
        "difficulty": "Intermediate",
        "recommended_iterations": 5,
        "default_theme": "cyber_matrix",
        "tags": ["plants", "tree", "canopy", "fruit-tree", "crown"],
        "credit": "cyber-turtle-studio",
        "config": {
            "name": "Mango Canopy Tree",
            "axiom": "X",
            "rules": {
                "X": "F[+X][-X][++X][--X]FX",
                "F": "FF",
            },
            "angle": 28.0,
            "iterations": 4,
            "step_size": 7.0,
            "start_heading": 90.0,
        },
    },
    # 28. Cyber Circuit Grid (Techno-Fractal)
    {
        "id": "cyber_circuit_grid",
        "name": "Cyber Circuit Bus Matrix",
        "category": "Techno & Circuit",
        "description": "Orthogonal PCB circuit trace network and microchip bus interconnects.",
        "difficulty": "Intermediate",
        "recommended_iterations": 4,
        "default_theme": "cyber_matrix",
        "tags": ["circuit", "pcb", "cyber", "techno", "orthogonal"],
        "credit": "cyber-turtle-studio",
        "config": {
            "name": "Cyber Circuit Bus Matrix",
            "axiom": "F+F+F+F",
            "rules": {
                "F": "FF+F-F+F+FF",
            },
            "angle": 90.0,
            "iterations": 3,
            "step_size": 10.0,
            "start_heading": 0.0,
        },
    },
]


def get_builtin_presets() -> List[PatternPreset]:
    """Instantiate and return all 28+ built-in pattern presets."""
    presets: List[PatternPreset] = []
    for item in PRESETS_DATA:
        cfg = LSystemConfig.from_dict(item["config"])
        preset = PatternPreset(
            id=item["id"],
            name=item["name"],
            category=item["category"],
            description=item["description"],
            config=cfg,
            tags=item.get("tags", []),
            difficulty=item.get("difficulty", "Beginner"),
            recommended_iterations=int(item.get("recommended_iterations", 4)),
            default_theme=item.get("default_theme", "cyber_matrix"),
            credit=item.get("credit", ""),
        )
        presets.append(preset)
    return presets


LSystemEngine = LSystemInterpreter

