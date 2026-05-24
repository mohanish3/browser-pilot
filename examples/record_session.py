"""
Example: start a recording session from Python.

Run with:
    python examples/record_session.py

A browser window opens. Navigate to any pages you like, then click the
floating '📸 Screenshot' button to capture the current view.
Close the browser window when done — a session.json log is written to
the output directory.
"""

from browser_pilot import BrowserRecorder

recorder = BrowserRecorder(
    browser="chromium",
    output_dir="recordings",
)

session = recorder.record(start_url="https://news.ycombinator.com")

print(f"\nVisited {len(session['history'])} pages.")
print(f"Saved   {len(session['screenshots'])} screenshots.")
