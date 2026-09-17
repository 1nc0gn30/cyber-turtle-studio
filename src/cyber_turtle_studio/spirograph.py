"""Spirograph (Hypotrochoid / Epitrochoid) and Harmonograph Acoustic Resonance Synthesizer.

Generates parametric geometric curves and multi-pendulum harmonic resonance traces as DrawingASTs.
100% Python Standard Library. Zero external dependencies.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple, Union

from cyber_turtle_studio.models import DrawingAST, PathSegment, PathSegmentType, Point2D


def _gcd(a: int, b: int) -> int:
    """Greatest Common Divisor helper."""
    while b:
        a, b = b, a % b
    return abs(a)


def generate_spirograph(
    R: float = 120.0,
    r: float = 80.0,
    d: float = 50.0,
    curve_type: str = "hypotrochoid",  # 'hypotrochoid' or 'epitrochoid'
    step_deg: float = 1.0,
    num_points: Optional[int] = None,
    color: str = "#00ffcc",
    stroke_width: float = 1.2,
    center: Optional[Point2D] = None,
) -> DrawingAST:
    """Generate a mathematical Spirograph curve (Hypotrochoid or Epitrochoid).

    Calculates exact closure period using the ratio of circle radii R and r.
    Hypotrochoid rolls inside the fixed circle; Epitrochoid rolls outside.
    """
    if R <= 0 or r <= 0 or d <= 0:
        raise ValueError("Radii R, r and distance d must be positive numbers")

    curve_type_clean = curve_type.lower().strip()
    if curve_type_clean not in ("hypotrochoid", "epitrochoid"):
        raise ValueError(f"Invalid curve_type: '{curve_type}'. Must be 'hypotrochoid' or 'epitrochoid'")

    origin = center or Point2D(0.0, 0.0)
    drawing = DrawingAST(title=f"Spirograph_{curve_type_clean}")

    # Calculate period until curve closes: k = r / gcd(R, r) revolutions of outer circle
    int_R = max(1, int(round(abs(R) * 100)))
    int_r = max(1, int(round(abs(r) * 100)))
    common = _gcd(int_R, int_r)
    rotations = int_r // common
    max_theta = 2.0 * math.pi * rotations

    # Clamp rotations to avoid millions of points
    max_theta = min(max_theta, 2.0 * math.pi * 100)

    if num_points is not None and num_points > 1:
        step_rad = max_theta / (num_points - 1)
    else:
        step_rad = math.radians(max(0.1, step_deg))
    is_hypo = curve_type_clean == "hypotrochoid"

    points: List[Point2D] = []
    theta = 0.0
    while theta <= max_theta + (step_rad / 2.0):
        if is_hypo:
            # Hypotrochoid equations
            diff = R - r
            ratio = diff / r if r != 0 else 1.0
            x = diff * math.cos(theta) + d * math.cos(ratio * theta)
            y = diff * math.sin(theta) - d * math.sin(ratio * theta)
        else:
            # Epitrochoid equations
            total = R + r
            ratio = total / r if r != 0 else 1.0
            x = total * math.cos(theta) - d * math.cos(ratio * theta)
            y = total * math.sin(theta) - d * math.sin(ratio * theta)

        points.append(Point2D(origin.x + x, origin.y + y))
        theta += step_rad

    # Convert consecutive point pairs into LINE segments
    for i in range(len(points) - 1):
        seg = PathSegment(
            segment_type=PathSegmentType.LINE,
            start=points[i],
            end=points[i + 1],
            color=color,
            stroke_width=stroke_width,
            is_draw=True,
        )
        drawing.add_segment(seg)

    return drawing


def generate_harmonograph(
    f1: float = 2.001,
    f2: float = 3.0,
    f3: float = 3.002,
    f4: float = 2.0,
    d1: float = 0.003,
    d2: float = 0.003,
    d3: float = 0.003,
    d4: float = 0.003,
    p1: float = 0.0,
    p2: float = math.pi / 2.0,
    p3: float = 0.0,
    p4: float = math.pi / 2.0,
    scale: float = 160.0,
    duration_steps: int = 1500,
    num_points: Optional[int] = None,
    t_max: Optional[float] = None,
    dt: float = 0.02,
    color: str = "#ff007f",
    stroke_width: float = 1.0,
    center: Optional[Point2D] = None,
) -> DrawingAST:
    """Generate a multi-pendulum rotary harmonograph acoustic resonance curve."""
    origin = center or Point2D(0.0, 0.0)
    drawing = DrawingAST(title="Harmonograph_resonance")

    total_steps = num_points if num_points is not None else duration_steps
    eff_dt = (t_max / total_steps) if (t_max is not None and total_steps > 0) else dt

    points: List[Point2D] = []
    t = 0.0

    for _ in range(total_steps):
        # Decay terms
        decay_x1 = math.exp(-d1 * t)
        decay_x2 = math.exp(-d2 * t)
        decay_y1 = math.exp(-d3 * t)
        decay_y2 = math.exp(-d4 * t)

        # Coordinate synthesis
        x = (math.sin(f1 * t + p1) * decay_x1 + math.sin(f2 * t + p2) * decay_x2) * 0.5 * scale
        y = (math.sin(f3 * t + p3) * decay_y1 + math.sin(f4 * t + p4) * decay_y2) * 0.5 * scale

        points.append(Point2D(origin.x + x, origin.y + y))
        t += dt

    for i in range(len(points) - 1):
        seg = PathSegment(
            segment_type=PathSegmentType.LINE,
            start=points[i],
            end=points[i + 1],
            color=color,
            stroke_width=stroke_width,
            is_draw=True,
        )
        drawing.add_segment(seg)

    return drawing
