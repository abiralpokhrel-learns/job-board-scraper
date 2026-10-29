"""Dynamic (JS-rendered) scraping with Playwright.

Implemented 2026-10-28, verified only against a LOCAL fixture page
that injects its listings with JavaScript (see
``tests/dynamic_listings.html``). It has NOT been run against any
live board: no live data, no board scraped yet.

Shape, deliberately the same as the static path in
``scraper/collect.py``: fetch rendered HTML -> reuse
``collect.parse_listings`` on that HTML -> same dedupe on URL.
The only difference is how the HTML is obtained (a real browser
waiting for the listing selector, instead of ``requests``).

Before pointing this at a live board: read that board's
``robots.txt`` and terms, scrape only what they allow, only public
listings, never log in, never bypass a check, keep the delay >= 1s
and ``MAX_PAGES`` small. Fill in ``SOURCE_URL`` / ``SELECTORS`` in
``scraper/config.py`` first — live mode refuses to run with the
placeholder defaults.
"""

import argparse
import json
import os
import time

from . import config
from .collect import parse_listings


def _chromium_executable_path(executable_path):
    """Return an explicit Chromium path, or None for Playwright's default.

    Priority: explicit argument > PLAYWRIGHT_CHROMIUM_PATH env var >
    config.CHROMIUM_EXECUTABLE_PATH > None (``playwright install
    chromium`` browser). This environment's system Chromium was
    verified at /opt/meta-chromium/chrome on 2026-10-28; a normal
    machine should use the Playwright-managed browser instead.
    """
    return (
        executable_path
        or os.environ.get("PLAYWRIGHT_CHROMIUM_PATH")
        or getattr(config, "CHROMIUM_EXECUTABLE_PATH", "")
        or None
    )


def fetch_rendered(url, card_selector, *, executable_path=None, timeout_ms=30000):
    """Return the rendered HTML of *url* after *card_selector* appears.

    Raises if Playwright is not installed or the selector never
    appears (e.g. the board's markup changed or the page blocked
    the browser) — a failure here is a signal, not something to
    work around by hammering the site.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:  # pragma: no cover - environment setup
        raise SystemExit(
            "Playwright is not installed: pip install -r requirements.txt "
            "and install a browser (playwright install chromium)."
        ) from exc

    launch_kwargs = {"args": ["--no-sandbox"]}
    path = _chromium_executable_path(executable_path)
    if path:
        launch_kwargs["executable_path"] = path

    with sync_playwright() as p:
        browser = p.chromium.launch(**launch_kwargs)
        try:
            page = browser.new_page(user_agent=config.USER_AGENT)
            page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            page.wait_for_selector(card_selector, timeout=timeout_ms)
            return page.content()
        finally:
            browser.close()


def collect_rendered(url, selectors, *, executable_path=None, delay_seconds=None):
    """Fetch one rendered page and parse it with the shared parser."""
    html = fetch_rendered(url, selectors["card"], executable_path=executable_path)
    if delay_seconds is None:
        delay_seconds = config.REQUEST_DELAY_SECONDS
    if delay_seconds:
        time.sleep(delay_seconds)
    return parse_listings(html, selectors, base_url=url)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Collect listings from a JS-rendered board (or a local fixture URL)."
    )
    parser.add_argument("--url", required=True, help="Page URL (http(s), or a local file:// fixture)")
    parser.add_argument("--out", required=True, help="Output JSONL path")
    parser.add_argument("--chromium-path", default=None, help="Chromium executable (default: Playwright's browser)")
    args = parser.parse_args()

    selectors = config.SELECTORS
    if not selectors.get("card"):
        if args.url.startswith(("http://127.0.0.1", "file://")):
            # Fixture mode: the local JS fixture uses the same markup as
            # tests/sample_listings.html.
            selectors = {
                "card": "li.listing",
                "title": "a.title",
                "company": "span.company",
                "location": "span.location",
                "url": "a.title",
            }
        else:
            raise SystemExit(
                "Live mode is not configured: set SOURCE_URL and SELECTORS "
                "in scraper/config.py after checking robots.txt/terms."
            )

    listings = collect_rendered(args.url, selectors, executable_path=args.chromium_path)

    seen, unique = set(), []
    for row in listings:
        if not row["title"] or not row["url"] or row["url"] in seen:
            continue
        seen.add(row["url"])
        unique.append(row)

    with open(args.out, "w", encoding="utf-8") as f:
        for row in unique:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"Wrote {len(unique)} listings to {args.out}")


if __name__ == "__main__":
    main()
