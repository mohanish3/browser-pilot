"""
Regression tests: mcp 2.x compatibility.

The venv ships mcp 2.3.0.  pyproject declares ``mcp>=1.0.0`` which resolves to
2.x, but browser_pilot/mcp.py imported ``mcp.server.fastmcp.FastMCP`` — a name
that does not exist in 2.x (renamed to ``MCPServer`` in ``mcp.server.mcpserver``).

Because ``browser_pilot/__init__.py`` imports ``.mcp`` at package-import time,
the bug made **every** ``from browser_pilot import BrowserPilot`` and the
``browser-pilot`` CLI entry point crash with:

    ModuleNotFoundError: No module named 'mcp.server.fastmcp'

These tests reproduce that failure and verify the fix.
"""

from __future__ import annotations

import asyncio
import importlib
import sys
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# 1. Package-level import must not raise
# ---------------------------------------------------------------------------

class TestPackageImport:
    """The package must import cleanly even when mcp 2.x is installed."""

    def test_import_browser_pilot(self):
        """``import browser_pilot`` must succeed."""
        # Remove any cached module so we test a fresh import
        for mod in list(sys.modules):
            if mod.startswith("browser_pilot"):
                del sys.modules[mod]
        import browser_pilot  # noqa: F401

    def test_import_browser_pilot_submodules(self):
        """All public submodules must import."""
        for mod in list(sys.modules):
            if mod.startswith("browser_pilot"):
                del sys.modules[mod]
        from browser_pilot import BrowserPilot, BrowserRecorder  # noqa: F401
        from browser_pilot import mcp, start_mcp_server  # noqa: F401
        from browser_pilot.core import BrowserPilot as BP2  # noqa: F401
        from browser_pilot.recorder import BrowserRecorder as BR2  # noqa: F401
        from browser_pilot.cli import build_parser, main  # noqa: F401
        from browser_pilot.mcp import mcp as m  # noqa: F401

    def test_mcp_server_instance_exists(self):
        """The module-level ``mcp`` object must be a real server instance."""
        for mod in list(sys.modules):
            if mod.startswith("browser_pilot"):
                del sys.modules[mod]
        from browser_pilot.mcp import mcp
        assert mcp is not None
        assert type(mcp).__name__ in ("FastMCP", "MCPServer")

    def test_mcp_server_name_and_instructions(self):
        """The server must be constructed with the expected name/instructions."""
        from browser_pilot.mcp import mcp
        # v1 FastMCP stores name in .name; v2 MCPServer also has .name
        assert hasattr(mcp, "name")


# ---------------------------------------------------------------------------
# 2. Tools must be registered on the server
# ---------------------------------------------------------------------------

class TestToolRegistration:
    """All @mcp.tool()-decorated functions must appear in the tool list."""

    EXPECTED_TOOLS = {
        "navigate",
        "click",
        "fill",
        "screenshot",
        "get_url",
        "get_title",
        "wait_ms",
        "evaluate",
        "scroll",
        "record_video",
    }

    def test_all_tools_registered(self):
        from browser_pilot.mcp import mcp
        tools = asyncio.run(mcp.list_tools())
        names = {t.name for t in tools}
        assert self.EXPECTED_TOOLS == names, (
            f"Expected {self.EXPECTED_TOOLS} but got {names}"
        )

    def test_tool_count(self):
        from browser_pilot.mcp import mcp
        tools = asyncio.run(mcp.list_tools())
        assert len(tools) == 10


# ---------------------------------------------------------------------------
# 3. A safe tool must be callable end-to-end (no real browser needed)
# ---------------------------------------------------------------------------

class TestToolCallable:
    """call_tool on a browser-free tool must return a valid result."""

    def test_call_wait_ms(self):
        from browser_pilot.mcp import mcp
        result = asyncio.run(mcp.call_tool("wait_ms", {"ms": 1}))
        assert result.is_error is False
        # The text content should mention the wait
        texts = [c.text for c in result.content if hasattr(c, "text")]
        assert any("1ms" in t for t in texts)

    def test_scroll_tool_schema(self):
        """The scroll tool must be registered with the documented parameters.

        (scroll is *not* invoked via call_tool here because it launches a real
        browser; we only verify its registration/schema.)
        """
        from browser_pilot.mcp import mcp
        tools = asyncio.run(mcp.list_tools())
        scroll = next(t for t in tools if t.name == "scroll")
        schema = getattr(scroll, "input_schema", None) or getattr(scroll, "inputSchema", None)
        assert schema is not None, "scroll tool has no input schema"
        props = schema.get("properties", {})
        assert "x" in props and "y" in props


# ---------------------------------------------------------------------------
# 4. CLI must be importable and parse args
# ---------------------------------------------------------------------------

class TestCLIImport:
    """The CLI module must import and parse arguments after the fix."""

    def test_build_parser(self):
        from browser_pilot.cli import build_parser
        p = build_parser()
        assert p.prog == "browser-pilot"

    def test_cli_no_args_exits_1(self):
        """Running main() with no args should exit 1 (not crash)."""
        from browser_pilot.cli import main
        import io
        import contextlib
        f = io.StringIO()
        with contextlib.redirect_stderr(f):
            rc = main([])
        assert rc == 1
        assert "error" in f.getvalue().lower()


# ---------------------------------------------------------------------------
# 5. Guard: the original bug must NOT be present
# ---------------------------------------------------------------------------

class TestNoFastMCPImportError:
    """Ensure the specific ModuleNotFoundError from the original bug is gone."""

    def test_no_fastmcp_modulenotfound(self):
        """Importing mcp sub-module must not raise ModuleNotFoundError for fastmcp."""
        for mod in list(sys.modules):
            if mod.startswith("browser_pilot"):
                del sys.modules[mod]
        try:
            importlib.import_module("browser_pilot.mcp")
        except ModuleNotFoundError as e:
            pytest.fail(
                f"browser_pilot.mcp raised ModuleNotFoundError: {e}. "
                "This is the original mcp 2.x compatibility bug."
            )
