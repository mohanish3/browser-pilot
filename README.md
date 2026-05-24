# browser-pilot

> Automate browsers from the command line — screenshot, click, fill forms, or record sessions interactively. Built on [Playwright](https://playwright.dev/python/).

```bash
pip install browser-pilot && playwright install chromium
```

```bash
# Screenshot any page in one command
browser-pilot --url https://example.com --screenshot out.png

# Click a link, then capture the result
browser-pilot --url https://example.com --click "text=More information" --screenshot after.png

# Fill a form and submit
browser-pilot --url https://example.com/search \
              --fill "input[name=q]=playwright" \
              --click "button[type=submit]" \
              --screenshot results.png
```

Or use it as a Python library:

```python
from browser_pilot import BrowserPilot

with BrowserPilot() as pilot:
    pilot.goto("https://example.com")
    pilot.click("text=More information")
    pilot.screenshot("result.png", full_page=True)
```

---

## Features

- Navigate to any URL
- Click elements by CSS selector, XPath, or visible text
- Fill and submit forms
- Take viewport or full-page screenshots (save to file or return bytes)
- Auto-timestamped screenshots
- **Record mode** — browse manually; a floating button captures screenshots on demand; full navigation history saved to `session.json`
- Works as a Python library **or** a CLI tool
- Supports Chromium, Firefox, and WebKit

## Install

```bash
pip install browser-pilot
playwright install chromium   # or: playwright install (all browsers)
```

## Record mode (interactive)

Open a real browser, browse freely, and click the floating **📸 Screenshot** button whenever you want to capture the current page. Every URL you visit is tracked. When you close the browser, a `session.json` log and all PNGs are saved to the output directory.

```bash
# Start recording from a URL
browser-pilot --record --url https://example.com

# Choose the output folder and browser
browser-pilot --record --url https://news.ycombinator.com --output my_session/ --browser firefox

# Start with a blank tab (navigate yourself)
browser-pilot --record
```

From Python:

```python
from browser_pilot import BrowserRecorder

recorder = BrowserRecorder(browser="chromium", output_dir="recordings")
session = recorder.record(start_url="https://example.com")

print(session["history"])      # list of {url, title, time}
print(session["screenshots"])  # list of {path, url, title, time}
```

`session.json` written on close:

```json
{
  "session": { "start": "2026-04-10 14:30:00", "end": "...", "browser": "chromium" },
  "history": [
    { "url": "https://example.com", "title": "Example Domain", "time": "14:30:05" }
  ],
  "screenshots": [
    { "path": "shot_001_20260410_143010.png", "url": "...", "title": "...", "time": "14:30:10" }
  ]
}
```

---

## CLI usage (automation)

```bash
# Screenshot a page
browser-pilot --url https://example.com --screenshot example.png

# Click a link by visible text, then screenshot
browser-pilot --url https://example.com \
              --click "text=More information" \
              --screenshot after_click.png

# Fill a form and submit
browser-pilot --url https://example.com/search \
              --fill "input[name=q]=playwright" \
              --click "button[type=submit]" \
              --screenshot results.png

# Full-page screenshot with Firefox (headed)
browser-pilot --url https://example.com \
              --browser firefox \
              --headed \
              --full-page \
              --screenshot full.png

# Run a custom Python script
browser-pilot --script examples/example.py
```

### All flags

| Flag | Default | Description |
|---|---|---|
| `--url URL` | — | URL to navigate to |
| `--record` | false | Open headed browser for manual recording |
| `--output DIR` | `recordings/` | Output directory for record mode |
| `--click SELECTOR` | — | Click an element (repeatable) |
| `--fill SELECTOR=VALUE` | — | Fill an input (repeatable) |
| `--wait MS` | — | Sleep N milliseconds |
| `--wait-for SELECTOR` | — | Wait until selector is visible |
| `--screenshot PATH` | auto | Save screenshot to path |
| `--full-page` | false | Capture full scrollable page |
| `--browser` | chromium | `chromium`, `firefox`, or `webkit` |
| `--headed` | false | Show browser window (automation mode) |
| `--slow-mo MS` | 0 | Delay between actions |
| `--timeout MS` | 30000 | Element wait timeout |
| `--script PATH` | — | Run a Python script |

## Python library usage

```python
from browser_pilot import BrowserPilot

with BrowserPilot(headless=True) as pilot:
    pilot.goto("https://example.com")

    # Click by text
    pilot.click("text=More information")

    # Fill a form
    pilot.fill("input[name=search]", "hello world")
    pilot.press("input[name=search]", "Enter")

    # Wait for results
    pilot.wait_for("#results")

    # Screenshot the viewport
    pilot.screenshot("viewport.png")

    # Full-page screenshot
    pilot.screenshot("full.png", full_page=True)

    # Screenshot a single element
    pilot.screenshot("header.png", element="header")

    # Auto-timestamped screenshot
    path = pilot.screenshot_timestamped("screenshots", prefix="run")
    print(path)  # e.g. screenshots/run_20260410_143022.png

    # Introspect the page
    print(pilot.url)
    print(pilot.title)
    print(pilot.text("h1"))
```

### Script mode

Pass a `.py` file to `--script`. It receives the `BrowserPilot` instance as `pilot`:

```python
# my_script.py
pilot.goto("https://news.ycombinator.com")
pilot.screenshot("hn.png", full_page=True)
```

```bash
browser-pilot --script my_script.py
```

## Development

```bash
git clone https://github.com/mohanish3/browser-pilot
cd browser-pilot
pip install -e ".[dev]"
playwright install chromium
pytest
```

## License

MIT
