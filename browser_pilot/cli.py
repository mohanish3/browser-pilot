"""
BrowserPilot CLI — run automation sequences from the command line.

Examples:
    browser-pilot --url https://example.com --screenshot shot.png
    browser-pilot --url https://example.com --click "text=More information" --screenshot after.png
    browser-pilot --script my_script.py

    # Interactive record mode — opens a real browser; click the floating button to screenshot
    browser-pilot --record
    browser-pilot --record --url https://example.com --output recordings/

    # MCP server mode
    browser-pilot --mcp

    # Session persistence
    browser-pilot --url https://example.com --session ./my-session
"""

import argparse
import sys
from pathlib import Path

from .core import BrowserPilot
from .recorder import BrowserRecorder


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="browser-pilot",
        description="Navigate pages, click elements, and take screenshots.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # Target
    p.add_argument("--url", metavar="URL", help="URL to navigate to first.")

    # Actions (executed in order they appear)
    p.add_argument(
        "--click",
        metavar="SELECTOR",
        action="append",
        default=[],
        help="Click an element (CSS selector or 'text=…'). Repeatable.",
    )
    p.add_argument(
        "--fill",
        metavar="SELECTOR=VALUE",
        action="append",
        default=[],
        help="Fill an input field. Format: 'selector=value'. Repeatable.",
    )
    p.add_argument(
        "--wait",
        metavar="MS",
        type=int,
        help="Wait for N milliseconds before taking the screenshot.",
    )
    p.add_argument(
        "--wait-for",
        metavar="SELECTOR",
        dest="wait_for",
        help="Wait until this selector is visible before screenshotting.",
    )

    # Screenshot
    p.add_argument(
        "--screenshot",
        metavar="PATH",
        help="Save a screenshot to PATH (PNG).",
    )
    p.add_argument(
        "--full-page",
        action="store_true",
        help="Capture the full scrollable page.",
    )

    # Browser settings
    p.add_argument(
        "--browser",
        choices=["chromium", "firefox", "webkit"],
        default="chromium",
        help="Browser engine (default: chromium).",
    )
    p.add_argument(
        "--headed",
        action="store_true",
        help="Run with a visible browser window.",
    )
    p.add_argument(
        "--slow-mo",
        metavar="MS",
        type=int,
        default=0,
        dest="slow_mo",
        help="Add N ms delay between actions (useful for debugging).",
    )
    p.add_argument(
        "--timeout",
        metavar="MS",
        type=int,
        default=30_000,
        help="Element wait timeout in milliseconds (default: 30000).",
    )

    # Script mode
    p.add_argument(
        "--script",
        metavar="PATH",
        help="Run a Python script that receives a BrowserPilot instance as `pilot`.",
    )

    # Record mode
    p.add_argument(
        "--record",
        action="store_true",
        help=(
            "Open a headed browser for manual browsing. "
            "A floating button lets you capture screenshots on demand. "
            "Navigation history and screenshots are saved to --output."
        ),
    )
    p.add_argument(
        "--output",
        metavar="DIR",
        default="recordings",
        help="Directory to save recorded screenshots and session log (default: recordings/).",
    )

    # Video recording
    p.add_argument(
        "--video",
        metavar="PATH",
        help="Record a video of the browser session to PATH.",
    )
    p.add_argument(
        "--video-size",
        metavar="WIDTH,HEIGHT",
        help="Size for video recording (e.g., 1920,1080).",
    )

    # Session persistence
    p.add_argument(
        "--session",
        metavar="DIR",
        help="Use session directory for cookie/state persistence.",
    )

    # MCP server mode
    p.add_argument(
        "--mcp",
        action="store_true",
        help="Run as MCP (Model Context Protocol) server for OpenClaw agents.",
    )

    # Info
    p.add_argument("--version", action="version", version="%(prog)s 0.1.0")

    return p


def run_script(path: str, pilot: BrowserPilot) -> None:
    script = Path(path).read_text(encoding="utf-8")
    exec(compile(script, path, "exec"), {"pilot": pilot})  # noqa: S102


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)

    # ------------------------------------------------------------------
    # MCP server mode
    # ------------------------------------------------------------------
    if args.mcp:
        from .mcp import start_mcp_server
        start_mcp_server()
        return 0

    # ------------------------------------------------------------------
    # Record mode with optional video recording
    # ------------------------------------------------------------------
    if args.record:
        recorder = BrowserRecorder(
            browser=args.browser,
            output_dir=args.output,
        )
        recorder.record(start_url=args.url or None)
        return 0

    # ------------------------------------------------------------------
    # Automation mode
    # ------------------------------------------------------------------
    if not args.url and not args.script:
        print("error: provide --url, --script, or --record", file=sys.stderr)
        return 1

    with BrowserPilot(
        browser=args.browser,
        headless=not args.headed,
        slow_mo=args.slow_mo,
        timeout=args.timeout,
        session_dir=args.session,
    ) as pilot:
        # Handle video recording
        if args.video:
            size = None
            if args.video_size:
                try:
                    width, height = map(int, args.video_size.split(","))
                    size = (width, height)
                except ValueError:
                    print(f"error: --video-size expects 'WIDTH,HEIGHT', got: {args.video_size!r}", file=sys.stderr)
                    return 1
            pilot.record_video(args.video, size=size)
            pilot.stop_video()

        if args.script:
            run_script(args.script, pilot)
            return 0

        if args.url:
            pilot.goto(args.url)

        # Process --fill before --click so forms can be filled then submitted
        for pair in args.fill:
            if "=" not in pair:
                print(f"error: --fill expects 'selector=value', got: {pair!r}", file=sys.stderr)
                return 1
            sel, _, value = pair.partition("=")
            pilot.fill(sel.strip(), value)

        for selector in args.click:
            pilot.click(selector)

        if args.wait:
            pilot.wait(args.wait)

        if args.wait_for:
            pilot.wait_for(args.wait_for)

        if args.screenshot:
            pilot.screenshot(args.screenshot, full_page=args.full_page)
            print(f"Screenshot saved: {args.screenshot}")
        else:
            path = pilot.screenshot_timestamped()
            print(f"Screenshot saved: {path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
