"""BrowserPilot — CLI Playwright wrapper for browser automation."""

from .core import BrowserPilot
from .recorder import BrowserRecorder
from .mcp import mcp, start_mcp_server

__all__ = ["BrowserPilot", "BrowserRecorder", "mcp", "start_mcp_server"]
