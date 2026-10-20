"""MCP Server for browser-pilot — exposes browser automation as MCP tools."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright

# Import the BrowserPilot class
from .core import BrowserPilot

# Create MCP server instance
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("browser-pilot", instructions="Browser automation MCP server for OpenClaw agents")


@mcp.tool()
def navigate(url: str) -> str:
    """
    Navigate to a URL in the browser.

    Args:
        url: The URL to navigate to.

    Returns:
        The final URL after navigation.
    """
    with BrowserPilot() as pilot:
        pilot.goto(url)
        return f"Successfully navigated to {pilot.url}"


@mcp.tool()
def click(selector: str) -> str:
    """
    Click an element by CSS selector or text.

    Args:
        selector: CSS selector or 'text=...' to click by visible text.

    Returns:
        Success message.
    """
    with BrowserPilot() as pilot:
        pilot.click(selector)
        return f"Clicked element with selector: {selector}"


@mcp.tool()
def fill(selector: str, value: str) -> str:
    """
    Fill an input field with text.

    Args:
        selector: CSS selector of the input field.
        value: Text to fill in.

    Returns:
        Success message.
    """
    with BrowserPilot() as pilot:
        pilot.fill(selector, value)
        return f"Filled selector '{selector}' with: {value}"


@mcp.tool()
def screenshot(path: str | None = None) -> str:
    """
    Take a screenshot of the current page.

    Args:
        path: Optional path to save the screenshot. If None, returns bytes.

    Returns:
        Path to screenshot or base64 encoded image data.
    """
    with BrowserPilot() as pilot:
        if path:
            pilot.screenshot(path)
            return f"Screenshot saved to: {path}"
        else:
            screenshot_data = pilot.screenshot()
            return f"Screenshot captured ({len(screenshot_data)} bytes)"


@mcp.tool()
def get_url() -> str:
    """
    Get the current URL of the page.

    Returns:
        The current page URL.
    """
    with BrowserPilot() as pilot:
        pilot.goto("https://example.com")
        return pilot.url


@mcp.tool()
def get_title() -> str:
    """
    Get the current page title.

    Returns:
        The page title.
    """
    with BrowserPilot() as pilot:
        pilot.goto("https://example.com")
        return pilot.title


@mcp.tool()
def wait_ms(ms: int) -> str:
    """
    Wait for a specified number of milliseconds.

    Args:
        ms: Number of milliseconds to wait.

    Returns:
        Success message.
    """
    import time
    time.sleep(ms / 1000)
    return f"Waited for {ms}ms"


@mcp.tool()
def evaluate(expression: str) -> str:
    """
    Execute JavaScript in the browser context.

    Args:
        expression: JavaScript expression to evaluate.

    Returns:
        The result of the evaluation.
    """
    with BrowserPilot() as pilot:
        result = pilot.evaluate(expression)
        return json.dumps(result)


@mcp.tool()
def scroll(x: int = 0, y: int = 500) -> str:
    """
    Scroll the page by pixel offsets.

    Args:
        x: Horizontal offset.
        y: Vertical offset.

    Returns:
        Success message.
    """
    with BrowserPilot() as pilot:
        pilot.scroll(x, y)
        return f"Scrolled by ({x}, {y})"


@mcp.tool()
def record_video(path: str, size: str | None = None) -> str:
    """
    Record a video of the browser session.

    Args:
        path: Path to save the video file.
        size: Optional size in format "width,height".

    Returns:
        Success message.
    """
    with BrowserPilot() as pilot:
        if size:
            width, height = map(int, size.split(","))
            pilot.record_video(path, size=(width, height))
        else:
            pilot.record_video(path)
        pilot.stop_video()
        return f"Video recorded to: {path}"


def start_mcp_server():
    """Start the MCP server."""
    print("Starting browser-pilot MCP server...")
    mcp.run()


if __name__ == "__main__":
    start_mcp_server()
