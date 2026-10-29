# job-board-scraper — NOT yet run against a live site

A small, polite scraper that collects public job listings, cleans them
and writes a tidy dataset. The dynamic (Playwright) path in
`scraper/dynamic.py` is now implemented and verified — but only
against a local fixture page whose listings are injected by
JavaScript (a plain `requests` parse of the same page finds 0
listings). Nothing here claims a live run: no board has been
scraped, and there is no live data in this repo.

## What it proves when finished

Collect → clean → structure, the same shape as the ecommerce and
ghtrends pipelines: raw JSONL in `data/raw/`, cleaned CSV + Parquet
in `data/clean/`, deduplicated on listing URL, with source and
collected date kept on every row.

## Run the fixtures (no network, no live site)

```sh
pip install -r requirements.txt
playwright install chromium   # for the dynamic path; or set CHROMIUM_EXECUTABLE_PATH
# Static path — parses the sample HTML directly:
python -m scraper.collect --fixture tests/sample_listings.html --out data/raw/sample.jsonl
python -m scraper.clean --in data/raw/sample.jsonl --out data/clean/sample
# Dynamic path — a real browser renders the JS-injected listings:
python tests/test_dynamic_fixture.py [--chromium-path PATH]
```

Verified 2026-10-28: the dynamic fixture test returned the 2
unique invented listings; the same fixture parsed without a
browser returns 0. The test loads the fixture from disk because
the hardened Chromium in this workspace blocks localhost
navigation — on a normal machine the same code runs against
http(s) board pages unchanged.

## Run against a live board (only after checking first)

1. Read the board's `robots.txt` and terms; scrape only what they
   allow, and only public listings — never log in, never bypass a
   check, never hammer the site.
2. Set `SOURCE_URL` and the CSS selectors in `scraper/config.py`
   to match the board's actual markup (verify by opening the page
   yourself first — selectors in a scaffold go stale).
3. Keep `REQUEST_DELAY_SECONDS >= 1` and `MAX_PAGES` small.

```sh
python -m scraper.collect --out data/raw/jobs.jsonl
python -m scraper.clean --in data/raw/jobs.jsonl --out data/clean/jobs
```

## Live data via an authorised API (no HTML scraping)

`scraper/api_collect.py` fetches Remotive's public, keyless JSON API
— the one live-data path that needs no scraping. Remotive's legal
notice on the response requires linking back to the Remotive job URL
and crediting Remotive as the source, forbids submitting its jobs to
third-party job sites, and asks for at most ~4 fetches a day. This
module was NOT run live yet; its field names were verified from a
checked `limit=3` API fetch on 2026-10-28. We Work Remotely is
deliberately excluded: its terms prohibit scraping and allow only
API-exposed data.

```sh
# One GET only — do not cron this hourly (Remotive: max ~4/day).
python -m scraper.api_collect --search "data engineer" --out data/raw/remotive.jsonl
python -m scraper.clean --in data/raw/remotive.jsonl --out data/clean/remotive
```

## Honest status (2026-10-28)

- Static scraping (`requests` + BeautifulSoup): implemented, fixture-tested.
- Dynamic scraping (Playwright for JS-rendered boards):
  implemented in `scraper/dynamic.py`, reusing the static path's
  parser and dedupe, and fixture-tested with a real browser
  against a local JS-injected page. Selenium is not used; do not
  claim it. The Playwright code has NOT been run against a real
  board yet — that step still needs a board whose robots/terms
  allow it, chosen and checked first.
- Live data (first run, 2026-10-29): `scraper/api_collect.py`
  was run twice (searches "data engineer" and "data analyst",
  limit 50 each) and wrote 11 unique listings to
  `data/raw/remotive.jsonl`, cleaned to `data/clean/remotive.csv`.
  The second search returned the identical 11 rows, so the API's
  `search` parameter did not appear to filter in these runs.
  None of the 11 is a data-engineering intern/junior role
  (senior/lead/head roles, AI-cording tasks, sales, writing).
  Nothing has been pushed to GitHub and no board has been scraped.
