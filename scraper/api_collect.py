"""Collect listings from Remotive's public, keyless JSON API.

This is the project's ONLY live-data path that does not scrape HTML:
Remotive publishes this API for developers to share its jobs further.
It was checked live on 2026-10-28 (a ``limit=3`` fetch returned the
``jobs`` array with ``title``, ``company_name``,
``candidate_required_location``, ``url``, ``category``, ``tags``,
``job_type``, ``publication_date`` and ``salary``). It was first run
on 2026-10-29 (two fetches, 11 unique listings, cleaned to CSV —
see Honest status). Remotive's own legal notice on the response (read it before running):
- Link back to the job URL on Remotive AND mention Remotive as the
  source. Do not submit Remotive jobs to third-party job sites
  (Jooble, Neuvoo, Google Jobs, LinkedIn Jobs, ...).
- Jobs are delayed by 24 hours. Do not use listings to collect
  signups / email addresses.
- Fetch at most ~4 times a day; excessive requests get blocked.
  One run of this module is one GET. Do not put it on an hourly cron.

Output shape matches ``scraper/collect.py`` (plus ``source``), so the
same ``scraper/clean.py`` turns it into CSV/Parquet. We Work Remotely
is deliberately NOT a target here: its API terms say scraping its
data is strictly prohibited and only API-exposed data may be used.
"""

import argparse
import json
from datetime import date

import requests

from . import config

API_URL = "https://remotive.com/api/remote-jobs"
SOURCE = "remotive-api"


def normalize_jobs(payload: dict) -> list[dict]:
    """Map a Remotive API payload to the project's row shape.

    Rows with no title or URL are dropped here, as in collect.py;
    dedupe on URL happens in main(), matching the other collectors.
    """
    today = date.today().isoformat()
    rows = []
    for job in payload.get("jobs", []):
        title = " ".join(str(job.get("title", "")).split())
        company = " ".join(str(job.get("company_name", "")).split())
        location = " ".join(str(job.get("candidate_required_location", "")).split())
        url = str(job.get("url", "")).strip()
        if not title or not url:
            continue
        rows.append({
            "title": title,
            "company": company,
            "location": location,
            "url": url,
            "source": SOURCE,
            "collected_date": today,
        })
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch live remote listings from Remotive's public API (max ~4 runs/day per Remotive's notice)."
    )
    parser.add_argument("--out", required=True, help="Output JSONL path")
    parser.add_argument("--search", default="", help="Keyword search, e.g. 'data engineer'")
    parser.add_argument("--category", default="", help="e.g. 'software-dev' (see Remotive API docs)")
    parser.add_argument("--limit", type=int, default=100, help="Max listings to request")
    args = parser.parse_args()

    params = {"limit": args.limit}
    if args.search:
        params["search"] = args.search
    if args.category:
        params["category"] = args.category

    resp = requests.get(
        API_URL, params=params, headers={"User-Agent": config.USER_AGENT}, timeout=30
    )
    resp.raise_for_status()
    rows = normalize_jobs(resp.json())

    seen, unique = set(), []
    for row in rows:
        if row["url"] in seen:
            continue
        seen.add(row["url"])
        unique.append(row)

    with open(args.out, "w", encoding="utf-8") as f:
        for row in unique:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"Wrote {len(unique)} listings to {args.out} (source: Remotive — link back and credit Remotive if shared)")


if __name__ == "__main__":
    main()
