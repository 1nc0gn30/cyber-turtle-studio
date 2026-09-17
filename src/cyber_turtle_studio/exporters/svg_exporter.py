"""High-fidelity Static and Animated SVG Exporter for cyber-turtle-studio.

Supports cyberpunk/sacred theme palettes, neon glow filters, blueprint grids,
path optimization, and CSS keyframe path stroke-dasharray animations.
"""

from __future__ import annotations

import html
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from cyber_turtle_studio.compat import atomic_write_text, safe_path
from cyber_turtle_studio.models import (
    BoundingBox,
    DrawingAST,
    PathSegment,
    PathSegmentType,
    Point2D,
)


@dataclass(frozen=True)
class ColorTheme:
    """Color and visual styling theme specification."""

    id: str
    name: str
    background: str
    stroke_primary: str
    stroke_secondary: str
    glow_color: str
    accent_color: str
    grid_color: Optional[str] = None
    enable_glow: bool = True
    enable_grid: bool = False


THEMES: Dict[str, ColorTheme] = {
    "cyber_matrix": ColorTheme(
        id="cyber_matrix",
        name="Cyber Matrix",
        background="#05080c",
        stroke_primary="#00ff66",
        stroke_secondary="#39ff14",
        glow_color="#00ff66",
        accent_color="#00ffff",
        grid_color="rgba(0, 255, 102, 0.08)",
        enable_glow=True,
        enable_grid=True,
    ),
    "retro_amber": ColorTheme(
        id="retro_amber",
        name="Retro CRT Amber",
        background="#120900",
        stroke_primary="#ffb000",
        stroke_secondary="#ff8c00",
        glow_color="#ffb000",
        accent_color="#ffd700",
        grid_color="rgba(255, 176, 0, 0.08)",
        enable_glow=True,
        enable_grid=True,
    ),
    "blueprint_cyan": ColorTheme(
        id="blueprint_cyan",
        name="CAD Blueprint Cyan",
        background="#0a192f",
        stroke_primary="#00d2ff",
        stroke_secondary="#64ffda",
        glow_color="#00d2ff",
        accent_color="#ffffff",
        grid_color="rgba(0, 210, 255, 0.12)",
        enable_glow=False,
        enable_grid=True,
    ),
    "sacred_gold": ColorTheme(
        id="sacred_gold",
        name="Sacred Alchemy Gold",
        background="#14101a",
        stroke_primary="#ffd700",
        stroke_secondary="#e6be8a",
        glow_color="#ffd700",
        accent_color="#ffae19",
        grid_color="rgba(255, 215, 0, 0.06)",
        enable_glow=True,
        enable_grid=False,
    ),
    "synthwave_neon": ColorTheme(
        id="synthwave_neon",
        name="Synthwave Neon",
        background="#180b2b",
        stroke_primary="#ff007f",
        stroke_secondary="#00f0ff",
        glow_color="#ff007f",
        accent_color="#ffe600",
        grid_color="rgba(255, 0, 127, 0.09)",
        enable_glow=True,
        enable_grid=True,
    ),
    "light_minimal": ColorTheme(
        id="light_minimal",
        name="Light Minimal",
        background="#ffffff",
        stroke_primary="#0f172a",
        stroke_secondary="#334155",
        glow_color="transparent",
        accent_color="#2563eb",
        grid_color="rgba(15, 23, 42, 0.05)",
        enable_glow=False,
        enable_grid=False,
    ),
    "monochrome": ColorTheme(
        id="monochrome",
        name="Monochrome High Contrast",
        background="#000000",
        stroke_primary="#ffffff",
        stroke_secondary="#cccccc",
        glow_color="transparent",
        accent_color="#888888",
        grid_color="rgba(255, 255, 255, 0.08)",
        enable_glow=False,
        enable_grid=False,
    ),
    "stealth_dark": ColorTheme(
        id="stealth_dark",
        name="Stealth Dark Matte",
        background="#121214",
        stroke_primary="#a1a1aa",
        stroke_secondary="#71717a",
        glow_color="transparent",
        accent_color="#e4e4e7",
        grid_color="rgba(161, 161, 170, 0.05)",
        enable_glow=False,
        enable_grid=False,
    ),
}


class SVGExporter:
    """Renderer converting DrawingAST into static or animated SVG."""

    def __init__(
        self,
        theme: Union[str, ColorTheme] = "cyber_matrix",
        width: int = 1000,
        height: int = 1000,
        padding: float = 40.0,
        stroke_width: Optional[float] = None,
        animated: bool = False,
        animation_duration: float = 4.0,
        loop_animation: bool = True,
        show_grid: Optional[bool] = None,
        show_glow: Optional[bool] = None,
    ) -> None:
        if isinstance(theme, ColorTheme):
            self.theme = theme
        else:
            self.theme = THEMES.get(theme, THEMES["cyber_matrix"])

        self.width = width
        self.height = height
        self.padding = padding
        self.override_stroke_width = stroke_width
        self.animated = animated
        self.animation_duration = animation_duration
        self.loop_animation = loop_animation
        self.show_grid = show_grid if show_grid is not None else self.theme.enable_grid
        self.show_glow = show_glow if show_glow is not None else self.theme.enable_glow

    def _optimize_paths(self, segments: Sequence[PathSegment]) -> List[Dict[str, Any]]:
        """Merge contiguous line segments of the same style into combined path elements."""
        path_groups: List[Dict[str, Any]] = []
        current_pts: List[Point2D] = []
        curr_color: Optional[str] = None
        curr_width: float = 1.0
        curr_opacity: float = 1.0

        def flush_current() -> None:
            nonlocal current_pts, curr_color, curr_width, curr_opacity
            if len(current_pts) >= 2:
                # Calculate approximate length for animation keyframe calculation
                path_len = 0.0
                for idx in range(len(current_pts) - 1):
                    path_len += current_pts[idx].distance_to(current_pts[idx + 1])
                path_groups.append({
                    "type": "path",
                    "points": list(current_pts),
                    "color": curr_color or self.theme.stroke_primary,
                    "stroke_width": self.override_stroke_width or curr_width,
                    "opacity": curr_opacity,
                    "length": path_len,
                })
            current_pts = []

        for seg in segments:
            if seg.segment_type == PathSegmentType.MOVE:
                flush_current()
            elif seg.segment_type == PathSegmentType.LINE:
                # Check if contiguous with current path
                is_same_style = (
                    curr_color == seg.color
                    and abs(curr_width - seg.stroke_width) < 0.01
                    and abs(curr_opacity - seg.opacity) < 0.01
                )
                if current_pts and is_same_style and current_pts[-1].distance_to(seg.start) < 0.001:
                    current_pts.append(seg.end)
                else:
                    flush_current()
                    curr_color = seg.color
                    curr_width = seg.stroke_width
                    curr_opacity = seg.opacity
                    current_pts = [seg.start, seg.end]
            elif seg.segment_type == PathSegmentType.DOT:
                flush_current()
                path_groups.append({
                    "type": "dot",
                    "center": seg.start,
                    "radius": float(seg.metadata.get("radius", 2.0)),
                    "color": seg.fill_color or seg.color or self.theme.accent_color,
                    "opacity": seg.opacity,
                    "length": 0.0,
                })
            elif seg.segment_type == PathSegmentType.FILL_POLYGON:
                flush_current()
                path_groups.append({
                    "type": "polygon",
                    "points": list(seg.points),
                    "fill_color": seg.fill_color or self.theme.stroke_secondary,
                    "stroke_color": seg.color,
                    "stroke_width": self.override_stroke_width or seg.stroke_width,
                    "opacity": seg.opacity,
                    "length": seg.length,
                })

        flush_current()
        return path_groups

    def render(self, drawing: DrawingAST) -> str:
        """Render DrawingAST to SVG markup string."""
        raw_bbox = drawing.bounding_box()
        if not raw_bbox.is_valid or (raw_bbox.width == 0 and raw_bbox.height == 0):
            view_min_x, view_min_y, view_w, view_h = -500, -500, 1000, 1000
        else:
            padded_box = raw_bbox.pad(self.padding)
            # Invert Y axis for SVG (Cartesian math Y is up, SVG Y is down)
            # We preserve standard Cartesian coordinates by translating / flipping viewBox
            view_min_x = padded_box.min_x
            view_min_y = padded_box.min_y
            view_w = max(padded_box.width, 10.0)
            view_h = max(padded_box.height, 10.0)

        optimized_elements = self._optimize_paths(drawing.segments)
        total_drawable_length = sum(el["length"] for el in optimized_elements if el["type"] == "path")

        # SVG Definitions (Glow filters, Grids, Animations)
        defs_list: List[str] = []

        if self.show_glow:
            defs_list.append(f"""
    <filter id="neon-glow" x="-50%" y="-50%" width="200%" height="200%">
      <feGaussianBlur stdDeviation="3.5" result="coloredBlur"/>
      <feMerge>
        <feMergeNode in="coloredBlur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
    <filter id="soft-glow" x="-50%" y="-50%" width="200%" height="200%">
      <feGaussianBlur stdDeviation="1.5" result="blur"/>
      <feMerge>
        <feMergeNode in="blur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>""")

        if self.show_grid and self.theme.grid_color:
            defs_list.append(f"""
    <pattern id="cyber-grid" width="40" height="40" patternUnits="userSpaceOnUse">
      <path d="M 40 0 L 0 0 0 40" fill="none" stroke="{self.theme.grid_color}" stroke-width="1"/>
      <circle cx="0" cy="0" r="1.5" fill="{self.theme.grid_color}"/>
    </pattern>""")

        # CSS Stylesheet
        css_rules: List[str] = [
            f"svg {{ background-color: {self.theme.background}; font-family: 'JetBrains Mono', 'Fira Code', monospace; }}",
            ".turtle-path { stroke-linecap: round; stroke-linejoin: round; }",
        ]

        if self.animated:
            anim_repeat = "infinite" if self.loop_animation else "forwards"
            css_rules.append(f"""
    @keyframes draw-dash {{
      0% {{ stroke-dashoffset: 1; }}
      70% {{ stroke-dashoffset: 0; }}
      90% {{ stroke-dashoffset: 0; }}
      100% {{ stroke-dashoffset: 0; }}
    }}
    .animated-path {{
      stroke-dasharray: 1;
      stroke-dashoffset: 1;
      animation: draw-dash {self.animation_duration:.2f}s cubic-bezier(0.4, 0, 0.2, 1) {anim_repeat};
      pathLength: 1;
    }}
""")

        defs_block = "\n".join(defs_list)
        css_block = "\n".join(css_rules)

        # Build Elements
        body_elements: List[str] = []

        # Background grid overlay
        if self.show_grid and self.theme.grid_color:
            body_elements.append(
                f'  <rect x="{view_min_x}" y="{view_min_y}" width="{view_w}" height="{view_h}" fill="url(#cyber-grid)" />'
            )

        # SVG Groups with Flip transform so +Y is up (standard math/turtle)
        # We transform around (0, 0) or flip Y
        glow_filter_attr = ' filter="url(#neon-glow)"' if self.show_glow else ""
        anim_class = " animated-path" if self.animated else ""

        for el in optimized_elements:
            el_type = el["type"]
            if el_type == "path":
                pts = el["points"]
                d_cmds = [f"M {pts[0].x:.3f} {-pts[0].y:.3f}"]
                for p in pts[1:]:
                    d_cmds.append(f"L {p.x:.3f} {-p.y:.3f}")
                d_str = " ".join(d_cmds)
                stroke_col = el["color"]
                sw = el["stroke_width"]
                op = el["opacity"]
                body_elements.append(
                    f'  <path d="{d_str}" fill="none" stroke="{stroke_col}" stroke-width="{sw:.2f}" '
                    f'stroke-opacity="{op:.2f}" class="turtle-path{anim_class}"{glow_filter_attr} />'
                )
            elif el_type == "dot":
                c = el["center"]
                rad = el["radius"]
                col = el["color"]
                op = el["opacity"]
                body_elements.append(
                    f'  <circle cx="{c.x:.3f}" cy="{-c.y:.3f}" r="{rad:.2f}" fill="{col}" '
                    f'fill-opacity="{op:.2f}"{glow_filter_attr} />'
                )
            elif el_type == "polygon":
                pts = el["points"]
                pts_str = " ".join(f"{p.x:.3f},{-p.y:.3f}" for p in pts)
                fill_c = el["fill_color"]
                strk_c = el["stroke_color"]
                sw = el["stroke_width"]
                body_elements.append(
                    f'  <polygon points="{pts_str}" fill="{fill_c}" stroke="{strk_c}" '
                    f'stroke-width="{sw:.2f}" class="turtle-path" />'
                )

        # Title & Metadata in XML Comments and desc
        title_escaped = html.escape(drawing.title or "Cyber Turtle Drawing")
        stats = drawing.stats()

        svg_out = f"""<?xml version="1.0" encoding="UTF-8"?>
<!-- Generated by cyber-turtle-studio -->
<!-- Stats: {stats['line_count']} lines, {stats['total_drawing_length']}mm total length -->
<svg xmlns="http://www.w3.org/2000/svg"
     viewBox="{view_min_x:.2f} {-padded_box.max_y:.2f} {view_w:.2f} {view_h:.2f}"
     width="100%" height="100%"
     shape-rendering="geometricPrecision"
     text-rendering="geometricPrecision">
  <title>{title_escaped}</title>
  <desc>Synthesized with cyber-turtle-studio | Theme: {self.theme.name}</desc>
  <defs>
    <style type="text/css">
{css_block}
    </style>{defs_block}
  </defs>
  <rect x="{view_min_x:.2f}" y="{-padded_box.max_y:.2f}" width="{view_w:.2f}" height="{view_h:.2f}" fill="{self.theme.background}" />
  <g id="turtle-artwork">
{chr(10).join(body_elements)}
  </g>
</svg>"""
        return svg_out

    def export(self, drawing: DrawingAST) -> str:
        """Alias for render method."""
        return self.render(drawing)

    def export_file(self, drawing: DrawingAST, file_path: Union[str, Path]) -> str:
        """Render and atomically write SVG to disk."""
        content = self.render(drawing)
        atomic_write_text(file_path, content, encoding="utf-8")
        return content



def export_svg(
    drawing: DrawingAST,
    file_path: Optional[Union[str, Path]] = None,
    theme: Union[str, ColorTheme] = "cyber_matrix",
    animated: Optional[bool] = None,
    animate: Optional[bool] = None,
    animation_duration: Optional[float] = None,
    duration: Optional[float] = None,
    duration_sec: Optional[float] = None,
    width: int = 1000,
    height: int = 1000,
    padding: float = 40.0,
    stroke_width: Optional[float] = None,
    show_grid: Optional[bool] = None,
    show_glow: Optional[bool] = None,
    **kwargs: Any,
) -> str:
    """Export DrawingAST to SVG markup, optionally writing atomically to disk."""
    is_anim = animated if animated is not None else (animate if animate is not None else False)
    dur = animation_duration if animation_duration is not None else (duration if duration is not None else (duration_sec if duration_sec is not None else 4.0))
    exporter = SVGExporter(
        theme=theme,
        width=width,
        height=height,
        padding=padding,
        stroke_width=stroke_width,
        animated=is_anim,
        animation_duration=dur,
        show_grid=show_grid,
        show_glow=show_glow,
    )
    svg_content = exporter.render(drawing)
    if file_path is not None:
        atomic_write_text(file_path, svg_content, encoding="utf-8")
    return svg_content


def export_animated_svg(
    drawing: DrawingAST,
    file_path: Optional[Union[str, Path]] = None,
    duration: float = 4.0,
    theme: Union[str, ColorTheme] = "cyber_matrix",
    **kwargs: Any,
) -> str:
    """Convenience function to export animated drawing with path reveal effects."""
    return export_svg(
        drawing,
        file_path=file_path,
        theme=theme,
        animated=True,
        animation_duration=duration,
        **kwargs,
    )

