"""
BrowserRecorder — open a real browser, let the user navigate freely,
and capture screenshots on demand via an injected floating button.

Python polls a JS flag so there are no threading/greenlet issues with
calling page.screenshot() from within an expose_function callback.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Literal

from playwright.sync_api import sync_playwright

# ---------------------------------------------------------------------------
# Injected overlay — runs on every page load via context.add_init_script()
# ---------------------------------------------------------------------------

_OVERLAY_JS = """
(function () {
    function injectButton() {
        if (document.getElementById('__bp_overlay')) return;
        if (!document.body) return;

        var wrap = document.createElement('div');
        wrap.id = '__bp_overlay';
        wrap.style.cssText = [
            'position:fixed',
            'bottom:20px',
            'right:20px',
            'z-index:2147483647',
            'font-family:system-ui,sans-serif',
            'display:flex',
            'flex-direction:column',
            'align-items:flex-end',
            'gap:8px',
            'pointer-events:none',
        ].join(';');

        // --- counter badge ---
        var badge = document.createElement('div');
        badge.id = '__bp_badge';
        badge.style.cssText = [
            'background:#0f0f23',
            'color:#aaa',
            'border:1.5px solid rgba(255,255,255,0.12)',
            'border-radius:6px',
            'padding:3px 9px',
            'font-size:11px',
            'display:none',
            'pointer-events:none',
        ].join(';');

        // --- screenshot button ---
        var btn = document.createElement('button');
        btn.id = '__bp_btn';
        btn.textContent = '📸  Screenshot';
        btn.style.cssText = [
            'padding:10px 18px',
            'background:#0f0f23',
            'color:#fff',
            'border:1.5px solid rgba(255,255,255,0.15)',
            'border-radius:10px',
            'font-size:13px',
            'font-weight:500',
            'cursor:pointer',
            'box-shadow:0 4px 18px rgba(0,0,0,0.45)',
            'transition:background 0.15s,transform 0.1s',
            'white-space:nowrap',
            'pointer-events:auto',
        ].join(';');

        btn.addEventListener('mouseenter', function () { btn.style.background = '#1e1e42'; });
        btn.addEventListener('mouseleave', function () { btn.style.background = '#0f0f23'; });
        btn.addEventListener('mousedown', function () { btn.style.transform = 'scale(0.96)'; });
        btn.addEventListener('mouseup',   function () { btn.style.transform = 'scale(1)'; });

        btn.addEventListener('click', function () {
            if (btn.disabled) return;
            btn.disabled = true;
            btn.textContent = '⏳  Saving…';

            window.__bp_screenshot = { url: location.href, title: document.title };

            var poll = setInterval(function () {
                if (window.__bp_done) {
                    clearInterval(poll);
                    window.__bp_done = false;

                    var count = (window.__bp_count || 0) + 1;
                    window.__bp_count = count;

                    btn.textContent = '✅  Saved!';
                    badge.style.display = 'block';
                    badge.textContent = count + ' screenshot' + (count === 1 ? '' : 's') + ' taken';

                    setTimeout(function () {
                        btn.textContent = '📸  Screenshot';
                        btn.disabled = false;
                    }, 1800);
                }
            }, 80);
        });

        wrap.appendChild(badge);
        wrap.appendChild(btn);
        document.body.appendChild(wrap);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', injectButton);
    } else {
        injectButton();
    }
})();
"""


class BrowserRecorder:
    """
    Open a headed browser session, track every page the user visits,
    and let them click a floating button to capture timestamped screenshots.

    Results are saved to `output_dir`:
        - PNG screenshots
        - session.json  (full history + screenshot metadata)

    Usage:
        recorder = BrowserRecorder()
        recorder.record("https://example.com")
    """

    def __init__(
        self,
        browser: Literal["chromium", "firefox", "webkit"] = "chromium",
        output_dir: str | Path = "recordings",
        viewport: tuple[int, int] = (1280, 800),
    ) -> None:
        self.browser_type = browser
        self.output_dir = Path(output_dir)
        self.viewport = {"width": viewport[0], "height": viewport[1]}

        self._history: list[dict] = []
        self._screenshots: list[dict] = []
        self._shot_count = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def record(self, start_url: str | None = None) -> dict:
        """
        Open the browser and block until the window is closed.

        Returns a session dict with 'history' and 'screenshots'.
        """
        self.output_dir.mkdir(parents=True, exist_ok=True)
        session_start = time.strftime("%Y-%m-%d %H:%M:%S")

        print(f"\nBrowserPilot recorder started  ({self.browser_type})")
        print(f"Output directory : {self.output_dir.resolve()}")
        if start_url:
            print(f"Starting URL     : {start_url}")
        print("\nNavigate freely. Click the '📸 Screenshot' button to capture any page.")
        print("Close the browser window when you are done.\n")

        with sync_playwright() as pw:
            browser = getattr(pw, self.browser_type).launch(headless=False)
            context = browser.new_context(viewport=self.viewport)
            context.add_init_script(_OVERLAY_JS)
            page = context.new_page()

            # Track every navigation
            def _on_load(p):
                try:
                    url = p.url
                    title = p.title()
                except Exception:
                    return
                if url in ("about:blank", ""):
                    return
                ts = time.strftime("%H:%M:%S")
                self._history.append({"url": url, "title": title, "time": ts})
                print(f"  [visit]      {ts}  {title or url}")

            page.on("load", _on_load)

            if start_url:
                page.goto(start_url, wait_until="domcontentloaded")

            # Poll loop — avoids threading issues with page.screenshot()
            while True:
                if page.is_closed():
                    break
                try:
                    data = page.evaluate(
                        "(() => { var d = window.__bp_screenshot;"
                        " if (d) { window.__bp_screenshot = null; return d; }"
                        " return null; })()"
                    )
                except Exception:
                    break  # page or browser closed mid-evaluate

                if data:
                    path = self._save_screenshot(page, data.get("url", ""), data.get("title", ""))
                    try:
                        page.evaluate("window.__bp_done = true;")
                    except Exception:
                        pass
                    print(f"  [screenshot] {path.name}  —  {data.get('title', '')}")

                time.sleep(0.1)

            try:
                context.close()
                browser.close()
            except Exception:
                pass

        session_end = time.strftime("%Y-%m-%d %H:%M:%S")
        result = self._build_session(session_start, session_end)
        self._save_log(result)
        self._print_summary(result)
        return result

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _save_screenshot(self, page, url: str, title: str) -> Path:
        self._shot_count += 1
        ts = time.strftime("%Y%m%d_%H%M%S")
        filename = f"shot_{self._shot_count:03d}_{ts}.png"
        path = self.output_dir / filename
        page.screenshot(path=str(path))
        self._screenshots.append({
            "path": filename,
            "url": url,
            "title": title,
            "time": time.strftime("%H:%M:%S"),
        })
        return path

    def _build_session(self, start: str, end: str) -> dict:
        return {
            "session": {
                "start": start,
                "end": end,
                "browser": self.browser_type,
                "output_dir": str(self.output_dir.resolve()),
            },
            "history": self._history,
            "screenshots": self._screenshots,
        }

    def _save_log(self, result: dict) -> None:
        log_path = self.output_dir / "session.json"
        log_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"\nSession log saved: {log_path}")

    def _print_summary(self, result: dict) -> None:
        history = result["history"]
        shots = result["screenshots"]
        print(f"\n{'─' * 52}")
        print(f"Session   {result['session']['start']}  →  {result['session']['end']}")
        print(f"Pages visited  : {len(history)}")
        print(f"Screenshots    : {len(shots)}")
        if shots:
            print("\nScreenshots:")
            for s in shots:
                print(f"  {s['path']}  [{s['time']}]  {s['title']}")
        print(f"{'─' * 52}\n")
