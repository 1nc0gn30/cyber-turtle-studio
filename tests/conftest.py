"""Pytest configuration, path initialization, and shared fixtures for cyber-turtle-studio."""

from __future__ import annotations

import os
import socket
import sys
import tempfile
from pathlib import Path
from typing import Dict, Generator, List

import pytest

# Ensure src/ is on sys.path for test execution
ROOT_DIR = Path(__file__).parent.parent.resolve()
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from cyber_turtle_studio.models import (
    BoundingBox,
    DrawingAST,
    LSystemConfig,
    LSystemRule,
    PathSegment,
    PathSegmentType,
    PatternPreset,
    Point2D,
    TurtleState,
)


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Provide a safe isolated temporary directory for file exports."""
    with tempfile.TemporaryDirectory(prefix="cyber_turtle_test_") as td:
        yield Path(td)


@pytest.fixture
def sample_points() -> List[Point2D]:
    """Sample 2D points for geometric and bounding box testing."""
    return [
        Point2D(0.0, 0.0),
        Point2D(100.0, 0.0),
        Point2D(100.0, 100.0),
        Point2D(0.0, 100.0),
    ]


@pytest.fixture
def sample_drawing_ast(sample_points: List[Point2D]) -> DrawingAST:
    """Provide a standard square DrawingAST fixture."""
    ast = DrawingAST(
        title="Test Square Drawing",
        description="Unit test fixture drawing",
    )
    # Add square perimeter
    pts = sample_points
    for i in range(len(pts)):
        p1 = pts[i]
        p2 = pts[(i + 1) % len(pts)]
        ast.add_segment(
            PathSegment(
                start=p1,
                end=p2,
                color="#00ffcc",
                stroke_width=2.0,
                opacity=1.0,
                segment_type=PathSegmentType.LINE,
            )
        )
    return ast



@pytest.fixture
def sample_logo_scripts() -> Dict[str, str]:
    """Collection of Logo DSL scripts for syntax and parser tests."""
    return {
        "square": "repeat 4 [ fd 100 rt 90 ]",
        "nested_repeat": "repeat 6 [ repeat 4 [ fd 50 rt 90 ] rt 60 ]",
        "star": "repeat 5 [ fd 100 rt 144 ]",
        "arcs": "circle 50 180 dot 10 #ff007f",
        "variables": "make \"size 80 make \"angle 90 repeat 4 [ fd :size rt :angle ]",
        "procedures": "to square :s repeat 4 [ fd :s rt 90 ] end square 120",
        "state_stack": "fd 50 push rt 90 fd 30 pop fd 50",
    }


@pytest.fixture
def sample_lsystem_config() -> LSystemConfig:
    """Koch curve configuration fixture."""
    return LSystemConfig(
        name="Test Koch Snowflake",
        axiom="F--F--F",
        rules={"F": "F+F--F+F"},
        angle=60.0,
        iterations=3,
        step_size=10.0,
    )


@pytest.fixture
def free_port() -> int:
    """Find a dynamically free TCP port for server tests."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]
