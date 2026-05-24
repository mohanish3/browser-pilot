"""
Example: navigate to Wikipedia, click a link, and capture a full-page screenshot.

Run with:
    python examples/example.py
or via the CLI:
    browser-pilot --script examples/example.py
"""

from browser_pilot import BrowserPilot

with BrowserPilot(headless=True) as pilot:
    # Navigate
    pilot.goto("https://en.wikipedia.org/wiki/Python_(programming_language)")

    # Wait until the content area is loaded
    pilot.wait_for("#mw-content-text")

    # Screenshot the landing page
    landing = pilot.screenshot_timestamped("screenshots", prefix="wikipedia_landing")
    print(f"Landing: {landing} — {pilot.title}")

    # Click the first internal link inside the article body
    pilot.click("#mw-content-text a[href^='/wiki/']:first-of-type")
    pilot.wait_for("#mw-content-text")

    # Screenshot the new page
    dest = pilot.screenshot_timestamped("screenshots", prefix="wikipedia_dest")
    print(f"Destination: {dest} — {pilot.title} ({pilot.url})")
