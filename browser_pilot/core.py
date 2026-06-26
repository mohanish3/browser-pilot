"""Core BrowserPilot class wrapping Playwright."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Literal

from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext, Playwright


class BrowserPilot:
    """
    Synchronous browser automation: navigate, click, type, and screenshot.

    Usage as context manager (recommended):
        with BrowserPilot() as pilot:
            pilot.goto("https://example.com")
            pilot.screenshot("example.png")

    Or manual lifecycle:
        pilot = BrowserPilot()
        pilot.start()
        pilot.goto("https://example.com")
        pilot.stop()
    """

    def __init__(
        self,
        browser: Literal["chromium", "firefox", "webkit"] = "chromium",
        headless: bool = True,
        slow_mo: int = 0,
        viewport: tuple[int, int] = (1280, 720),
        timeout: int = 30_000,
        session_dir: str | Path | None = None,
    ) -> None:
        self.browser_type = browser
        self.headless = headless
        self.slow_mo = slow_mo
        self.viewport = {"width": viewport[0], "height": viewport[1]}
        self.timeout = timeout
        self.session_dir = session_dir

        self._pw: Playwright | None = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> "BrowserPilot":
        self._pw = sync_playwright().start()
        launcher = getattr(self._pw, self.browser_type)
        self._browser = launcher.launch(headless=self.headless, slow_mo=self.slow_mo)
        
        # Handle session persistence
        if self.session_dir:
            session_dir = Path(self.session_dir)
            session_dir.mkdir(parents=True, exist_ok=True)
            cookie_file = session_dir / "cookies.json"
            if cookie_file.exists():
                cookies_data = cookie_file.read_text(encoding="utf-8")
                cookies = json.loads(cookies_data)
                self._context = self._browser.new_context(
                    viewport=self.viewport,
                    storage_state=cookies
                )
                self._context.set_default_timeout(self.timeout)
            else:
                self._context = self._browser.new_context(viewport=self.viewport)
                self._context.set_default_timeout(self.timeout)
        else:
            self._context = self._browser.new_context(viewport=self.viewport)
            self._context.set_default_timeout(self.timeout)
        
        self._page = self._context.new_page()
        return self

    def stop(self) -> None:
        # Save session before stopping
        if self.session_dir and self._context:
            session_dir = Path(self.session_dir)
            session_dir.mkdir(parents=True, exist_ok=True)
            cookie_file = session_dir / "cookies.json"
            storage_state = self._context.storage_state()
            if storage_state:
                cookie_file.write_text(
                    json.dumps(storage_state, indent=2),
                    encoding="utf-8"
                )
        
        if self._context:
            self._context.close()
        if self._browser:
            self._browser.close()
        if self._pw:
            self._pw.stop()
        self._page = self._context = self._browser = self._pw = None

    def __enter__(self) -> "BrowserPilot":
        return self.start()

    def __exit__(self, *_) -> None:
        self.stop()

    @property
    def page(self) -> Page:
        if self._page is None:
            raise RuntimeError("BrowserPilot not started. Call .start() or use as context manager.")
        return self._page

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def goto(self, url: str, wait_until: str = "domcontentloaded") -> "BrowserPilot":
        """Navigate to a URL."""
        self.page.goto(url, wait_until=wait_until)
        return self

    def back(self) -> "BrowserPilot":
        self.page.go_back()
        return self

    def forward(self) -> "BrowserPilot":
        self.page.go_forward()
        return self

    def reload(self) -> "BrowserPilot":
        self.page.reload()
        return self

    # ------------------------------------------------------------------
    # Interaction
    # ------------------------------------------------------------------

    def click(
        self,
        selector: str,
        *,
        button: Literal["left", "right", "middle"] = "left",
        timeout: int | None = None,
    ) -> "BrowserPilot":
        """Click an element by CSS selector, XPath, or text (e.g. 'text=Submit')."""
        self.page.click(selector, button=button, timeout=timeout or self.timeout)
        return self

    def click_at(self, x: int, y: int) -> "BrowserPilot":
        """Click at absolute page coordinates."""
        self.page.mouse.click(x, y)
        return self

    def type(self, selector: str, text: str, delay: int = 50) -> "BrowserPilot":
        """Type text into an input element."""
        self.page.type(selector, text, delay=delay)
        return self

    def fill(self, selector: str, value: str) -> "BrowserPilot":
        """Fill an input (clears existing value first)."""
        self.page.fill(selector, value)
        return self

    def press(self, selector: str, key: str) -> "BrowserPilot":
        """Press a key while an element is focused (e.g. 'Enter', 'Tab')."""
        self.page.press(selector, key)
        return self

    def hover(self, selector: str) -> "BrowserPilot":
        self.page.hover(selector)
        return self

    def scroll(self, x: int = 0, y: int = 500) -> "BrowserPilot":
        """Scroll the page by (x, y) pixels."""
        self.page.mouse.wheel(x, y)
        return self

    def wait(self, ms: int) -> "BrowserPilot":
        """Pause execution for a fixed number of milliseconds."""
        time.sleep(ms / 1000)
        return self

    def wait_for(self, selector: str, state: str = "visible") -> "BrowserPilot":
        """Wait until an element reaches a given state ('visible', 'hidden', 'attached')."""
        self.page.wait_for_selector(selector, state=state, timeout=self.timeout)
        return self

    def wait_for_url(self, url_pattern: str) -> "BrowserPilot":
        self.page.wait_for_url(url_pattern, timeout=self.timeout)
        return self

    # ------------------------------------------------------------------
    # Screenshots
    # ------------------------------------------------------------------

    def screenshot(
        self,
        path: str | Path | None = None,
        *,
        full_page: bool = False,
        element: str | None = None,
    ) -> bytes:
        """
        Capture a screenshot.

        Args:
            path: File path to save the image (PNG/JPEG detected by extension).
                  If None, returns raw bytes without saving.
            full_page: Capture the full scrollable page.
            element:   CSS selector — capture only this element.

        Returns:
            PNG bytes of the screenshot.
        """
        kwargs: dict = {"full_page": full_page}
        if path:
            kwargs["path"] = str(path)

        if element:
            loc = self.page.locator(element)
            return loc.screenshot(**kwargs)

        return self.page.screenshot(**kwargs)

    def screenshot_timestamped(
        self,
        directory: str | Path = "screenshots",
        prefix: str = "shot",
        full_page: bool = False,
    ) -> Path:
        """Save a screenshot with a timestamp filename and return the path."""
        directory = Path(directory)
        ts = time.strftime("%Y%m%d_%H%M%S")
        path = directory / f"{prefix}_{ts}.png"
        self.screenshot(path, full_page=full_page)
        return path

    # ------------------------------------------------------------------
    # Video Recording
    # ------------------------------------------------------------------

    def record_video(
        self,
        path: str | Path,
        *,
        size: tuple[int, int] | None = None,
        screen: bool = False,
    ) -> "BrowserPilot":
        """
        Record a video of the browser session.

        Args:
            path: Path to save the video file.
            size: Optional video size (width, height). If None, uses viewport.
            screen: If True, record the entire screen instead of just the browser.

        Returns:
            Self for method chaining.
        """
        if screen:
            self.page.screencast(str(path))
        else:
            self._page.video = self.page.context.new_video_path(str(path))
        return self

    def stop_video(self) -> "BrowserPilot":
        """Stop recording and save the video file."""
        if self._page:
            self._page.stop_screencast()
        return self

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    @property
    def url(self) -> str:
        return self.page.url

    @property
    def title(self) -> str:
        return self.page.title()

    def text(self, selector: str) -> str:
        """Return the inner text of the first matching element."""
        return self.page.inner_text(selector)

    def attr(self, selector: str, name: str) -> str | None:
        """Return an attribute value from the first matching element."""
        return self.page.get_attribute(selector, name)

    def evaluate(self, expression: str):
        """Execute JavaScript and return the result."""
        return self.page.evaluate(expression)

    def exists(self, selector: str) -> bool:
        """Return True if at least one element matches the selector."""
        return self.page.locator(selector).count() > 0
