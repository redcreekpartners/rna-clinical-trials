#!/usr/bin/env python3
"""Refresh data/trials.json from ClinicalTrials.gov.

    python scripts/update.py                   # live fetch
    python scripts/update.py --raw cache.json  # reuse a saved fetch
    python scripts/update.py --save-raw cache.json

The file is rewritten only when the list itself changes, so its generated_at
means "when this list last changed" and a quiet day makes no commit.
"""
import argparse
import datetime
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from trials import fetch, pipeline, publish  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "data" / "trials.json"

# A day's list shrinking this much is far more likely to be a broken source than
# a real change in the field. Refuse to publish it; the page keeps yesterday's
# list and its "last updated" date stops moving, which is how a break shows.
MIN_RETAINED = 0.8


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--raw", help="read a saved fetch instead of querying the API")
    ap.add_argument("--save-raw", help="save the live fetch here for reuse")
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()
    out = Path(args.out)

    try:
        studies, matched = pipeline.load_or_fetch(args.raw, args.save_raw)
    except fetch.FetchError as error:
        print(f"fetch failed, leaving {out.name} alone: {error}", file=sys.stderr)
        return 1

    recs = pipeline.records(studies, matched)
    published = publish.page_records(recs)
    print(f"{len(studies)} trials searched, {len(published)} published", file=sys.stderr)

    previous = json.loads(out.read_text()) if out.exists() else None
    if previous and previous.get("records"):
        before = len(previous["records"])
        if len(published) < before * MIN_RETAINED:
            print(f"refusing to publish: {len(published)} trials against {before} yesterday",
                  file=sys.stderr)
            return 1
        if previous["records"] == published:
            print(f"{out.name}: unchanged", file=sys.stderr)
            return 0

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "source": "ClinicalTrials.gov API v2",
        "records": published,
    }, indent=1, ensure_ascii=False) + "\n")
    print(f"{out.name}: updated", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
