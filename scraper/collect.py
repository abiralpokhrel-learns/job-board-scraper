"""Collect public job listings into raw JSONL.

Two modes:
  --fixture PATH : parse a local sample HTML file (no network; the
                   only mode that runs with the scaffold as shipped).
  live (default) : fetch SOURCE_URL from config.py, honouring
                   robots.txt and REQUEST_DELAY_SECONDS. Refuses to
                   run until SOURCE_URL and SELECTORS are filled in.
"""
import argparse
import json
import time
import urllib.parse
import urllib.robotparser
from datetime import date

import requests
from bs4 import BeautifulSoup

from . import config


def robots_allowed(url: str) -> bool:
    parsed = urllib.parse.urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    rp = urllib.robotparser.RobotFileParser()
    rp.set_url(robots_url)
    try:
        rp.read()
    except Exception:
        return False  # If robots.txt cannot be read, do not scrape.
    return rp.can_fetch(config.USER_AGENT, url)


def parse_listings(html: str, selectors: dict, base_url: str = "") -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    listings = []
    for card in soup.select(selectors["card"]):
        def text(key):
            el = card.select_one(selectors[key])
            return el.get_text(" ", strip=True) if el is not None else ""

        def href(key):
            el = card.select_one(selectors[key])
            if el is None or not el.has_attr("href"):
                return ""
            return urllib.parse.urljoin(base_url, el["href"])

        listings.append({
            "title": text("title"),
            "company": text("company"),
            "location": text("location"),
            "url": href("url"),
            "collected_date": date.today().isoformat(),
        })
    return listings


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", help="Local sample HTML file (no network)")
    parser.add_argument("--out", required=True, help="Output JSONL path")
    args = parser.parse_args()

    if args.fixture:
        selectors = {
            "card": "li.listing",
            "title": "a.title",
            "company": "span.company",
            "location": "span.location",
            "url": "a.title",
        }
        with open(args.fixture, encoding="utf-8") as f:
            listings = parse_listings(f.read(), selectors)
    else:
        if not config.SOURCE_URL or not config.SELECTORS.get("card"):
            raise SystemExit(
                "Live mode is not configured: set SOURCE_URL and SELECTORS "
                "in scraper/config.py after checking robots.txt/terms."
            )
        if not robots_allowed(config.SOURCE_URL):
            raise SystemExit(f"robots.txt disallows scraping {config.SOURCE_URL}")
        listings = []
        session = requests.Session()
        session.headers["User-Agent"] = config.USER_AGENT
        for page in range(1, config.MAX_PAGES + 1):
            url = config.SOURCE_URL if page == 1 else f"{config.SOURCE_URL}?page={page}"
            resp = session.get(url, timeout=30)
            resp.raise_for_status()
            listings.extend(parse_listings(resp.text, config.SELECTORS, base_url=url))
            time.sleep(config.REQUEST_DELAY_SECONDS)

    # Deduplicate on URL, drop rows with no title or URL.
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
