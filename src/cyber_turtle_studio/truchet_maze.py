"""Truchet Tile Generator and Cyber Labyrinth Engine for cyber-turtle-studio.

Generates mathematical Truchet tiling patterns (Smith quarter-circle arcs, diagonal slashes,
concentric multi-track ribbons) and algorithmic mazes (Recursive Backtracker, Wilson's
uniform spanning trees, and braided loops) convertible directly into DrawingAST vector paths
for SVG export, G-code CNC pen plotting, and ASCII terminal visualization.

100% Python Standard Library. Zero external dependencies.
"""

from __future__ import annotations

import collections
import math
import random
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from .models import DrawingAST, PathSegment, PathSegmentType, Point2D


class TruchetStyle(str, Enum):
    """Visual style classification for Truchet tiles."""

    ARCS = "arcs"                       # Smith quarter-circle arcs (organic winding ribbons)
    DIAGONAL = "diagonal"               # Diagonal slashes (circuit board / meander lines)
    CONCENTRIC_ARCS = "concentric_arcs" # Dual concentric quarter-circle arcs
    CROSS_LINE = "cross_line"           # Perpendicular cross-connectors


class MazeAlgorithm(str, Enum):
    """Algorithmic maze generation method."""

    RECURSIVE_BACKTRACKER = "backtracker"  # Deep winding corridors, high river factor
    WILSON = "wilson"                      # Loop-erased random walks, unbiased uniform spanning tree
    BRAIDED = "braided"                    # Backtracker with removed dead-ends (ideal for continuous plotters)


def generate_truchet_tiling(
    rows: int = 12,
    cols: int = 12,
    tile_size: float = 40.0,
    style: Union[TruchetStyle, str] = TruchetStyle.ARCS,
    seed: Optional[int] = None,
    stroke_color: str = "#00ffcc",
    stroke_width: float = 2.0,
    arc_segments: int = 12,
) -> Tuple[DrawingAST, Dict[str, Any]]:
    """Generate a procedural Truchet tiling pattern as a DrawingAST and metadata dict.
    
    Args:
        rows: Number of tile rows.
        cols: Number of tile columns.
        tile_size: Dimensions (width and height) of each square tile in canvas units.
        style: Tiling variation (arcs, diagonal, concentric_arcs, cross_line).
        seed: Optional RNG seed for deterministic reproducibility.
        stroke_color: Hex color string for drawing strokes.
        stroke_width: Vector stroke thickness.
        arc_segments: Number of linear approximation subdivisions per 90-degree arc.

    Returns:
        Tuple of (DrawingAST, stats_dict).
    """
    if isinstance(style, str):
        try:
            style_enum = TruchetStyle(style.lower())
        except ValueError:
            raise ValueError(f"Unknown TruchetStyle: '{style}'. Must be one of {[s.value for s in TruchetStyle]}")
    elif isinstance(style, TruchetStyle):
        style_enum = style
    else:
        raise ValueError(f"Unknown TruchetStyle: {style}")

    rng = random.Random(seed)
    total_w = cols * tile_size
    total_h = rows * tile_size
    drawing = DrawingAST(canvas_width=total_w + 40.0, canvas_height=total_h + 40.0)

    ox = 20.0
    oy = 20.0
    half = tile_size / 2.0

    for r in range(rows):
        for c in range(cols):
            tx = ox + c * tile_size
            ty = oy + r * tile_size
            state = rng.choice([0, 1])

            if style_enum == TruchetStyle.DIAGONAL:
                if state == 0:
                    p1, p2 = Point2D(tx, ty), Point2D(tx + tile_size, ty + tile_size)
                else:
                    p1, p2 = Point2D(tx + tile_size, ty), Point2D(tx, ty + tile_size)
                drawing.add_segment(
                    PathSegment(
                        segment_type=PathSegmentType.LINE,
                        start=p1,
                        end=p2,
                        points=[p1, p2],
                        color=stroke_color,
                        stroke_width=stroke_width,
                        is_draw=True,
                    )
                )

            elif style_enum == TruchetStyle.CROSS_LINE:
                m_top = Point2D(tx + half, ty)
                m_bottom = Point2D(tx + half, ty + tile_size)
                m_left = Point2D(tx, ty + half)
                m_right = Point2D(tx + tile_size, ty + half)
                center = Point2D(tx + half, ty + half)

                if state == 0:
                    drawing.add_segment(
                        PathSegment(
                            segment_type=PathSegmentType.LINE,
                            start=m_left,
                            end=m_right,
                            points=[m_left, m_right],
                            color=stroke_color,
                            stroke_width=stroke_width,
                            is_draw=True,
                        )
                    )
                    drawing.add_segment(
                        PathSegment(
                            segment_type=PathSegmentType.LINE,
                            start=m_top,
                            end=m_bottom,
                            points=[m_top, m_bottom],
                            color=stroke_color,
                            stroke_width=stroke_width,
                            is_draw=True,
                        )
                    )
                else:
                    drawing.add_segment(
                        PathSegment(
                            segment_type=PathSegmentType.LINE,
                            start=m_left,
                            end=center,
                            points=[m_left, center],
                            color=stroke_color,
                            stroke_width=stroke_width,
                            is_draw=True,
                        )
                    )
                    drawing.add_segment(
                        PathSegment(
                            segment_type=PathSegmentType.LINE,
                            start=m_top,
                            end=center,
                            points=[m_top, center],
                            color=stroke_color,
                            stroke_width=stroke_width,
                            is_draw=True,
                        )
                    )
                    drawing.add_segment(
                        PathSegment(
                            segment_type=PathSegmentType.LINE,
                            start=center,
                            end=m_right,
                            points=[center, m_right],
                            color=stroke_color,
                            stroke_width=stroke_width,
                            is_draw=True,
                        )
                    )
                    drawing.add_segment(
                        PathSegment(
                            segment_type=PathSegmentType.LINE,
                            start=center,
                            end=m_bottom,
                            points=[center, m_bottom],
                            color=stroke_color,
                            stroke_width=stroke_width,
                            is_draw=True,
                        )
                    )

            elif style_enum == TruchetStyle.CONCENTRIC_ARCS:
                radii = [tile_size * 0.3, tile_size * 0.7]
                if state == 0:
                    centers = [((tx, ty), 0.0, math.pi / 2.0), ((tx + tile_size, ty + tile_size), math.pi, 1.5 * math.pi)]
                else:
                    centers = [((tx + tile_size, ty), math.pi / 2.0, math.pi), ((tx, ty + tile_size), 1.5 * math.pi, 2.0 * math.pi)]

                for (cx, cy), a_s, a_e in centers:
                    for r_val in radii:
                        pts = []
                        for s_idx in range(arc_segments + 1):
                            t = s_idx / arc_segments
                            ang = a_s + t * (a_e - a_s)
                            pts.append(Point2D(cx + r_val * math.cos(ang), cy + r_val * math.sin(ang)))
                        drawing.add_segment(
                            PathSegment(
                                segment_type=PathSegmentType.LINE,
                                start=pts[0],
                                end=pts[-1],
                                points=pts,
                                color=stroke_color,
                                stroke_width=stroke_width,
                                is_draw=True,
                            )
                        )

            else:  # TruchetStyle.ARCS
                rad = half
                if state == 0:
                    c1 = (tx, ty)
                    a1_start, a1_end = 0.0, math.pi / 2.0
                    c2 = (tx + tile_size, ty + tile_size)
                    a2_start, a2_end = math.pi, 3.0 * math.pi / 2.0
                else:
                    c1 = (tx + tile_size, ty)
                    a1_start, a1_end = math.pi / 2.0, math.pi
                    c2 = (tx, ty + tile_size)
                    a2_start, a2_end = 3.0 * math.pi / 2.0, 2.0 * math.pi

                for (cx, cy), a_s, a_e in [(c1, a1_start, a1_end), (c2, a2_start, a2_end)]:
                    pts = []
                    for s_idx in range(arc_segments + 1):
                        t = s_idx / arc_segments
                        ang = a_s + t * (a_e - a_s)
                        pts.append(Point2D(cx + rad * math.cos(ang), cy + rad * math.sin(ang)))
                    drawing.add_segment(
                        PathSegment(
                            segment_type=PathSegmentType.LINE,
                            start=pts[0],
                            end=pts[-1],
                            points=pts,
                            color=stroke_color,
                            stroke_width=stroke_width,
                            is_draw=True,
                        )
                    )

    stats = {
        "style": style_enum.value,
        "rows": rows,
        "cols": cols,
        "tile_size": tile_size,
        "total_tiles": rows * cols,
        "total_segments": len(drawing.segments),
        "bounds": {"width": total_w, "height": total_h},
    }
    return drawing, stats


def generate_maze_labyrinth(
    rows: int = 15,
    cols: int = 15,
    cell_size: float = 30.0,
    algorithm: Union[MazeAlgorithm, str] = MazeAlgorithm.RECURSIVE_BACKTRACKER,
    solve: bool = True,
    seed: Optional[int] = None,
    wall_color: str = "#00e5ff",
    path_color: str = "#00ff66",
    wall_stroke_width: float = 2.0,
    path_stroke_width: float = 3.0,
) -> Tuple[DrawingAST, Dict[str, Any]]:
    """Generate an algorithmic labyrinth with walls and solved pathfinding trail.
    
    Args:
        rows: Number of vertical grid cells.
        cols: Number of horizontal grid cells.
        cell_size: Pixel / canvas size of each grid cell.
        algorithm: Maze generation algorithm (Recursive Backtracker, Wilson's, Braided).
        solve: Whether to compute and draw the solved path from (0,0) to (rows-1, cols-1).
        seed: Random seed for deterministic pattern generation.

    Returns:
        Tuple of (DrawingAST, meta_dict).
    """
    if isinstance(algorithm, str):
        algo_str = algorithm.lower().strip()
        if algo_str in ("recursive_backtracker", "backtracker"):
            algo_enum = MazeAlgorithm.RECURSIVE_BACKTRACKER
        elif algo_str == "wilson":
            algo_enum = MazeAlgorithm.WILSON
        elif algo_str == "braided":
            algo_enum = MazeAlgorithm.BRAIDED
        else:
            raise ValueError(f"Unknown MazeAlgorithm: '{algorithm}'. Must be one of {[a.value for a in MazeAlgorithm]}")
    elif isinstance(algorithm, MazeAlgorithm):
        algo_enum = algorithm
    else:
        raise ValueError(f"Unknown MazeAlgorithm: {algorithm}")

    rng = random.Random(seed)
    total_w = cols * cell_size
    total_h = rows * cell_size
    drawing = DrawingAST(canvas_width=total_w + 40.0, canvas_height=total_h + 40.0)

    ox = 20.0
    oy = 20.0

    passages: Set[frozenset[Tuple[int, int]]] = set()

    def neighbors(r: int, c: int) -> List[Tuple[int, int]]:
        nbrs = []
        if r > 0: nbrs.append((r - 1, c))
        if r < rows - 1: nbrs.append((r + 1, c))
        if c > 0: nbrs.append((r, c - 1))
        if c < cols - 1: nbrs.append((r, c + 1))
        return nbrs

    if algo_enum in (MazeAlgorithm.RECURSIVE_BACKTRACKER, MazeAlgorithm.BRAIDED):
        visited: Set[Tuple[int, int]] = set()
        stack: List[Tuple[int, int]] = [(0, 0)]
        visited.add((0, 0))

        while stack:
            current = stack[-1]
            unvisited_nbrs = [n for n in neighbors(*current) if n not in visited]

            if unvisited_nbrs:
                chosen = rng.choice(unvisited_nbrs)
                passages.add(frozenset({current, chosen}))
                visited.add(chosen)
                stack.append(chosen)
            else:
                stack.pop()

        if algo_enum == MazeAlgorithm.BRAIDED:
            for r in range(rows):
                for c in range(cols):
                    cell = (r, c)
                    connected = [n for n in neighbors(r, c) if frozenset({cell, n}) in passages]
                    if len(connected) == 1:
                        candidates = [n for n in neighbors(r, c) if n not in connected]
                        if candidates:
                            choice = rng.choice(candidates)
                            passages.add(frozenset({cell, choice}))

    elif algo_enum == MazeAlgorithm.WILSON:
        in_maze: Set[Tuple[int, int]] = {(rng.randint(0, rows - 1), rng.randint(0, cols - 1))}
        unvisited = [((r, c)) for r in range(rows) for c in range(cols) if (r, c) not in in_maze]
        rng.shuffle(unvisited)

        for cell in unvisited:
            if cell in in_maze:
                continue

            path = [cell]
            current = cell
            while current not in in_maze:
                nbrs = neighbors(*current)
                next_cell = rng.choice(nbrs)
                if next_cell in path:
                    idx = path.index(next_cell)
                    path = path[:idx + 1]
                else:
                    path.append(next_cell)
                current = next_cell

            for i in range(len(path) - 1):
                passages.add(frozenset({path[i], path[i + 1]}))
                in_maze.add(path[i])
            in_maze.add(path[-1])

    # Outer border walls
    drawing.add_segment(PathSegment(segment_type=PathSegmentType.LINE, start=Point2D(ox, oy), end=Point2D(ox + total_w, oy), points=[Point2D(ox, oy), Point2D(ox + total_w, oy)], color=wall_color, stroke_width=wall_stroke_width))
    drawing.add_segment(PathSegment(segment_type=PathSegmentType.LINE, start=Point2D(ox, oy + total_h), end=Point2D(ox + total_w, oy + total_h), points=[Point2D(ox, oy + total_h), Point2D(ox + total_w, oy + total_h)], color=wall_color, stroke_width=wall_stroke_width))
    drawing.add_segment(PathSegment(segment_type=PathSegmentType.LINE, start=Point2D(ox, oy), end=Point2D(ox, oy + total_h), points=[Point2D(ox, oy), Point2D(ox, oy + total_h)], color=wall_color, stroke_width=wall_stroke_width))
    drawing.add_segment(PathSegment(segment_type=PathSegmentType.LINE, start=Point2D(ox + total_w, oy), end=Point2D(ox + total_w, oy + total_h), points=[Point2D(ox + total_w, oy), Point2D(ox + total_w, oy + total_h)], color=wall_color, stroke_width=wall_stroke_width))

    wall_count = 4
    # Internal horizontal walls
    for r in range(rows - 1):
        for c in range(cols):
            if frozenset({(r, c), (r + 1, c)}) not in passages:
                p1 = Point2D(ox + c * cell_size, oy + (r + 1) * cell_size)
                p2 = Point2D(ox + (c + 1) * cell_size, oy + (r + 1) * cell_size)
                drawing.add_segment(PathSegment(segment_type=PathSegmentType.LINE, start=p1, end=p2, points=[p1, p2], color=wall_color, stroke_width=wall_stroke_width))
                wall_count += 1

    # Internal vertical walls
    for r in range(rows):
        for c in range(cols - 1):
            if frozenset({(r, c), (r, c + 1)}) not in passages:
                p1 = Point2D(ox + (c + 1) * cell_size, oy + r * cell_size)
                p2 = Point2D(ox + (c + 1) * cell_size, oy + (r + 1) * cell_size)
                drawing.add_segment(PathSegment(segment_type=PathSegmentType.LINE, start=p1, end=p2, points=[p1, p2], color=wall_color, stroke_width=wall_stroke_width))
                wall_count += 1

    solution_path: Optional[List[Tuple[int, int]]] = None
    if solve:
        start_cell = (0, 0)
        target_cell = (rows - 1, cols - 1)
        queue: collections.deque[Tuple[Tuple[int, int], List[Tuple[int, int]]]] = collections.deque([(start_cell, [start_cell])])
        visited_solve = {start_cell}

        while queue:
            curr, p_route = queue.popleft()
            if curr == target_cell:
                solution_path = p_route
                break

            for nbr in neighbors(*curr):
                if nbr not in visited_solve and frozenset({curr, nbr}) in passages:
                    visited_solve.add(nbr)
                    queue.append((nbr, p_route + [nbr]))

        if solution_path:
            pts: List[Point2D] = []
            half = cell_size / 2.0
            for r, c in solution_path:
                pts.append(Point2D(ox + c * cell_size + half, oy + r * cell_size + half))

            for i in range(len(pts) - 1):
                drawing.add_segment(
                    PathSegment(
                        segment_type=PathSegmentType.LINE,
                        start=pts[i],
                        end=pts[i + 1],
                        points=[pts[i], pts[i + 1]],
                        color=path_color,
                        stroke_width=path_stroke_width,
                        is_draw=True,
                        metadata={"type": "solution_path"},
                    )
                )

    meta = {
        "algorithm": algo_enum.value,
        "rows": rows,
        "cols": cols,
        "cell_size": cell_size,
        "seed": seed,
        "wall_segments_count": wall_count,
        "solved": bool(solution_path is not None),
        "solution_path": [[r, c] for r, c in (solution_path or [])],
        "solution_length": len(solution_path) if solution_path else 0,
        "passages": [list(p) for p in passages],
    }
    return drawing, meta


def render_ascii_maze(
    meta_or_rows: Any = 8,
    cols: int = 12,
    seed: Optional[int] = 42,
) -> str:
    """Render a compact terminal ASCII representation of a maze."""
    if isinstance(meta_or_rows, dict):
        rows = meta_or_rows.get("rows", 8)
        cols = meta_or_rows.get("cols", 12)
        raw_passages = meta_or_rows.get("passages", [])
        passages: Set[frozenset[Tuple[int, int]]] = set()
        for p in raw_passages:
            if len(p) == 2:
                passages.add(frozenset({tuple(p[0]), tuple(p[1])}))
        sol_set = {tuple(x) for x in meta_or_rows.get("solution_path", [])}
    else:
        rows = int(meta_or_rows)
        rng = random.Random(seed)
        passages = set()

        def nbrs(r: int, c: int) -> List[Tuple[int, int]]:
            res = []
            if r > 0: res.append((r - 1, c))
            if r < rows - 1: res.append((r + 1, c))
            if c > 0: res.append((r, c - 1))
            if c < cols - 1: res.append((r, c + 1))
            return res

        visited = set([(0, 0)])
        stack = [(0, 0)]
        while stack:
            curr = stack[-1]
            unv = [n for n in nbrs(*curr) if n not in visited]
            if unv:
                nxt = rng.choice(unv)
                passages.add(frozenset({curr, nxt}))
                visited.add(nxt)
                stack.append(nxt)
            else:
                stack.pop()
        sol_set = set()

    lines = []
    lines.append("+" + "---+" * cols)
    for r in range(rows):
        row_str = "|"
        for c in range(cols):
            cell = (r, c)
            if cell == (0, 0):
                content = " S "
            elif cell == (rows - 1, cols - 1):
                content = " E "
            elif cell in sol_set:
                content = " * "
            else:
                content = "   "
            row_str += content
            if c < cols - 1:
                row_str += " " if frozenset({(r, c), (r, c + 1)}) in passages else "|"
            else:
                row_str += "|"
        lines.append(row_str)

        bottom_str = "+"
        for c in range(cols):
            bottom_str += "   +" if (r < rows - 1 and frozenset({(r, c), (r + 1, c)}) in passages) else "---+"
        lines.append(bottom_str)

    return "\n".join(lines)
