"""Build the 200-example labeling set for TakeMeter.

Strategy (per project decision: "try scraping all srcs, else curate, or both"):
  1. Try to pull real public posts from r/soccer-style subreddits via Reddit's
     public JSON endpoints (no auth, no API key). This is best-effort — if the
     network is blocked, rate-limited, or returns junk, we just skip it.
  2. Fill the remainder (up to 200) from the hand-authored curated corpus in
     ``curated_examples.py`` so the dataset is ALWAYS complete, even offline.
  3. Clean, dedupe, shuffle deterministically, and write
     ``data/examples_to_label.csv`` with a BLANK ``label`` column for you to fill.

Usage:
    python data/build_dataset.py                # blend scraped + curated -> 200
    python data/build_dataset.py --no-scrape    # curated only (fully offline)
    python data/build_dataset.py --target 240   # collect more than 200

The output CSV columns are: id, text, label, notes, source
  - label  : intentionally empty — this is the work you (and the 3 models) do.
  - notes  : free-text column for difficult-case annotations.
  - source : "reddit:<sub>" for scraped rows, "curated" otherwise (provenance).
"""
from __future__ import annotations

import argparse
import csv
import html
import os
import random
import re
import sys

# Windows consoles default to cp1252 and choke on emoji — force UTF-8 output.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# Allow running both as `python data/build_dataset.py` and from the data dir.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from curated_examples import all_curated  # noqa: E402

OUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "examples_to_label.csv")
SEED = 42

# Public, no-auth Reddit JSON listings. We pull self-text + top comments.
SUBREDDITS = ["soccer", "MLS", "footballtactics", "PremierLeague"]
LISTINGS = ["hot", "top"]
USER_AGENT = "takemeter-coursework/1.0 (educational; non-commercial)"

# Reasonable bounds so a "post" is a real take, not a title fragment or essay.
MIN_LEN = 60
MAX_LEN = 600
MIN_WORDS = 10


def clean_text(raw: str) -> str:
    """Normalize whitespace, unescape HTML entities, strip URLs/markdown noise."""
    if not raw:
        return ""
    t = html.unescape(raw)
    t = re.sub(r"https?://\S+", "", t)          # drop links
    t = re.sub(r"/?u/\w+|/?r/\w+", "", t)        # drop user/sub mentions
    t = re.sub(r"[*_>#`~]+", "", t)               # drop markdown markers
    t = re.sub(r"\s+", " ", t).strip()
    return t


def is_good(t: str) -> bool:
    if not (MIN_LEN <= len(t) <= MAX_LEN):
        return False
    if len(t.split()) < MIN_WORDS:
        return False
    if t.lower().startswith(("[removed]", "[deleted]")):
        return False
    # crude English-ish / non-bot filter
    if t.count("http") or "subreddit" in t.lower():
        return False
    return True


def scrape_reddit(target: int) -> list[tuple[str, str]]:
    """Best-effort scrape. Returns list of (text, source). Empty on any failure."""
    try:
        import requests  # optional dependency
    except Exception:
        print("  [scrape] `requests` not installed — skipping scrape. "
              "(`pip install requests` to enable.)")
        return []

    collected: list[tuple[str, str]] = []
    seen: set[str] = set()
    headers = {"User-Agent": USER_AGENT}

    for sub in SUBREDDITS:
        if len(collected) >= target:
            break
        for listing in LISTINGS:
            if len(collected) >= target:
                break
            url = f"https://www.reddit.com/r/{sub}/{listing}.json?limit=100&t=month"
            try:
                resp = requests.get(url, headers=headers, timeout=12)
                if resp.status_code != 200:
                    print(f"  [scrape] r/{sub}/{listing} -> HTTP {resp.status_code}, skipping")
                    continue
                children = resp.json().get("data", {}).get("children", [])
            except Exception as e:  # network/JSON/anything
                print(f"  [scrape] r/{sub}/{listing} failed ({type(e).__name__}), skipping")
                continue

            for ch in children:
                d = ch.get("data", {})
                for raw in (d.get("selftext", ""), d.get("title", "")):
                    t = clean_text(raw)
                    key = t.lower()
                    if is_good(t) and key not in seen:
                        seen.add(key)
                        collected.append((t, f"reddit:{sub}"))
            print(f"  [scrape] r/{sub}/{listing}: total collected so far = {len(collected)}")

    return collected


def build(target: int, do_scrape: bool) -> list[dict]:
    rng = random.Random(SEED)

    rows: list[tuple[str, str]] = []
    seen: set[str] = set()

    if do_scrape:
        print("Attempting to scrape public sources...")
        for t, src in scrape_reddit(target):
            key = t.lower()
            if key not in seen:
                seen.add(key)
                rows.append((t, src))
        print(f"  scraped {len(rows)} usable real posts")
    else:
        print("Scraping disabled (--no-scrape): curated corpus only.")

    # Fill the rest from curated, shuffled for label variety.
    curated = all_curated()
    rng.shuffle(curated)
    for t in curated:
        if len(rows) >= target:
            break
        key = t.lower()
        if key not in seen:
            seen.add(key)
            rows.append((t, "curated"))

    if len(rows) < target:
        print(f"  ⚠️  only {len(rows)} unique posts available (< {target}). "
              "Add more curated examples or enable scraping.")

    # Final shuffle so scraped/curated are interleaved (no ordering signal).
    rng.shuffle(rows)
    rows = rows[:target]

    return [
        {"id": i + 1, "text": t, "label": "", "notes": "", "source": src}
        for i, (t, src) in enumerate(rows)
    ]


def main() -> None:
    ap = argparse.ArgumentParser(description="Build the TakeMeter labeling CSV.")
    ap.add_argument("--target", type=int, default=200, help="number of examples (default 200)")
    ap.add_argument("--no-scrape", action="store_true", help="curated corpus only, no network")
    ap.add_argument("--out", default=OUT_PATH, help="output CSV path")
    args = ap.parse_args()

    rows = build(args.target, do_scrape=not args.no_scrape)

    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["id", "text", "label", "notes", "source"])
        w.writeheader()
        w.writerows(rows)

    n_scraped = sum(1 for r in rows if r["source"].startswith("reddit:"))
    print()
    print(f"✅ wrote {len(rows)} examples -> {args.out}")
    print(f"   real (scraped): {n_scraped}   |   curated: {len(rows) - n_scraped}")
    print("   `label` column is blank on purpose — label them in the web Train page")
    print("   or with the prompts in prompts/.")


if __name__ == "__main__":
    main()
