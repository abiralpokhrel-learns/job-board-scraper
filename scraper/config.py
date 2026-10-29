"""Config for the job-board scraper.

SOURCE_URL and SELECTORS are placeholders on purpose: fill them in
only after reading the target board's robots.txt/terms and opening
its listing page to confirm the markup. Nothing live runs with
these defaults.
"""

SOURCE_URL = ""  # e.g. a public, static job-listing category page
REQUEST_DELAY_SECONDS = 1.0
MAX_PAGES = 2
USER_AGENT = "job-board-scraper/0.1 (learning project; contact: abhiral1119@gmail.com)"

# Chromium for Playwright. Leave empty to use Playwright's own
# browser (``playwright install chromium``). Set it only when a
# system Chromium is the intended browser, e.g. in this workspace.
CHROMIUM_EXECUTABLE_PATH = ""

# CSS selectors, one per field, relative to one listing card.
SELECTORS = {
    "card": "",       # e.g. "li.job-listing"
    "title": "",      # e.g. "a.job-title"
    "company": "",    # e.g. "span.company"
    "location": "",   # e.g. "span.location"
    "url": "",        # e.g. "a.job-title" (href taken from this element)
}
