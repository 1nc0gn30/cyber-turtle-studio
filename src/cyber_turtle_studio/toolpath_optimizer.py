"""
Toolpath Optimizer: Pen-Plotter Traveling Salesperson (TSP) & 2-Opt Rapid Air Travel Minimizer.
Zero external runtime dependencies (100% Python Standard Library).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from cyber_turtle_studio.models import (
    DrawingAST,
    PathSegment,
    PathSegmentType,
    Point2D,
)


@dataclass
class Polyline:
    """Continuous chain of drawing segments that can be traversed forward or backward."""
    segments: List[PathSegment]
    is_closed: bool = False

    @property
    def start_point(self) -> Point2D:
        return self.segments[0].start

    @property
    def end_point(self) -> Point2D:
        return self.segments[-1].end

    @property
    def length(self) -> float:
        total = 0.0
        for seg in self.segments:
            dx = seg.end.x - seg.start.x
            dy = seg.end.y - seg.start.y
            total += math.hypot(dx, dy)
        return total

    def reversed(self) -> Polyline:
        """Return a copy of the polyline with direction flipped."""
        rev_segs = []
        for seg in reversed(self.segments):
            rev_seg = PathSegment(
                segment_type=seg.segment_type,
                start=seg.end,
                end=seg.start,
                points=list(reversed(seg.points)) if seg.points else [],
                color=seg.color,
                stroke_width=seg.stroke_width,
                opacity=seg.opacity,
                is_fill=seg.is_fill,
            )
            rev_segs.append(rev_seg)
        return Polyline(segments=rev_segs, is_closed=self.is_closed)


@dataclass
class ToolpathOptimizationReport:
    """Quantitative performance comparison between unoptimized and optimized toolpaths."""
    initial_air_travel_mm: float
    optimized_air_travel_mm: float
    reduction_percent: float
    drawing_distance_mm: float
    total_polylines: int
    pen_up_count: int
    estimated_time_initial_sec: float
    estimated_time_optimized_sec: float
    efficiency_score: float  # drawing_distance / (drawing_distance + air_travel)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "initial_air_travel_mm": round(self.initial_air_travel_mm, 2),
            "optimized_air_travel_mm": round(self.optimized_air_travel_mm, 2),
            "reduction_percent": round(self.reduction_percent, 2),
            "drawing_distance_mm": round(self.drawing_distance_mm, 2),
            "total_polylines": self.total_polylines,
            "pen_up_count": self.pen_up_count,
            "estimated_time_initial_sec": round(self.estimated_time_initial_sec, 2),
            "estimated_time_optimized_sec": round(self.estimated_time_optimized_sec, 2),
            "efficiency_score": round(self.efficiency_score, 4),
        }


class ToolpathOptimizer:
    """
    Optimizes pen-plotter vector toolpaths using Nearest-Neighbor Greedy Chaining
    and 2-Opt local search heuristics to eliminate non-drawing rapid travel moves.
    """

    def __init__(
        self,
        connection_tolerance: float = 0.01,
        max_2opt_iterations: int = 50,
        draw_feedrate_mm_min: float = 1200.0,
        travel_feedrate_mm_min: float = 3000.0,
        pen_lift_time_sec: float = 0.2,
    ) -> None:
        self.tolerance = connection_tolerance
        self.max_2opt_iterations = max_2opt_iterations
        self.draw_speed = draw_feedrate_mm_min / 60.0  # mm/sec
        self.travel_speed = travel_feedrate_mm_min / 60.0  # mm/sec
        self.pen_lift_time = pen_lift_time_sec

    def extract_polylines(self, ast: DrawingAST) -> List[Polyline]:
        """
        Group consecutive connected drawing segments into continuous polylines.
        """
        polylines: List[Polyline] = []
        current_chain: List[PathSegment] = []

        for seg in ast.segments:
            if seg.segment_type == PathSegmentType.MOVE:
                if current_chain:
                    polylines.append(Polyline(segments=current_chain))
                    current_chain = []
                continue

            if not current_chain:
                current_chain.append(seg)
            else:
                prev_end = current_chain[-1].end
                # Check if current seg start connects to prev end
                dist = math.hypot(seg.start.x - prev_end.x, seg.start.y - prev_end.y)
                if dist <= self.tolerance:
                    current_chain.append(seg)
                else:
                    polylines.append(Polyline(segments=current_chain))
                    current_chain = [seg]

        if current_chain:
            polylines.append(Polyline(segments=current_chain))

        return polylines

    def calculate_air_travel(self, polylines: List[Polyline], start_pos: Optional[Point2D] = None) -> float:
        """Calculate total pen-up rapid air travel distance between polylines."""
        if not polylines:
            return 0.0

        pos = start_pos or Point2D(0.0, 0.0)
        total_air = 0.0

        for poly in polylines:
            dx = poly.start_point.x - pos.x
            dy = poly.start_point.y - pos.y
            total_air += math.hypot(dx, dy)
            pos = poly.end_point

        return total_air

    def optimize_toolpath(
        self,
        ast: DrawingAST,
        start_pos: Optional[Point2D] = None,
    ) -> Tuple[DrawingAST, ToolpathOptimizationReport]:
        """
        Optimize the sequence and orientation of drawing strokes in the AST.
        Returns the optimized DrawingAST and an optimization metrics report.
        """
        initial_polylines = self.extract_polylines(ast)
        if not initial_polylines:
            report = ToolpathOptimizationReport(
                initial_air_travel_mm=0.0,
                optimized_air_travel_mm=0.0,
                reduction_percent=0.0,
                drawing_distance_mm=0.0,
                total_polylines=0,
                pen_up_count=0,
                estimated_time_initial_sec=0.0,
                estimated_time_optimized_sec=0.0,
                efficiency_score=1.0,
            )
            return ast, report

        origin = start_pos or Point2D(0.0, 0.0)
        initial_air = self.calculate_air_travel(initial_polylines, origin)
        total_draw = sum(poly.length for poly in initial_polylines)

        # Step 1: Greedy Nearest-Neighbor with Directional Inversion
        unvisited = list(initial_polylines)
        ordered: List[Polyline] = []
        curr_pos = origin

        while unvisited:
            best_idx = 0
            best_dist = float("inf")
            best_reversed = False

            for i, poly in enumerate(unvisited):
                # Distance to forward start
                d_forward = math.hypot(poly.start_point.x - curr_pos.x, poly.start_point.y - curr_pos.y)
                # Distance to reversed start (original end)
                d_reversed = math.hypot(poly.end_point.x - curr_pos.x, poly.end_point.y - curr_pos.y)

                if d_forward < best_dist:
                    best_dist = d_forward
                    best_idx = i
                    best_reversed = False

                if d_reversed < best_dist:
                    best_dist = d_reversed
                    best_idx = i
                    best_reversed = True

            chosen = unvisited.pop(best_idx)
            if best_reversed:
                chosen = chosen.reversed()
            ordered.append(chosen)
            curr_pos = chosen.end_point

        # Step 2: 2-Opt Local Search Improvement
        improved = True
        iteration = 0
        n = len(ordered)

        while improved and iteration < self.max_2opt_iterations and n > 2:
            improved = False
            iteration += 1

            for i in range(n - 1):
                for j in range(i + 1, n):
                    # Evaluate if reversing subsegment [i...j] decreases air travel
                    current_dist = self.calculate_air_travel(ordered, origin)
                    # Candidate with slice reversed
                    candidate = ordered[:i] + [p.reversed() for p in reversed(ordered[i:j + 1])] + ordered[j + 1:]
                    cand_dist = self.calculate_air_travel(candidate, origin)

                    if cand_dist < current_dist - 1e-4:
                        ordered = candidate
                        improved = True
                        break
                if improved:
                    break

        optimized_air = self.calculate_air_travel(ordered, origin)
        reduction = ((initial_air - optimized_air) / initial_air * 100.0) if initial_air > 0 else 0.0

        # Construct new DrawingAST
        optimized_segments: List[PathSegment] = []
        for poly in ordered:
            # Pen-up travel move to polyline start
            move_seg = PathSegment(
                segment_type=PathSegmentType.MOVE,
                start=poly.start_point,
                end=poly.start_point,
            )
            optimized_segments.append(move_seg)
            optimized_segments.extend(poly.segments)

        title_val = getattr(ast, "title", "") or getattr(ast, "name", "")
        opt_ast = DrawingAST(
            title=f"{title_val}_optimized" if title_val else "optimized_drawing",
            segments=optimized_segments,
            background_color=ast.background_color,
            metadata=dict(ast.metadata),
        )

        time_init = (total_draw / self.draw_speed) + (initial_air / self.travel_speed) + (len(initial_polylines) * self.pen_lift_time)
        time_opt = (total_draw / self.draw_speed) + (optimized_air / self.travel_speed) + (len(ordered) * self.pen_lift_time)
        efficiency = total_draw / (total_draw + optimized_air) if (total_draw + optimized_air) > 0 else 1.0

        report = ToolpathOptimizationReport(
            initial_air_travel_mm=initial_air,
            optimized_air_travel_mm=optimized_air,
            reduction_percent=reduction,
            drawing_distance_mm=total_draw,
            total_polylines=len(ordered),
            pen_up_count=len(ordered),
            estimated_time_initial_sec=time_init,
            estimated_time_optimized_sec=time_opt,
            efficiency_score=efficiency,
        )

        return opt_ast, report


def render_toolpath_comparison_svg(
    unoptimized_ast: DrawingAST,
    optimized_ast: DrawingAST,
    width: float = 800.0,
    height: float = 400.0,
) -> str:
    """
    Generate an SVG visualization comparing unoptimized vs optimized toolpaths side-by-side
    with non-drawing pen-up travel paths drawn in red and green dashed lines.
    """
    box_unopt = unoptimized_ast.bounding_box()
    min_x = box_unopt.min_x if box_unopt.is_valid else 0.0
    min_y = box_unopt.min_y if box_unopt.is_valid else 0.0
    bw = max(box_unopt.width, 10.0)
    bh = max(box_unopt.height, 10.0)

    half_w = width / 2.0
    pad = 40.0
    scale = min((half_w - pad * 2) / bw, (height - pad * 2) / bh)

    def draw_panel(ast: DrawingAST, offset_x: float, air_color: str, title: str) -> List[str]:
        elements = [
            f'<text x="{offset_x + half_w / 2.0}" y="25" fill="#e8eaed" font-family="monospace" font-size="14" text-anchor="middle" font-weight="bold">{title}</text>'
        ]
        prev_pt = Point2D(0.0, 0.0)

        for seg in ast.segments:
            sx = offset_x + pad + (seg.start.x - min_x) * scale
            sy = pad + (bh - (seg.start.y - min_y)) * scale
            ex = offset_x + pad + (seg.end.x - min_x) * scale
            ey = pad + (bh - (seg.end.y - min_y)) * scale

            if seg.segment_type == PathSegmentType.MOVE:
                # Pen-up air travel
                elements.append(
                    f'<line x1="{prev_pt.x}" y1="{prev_pt.y}" x2="{ex}" y2="{ey}" stroke="{air_color}" stroke-width="1.2" stroke-dasharray="4,4" opacity="0.7" />'
                )
                prev_pt = Point2D(ex, ey)
            else:
                # Drawing move
                elements.append(
                    f'<line x1="{sx}" y1="{sy}" x2="{ex}" y2="{ey}" stroke="{seg.color}" stroke-width="2.0" stroke-linecap="round" />'
                )
                prev_pt = Point2D(ex, ey)

        return elements

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" style="background:#121316;">',
        f'<line x1="{half_w}" y1="0" x2="{half_w}" y2="{height}" stroke="#3c4043" stroke-width="1" stroke-dasharray="4,4" />',
    ]
    svg.extend(draw_panel(unoptimized_ast, 0.0, "#ea4335", "Unoptimized Toolpath (Red = Air Travel)"))
    svg.extend(draw_panel(optimized_ast, half_w, "#34a853", "2-Opt Optimized Toolpath (Green = Air Travel)"))
    svg.append("</svg>")

    return "\n".join(svg)
