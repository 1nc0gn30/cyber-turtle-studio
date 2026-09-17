"""Core domain models and AST structures for cyber-turtle-studio.

Defines point geometry, bounding boxes, turtle state, path segments,
drawing ASTs, L-System rules, and preset configurations.
"""

from __future__ import annotations

import copy
import json
import math
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union


@dataclass
class Point2D:
    """2D Cartesian Coordinate Point with vector arithmetic."""

    x: float
    y: float

    def __add__(self, other: Union[Point2D, Tuple[float, float]]) -> Point2D:
        if isinstance(other, Point2D):
            return Point2D(self.x + other.x, self.y + other.y)
        return Point2D(self.x + other[0], self.y + other[1])

    def __sub__(self, other: Union[Point2D, Tuple[float, float]]) -> Point2D:
        if isinstance(other, Point2D):
            return Point2D(self.x - other.x, self.y - other.y)
        return Point2D(self.x - other[0], self.y - other[1])

    def __mul__(self, scalar: float) -> Point2D:
        return Point2D(self.x * scalar, self.y * scalar)

    def __rmul__(self, scalar: float) -> Point2D:
        return Point2D(self.x * scalar, self.y * scalar)

    def __truediv__(self, scalar: float) -> Point2D:
        if scalar == 0:
            raise ZeroDivisionError("Division by zero in Point2D scaling")
        return Point2D(self.x / scalar, self.y / scalar)

    def distance_to(self, other: Point2D) -> float:
        """Euclidean distance to another point."""
        return math.hypot(self.x - other.x, self.y - other.y)

    def manhattan_distance(self, other: Point2D) -> float:
        """Manhattan (L1) distance to another point."""
        return abs(self.x - other.x) + abs(self.y - other.y)

    def angle_to(self, other: Point2D) -> float:
        """Heading angle in degrees from self towards other (0 deg = East, 90 deg = North)."""
        rad = math.atan2(other.y - self.y, other.x - self.x)
        deg = math.degrees(rad)
        return deg % 360.0

    def translate(self, dx: float, dy: float) -> Point2D:
        """Translate point by (dx, dy)."""
        return Point2D(self.x + dx, self.y + dy)

    def rotate(self, angle: float, origin: Optional[Point2D] = None) -> Point2D:
        """Rotate point around an origin by angle in degrees or radians."""
        ox = origin.x if origin else 0.0
        oy = origin.y if origin else 0.0
        if abs(angle) > (2 * math.pi + 0.001):
            rad = math.radians(angle)
        else:
            rad = angle
        cos_a = math.cos(rad)
        sin_a = math.sin(rad)
        dx = self.x - ox
        dy = self.y - oy
        rx = cos_a * dx - sin_a * dy + ox
        ry = sin_a * dx + cos_a * dy + oy
        return Point2D(rx, ry)

    @classmethod
    def from_polar(cls, r: float, theta: float) -> Point2D:
        """Create Point2D from polar coordinates (r, theta)."""
        if abs(theta) > (2 * math.pi + 0.001):
            rad = math.radians(theta)
        else:
            rad = theta
        return cls(x=r * math.cos(rad), y=r * math.sin(rad))

    def scale(self, factor: float, origin: Optional[Point2D] = None) -> Point2D:
        """Scale point relative to origin."""
        ox = origin.x if origin else 0.0
        oy = origin.y if origin else 0.0
        return Point2D(ox + (self.x - ox) * factor, oy + (self.y - oy) * factor)

    def to_tuple(self) -> Tuple[float, float]:
        return (self.x, self.y)

    def to_dict(self) -> Dict[str, float]:
        return {"x": round(self.x, 4), "y": round(self.y, 4)}

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> Point2D:
        return cls(x=float(d["x"]), y=float(d["y"]))

    @classmethod
    def from_tuple(cls, t: Sequence[float]) -> Point2D:
        return cls(x=float(t[0]), y=float(t[1]))



@dataclass
class BoundingBox:
    """Axis-aligned 2D bounding box."""

    min_x: float = float("inf")
    min_y: float = float("inf")
    max_x: float = float("-inf")
    max_y: float = float("-inf")

    @property
    def is_valid(self) -> bool:
        return self.min_x <= self.max_x and self.min_y <= self.max_y

    @property
    def width(self) -> float:
        return max(0.0, self.max_x - self.min_x) if self.is_valid else 0.0

    @property
    def height(self) -> float:
        return max(0.0, self.max_y - self.min_y) if self.is_valid else 0.0

    @property
    def center(self) -> Point2D:
        if not self.is_valid:
            return Point2D(0.0, 0.0)
        return Point2D((self.min_x + self.max_x) / 2.0, (self.min_y + self.max_y) / 2.0)

    @property
    def aspect_ratio(self) -> float:
        h = self.height
        return (self.width / h) if h > 0 else 1.0

    @property
    def area(self) -> float:
        return self.width * self.height

    @property
    def diagonal(self) -> float:
        return math.hypot(self.width, self.height)

    def expand_point(self, p: Point2D) -> None:
        """Expand bounding box to include point `p`."""
        if p.x < self.min_x:
            self.min_x = p.x
        if p.x > self.max_x:
            self.max_x = p.x
        if p.y < self.min_y:
            self.min_y = p.y
        if p.y > self.max_y:
            self.max_y = p.y

    def expand_box(self, other: BoundingBox) -> None:
        """Expand bounding box to include another box."""
        if not other.is_valid:
            return
        if other.min_x < self.min_x:
            self.min_x = other.min_x
        if other.max_x > self.max_x:
            self.max_x = other.max_x
        if other.min_y < self.min_y:
            self.min_y = other.min_y
        if other.max_y > self.max_y:
            self.max_y = other.max_y

    def pad(self, padding: float) -> BoundingBox:
        """Return a new bounding box expanded by a uniform padding amount."""
        if not self.is_valid:
            return BoundingBox(0, 0, 0, 0)
        return BoundingBox(
            min_x=self.min_x - padding,
            min_y=self.min_y - padding,
            max_x=self.max_x + padding,
            max_y=self.max_y + padding,
        )

    def pad_percent(self, ratio: float = 0.05) -> BoundingBox:
        """Pad by a percentage of the maximum dimension."""
        dim = max(self.width, self.height)
        pad_amt = max(dim * ratio, 1.0)
        return self.pad(pad_amt)

    def to_dict(self) -> Dict[str, float]:
        return {
            "min_x": round(self.min_x, 4),
            "min_y": round(self.min_y, 4),
            "max_x": round(self.max_x, 4),
            "max_y": round(self.max_y, 4),
            "width": round(self.width, 4),
            "height": round(self.height, 4),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> BoundingBox:
        return cls(
            min_x=float(d["min_x"]),
            min_y=float(d["min_y"]),
            max_x=float(d["max_x"]),
            max_y=float(d["max_y"]),
        )

    @classmethod
    def from_points(cls, points: Sequence[Point2D]) -> BoundingBox:
        """Create bounding box spanning all given points."""
        box = cls()
        for p in points:
            box.expand_point(p)
        return box


class PathSegmentType(str, Enum):
    """Path segment classification."""

    LINE = "line"
    MOVE = "move"
    ARC = "arc"
    DOT = "dot"
    FILL_POLYGON = "fill_polygon"


@dataclass
class PathSegment:
    """Individual geometric drawing or travel segment."""

    segment_type: PathSegmentType = PathSegmentType.LINE
    start: Point2D = field(default_factory=lambda: Point2D(0.0, 0.0))
    end: Point2D = field(default_factory=lambda: Point2D(0.0, 0.0))
    points: List[Point2D] = field(default_factory=list)
    color: str = "#00ffcc"
    stroke_width: float = 1.0
    opacity: float = 1.0
    is_fill: bool = False
    fill_color: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    is_draw: bool = True

    def __post_init__(self) -> None:
        if not self.is_draw and self.segment_type == PathSegmentType.LINE:
            self.segment_type = PathSegmentType.MOVE
        elif self.segment_type == PathSegmentType.MOVE:
            self.is_draw = False

    @property
    def length(self) -> float:
        """Calculate geometric arc/polyline length of the segment."""
        if self.segment_type == PathSegmentType.DOT:
            return 0.0
        if self.points and len(self.points) > 1:
            total = 0.0
            for i in range(len(self.points) - 1):
                total += self.points[i].distance_to(self.points[i + 1])
            return total
        return self.start.distance_to(self.end)

    def bounding_box(self) -> BoundingBox:
        """Compute bounding box for this segment."""
        box = BoundingBox()
        box.expand_point(self.start)
        box.expand_point(self.end)
        for p in self.points:
            box.expand_point(p)
        if self.segment_type == PathSegmentType.DOT:
            radius = float(self.metadata.get("radius", 2.0))
            box.expand_point(Point2D(self.start.x - radius, self.start.y - radius))
            box.expand_point(Point2D(self.start.x + radius, self.start.y + radius))
        return box

    def to_dict(self) -> Dict[str, Any]:
        return {
            "segment_type": self.segment_type.value,
            "start": self.start.to_dict(),
            "end": self.end.to_dict(),
            "points": [p.to_dict() for p in self.points],
            "color": self.color,
            "stroke_width": self.stroke_width,
            "opacity": self.opacity,
            "is_fill": self.is_fill,
            "fill_color": self.fill_color,
            "is_draw": self.is_draw,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> PathSegment:
        seg_t_str = d.get("segment_type")
        if not seg_t_str:
            seg_t = PathSegmentType.LINE if d.get("is_draw", True) else PathSegmentType.MOVE
        else:
            seg_t = PathSegmentType(seg_t_str)

        return cls(
            segment_type=seg_t,
            start=Point2D.from_dict(d["start"]),
            end=Point2D.from_dict(d["end"]),
            points=[Point2D.from_dict(p) for p in d.get("points", [])],
            color=d.get("color", d.get("stroke_color", "#00ffcc")),
            stroke_width=float(d.get("stroke_width", d.get("width", 1.0))),
            opacity=float(d.get("opacity", 1.0)),
            is_fill=bool(d.get("is_fill", False)),
            fill_color=d.get("fill_color"),
            metadata=d.get("metadata", {}),
            is_draw=bool(d.get("is_draw", seg_t != PathSegmentType.MOVE)),
        )


@dataclass
class TurtleState:
    """Internal turtle state snapshot."""

    position: Point2D = field(default_factory=lambda: Point2D(0.0, 0.0))
    heading: float = 0.0  # Angle in degrees (0 = East, 90 = North)
    pen_down: bool = True
    pen_color: str = "#00ffcc"
    stroke_width: float = 1.0
    opacity: float = 1.0
    is_filling: bool = False
    fill_color: Optional[str] = None
    step_size: float = 10.0
    angle_step: float = 90.0

    @property
    def color(self) -> str:
        return self.pen_color

    @property
    def width(self) -> float:
        return self.stroke_width

    def clone(self) -> TurtleState:
        """Create deep clone of current state."""
        return copy.deepcopy(self)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "position": self.position.to_dict(),
            "heading": self.heading,
            "pen_down": self.pen_down,
            "pen_color": self.pen_color,
            "stroke_width": self.stroke_width,
            "opacity": self.opacity,
            "is_filling": self.is_filling,
            "fill_color": self.fill_color,
            "step_size": self.step_size,
            "angle_step": self.angle_step,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> TurtleState:
        return cls(
            position=Point2D.from_dict(d.get("position", {"x": 0.0, "y": 0.0})),
            heading=float(d.get("heading", 0.0)),
            pen_down=bool(d.get("pen_down", True)),
            pen_color=d.get("pen_color", d.get("color", "#00ffcc")),
            stroke_width=float(d.get("stroke_width", d.get("width", 1.0))),
            opacity=float(d.get("opacity", 1.0)),
            is_filling=bool(d.get("is_filling", d.get("fill_active", False))),
            fill_color=d.get("fill_color"),
            step_size=float(d.get("step_size", 10.0)),
            angle_step=float(d.get("angle_step", 90.0)),
        )


@dataclass
class DrawingAST:
    """Abstract Syntax Tree and Geometry collection representing a complete drawing."""

    segments: List[PathSegment] = field(default_factory=list)
    background_color: Optional[str] = None
    title: str = ""
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    polygons: List[List[Point2D]] = field(default_factory=list)
    canvas_width: float = 800.0
    canvas_height: float = 800.0

    def bounding_box(self) -> BoundingBox:
        """Compute the overall bounding box containing all segments."""
        box = BoundingBox()
        for seg in self.segments:
            box.expand_box(seg.bounding_box())
        for poly in self.polygons:
            for pt in poly:
                box.expand_point(pt)
        if not box.is_valid:
            return BoundingBox(0.0, 0.0, 0.0, 0.0)
        return box

    def bounds(self) -> BoundingBox:
        """Alias for bounding_box()."""
        return self.bounding_box()

    def add_segment(self, segment: PathSegment) -> None:
        """Add a path segment to drawing."""
        self.segments.append(segment)

    def add_polygon(self, points: List[Point2D]) -> None:
        """Add a polygon to drawing."""
        self.polygons.append(points)

    def stats(self) -> Dict[str, Any]:
        """Compute comprehensive metrics and telemetry for the drawing."""
        bbox = self.bounding_box()
        total_draw_len = 0.0
        total_travel_len = 0.0
        line_count = 0
        move_count = 0
        dot_count = 0
        arc_count = 0
        poly_count = len(self.polygons)
        colors_used = set()

        for seg in self.segments:
            seg_len = seg.length
            colors_used.add(seg.color)
            if seg.fill_color:
                colors_used.add(seg.fill_color)

            if seg.segment_type == PathSegmentType.MOVE or not seg.is_draw:
                total_travel_len += seg_len
                move_count += 1
            elif seg.segment_type == PathSegmentType.LINE:
                total_draw_len += seg_len
                line_count += 1
            elif seg.segment_type == PathSegmentType.DOT:
                dot_count += 1
            elif seg.segment_type == PathSegmentType.ARC:
                total_draw_len += seg_len
                arc_count += 1
            elif seg.segment_type == PathSegmentType.FILL_POLYGON:
                total_draw_len += seg_len
                poly_count += 1

        draw_segs = len(self.segments) - move_count
        return {
            "total_segments": len(self.segments),
            "drawing_segments": draw_segs,
            "draw_segments": draw_segs,
            "travel_segments": move_count,
            "line_count": line_count,
            "travel_count": move_count,
            "dot_count": dot_count,
            "arc_count": arc_count,
            "polygon_count": poly_count,
            "total_drawing_length": round(total_draw_len, 3),
            "total_draw_length": round(total_draw_len, 3),
            "total_travel_length": round(total_travel_len, 3),
            "total_path_length": round(total_draw_len + total_travel_len, 3),
            "unique_colors": sorted(list(colors_used)),
            "bounding_box": bbox.to_dict(),
            "width": round(bbox.width, 3),
            "height": round(bbox.height, 3),
            "aspect_ratio": round(bbox.aspect_ratio, 4),
        }

    def scale(self, factor: float) -> DrawingAST:
        """Scale all coordinates in-place and return self."""
        transformed = self.transform(factor, factor)
        self.segments = transformed.segments
        self.polygons = transformed.polygons
        return self

    def center_at(self, target_x: float = 0.0, target_y: float = 0.0) -> DrawingAST:
        """Center the drawing at target coordinates."""
        bbox = self.bounding_box()
        if not bbox.is_valid:
            return self
        c = bbox.center
        dx = target_x - c.x
        dy = target_y - c.y
        shifted = self.transform(1.0, 1.0, dx, dy)
        self.segments = shifted.segments
        self.polygons = shifted.polygons
        return self


    def transform(
        self,
        scale_x: float = 1.0,
        scale_y: float = 1.0,
        offset_x: float = 0.0,
        offset_y: float = 0.0,
    ) -> DrawingAST:
        """Return a new transformed DrawingAST."""
        def tx_pt(p: Point2D) -> Point2D:
            return Point2D(p.x * scale_x + offset_x, p.y * scale_y + offset_y)

        new_segments: List[PathSegment] = []
        for seg in self.segments:
            new_pts = [tx_pt(p) for p in seg.points]
            new_seg = PathSegment(
                segment_type=seg.segment_type,
                start=tx_pt(seg.start),
                end=tx_pt(seg.end),
                points=new_pts,
                color=seg.color,
                stroke_width=seg.stroke_width * max(abs(scale_x), abs(scale_y)),
                opacity=seg.opacity,
                is_fill=seg.is_fill,
                fill_color=seg.fill_color,
                metadata=copy.deepcopy(seg.metadata),
            )
            new_segments.append(new_seg)

        new_polys = [[tx_pt(p) for p in poly] for poly in self.polygons]

        return DrawingAST(
            segments=new_segments,
            background_color=self.background_color,
            title=self.title,
            description=self.description,
            metadata=copy.deepcopy(self.metadata),
            polygons=new_polys,
        )

    def normalize(
        self,
        target_width: float = 800.0,
        target_height: float = 800.0,
        margin: float = 40.0,
        keep_aspect_ratio: bool = True,
    ) -> DrawingAST:
        """Fit and center the drawing within target bounds with margins."""
        bbox = self.bounding_box()
        if not bbox.is_valid or (bbox.width == 0 and bbox.height == 0):
            return self

        avail_w = max(10.0, target_width - 2 * margin)
        avail_h = max(10.0, target_height - 2 * margin)

        orig_w = max(bbox.width, 0.001)
        orig_h = max(bbox.height, 0.001)

        if keep_aspect_ratio:
            scale = min(avail_w / orig_w, avail_h / orig_h)
            scale_x = scale
            scale_y = scale
        else:
            scale_x = avail_w / orig_w
            scale_y = avail_h / orig_h

        c = bbox.center
        tx = (target_width / 2.0) - (c.x * scale_x)
        ty = (target_height / 2.0) - (c.y * scale_y)

        return self.transform(scale_x, scale_y, tx, ty)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "description": self.description,
            "background_color": self.background_color,
            "metadata": self.metadata,
            "stats": self.stats(),
            "segments": [s.to_dict() for s in self.segments],
            "polygons": [[p.to_dict() for p in poly] for poly in self.polygons],
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> DrawingAST:
        return cls(
            title=d.get("title", ""),
            description=d.get("description", ""),
            background_color=d.get("background_color"),
            metadata=d.get("metadata", {}),
            segments=[PathSegment.from_dict(s) for s in d.get("segments", [])],
            polygons=[[Point2D.from_dict(p) for p in poly] for poly in d.get("polygons", [])],
        )

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_json(cls, json_str: str) -> DrawingAST:
        return cls.from_dict(json.loads(json_str))


@dataclass
class LSystemRule:
    """Production rule for L-System rewriting."""

    predecessor: str
    successor: str
    probability: float = 1.0
    condition: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "predecessor": self.predecessor,
            "successor": self.successor,
            "probability": self.probability,
            "condition": self.condition,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> LSystemRule:
        return cls(
            predecessor=str(d["predecessor"]),
            successor=str(d["successor"]),
            probability=float(d.get("probability", 1.0)),
            condition=d.get("condition"),
        )


@dataclass
class LSystemConfig:
    """Complete specification for a Lindenmayer System."""

    axiom: str
    rules: Dict[str, Union[str, List[Union[str, LSystemRule, Dict[str, Any]]]]]
    angle: float
    iterations: int
    step_size: float = 10.0
    step_scale: float = 1.0
    angle_scale: float = 1.0
    start_heading: float = 0.0
    start_pos: Tuple[float, float] = (0.0, 0.0)
    seed: Optional[int] = None
    name: str = ""
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_parsed_rules(self) -> Dict[str, List[LSystemRule]]:
        """Normalize rules dictionary into a typed map of LSystemRule lists."""
        normalized: Dict[str, List[LSystemRule]] = {}
        for pred, rule_val in self.rules.items():
            if isinstance(rule_val, str):
                normalized[pred] = [LSystemRule(predecessor=pred, successor=rule_val, probability=1.0)]
            elif isinstance(rule_val, list):
                parsed_list: List[LSystemRule] = []
                for item in rule_val:
                    if isinstance(item, str):
                        parsed_list.append(LSystemRule(predecessor=pred, successor=item, probability=1.0))
                    elif isinstance(item, LSystemRule):
                        parsed_list.append(item)
                    elif isinstance(item, dict):
                        parsed_list.append(LSystemRule.from_dict({**item, "predecessor": pred}))
                normalized[pred] = parsed_list
            elif isinstance(rule_val, LSystemRule):
                normalized[pred] = [rule_val]
        return normalized

    def to_dict(self) -> Dict[str, Any]:
        serialized_rules: Dict[str, Any] = {}
        for k, v in self.get_parsed_rules().items():
            if len(v) == 1 and v[0].probability == 1.0 and v[0].condition is None:
                serialized_rules[k] = v[0].successor
            else:
                serialized_rules[k] = [r.to_dict() for r in v]

        return {
            "name": self.name,
            "description": self.description,
            "axiom": self.axiom,
            "rules": serialized_rules,
            "angle": self.angle,
            "iterations": self.iterations,
            "step_size": self.step_size,
            "step_scale": self.step_scale,
            "angle_scale": self.angle_scale,
            "start_heading": self.start_heading,
            "start_pos": list(self.start_pos),
            "seed": self.seed,
            "metadata": self.metadata,
        }


    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> LSystemConfig:
        return cls(
            name=d.get("name", ""),
            description=d.get("description", ""),
            axiom=str(d["axiom"]),
            rules=d.get("rules", {}),
            angle=float(d.get("angle", 90.0)),
            iterations=int(d.get("iterations", 3)),
            step_size=float(d.get("step_size", 10.0)),
            step_scale=float(d.get("step_scale", 1.0)),
            angle_scale=float(d.get("angle_scale", 1.0)),
            start_heading=float(d.get("start_heading", 0.0)),
            start_pos=tuple(d.get("start_pos", (0.0, 0.0))),  # type: ignore
            seed=d.get("seed"),
            metadata=d.get("metadata", {}),
        )

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_json(cls, json_str: str) -> LSystemConfig:
        return cls.from_dict(json.loads(json_str))


@dataclass
class PatternPreset:
    """Preset metadata and configuration for catalog entries."""

    id: str
    name: str
    category: str
    description: str
    config: LSystemConfig
    tags: List[str] = field(default_factory=list)
    difficulty: str = "Beginner"  # Beginner, Intermediate, Advanced, Master
    recommended_iterations: int = 4
    default_theme: str = "cyber_matrix"
    credit: str = ""

    @property
    def title(self) -> str:
        return self.name

    @property
    def type(self) -> str:
        return "lsystem"

    @property
    def default_parameters(self) -> Dict[str, Any]:
        return {
            "iterations": self.recommended_iterations,
            "step_size": self.config.step_size,
            "angle": self.config.angle,
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "title": self.title,
            "type": self.type,
            "category": self.category,
            "description": self.description,
            "config": self.config.to_dict(),
            "tags": self.tags,
            "difficulty": self.difficulty,
            "recommended_iterations": self.recommended_iterations,
            "default_parameters": self.default_parameters,
            "default_theme": self.default_theme,
            "credit": self.credit,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> PatternPreset:
        return cls(
            id=d["id"],
            name=d.get("name", d.get("title", "")),
            category=d["category"],
            description=d["description"],
            config=LSystemConfig.from_dict(d["config"]),
            tags=d.get("tags", []),
            difficulty=d.get("difficulty", "Beginner"),
            recommended_iterations=int(d.get("recommended_iterations", 4)),
            default_theme=d.get("default_theme", "cyber_matrix"),
            credit=d.get("credit", ""),
        )

