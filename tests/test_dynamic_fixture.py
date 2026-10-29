"""Verify the Playwright path against the LOCAL JS fixture only.

Runs ``python -m scraper.dynamic`` against
``tests/dynamic_listings.html`` via a file:// URL and asserts the
two unique invented listings come back. The fixture is loaded from
disk (not over HTTP) because the hardened Chromium in this
workspace blocks navigation to localhost addresses; the code under
test — launch Chromium, wait for the listing selector, parse the
rendered HTML with the shared parser — is identical for http(s)
pages. No external network, no live board. Run from the project
root:

    python tests/test_dynamic_fixture.py [--chromium-path PATH]

Exit code 0 = the dynamic path works end to end on the fixture.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--chromium-path", default=None)
    args = parser.parse_args()

    url = (ROOT / "tests" / "dynamic_listings.html").as_uri()
    out = "/tmp/scraper-dynamic-fixture.jsonl"
    cmd = [sys.executable, "-m", "scraper.dynamic", "--url", url, "--out", out]
    if args.chromium_path:
        cmd += ["--chromium-path", args.chromium_path]
    result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    print(result.stdout, end="")
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        return result.returncode
    rows = [json.loads(line) for line in Path(out).read_text().splitlines() if line.strip()]
    assert len(rows) == 2, f"expected 2 unique rows, got {len(rows)}: {rows}"
    assert rows[0]["title"] == "Sample Data Engineer Intern", rows
    assert rows[1]["company"] == "Sample Labs", rows
    assert all(r["url"].startswith("https://example.com/jobs/") for r in rows), rows
    print(f"OK: dynamic fixture returned {len(rows)} unique listings (JS-rendered, local only)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
