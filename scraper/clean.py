"""Clean raw listings JSONL into a tidy dataset.

Normalises whitespace/case on title/company/location, drops
duplicates and empty rows, and writes CSV always plus Parquet when
pandas + pyarrow are available.
"""
import argparse
import csv
import json


def clean_rows(rows: list[dict]) -> list[dict]:
    seen, out = set(), []
    for row in rows:
        title = " ".join(str(row.get("title", "")).split())
        company = " ".join(str(row.get("company", "")).split())
        location = " ".join(str(row.get("location", "")).split())
        url = str(row.get("url", "")).strip()
        if not title or not url or url in seen:
            continue
        seen.add(url)
        out.append({
            "title": title,
            "company": company,
            "location": location,
            "url": url,
            "source": str(row.get("source", "")).strip(),
            "collected_date": row.get("collected_date", ""),
        })
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--in", dest="inp", required=True)
    parser.add_argument("--out", required=True, help="Output path without extension")
    args = parser.parse_args()

    with open(args.inp, encoding="utf-8") as f:
        rows = [json.loads(line) for line in f if line.strip()]
    cleaned = clean_rows(rows)

    with open(f"{args.out}.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(cleaned[0].keys()) if cleaned else [])
        writer.writeheader()
        writer.writerows(cleaned)
    try:
        import pandas as pd

        pd.DataFrame(cleaned).to_parquet(f"{args.out}.parquet", index=False)
        print(f"Wrote {len(cleaned)} rows to {args.out}.csv and {args.out}.parquet")
    except ImportError:
        print(f"Wrote {len(cleaned)} rows to {args.out}.csv (pandas/pyarrow not installed, no Parquet)")


if __name__ == "__main__":
    main()
