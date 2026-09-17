"""High-resolution Terminal Braille and ASCII Text Grid Canvas Renderer.

Renders vector drawings directly in terminal interfaces using 2x4 subpixel
Unicode Braille patterns (U+2800..U+28FF), ASCII fallback glyphs, Bresenham
line rasterization, and 24-bit TrueColor ANSI styling.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from cyber_turtle_studio.compat import atomic_write_text, get_platform_info, safe_path
from cyber_turtle_studio.models import (
    BoundingBox,
    DrawingAST,
    PathSegment,
    PathSegmentType,
    Point2D,
)


class ASCIIRenderMode(str, Enum):
    """Rendering mode for ASCII/Terminal canvas."""

    BRAILLE = "braille"  # High-res 2x4 subpixel Unicode Braille (U+2800..U+28FF)
    ASCII = "ascii"      # Classic ASCII blocks (#, *, +, .)
    DENSE = "dense"      # Solid block density shading (█, ▓, ▒, ░)


def hex_to_rgb(hex_str: str) -> Tuple[int, int, int]:
    """Parse hex color string (#rgb, #rrggbb, #rrggbbaa) to (r, g, b) integers."""
    clean = hex_str.strip().lstrip("#")
    if len(clean) == 3:
        clean = "".join(c * 2 for c in clean)
    elif len(clean) >= 6:
        clean = clean[:6]
    else:
        return (0, 255, 204)  # Default fallback cyan
    try:
        r = int(clean[0:2], 16)
        g = int(clean[2:4], 16)
        b = int(clean[4:6], 16)
        return (r, g, b)
    except ValueError:
        return (0, 255, 204)


class ASCIIExporter:
    """Renders DrawingAST vector graphics onto character grid canvases."""

    # Unicode Braille bitmask offsets for (col, row) in 2x4 grid:
    # col: 0..1, row: 0..3
    BRAILLE_MAP = [
        [0x01, 0x08],  # Row 0: Dot 1 (L), Dot 4 (R)
        [0x02, 0x10],  # Row 1: Dot 2 (L), Dot 5 (R)
        [0x04, 0x20],  # Row 2: Dot 3 (L), Dot 6 (R)
        [0x40, 0x80],  # Row 3: Dot 7 (L), Dot 8 (R)
    ]

    def __init__(
        self,
        width: int = 80,
        height: int = 40,
        mode: ASCIIRenderMode = ASCIIRenderMode.BRAILLE,
        use_color: Optional[bool] = None,
        show_border: bool = True,
        show_header: bool = True,
        ascii_char: str = "#",
    ) -> None:
        self.char_width = max(10, width)
        self.char_height = max(5, height)
        self.mode = mode
        self.show_border = show_border
        self.show_header = show_header
        self.ascii_char = ascii_char

        # Auto-detect ANSI color capability if not explicitly specified
        if use_color is None:
            self.use_color = get_platform_info().supports_ansi_color
        else:
            self.use_color = use_color

    def _bresenham_line(
        self,
        x0: int,
        y0: int,
        x1: int,
        y1: int,
        plot_fn: Any,
    ) -> None:
        """Standard Bresenham integer line algorithm."""
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy

        while True:
            plot_fn(x0, y0)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy

    def render(self, drawing: DrawingAST) -> str:
        """Render vector drawing to text/terminal canvas string."""
        raw_bbox = drawing.bounding_box()
        if not raw_bbox.is_valid or (raw_bbox.width == 0 and raw_bbox.height == 0):
            return "[Empty Cyber Turtle Drawing]"

        # Coordinate domain calculations
        if self.mode == ASCIIRenderMode.BRAILLE:
            # 2x horizontal, 4x vertical subpixel resolution
            pixel_w = self.char_width * 2
            pixel_h = self.char_height * 4
        else:
            pixel_w = self.char_width
            pixel_h = self.char_height

        # Fit with margin into pixel grid
        # Add slight margin
        box_w = max(0.001, raw_bbox.width)
        box_h = max(0.001, raw_bbox.height)
        scale_x = (pixel_w - 4) / box_w
        scale_y = (pixel_h - 4) / box_h
        scale = min(scale_x, scale_y)

        c = raw_bbox.center
        offset_x = (pixel_w / 2.0) - (c.x * scale)
        offset_y = (pixel_h / 2.0) - (c.y * scale)

        def to_grid(p: Point2D) -> Tuple[int, int]:
            gx = int(round(p.x * scale + offset_x))
            # Flip Y coordinate for terminal (top line is 0)
            gy = int(round(pixel_h - 1 - (p.y * scale + offset_y)))
            return max(0, min(pixel_w - 1, gx)), max(0, min(pixel_h - 1, gy))

        # Render Braille Mode
        if self.mode == ASCIIRenderMode.BRAILLE:
            # Grid of char cells: char_height x char_width storing bitmask and color
            grid_bits = [[0 for _ in range(self.char_width)] for _ in range(self.char_height)]
            grid_color = [[(0, 255, 204) for _ in range(self.char_width)] for _ in range(self.char_height)]

            def plot_braille_dot(px: int, py: int, rgb: Tuple[int, int, int]) -> None:
                char_x = px // 2
                char_y = py // 4
                if 0 <= char_x < self.char_width and 0 <= char_y < self.char_height:
                    sub_x = px % 2
                    sub_y = py % 4
                    grid_bits[char_y][char_x] |= self.BRAILLE_MAP[sub_y][sub_x]
                    grid_color[char_y][char_x] = rgb

            for seg in drawing.segments:
                if seg.segment_type in (PathSegmentType.LINE, PathSegmentType.MOVE, PathSegmentType.FILL_POLYGON):
                    if seg.segment_type == PathSegmentType.MOVE:
                        continue
                    rgb = hex_to_rgb(seg.color)
                    p0 = to_grid(seg.start)
                    p1 = to_grid(seg.end)
                    self._bresenham_line(p0[0], p0[1], p1[0], p1[1], lambda x, y: plot_braille_dot(x, y, rgb))
                elif seg.segment_type == PathSegmentType.DOT:
                    rgb = hex_to_rgb(seg.fill_color or seg.color)
                    p0 = to_grid(seg.start)
                    plot_braille_dot(p0[0], p0[1], rgb)

            # Build lines
            canvas_lines: List[str] = []
            for r in range(self.char_height):
                line_chars: List[str] = []
                for c in range(self.char_width):
                    bits = grid_bits[r][c]
                    ch = chr(0x2800 + bits) if bits > 0 else " "
                    if self.use_color and bits > 0:
                        cr, cg, cb = grid_color[r][c]
                        line_chars.append(f"\033[38;2;{cr};{cg};{cb}m{ch}\033[0m")
                    else:
                        line_chars.append(ch)
                canvas_lines.append("".join(line_chars))

        # Render ASCII / Dense Mode
        else:
            glyph = self.ascii_char if self.mode == ASCIIRenderMode.ASCII else "█"
            grid_char = [[" " for _ in range(self.char_width)] for _ in range(self.char_height)]
            grid_color = [[(0, 255, 204) for _ in range(self.char_width)] for _ in range(self.char_height)]

            def plot_ascii_pt(px: int, py: int, rgb: Tuple[int, int, int]) -> None:
                if 0 <= px < self.char_width and 0 <= py < self.char_height:
                    grid_char[py][px] = glyph
                    grid_color[py][px] = rgb

            for seg in drawing.segments:
                if seg.segment_type in (PathSegmentType.LINE, PathSegmentType.MOVE, PathSegmentType.FILL_POLYGON):
                    if seg.segment_type == PathSegmentType.MOVE:
                        continue
                    rgb = hex_to_rgb(seg.color)
                    p0 = to_grid(seg.start)
                    p1 = to_grid(seg.end)
                    self._bresenham_line(p0[0], p0[1], p1[0], p1[1], lambda x, y: plot_ascii_pt(x, y, rgb))
                elif seg.segment_type == PathSegmentType.DOT:
                    rgb = hex_to_rgb(seg.fill_color or seg.color)
                    p0 = to_grid(seg.start)
                    plot_ascii_pt(p0[0], p0[1], rgb)

            canvas_lines = []
            for r in range(self.char_height):
                line_chars = []
                for c in range(self.char_width):
                    ch = grid_char[r][c]
                    if self.use_color and ch != " ":
                        cr, cg, cb = grid_color[r][c]
                        line_chars.append(f"\033[38;2;{cr};{cg};{cb}m{ch}\033[0m")
                    else:
                        line_chars.append(ch)
                canvas_lines.append("".join(line_chars))

        # Format with Optional Header and Frame Borders
        output_rows: List[str] = []
        inner_w = self.char_width

        if self.show_header:
            title_text = f" CYBER TURTLE STUDIO // {drawing.title or 'FRACTAL SYNTHESIS'} "
            if len(title_text) > inner_w:
                title_text = title_text[:inner_w]
            output_rows.append("┌" + title_text.center(inner_w, "─") + "┐")
        elif self.show_border:
            output_rows.append("┌" + "─" * inner_w + "┐")

        for row in canvas_lines:
            if self.show_border:
                output_rows.append(f"│{row}│")
            else:
                output_rows.append(row)

        if self.show_border:
            stats = drawing.stats()
            footer_text = f" lines: {stats['line_count']} | len: {stats['total_drawing_length']}mm "
            if len(footer_text) > inner_w:
                footer_text = footer_text[:inner_w]
            output_rows.append("└" + footer_text.center(inner_w, "─") + "┘")

        return "\n".join(output_rows)

    def export(self, drawing: DrawingAST) -> str:
        """Alias for render returning ASCII art string."""
        return self.render(drawing)

    def export_file(self, drawing: DrawingAST, file_path: Union[str, Path]) -> str:
        """Render and atomically write ASCII art to file."""
        rendered = self.render(drawing)
        atomic_write_text(file_path, rendered, encoding="utf-8")
        return rendered



def export_ascii(
    drawing: DrawingAST,
    file_path: Optional[Union[str, Path]] = None,
    width: int = 80,
    height: int = 40,
    mode: str = "braille",
    use_color: Optional[bool] = None,
    show_border: bool = True,
    show_header: bool = True,
) -> str:
    """Export DrawingAST to ASCII or Unicode Braille terminal art."""
    renderer = ASCIIExporter(
        width=width,
        height=height,
        mode=ASCIIRenderMode(mode),
        use_color=use_color,
        show_border=show_border,
        show_header=show_header,
    )
    rendered = renderer.render(drawing)

    if file_path is not None:
        atomic_write_text(file_path, rendered, encoding="utf-8")

    return rendered
