"""G-Code generator for CNC Pen Plotters and Laser Cutters.

Translates DrawingAST vector paths into highly optimized G-Code toolpaths
with pen lift controls (Z-axis / servo), laser power modulation (M3/M5),
feedrate management, and bed layout scaling.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
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


class GCodeToolMode(str, Enum):
    """Tool actuation mode for G-Code generation."""

    PEN_PLOTTER_Z = "pen_z"          # Standard Z-axis pen lift (e.g. Z5.0 / Z0.0)
    PEN_PLOTTER_SERVO = "pen_servo"  # RC Servo pen lift (e.g. M3 S30 / M3 S90 or M280 P0)
    LASER_CUTTER = "laser"           # Laser power on/off (e.g. M3 S255 / M5)


class BedOrigin(str, Enum):
    """Origin reference coordinate alignment."""

    BOTTOM_LEFT = "bottom_left"  # Standard Cartesian CNC bed origin (0,0) at bottom-left
    CENTER = "center"            # (0,0) at center of working envelope
    TOP_LEFT = "top_left"        # (0,0) at top-left
    RAW = "raw"                  # Unmodified raw coordinates


@dataclass
class GCodeConfig:
    """Configuration options for G-Code export."""

    tool_mode: GCodeToolMode = GCodeToolMode.PEN_PLOTTER_Z
    draw_feedrate: float = 1200.0     # mm/min during drawing moves (G1)
    travel_feedrate: float = 3000.0   # mm/min during travel moves (G0)
    pen_up_z: float = 5.0             # Z height in mm when pen is lifted
    pen_down_z: float = 0.0           # Z height in mm when pen touches surface
    servo_up_cmd: str = "M3 S30"      # Servo command for pen up
    servo_down_cmd: str = "M3 S90"    # Servo command for pen down
    laser_power: int = 255            # Laser S-value (0-255 or 0-1000)
    laser_on_cmd: str = "M3 S{power}" # Laser on command template
    laser_off_cmd: str = "M5"         # Laser off command
    pause_after_pen_move_ms: int = 150 # Delay after pen up/down in milliseconds (G4 P...)
    bed_width: float = 210.0          # Bed width in mm (default A4 width)
    bed_height: float = 297.0         # Bed height in mm (default A4 height)
    bed_margin: float = 15.0          # Safety margin from bed boundaries in mm
    auto_fit_bed: bool = True         # Automatically scale and center drawing onto bed
    bed_origin: BedOrigin = BedOrigin.BOTTOM_LEFT
    precision_decimals: int = 3       # Floating point coordinate decimal precision
    home_on_start: bool = True        # Emit G28 homing command in preamble
    disable_motors_on_end: bool = True # Emit M84 in postamble
    optimize_paths: bool = False       # Run 2-Opt TSP rapid travel minimizer on drawing
    custom_preamble: Optional[List[str]] = None
    custom_postamble: Optional[List[str]] = None
    feed_draw: Optional[float] = None
    feed_travel: Optional[float] = None

    def __post_init__(self) -> None:
        if self.feed_draw is not None:
            self.draw_feedrate = self.feed_draw
        if self.feed_travel is not None:
            self.travel_feedrate = self.feed_travel



class GCodeExporter:
    """Converts DrawingAST into optimized CNC G-Code instructions."""

    def __init__(self, config: Optional[GCodeConfig] = None) -> None:
        self.config = config or GCodeConfig()

    def _prepare_drawing(self, drawing: DrawingAST) -> Tuple[DrawingAST, float]:
        """Optionally fit, scale, and center the drawing on the CNC bed."""
        cfg = self.config
        if not cfg.auto_fit_bed:
            return drawing, 1.0

        raw_bbox = drawing.bounding_box()
        if not raw_bbox.is_valid or (raw_bbox.width == 0 and raw_bbox.height == 0):
            return drawing, 1.0

        avail_w = max(10.0, cfg.bed_width - 2 * cfg.bed_margin)
        avail_h = max(10.0, cfg.bed_height - 2 * cfg.bed_margin)

        orig_w = max(0.001, raw_bbox.width)
        orig_h = max(0.001, raw_bbox.height)

        scale = min(avail_w / orig_w, avail_h / orig_h)
        scaled_w = orig_w * scale
        scaled_h = orig_h * scale

        # Calculate target position based on origin alignment
        if cfg.bed_origin == BedOrigin.BOTTOM_LEFT:
            # Center on bed: center is (bed_width/2, bed_height/2)
            c = raw_bbox.center
            tx = (cfg.bed_width / 2.0) - (c.x * scale)
            ty = (cfg.bed_height / 2.0) - (c.y * scale)
        elif cfg.bed_origin == BedOrigin.CENTER:
            c = raw_bbox.center
            tx = -(c.x * scale)
            ty = -(c.y * scale)
        elif cfg.bed_origin == BedOrigin.TOP_LEFT:
            c = raw_bbox.center
            tx = (cfg.bed_width / 2.0) - (c.x * scale)
            ty = -(cfg.bed_height / 2.0) - (c.y * scale)
        else:
            tx = 0.0
            ty = 0.0

        return drawing.transform(scale, scale, tx, ty), scale

    def generate(self, drawing: DrawingAST) -> Tuple[str, Dict[str, Any]]:
        """Generate G-Code text and execution telemetry stats."""
        cfg = self.config
        dec = cfg.precision_decimals
        fmt = f"{{:.{dec}f}}"

        target_drawing = drawing
        if cfg.optimize_paths:
            from cyber_turtle_studio.toolpath_optimizer import ToolpathOptimizer
            opt = ToolpathOptimizer(
                draw_feedrate_mm_min=cfg.draw_feedrate,
                travel_feedrate_mm_min=cfg.travel_feedrate,
            )
            target_drawing, _ = opt.optimize_toolpath(drawing)

        processed_drawing, applied_scale = self._prepare_drawing(target_drawing)
        lines: List[str] = []

        # Preamble / Header
        lines.append("; ==========================================================================")
        lines.append(f"; G-Code generated by cyber-turtle-studio")
        lines.append(f"; Title: {drawing.title or 'Cyber Turtle Design'}")
        lines.append(f"; Tool Mode: {cfg.tool_mode.value}")
        lines.append(f"; Bed: {cfg.bed_width}x{cfg.bed_height}mm (Margin: {cfg.bed_margin}mm)")
        lines.append("; ==========================================================================")
        lines.append("G21 ; Set units to millimeters")
        lines.append("G90 ; Absolute positioning")

        if cfg.home_on_start:
            lines.append("G28 ; Home all axes")
        else:
            lines.append("G92 X0 Y0 Z0 ; Set current position as origin")

        if cfg.custom_preamble:
            lines.extend(cfg.custom_preamble)

        # Pen up / Laser off helper commands
        def cmd_tool_up() -> List[str]:
            out = []
            if cfg.tool_mode == GCodeToolMode.PEN_PLOTTER_Z:
                out.append(f"G0 Z{fmt.format(cfg.pen_up_z)} F{cfg.travel_feedrate:.0f}")
            elif cfg.tool_mode == GCodeToolMode.PEN_PLOTTER_SERVO:
                out.append(cfg.servo_up_cmd)
            elif cfg.tool_mode == GCodeToolMode.LASER_CUTTER:
                out.append(cfg.laser_off_cmd)
            if cfg.pause_after_pen_move_ms > 0:
                out.append(f"G4 P{cfg.pause_after_pen_move_ms}")
            return out

        def cmd_tool_down() -> List[str]:
            out = []
            if cfg.tool_mode == GCodeToolMode.PEN_PLOTTER_Z:
                out.append(f"G1 Z{fmt.format(cfg.pen_down_z)} F{cfg.draw_feedrate:.0f}")
            elif cfg.tool_mode == GCodeToolMode.PEN_PLOTTER_SERVO:
                out.append(cfg.servo_down_cmd)
            elif cfg.tool_mode == GCodeToolMode.LASER_CUTTER:
                laser_cmd = cfg.laser_on_cmd.replace("{power}", str(cfg.laser_power))
                out.append(laser_cmd)
            if cfg.pause_after_pen_move_ms > 0:
                out.append(f"G4 P{cfg.pause_after_pen_move_ms}")
            return out

        # Initialize to tool up
        lines.extend(cmd_tool_up())

        # Telemetry tracking
        total_draw_mm = 0.0
        total_travel_mm = 0.0
        pen_lift_count = 0
        current_pos = Point2D(0.0, 0.0)
        is_tool_down = False

        for seg in processed_drawing.segments:
            if seg.segment_type == PathSegmentType.MOVE:
                if is_tool_down:
                    lines.extend(cmd_tool_up())
                    is_tool_down = False
                    pen_lift_count += 1
                dist = current_pos.distance_to(seg.end)
                total_travel_mm += dist
                lines.append(f"G0 X{fmt.format(seg.end.x)} Y{fmt.format(seg.end.y)} F{cfg.travel_feedrate:.0f}")
                current_pos = seg.end

            elif seg.segment_type == PathSegmentType.LINE:
                # If tool was up or current position differs from start, travel to start
                if current_pos.distance_to(seg.start) > 0.001:
                    if is_tool_down:
                        lines.extend(cmd_tool_up())
                        is_tool_down = False
                        pen_lift_count += 1
                    dist = current_pos.distance_to(seg.start)
                    total_travel_mm += dist
                    lines.append(f"G0 X{fmt.format(seg.start.x)} Y{fmt.format(seg.start.y)} F{cfg.travel_feedrate:.0f}")
                    current_pos = seg.start

                # Lower tool if not down
                if not is_tool_down:
                    lines.extend(cmd_tool_down())
                    is_tool_down = True

                # Draw to end
                dist = current_pos.distance_to(seg.end)
                total_draw_mm += dist
                lines.append(f"G1 X{fmt.format(seg.end.x)} Y{fmt.format(seg.end.y)} F{cfg.draw_feedrate:.0f}")
                current_pos = seg.end

            elif seg.segment_type == PathSegmentType.DOT:
                if current_pos.distance_to(seg.start) > 0.001:
                    if is_tool_down:
                        lines.extend(cmd_tool_up())
                        is_tool_down = False
                        pen_lift_count += 1
                    lines.append(f"G0 X{fmt.format(seg.start.x)} Y{fmt.format(seg.start.y)} F{cfg.travel_feedrate:.0f}")
                    current_pos = seg.start
                # Dip tool down and up
                lines.extend(cmd_tool_down())
                lines.extend(cmd_tool_up())
                pen_lift_count += 1
                is_tool_down = False

            elif seg.segment_type == PathSegmentType.FILL_POLYGON and seg.points:
                pts = seg.points
                if current_pos.distance_to(pts[0]) > 0.001:
                    if is_tool_down:
                        lines.extend(cmd_tool_up())
                        is_tool_down = False
                        pen_lift_count += 1
                    lines.append(f"G0 X{fmt.format(pts[0].x)} Y{fmt.format(pts[0].y)} F{cfg.travel_feedrate:.0f}")
                    current_pos = pts[0]
                if not is_tool_down:
                    lines.extend(cmd_tool_down())
                    is_tool_down = True
                for p in pts[1:]:
                    total_draw_mm += current_pos.distance_to(p)
                    lines.append(f"G1 X{fmt.format(p.x)} Y{fmt.format(p.y)} F{cfg.draw_feedrate:.0f}")
                    current_pos = p
                # Close polygon
                total_draw_mm += current_pos.distance_to(pts[0])
                lines.append(f"G1 X{fmt.format(pts[0].x)} Y{fmt.format(pts[0].y)} F{cfg.draw_feedrate:.0f}")
                current_pos = pts[0]

        # Ensure tool is lifted at end
        if is_tool_down:
            lines.extend(cmd_tool_up())
            pen_lift_count += 1

        # Postamble / Footer
        lines.append("; ==========================================================================")
        lines.append("; Job Completion & Park")
        lines.append("; ==========================================================================")
        lines.append(f"G0 X0 Y0 F{cfg.travel_feedrate:.0f} ; Return home")

        if cfg.custom_postamble:
            lines.extend(cfg.custom_postamble)

        if cfg.disable_motors_on_end:
            lines.append("M84 ; Disable steppers")
        lines.append("M30 ; Program End")

        # Compute estimated execution time
        draw_time_min = total_draw_mm / cfg.draw_feedrate if cfg.draw_feedrate > 0 else 0.0
        travel_time_min = total_travel_mm / cfg.travel_feedrate if cfg.travel_feedrate > 0 else 0.0
        pen_lift_time_min = (pen_lift_count * cfg.pause_after_pen_move_ms) / 60000.0
        total_est_seconds = (draw_time_min + travel_time_min + pen_lift_time_min) * 60.0

        telemetry: Dict[str, Any] = {
            "total_lines": len(lines),
            "drawing_distance_mm": round(total_draw_mm, 2),
            "travel_distance_mm": round(total_travel_mm, 2),
            "total_distance_mm": round(total_draw_mm + total_travel_mm, 2),
            "pen_lifts": pen_lift_count,
            "estimated_duration_seconds": round(total_est_seconds, 1),
            "applied_scale": round(applied_scale, 4),
            "bounding_box": processed_drawing.bounding_box().to_dict(),
        }

        return "\n".join(lines), telemetry


    def export(self, drawing: DrawingAST) -> str:
        """Alias for generate returning G-Code text."""
        gcode_str, _ = self.generate(drawing)
        return gcode_str

    def export_file(self, drawing: DrawingAST, file_path: Union[str, Path]) -> str:
        """Generate and atomically write G-Code program to disk."""
        gcode_str, _ = self.generate(drawing)
        atomic_write_text(file_path, gcode_str, encoding="utf-8")
        return gcode_str


class GCodeString(str):
    """String subclass containing telemetry stats and supporting 2-tuple unpacking."""

    stats: Dict[str, Any]

    def __new__(cls, content: str, stats: Optional[Dict[str, Any]] = None) -> GCodeString:
        instance = super().__new__(cls, content)
        instance.stats = stats or {}
        return instance

    def __iter__(self):
        yield str(self)
        yield self.stats


def export_gcode(
    drawing: DrawingAST,
    file_path: Optional[Union[str, Path]] = None,
    config: Optional[GCodeConfig] = None,
    tool_mode: Optional[Union[str, GCodeToolMode]] = None,
    draw_feedrate: Optional[float] = None,
    travel_feedrate: Optional[float] = None,
    feed_draw: Optional[float] = None,
    feed_travel: Optional[float] = None,
    feed: Optional[float] = None,
    pen_up_z: Optional[float] = None,
    pen_down_z: Optional[float] = None,
    z_up: Optional[float] = None,
    z_down: Optional[float] = None,
    laser_mode: Optional[bool] = None,
    laser: Optional[bool] = None,
    bed_width: float = 210.0,
    bed_height: float = 297.0,
    **kwargs: Any,
) -> GCodeString:
    """Export DrawingAST to CNC G-Code, optionally writing atomically to disk."""
    if config is not None:
        cfg = config
    else:
        d_feed = draw_feedrate if draw_feedrate is not None else (feed_draw if feed_draw is not None else (feed if feed is not None else 1200.0))
        t_feed = travel_feedrate if travel_feedrate is not None else (feed_travel if feed_travel is not None else 3000.0)
        p_up = pen_up_z if pen_up_z is not None else (z_up if z_up is not None else 5.0)
        p_down = pen_down_z if pen_down_z is not None else (z_down if z_down is not None else 0.0)
        is_laser = laser_mode if laser_mode is not None else (laser if laser is not None else False)
        mode = GCodeToolMode.LASER_CUTTER if is_laser else (GCodeToolMode(tool_mode) if tool_mode is not None else GCodeToolMode.PEN_PLOTTER_Z)

        cfg = GCodeConfig(
            tool_mode=mode,
            draw_feedrate=d_feed,
            travel_feedrate=t_feed,
            pen_up_z=p_up,
            pen_down_z=p_down,
            bed_width=bed_width,
            bed_height=bed_height,
            **kwargs,
        )

    exporter = GCodeExporter(cfg)
    gcode_str, stats = exporter.generate(drawing)

    if file_path is not None:
        atomic_write_text(file_path, gcode_str, encoding="utf-8")

    return GCodeString(gcode_str, stats)

