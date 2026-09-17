"""High-precision Pure Python Turtle graphics interpreter and Logo DSL parser.

Provides complete 2D turtle navigation, vector transformations, state stacks,
fill polygon generation, and an extensible Logo mini-script interpreter.
"""

from __future__ import annotations

import math
import re
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Union

from cyber_turtle_studio.models import (
    BoundingBox,
    DrawingAST,
    PathSegment,
    PathSegmentType,
    Point2D,
    TurtleState,
)


class TurtleEngine:
    """High-precision 2D Turtle Graphics Interpreter."""

    def __init__(
        self,
        start_pos: Union[Point2D, Tuple[float, float]] = (0.0, 0.0),
        start_heading: float = 0.0,  # 0.0 = East, 90.0 = North
        pen_down: bool = True,
        pen_color: str = "#00ffcc",
        stroke_width: float = 1.0,
        opacity: float = 1.0,
        background_color: Optional[str] = None,
        title: str = "",
    ) -> None:
        if isinstance(start_pos, Point2D):
            pos = start_pos
        else:
            pos = Point2D(float(start_pos[0]), float(start_pos[1]))

        self._state = TurtleState(
            position=pos,
            heading=float(start_heading) % 360.0,
            pen_down=pen_down,
            pen_color=pen_color,
            stroke_width=max(0.1, stroke_width),
            opacity=max(0.0, min(1.0, opacity)),
            is_filling=False,
            fill_color=None,
            step_size=10.0,
            angle_step=90.0,
        )
        self._initial_state = self._state.clone()
        self._state_stack: List[TurtleState] = []
        self._segments: List[PathSegment] = []
        self._fill_polygon_points: List[Point2D] = []
        self._fill_active_color: Optional[str] = None
        self._background_color: Optional[str] = background_color
        self._title: str = title
        self._metadata: Dict[str, Any] = {}

    @property
    def position(self) -> Point2D:
        """Current position of turtle."""
        return self._state.position

    @property
    def x(self) -> float:
        return self._state.position.x

    @property
    def y(self) -> float:
        return self._state.position.y

    @property
    def heading(self) -> float:
        """Current heading in degrees (0 = East, 90 = North)."""
        return self._state.heading

    @property
    def is_pen_down(self) -> bool:
        return self._state.pen_down

    @property
    def pen_color(self) -> str:
        return self._state.pen_color

    @property
    def stroke_width(self) -> float:
        return self._state.stroke_width

    @property
    def opacity(self) -> float:
        return self._state.opacity

    @property
    def segments(self) -> List[PathSegment]:
        return self._segments

    def reset(self) -> TurtleEngine:
        """Reset turtle to initial state and clear drawing."""
        self._state = self._initial_state.clone()
        self._state_stack.clear()
        self._segments.clear()
        self._fill_polygon_points.clear()
        self._fill_active_color = None
        return self

    def clear(self) -> TurtleEngine:
        """Clear all drawn segments without resetting turtle position/state."""
        self._segments.clear()
        self._fill_polygon_points.clear()
        return self

    def pen_up(self) -> TurtleEngine:
        """Lift the pen up (move without drawing lines)."""
        self._state.pen_down = False
        return self

    pu = pen_up
    penup = pen_up

    def pen_down(self) -> TurtleEngine:
        """Put the pen down (moves draw lines)."""
        self._state.pen_down = True
        return self

    pd = pen_down
    pendown = pen_down

    def set_color(self, color: str) -> TurtleEngine:
        """Set pen stroke color (hex, rgb, or named color)."""
        clean_color = color.strip()
        if clean_color:
            self._state.pen_color = clean_color
        return self

    color = set_color
    pencolor = set_color

    def set_width(self, width: float) -> TurtleEngine:
        """Set pen stroke width."""
        self._state.stroke_width = max(0.01, float(width))
        return self

    width = set_width
    pensize = set_width

    def set_opacity(self, opacity: float) -> TurtleEngine:
        """Set stroke opacity (0.0 to 1.0)."""
        self._state.opacity = max(0.0, min(1.0, float(opacity)))
        return self

    def set_heading(self, angle_deg: float) -> TurtleEngine:
        """Set absolute heading angle in degrees (0 = East, 90 = North)."""
        self._state.heading = float(angle_deg) % 360.0
        return self

    seth = set_heading
    heading_to = set_heading

    def left(self, angle_deg: float) -> TurtleEngine:
        """Turn turtle left (counter-clockwise) by angle in degrees."""
        self._state.heading = (self._state.heading + float(angle_deg)) % 360.0
        return self

    lt = left

    def right(self, angle_deg: float) -> TurtleEngine:
        """Turn turtle right (clockwise) by angle in degrees."""
        self._state.heading = (self._state.heading - float(angle_deg)) % 360.0
        return self

    rt = right

    def forward(self, distance: float) -> TurtleEngine:
        """Move turtle forward by distance along current heading."""
        d = float(distance)
        rad = math.radians(self._state.heading)
        nx = self._state.position.x + d * math.cos(rad)
        ny = self._state.position.y + d * math.sin(rad)
        return self.goto(nx, ny)

    fd = forward

    def backward(self, distance: float) -> TurtleEngine:
        """Move turtle backward by distance."""
        return self.forward(-float(distance))

    bk = backward
    back = backward

    def goto(self, x: float, y: float) -> TurtleEngine:
        """Move turtle to absolute Cartesian coordinates (x, y)."""
        target = Point2D(float(x), float(y))
        start = self._state.position

        if self._state.is_filling:
            self._fill_polygon_points.append(target)

        if start != target:
            if self._state.pen_down:
                seg = PathSegment(
                    segment_type=PathSegmentType.LINE,
                    start=start,
                    end=target,
                    points=[start, target],
                    color=self._state.pen_color,
                    stroke_width=self._state.stroke_width,
                    opacity=self._state.opacity,
                )
                self._segments.append(seg)
            else:
                seg = PathSegment(
                    segment_type=PathSegmentType.MOVE,
                    start=start,
                    end=target,
                    points=[start, target],
                    color=self._state.pen_color,
                    stroke_width=self._state.stroke_width,
                    opacity=self._state.opacity,
                )
                self._segments.append(seg)

        self._state.position = target
        return self

    setpos = goto
    setposition = goto

    def dot(self, size: float = 5.0, color: Optional[str] = None) -> TurtleEngine:
        """Draw a circular dot at current position."""
        dot_color = color.strip() if color else self._state.pen_color
        radius = max(0.5, float(size) / 2.0)
        pos = self._state.position

        seg = PathSegment(
            segment_type=PathSegmentType.DOT,
            start=pos,
            end=pos,
            points=[pos],
            color=dot_color,
            stroke_width=self._state.stroke_width,
            opacity=self._state.opacity,
            is_fill=True,
            fill_color=dot_color,
            metadata={"radius": radius, "diameter": size},
        )
        self._segments.append(seg)
        return self

    def circle(
        self,
        radius: float,
        extent: float = 360.0,
        steps: Optional[int] = None,
    ) -> TurtleEngine:
        """Draw a circle or circular arc of given radius and angular extent.

        The center is `radius` units to the left of the turtle (if radius > 0),
        or to the right (if radius < 0).
        """
        r = float(radius)
        ext = float(extent)
        if ext == 0.0 or r == 0.0:
            return self

        # Determine step count for smooth approximation
        if steps is None:
            # Scale steps based on radius and extent
            arc_len = abs(r * math.radians(ext))
            step_count = max(8, min(360, int(arc_len / 3.0) + int(abs(ext) / 8.0)))
        else:
            step_count = max(3, int(steps))

        step_angle = ext / step_count
        step_chord = 2.0 * abs(r) * math.sin(math.radians(abs(step_angle) / 2.0))
        # Direction of turn: positive radius turns left, negative radius turns right
        turn_mult = 1.0 if (r >= 0 and ext >= 0) or (r < 0 and ext < 0) else -1.0

        half_turn = (step_angle / 2.0) * (1.0 if r >= 0 else -1.0)
        for _ in range(step_count):
            self.left(half_turn)
            self.forward(step_chord)
            self.left(half_turn)

        return self

    def push_state(self) -> TurtleEngine:
        """Push a copy of the current turtle state onto the stack."""
        self._state_stack.append(self._state.clone())
        return self

    def pop_state(self) -> TurtleEngine:
        """Pop and restore previous turtle state from the stack."""
        if self._state_stack:
            prev_state = self._state_stack.pop()
            old_pos = self._state.position
            self._state = prev_state
            # If position changed via pop, record travel move if pen up/down
            if old_pos != self._state.position:
                self._segments.append(
                    PathSegment(
                        segment_type=PathSegmentType.MOVE,
                        start=old_pos,
                        end=self._state.position,
                        points=[old_pos, self._state.position],
                        color=self._state.pen_color,
                        stroke_width=self._state.stroke_width,
                        opacity=self._state.opacity,
                    )
                )
        return self

    def begin_fill(self, color: Optional[str] = None) -> TurtleEngine:
        """Begin recording points for a filled polygon."""
        self._state.is_filling = True
        self._fill_active_color = color.strip() if color else self._state.pen_color
        self._fill_polygon_points = [self._state.position]
        return self

    def end_fill(self) -> TurtleEngine:
        """Close and emit the recorded polygon fill segment."""
        if self._state.is_filling and len(self._fill_polygon_points) >= 3:
            pts = list(self._fill_polygon_points)
            fill_col = self._fill_active_color or self._state.pen_color
            seg = PathSegment(
                segment_type=PathSegmentType.FILL_POLYGON,
                start=pts[0],
                end=pts[-1],
                points=pts,
                color=self._state.pen_color,
                stroke_width=self._state.stroke_width,
                opacity=self._state.opacity,
                is_fill=True,
                fill_color=fill_col,
            )
            self._segments.append(seg)

        self._state.is_filling = False
        self._fill_active_color = None
        self._fill_polygon_points = []
        return self

    def get_drawing(self) -> DrawingAST:
        """Compile and return the complete DrawingAST."""
        return DrawingAST(
            segments=list(self._segments),
            background_color=self._background_color,
            title=self._title,
            metadata={
                "turtle_pos": self._state.position.to_dict(),
                "turtle_heading": self._state.heading,
                **self._metadata,
            },
        )


class LogoParser:
    """Parser and evaluator for standard Logo DSL scripts."""

    def __init__(self, engine: Optional[TurtleEngine] = None) -> None:
        self.engine = engine if engine is not None else TurtleEngine()
        self.variables: Dict[str, float] = {}
        self.procedures: Dict[str, Tuple[List[str], List[str]]] = {}

    def _tokenize(self, script: str) -> List[str]:
        """Tokenize Logo script into words, numbers, brackets, and operators."""
        # Strip comments starting with ;, //, or # (unless # is a hex color)
        lines: List[str] = []
        for line in script.splitlines():
            line_no_comment = re.sub(r"(;|//|(?<![a-zA-Z0-9_])#(?!([0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})\b)).*$", "", line)
            lines.append(line_no_comment)
        clean_script = " ".join(lines)


        # Token regex matching brackets, strings, variables (:var), numbers/expressions, commands
        pattern = r'\[|\]|\"[a-zA-Z0-9_-]+|:[a-zA-Z0-9_-]+|#[0-9a-fA-F]{3,8}|[a-zA-Z_][a-zA-Z0-9_]*|[-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?|[^\s\[\]]+'
        tokens = re.findall(pattern, clean_script)
        return tokens

    def _eval_expr(self, val_str: str) -> float:
        """Safely evaluate arithmetic expressions or variable lookups."""
        val_clean = val_str.strip()
        if val_clean.startswith(":"):
            var_name = val_clean[1:]
            return self.variables.get(var_name, 0.0)
        if val_clean in self.variables:
            return self.variables[val_clean]

        # Safe math evaluation
        try:
            # Whitelisted math tokens
            safe_dict = {
                "pi": math.pi,
                "e": math.e,
                "sin": math.sin,
                "cos": math.cos,
                "tan": math.tan,
                "sqrt": math.sqrt,
                "abs": abs,
                "rad": math.radians,
                "deg": math.degrees,
            }
            safe_dict.update(self.variables)
            # Only evaluate if contains basic math characters
            if re.match(r"^[0-9\.\+\-\*\/\(\)\s_a-zA-Z:,]+$", val_clean):
                return float(eval(val_clean, {"__builtins__": None}, safe_dict))
        except Exception:
            pass

        try:
            return float(val_clean)
        except ValueError:
            return 0.0

    def parse_blocks(self, tokens: List[str]) -> List[Any]:
        """Convert a flat token list with nested brackets into a nested list structure."""
        stack: List[List[Any]] = [[]]
        for token in tokens:
            if token == "[":
                new_block: List[Any] = []
                stack[-1].append(new_block)
                stack.append(new_block)
            elif token == "]":
                if len(stack) > 1:
                    stack.pop()
            else:
                stack[-1].append(token)
        return stack[0]

    def execute_tokens(self, tokens: List[Any]) -> None:
        """Execute structured Logo command tokens."""
        i = 0
        n = len(tokens)

        while i < n:
            token = tokens[i]

            if isinstance(token, list):
                # Nested block standalone execution
                self.execute_tokens(token)
                i += 1
                continue

            cmd = str(token).lower()

            # Forward
            if cmd in ("fd", "forward"):
                if i + 1 < n and not isinstance(tokens[i + 1], list):
                    dist = self._eval_expr(str(tokens[i + 1]))
                    self.engine.forward(dist)
                    i += 2
                else:
                    self.engine.forward(10.0)
                    i += 1

            # Backward
            elif cmd in ("bk", "backward", "back"):
                if i + 1 < n and not isinstance(tokens[i + 1], list):
                    dist = self._eval_expr(str(tokens[i + 1]))
                    self.engine.backward(dist)
                    i += 2
                else:
                    self.engine.backward(10.0)
                    i += 1

            # Left
            elif cmd in ("lt", "left"):
                if i + 1 < n and not isinstance(tokens[i + 1], list):
                    angle = self._eval_expr(str(tokens[i + 1]))
                    self.engine.left(angle)
                    i += 2
                else:
                    self.engine.left(90.0)
                    i += 1

            # Right
            elif cmd in ("rt", "right"):
                if i + 1 < n and not isinstance(tokens[i + 1], list):
                    angle = self._eval_expr(str(tokens[i + 1]))
                    self.engine.right(angle)
                    i += 2
                else:
                    self.engine.right(90.0)
                    i += 1

            # Pen Up
            elif cmd in ("pu", "penup"):
                self.engine.pen_up()
                i += 1

            # Pen Down
            elif cmd in ("pd", "pendown"):
                self.engine.pen_down()
                i += 1

            # Set Heading
            elif cmd in ("seth", "setheading", "heading"):
                if i + 1 < n and not isinstance(tokens[i + 1], list):
                    angle = self._eval_expr(str(tokens[i + 1]))
                    self.engine.set_heading(angle)
                    i += 2
                else:
                    i += 1

            # Goto / Setpos
            elif cmd in ("goto", "setpos", "setposition"):
                if i + 2 < n and not isinstance(tokens[i + 1], list) and not isinstance(tokens[i + 2], list):
                    x = self._eval_expr(str(tokens[i + 1]))
                    y = self._eval_expr(str(tokens[i + 2]))
                    self.engine.goto(x, y)
                    i += 3
                else:
                    i += 1

            # Color
            elif cmd in ("color", "pencolor", "setcolor"):
                if i + 1 < n and not isinstance(tokens[i + 1], list):
                    col = str(tokens[i + 1]).strip('"')
                    self.engine.set_color(col)
                    i += 2
                else:
                    i += 1

            # Width / Size
            elif cmd in ("width", "pensize", "size", "setwidth"):
                if i + 1 < n and not isinstance(tokens[i + 1], list):
                    w = self._eval_expr(str(tokens[i + 1]))
                    self.engine.set_width(w)
                    i += 2
                else:
                    i += 1

            # Opacity
            elif cmd in ("opacity", "setopacity"):
                if i + 1 < n and not isinstance(tokens[i + 1], list):
                    op = self._eval_expr(str(tokens[i + 1]))
                    self.engine.set_opacity(op)
                    i += 2
                else:
                    i += 1

            # Circle: circle <radius> [extent] [steps]
            elif cmd == "circle":
                if i + 1 < n and not isinstance(tokens[i + 1], list):
                    r = self._eval_expr(str(tokens[i + 1]))
                    ext = 360.0
                    steps = None
                    adv = 2
                    if i + 2 < n and not isinstance(tokens[i + 2], list) and str(tokens[i + 2]).lower() not in (
                        "fd", "bk", "lt", "rt", "pu", "pd", "repeat", "circle", "dot"
                    ):
                        ext = self._eval_expr(str(tokens[i + 2]))
                        adv = 3
                        if i + 3 < n and not isinstance(tokens[i + 3], list) and str(tokens[i + 3]).lower() not in (
                            "fd", "bk", "lt", "rt", "pu", "pd", "repeat", "circle", "dot"
                        ):
                            steps = int(self._eval_expr(str(tokens[i + 3])))
                            adv = 4
                    self.engine.circle(r, extent=ext, steps=steps)
                    i += adv
                else:
                    i += 1

            # Dot: dot <size> [color]
            elif cmd == "dot":
                if i + 1 < n and not isinstance(tokens[i + 1], list):
                    size = self._eval_expr(str(tokens[i + 1]))
                    dot_col = None
                    adv = 2
                    if i + 2 < n and not isinstance(tokens[i + 2], list) and str(tokens[i + 2]).startswith("#"):
                        dot_col = str(tokens[i + 2])
                        adv = 3
                    self.engine.dot(size, color=dot_col)
                    i += adv
                else:
                    self.engine.dot(5.0)
                    i += 1

            # Push / Pop State
            elif cmd in ("push", "push_state", "[state]"):
                self.engine.push_state()
                i += 1
            elif cmd in ("pop", "pop_state", "[/state]"):
                self.engine.pop_state()
                i += 1

            # Fill
            elif cmd in ("begin_fill", "fill_start"):
                fill_c = None
                if i + 1 < n and not isinstance(tokens[i + 1], list) and str(tokens[i + 1]).startswith("#"):
                    fill_c = str(tokens[i + 1])
                    i += 1
                self.engine.begin_fill(fill_c)
                i += 1
            elif cmd in ("end_fill", "fill_end"):
                self.engine.end_fill()
                i += 1

            # Repeat: repeat <count> [ <commands> ]
            elif cmd == "repeat":
                if i + 2 < n:
                    count = int(self._eval_expr(str(tokens[i + 1])))
                    block = tokens[i + 2]
                    if isinstance(block, list):
                        for _ in range(max(0, count)):
                            self.execute_tokens(block)
                        i += 3
                    else:
                        i += 2
                else:
                    i += 1

            # Variable assignment: make "var <val> or set <var> <val>
            elif cmd in ("make", "set", "let"):
                if i + 2 < n:
                    var_name = str(tokens[i + 1]).lstrip('":')
                    var_val = self._eval_expr(str(tokens[i + 2]))
                    self.variables[var_name] = var_val
                    i += 3
                else:
                    i += 1

            # Procedure definition: to <proc_name> [:arg1 :arg2] ... end
            elif cmd == "to":
                proc_name = str(tokens[i + 1]).lower()
                param_names: List[str] = []
                idx = i + 2
                while idx < n and str(tokens[idx]).startswith(":"):
                    param_names.append(str(tokens[idx])[1:])
                    idx += 1
                body_tokens: List[Any] = []
                while idx < n and str(tokens[idx]).lower() != "end":
                    body_tokens.append(tokens[idx])
                    idx += 1
                self.procedures[proc_name] = (param_names, body_tokens)
                i = idx + 1 if idx < n else n

            # Procedure invocation
            elif cmd in self.procedures:
                params, body = self.procedures[cmd]
                saved_vars = dict(self.variables)
                # Read arguments
                adv = 1
                for p_name in params:
                    if i + adv < n and not isinstance(tokens[i + adv], list):
                        self.variables[p_name] = self._eval_expr(str(tokens[i + adv]))
                        adv += 1
                self.execute_tokens(body)
                self.variables = saved_vars
                i += adv

            else:
                # Unknown or skipped token
                i += 1

    def run(self, script: str) -> DrawingAST:
        """Parse and execute a Logo DSL script string."""
        raw_tokens = self._tokenize(script)
        structured_tokens = self.parse_blocks(raw_tokens)
        self.execute_tokens(structured_tokens)
        return self.engine.get_drawing()


def execute_logo(
    script: str,
    initial_state: Optional[TurtleState] = None,
    color: Optional[str] = None,
    width: Optional[float] = None,
    **kwargs: Any,
) -> DrawingAST:
    """Convenience function to parse and execute a Logo DSL script."""
    engine = TurtleEngine()
    if initial_state is not None:
        engine._state = initial_state.clone()
    if color is not None:
        engine.set_color(color)
    if width is not None:
        engine.set_width(width)
    parser = LogoParser(engine)
    return parser.run(script)


Turtle = TurtleEngine

