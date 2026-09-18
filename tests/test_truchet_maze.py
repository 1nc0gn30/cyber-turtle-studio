"""Comprehensive Test Suite for Truchet Tilings and Algorithmic Maze Labyrinths.

Tests procedural vector Truchet pattern synthesis, algorithmic maze generators
(Recursive Backtracker, Wilson's UST, Braided), BFS shortest-path routing,
terminal ASCII maze rendering, MCP tools, CLI integration, and REST endpoints.
"""

from __future__ import annotations

import json
import threading
import time
import urllib.parse
import urllib.request
from typing import Any, Dict, Generator

import pytest

from cyber_turtle_studio.cli import build_parser, main
from cyber_turtle_studio.mcp_server import MCPServer
from cyber_turtle_studio.truchet_maze import (
    MazeAlgorithm,
    TruchetStyle,
    generate_maze_labyrinth,
    generate_truchet_tiling,
    render_ascii_maze,
)
from cyber_turtle_studio.ui_server import create_server


# =============================================================================
# 1. Truchet Tiling Tests
# =============================================================================

class TestTruchetTiling:
    """Test procedural Truchet vector tiling generation."""

    @pytest.mark.parametrize("style", [
        TruchetStyle.ARCS,
        TruchetStyle.DIAGONAL,
        TruchetStyle.CONCENTRIC_ARCS,
        TruchetStyle.CROSS_LINE,
        "arcs",
        "diagonal",
        "concentric_arcs",
        "cross_line",
    ])
    def test_truchet_styles(self, style: Any) -> None:
        """Verify each Truchet style generates valid AST with segments."""
        ast, stats = generate_truchet_tiling(
            rows=6,
            cols=6,
            tile_size=30.0,
            style=style,
            seed=42,
        )
        assert ast is not None
        assert len(ast.segments) > 0
        assert stats["rows"] == 6
        assert stats["cols"] == 6
        assert stats["total_tiles"] == 36
        assert stats["bounds"]["width"] == pytest.approx(180.0)
        assert stats["bounds"]["height"] == pytest.approx(180.0)

    def test_truchet_seed_determinism(self) -> None:
        """Verify identical seeds produce identical ASTs, different seeds differ."""
        ast1, stats1 = generate_truchet_tiling(rows=5, cols=5, seed=1234)
        ast2, stats2 = generate_truchet_tiling(rows=5, cols=5, seed=1234)
        ast3, stats3 = generate_truchet_tiling(rows=5, cols=5, seed=5678)

        assert len(ast1.segments) == len(ast2.segments)
        assert [s.to_dict() for s in ast1.segments] == [s.to_dict() for s in ast2.segments]

        # Different seed should generate different tile orientations
        dicts1 = [s.to_dict() for s in ast1.segments]
        dicts3 = [s.to_dict() for s in ast3.segments]
        assert dicts1 != dicts3

    def test_truchet_invalid_style(self) -> None:
        """Verify unknown style raises ValueError."""
        with pytest.raises(ValueError, match="Unknown TruchetStyle"):
            generate_truchet_tiling(style="nonexistent_style")

    def test_truchet_geometry_bounds(self) -> None:
        """Verify bounding box calculation is non-empty and well-formed."""
        ast, stats = generate_truchet_tiling(rows=4, cols=8, tile_size=25.0, seed=99)
        bbox = ast.bounding_box()
        assert bbox.width > 0
        assert bbox.height > 0
        assert stats["total_segments"] == len(ast.segments)


# =============================================================================
# 2. Maze Labyrinth Tests
# =============================================================================

class TestMazeLabyrinth:
    """Test algorithmic labyrinth maze generation and BFS solver."""

    @pytest.mark.parametrize("algo", [
        MazeAlgorithm.RECURSIVE_BACKTRACKER,
        MazeAlgorithm.WILSON,
        MazeAlgorithm.BRAIDED,
        "recursive_backtracker",
        "wilson",
        "braided",
    ])
    def test_maze_algorithms(self, algo: Any) -> None:
        """Verify all three maze generation algorithms produce valid mazes."""
        ast, meta = generate_maze_labyrinth(
            rows=8,
            cols=8,
            cell_size=20.0,
            algorithm=algo,
            seed=777,
            solve=False,
        )
        assert ast is not None
        assert len(ast.segments) > 0
        assert meta["rows"] == 8
        assert meta["cols"] == 8
        assert meta["wall_segments_count"] > 0
        assert not meta["solved"]

    def test_maze_solver_bfs(self) -> None:
        """Verify BFS path solver finds a valid route from start to exit."""
        ast, meta = generate_maze_labyrinth(
            rows=10,
            cols=10,
            cell_size=20.0,
            algorithm=MazeAlgorithm.RECURSIVE_BACKTRACKER,
            seed=42,
            solve=True,
        )
        assert meta["solved"] is True
        solution = meta["solution_path"]
        assert len(solution) > 0
        assert solution[0] == [0, 0]
        assert solution[-1] == [9, 9]

        # Check that consecutive cells in solution are orthogonal neighbors
        for i in range(len(solution) - 1):
            r1, c1 = solution[i]
            r2, c2 = solution[i + 1]
            dist = abs(r1 - r2) + abs(c1 - c2)
            assert dist == 1, f"Path jumped non-adjacently from ({r1},{c1}) to ({r2},{c2})"

        # Verify green solution path segments exist in AST
        green_segs = [s for s in ast.segments if s.color == "#00ff66"]
        assert len(green_segs) > 0

    def test_maze_seed_determinism(self) -> None:
        """Verify same seed produces identical walls and solution path."""
        ast1, meta1 = generate_maze_labyrinth(rows=6, cols=6, seed=999, solve=True)
        ast2, meta2 = generate_maze_labyrinth(rows=6, cols=6, seed=999, solve=True)
        assert meta1["solution_path"] == meta2["solution_path"]
        assert meta1["wall_segments_count"] == meta2["wall_segments_count"]

    def test_maze_invalid_algo(self) -> None:
        """Verify invalid algorithm raises ValueError."""
        with pytest.raises(ValueError, match="Unknown MazeAlgorithm"):
            generate_maze_labyrinth(algorithm="quantum_teleportation")

    def test_ascii_maze_rendering(self) -> None:
        """Verify ASCII renderer outputs proper characters."""
        _, meta = generate_maze_labyrinth(rows=5, cols=5, seed=12, solve=True)
        ascii_art = render_ascii_maze(meta)
        assert "S" in ascii_art
        assert "E" in ascii_art
        assert "+" in ascii_art
        assert "-" in ascii_art
        assert "|" in ascii_art
        assert "*" in ascii_art  # Solved path marker


# =============================================================================
# 3. MCP Server Tool Tests
# =============================================================================

class TestMCPTruchetMazeTools:
    """Test MCP protocol tools for Truchet and Maze generation."""

    def test_mcp_turtle_generate_truchet(self) -> None:
        """Test turtle_generate_truchet via JSON-RPC 2.0."""
        server = MCPServer()
        req = {
            "jsonrpc": "2.0",
            "id": "test-truchet-1",
            "method": "tools/call",
            "params": {
                "name": "turtle_generate_truchet",
                "arguments": {
                    "rows": 5,
                    "cols": 5,
                    "tile_size": 30.0,
                    "style": "diagonal",
                    "seed": 100,
                },
            },
        }
        res = server.handle_jsonrpc_request(req)
        assert "result" in res
        content = res["result"]["content"]
        assert len(content) > 0
        parsed = json.loads(content[0]["text"])
        assert parsed["success"] is True
        assert parsed["style"] == "diagonal"
        assert parsed["rows"] == 5
        assert parsed["cols"] == 5
        assert "<svg" in parsed["svg"]

    def test_mcp_turtle_generate_maze(self) -> None:
        """Test turtle_generate_maze via JSON-RPC 2.0."""
        server = MCPServer()
        req = {
            "jsonrpc": "2.0",
            "id": "test-maze-1",
            "method": "tools/call",
            "params": {
                "name": "turtle_generate_maze",
                "arguments": {
                    "rows": 6,
                    "cols": 6,
                    "cell_size": 20.0,
                    "algorithm": "wilson",
                    "seed": 200,
                    "solve": True,
                },
            },
        }
        res = server.handle_jsonrpc_request(req)
        assert "result" in res
        content = res["result"]["content"]
        assert len(content) > 0
        parsed = json.loads(content[0]["text"])
        assert parsed["success"] is True
        assert parsed["solved"] is True
        assert parsed["solution_length"] > 0
        assert "<svg" in parsed["svg"]
        assert "S" in parsed["ascii"]


# =============================================================================
# 4. CLI Subcommand Tests
# =============================================================================

class TestCLITruchetMaze:
    """Test CLI commands for truchet and maze."""

    def test_cli_truchet_json(self, capsys: pytest.CaptureFixture) -> None:
        """Verify 'cyber-turtle truchet --format json' outputs valid JSON stats."""
        code = main(["truchet", "-r", "4", "-c", "4", "--style", "arcs", "--seed", "1", "-f", "json"])
        assert code == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["total_tiles"] == 16
        assert data["rows"] == 4
        assert data["cols"] == 4

    def test_cli_maze_ascii(self, capsys: pytest.CaptureFixture) -> None:
        """Verify 'cyber-turtle maze --ascii' renders ASCII grid."""
        code = main(["maze", "-r", "5", "-c", "5", "--algo", "braided", "--seed", "42", "--ascii"])
        assert code == 0
        captured = capsys.readouterr()
        assert "+" in captured.out
        assert "S" in captured.out
        assert "E" in captured.out

    def test_cli_maze_json(self, capsys: pytest.CaptureFixture) -> None:
        """Verify 'cyber-turtle maze -f json' outputs valid maze metadata."""
        code = main(["maze", "-r", "6", "-c", "6", "--solve", "-f", "json", "--seed", "10"])
        assert code == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["solved"] is True
        assert data["solution_length"] > 0


# =============================================================================
# 5. UI Server REST Endpoint Tests
# =============================================================================

@pytest.fixture
def live_server(free_port: int) -> Generator[str, None, None]:
    """Spin up live ThreadingHTTPServer in background thread for testing."""
    host = "127.0.0.1"
    port = free_port
    httpd = create_server(host, port)

    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.05)

    base_url = f"http://{host}:{port}"
    try:
        yield base_url
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=1.0)


def test_ui_server_truchet_get(live_server: str) -> None:
    """Verify GET /api/truchet produces valid JSON response."""
    req = urllib.request.Request(f"{live_server}/api/truchet?rows=4&cols=4&style=concentric_arcs&seed=42")
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["success"] is True
        assert data["style"] == "concentric_arcs"
        assert data["rows"] == 4
        assert "<svg" in data["svg"]


def test_ui_server_maze_post(live_server: str) -> None:
    """Verify POST /api/maze produces solved maze with SVG."""
    payload = json.dumps({
        "rows": 7,
        "cols": 7,
        "cell_size": 20.0,
        "algorithm": "recursive_backtracker",
        "seed": 55,
        "solve": True,
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{live_server}/api/maze",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["success"] is True
        assert data["solved"] is True
        assert data["solution_length"] > 0
        assert "<svg" in data["svg"]
        assert "S" in data["ascii"]
