"""Build / expand the labeling set for TakeMeter.

Multi-source, best-effort scraping with a curated fallback so the dataset is
ALWAYS complete, even when a source is blocked. Sources (from planning.md):

  reddit_posts    — r/soccer-style subreddit titles + self-text (hot & top)
  reddit_comments — recent COMMENTS from those subs (the actual "takes")
  rss             — football news/opinion feeds: ESPN, BBC, Sky, Guardian, etc.
  curated         — ~205 hand-authored realistic posts (data/curated_examples.py)

The `label` column is left BLANK on purpose — labeling is the project work
(do it in the web Train page, or pre-label with the prompts in ../prompts/).

Usage:
    python data/build_dataset.py                       # fresh build -> 200 rows
    python data/build_dataset.py --target 300          # collect more
    python data/build_dataset.py --append --target 300 # GROW the set, keep existing labels
    python data/build_dataset.py --sources rss,curated # pick sources
    python data/build_dataset.py --no-scrape           # curated only, fully offline

Output columns: id, text, label, notes, source
"""
from __future__ import annotations

import argparse
import csv
import html
import os
import random
import re
import sys
import xml.etree.ElementTree as ET

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from curated_examples import all_curated  # noqa: E402

OUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "examples_to_label.csv")
SEED = 42

# Public, no-auth Reddit JSON listings.
SUBREDDITS = ["soccer", "MLS", "footballtactics", "PremierLeague",
              "football", "championsleague", "Championship", "WorldCup"]
LISTINGS = ["hot", "top"]

# Football news / opinion RSS feeds (title + summary). All public, no auth.
RSS_FEEDS = {
    "espn":     "https://www.espn.com/espn/rss/soccer/news",
    "bbc":      "https://feeds.bbci.co.uk/sport/football/rss.xml",
    "sky":      "https://www.skysports.com/rss/11095",     # 11095 = Football (12040 is all-sport)
    "guardian": "https://www.theguardian.com/football/rss",
    "90min":    "https://www.90min.com/posts.rss",
}

# Drop items that are clearly about a different sport (some feeds mix sports).
_OTHER_SPORT = re.compile(
    r"\b(cricket|wicket|innings|bowler|batsman|test match|PGA|LPGA|birdie|"
    r"fairway|rugby|scrum|six nations|NBA|NFL|touchdown|home run|Verstappen|"
    r"grand prix|pole position|Wimbledon|\bATP\b|\bWTA\b|tennis|golf|Korda|"
    r"McIlroy|snooker|darts|boxing|UFC|NASCAR)\b", re.I)


def is_football(t: str) -> bool:
    return not _OTHER_SPORT.search(t)

USER_AGENT = "Mozilla/5.0 (takemeter-coursework; educational; non-commercial)"

MIN_LEN, MAX_LEN, MIN_WORDS = 60, 600, 10
ALL_SOURCES = ["reddit_posts", "reddit_comments", "rss", "curated"]
PER_FEED_CAP = 18          # max items per RSS feed, for source diversity
DEFAULT_REAL_FRAC = 0.5    # max share of the set from scraped sources; rest curated


# ── cleaning / filtering ──────────────────────────────────────────────────
def clean_text(raw: str) -> str:
    if not raw:
        return ""
    t = html.unescape(raw)
    # Some feeds occasionally ship U+FFFD where an apostrophe/quote was lost
    # upstream — the original char is unrecoverable, so best-guess it back.
    t = t.replace("�", "'")
    t = re.sub(r"<[^>]+>", " ", t)               # strip HTML tags (RSS summaries)
    t = re.sub(r"https?://\S+", "", t)            # drop links
    t = re.sub(r"/?u/\w+|/?r/\w+", "", t)         # drop user/sub mentions
    t = re.sub(r"[*_>#`~]+", "", t)                # drop markdown markers
    t = re.sub(r"\s+", " ", t).strip()
    return t


def is_good(t: str) -> bool:
    if not (MIN_LEN <= len(t) <= MAX_LEN):
        return False
    if len(t.split()) < MIN_WORDS:
        return False
    if t.lower().startswith(("[removed]", "[deleted]")):
        return False
    if "subreddit" in t.lower() or t.count("http"):
        return False
    return True


def _get(url: str, timeout: int = 12):
    import urllib.request, ssl
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    return urllib.request.urlopen(req, timeout=timeout, context=ctx).read()


# ── source: reddit posts ──────────────────────────────────────────────────
def scrape_reddit_posts(target, seen):
    out = []
    try:
        import json
    except Exception:
        return out
    for sub in SUBREDDITS:
        if len(out) >= target:
            break
        for listing in LISTINGS:
            url = f"https://www.reddit.com/r/{sub}/{listing}.json?limit=100&t=month"
            try:
                children = json.loads(_get(url)).get("data", {}).get("children", [])
            except Exception as e:
                print(f"  [reddit_posts] r/{sub}/{listing}: {type(e).__name__}, skip")
                continue
            for ch in children:
                d = ch.get("data", {})
                for raw in (d.get("selftext", ""), d.get("title", "")):
                    t = clean_text(raw)
                    if is_good(t) and t.lower() not in seen:
                        seen.add(t.lower())
                        out.append((t, f"reddit:{sub}"))
            print(f"  [reddit_posts] r/{sub}/{listing}: total {len(out)}")
    return out


# ── source: reddit comments (the real "takes") ────────────────────────────
def scrape_reddit_comments(target, seen):
    out = []
    import json
    for sub in SUBREDDITS:
        if len(out) >= target:
            break
        url = f"https://www.reddit.com/r/{sub}/comments.json?limit=100"
        try:
            children = json.loads(_get(url)).get("data", {}).get("children", [])
        except Exception as e:
            print(f"  [reddit_comments] r/{sub}: {type(e).__name__}, skip")
            continue
        for ch in children:
            t = clean_text(ch.get("data", {}).get("body", ""))
            if is_good(t) and t.lower() not in seen:
                seen.add(t.lower())
                out.append((t, f"reddit_c:{sub}"))
        print(f"  [reddit_comments] r/{sub}: total {len(out)}")
    return out


# ── source: RSS news/opinion feeds ────────────────────────────────────────
def _local(tag):  # strip XML namespace
    return tag.rsplit("}", 1)[-1]


def scrape_rss(target, seen):
    out = []
    for name, url in RSS_FEEDS.items():
        if len(out) >= target:
            break
        try:
            root = ET.fromstring(_get(url))
        except Exception as e:
            print(f"  [rss] {name}: {type(e).__name__}, skip")
            continue
        added = 0
        for item in root.iter():
            if added >= PER_FEED_CAP:
                break
            if _local(item.tag) not in ("item", "entry"):
                continue
            title = desc = ""
            for c in item:
                lt = _local(c.tag)
                if lt == "title":
                    title = c.text or ""
                elif lt in ("description", "summary", "content"):
                    desc = "".join(c.itertext()) if list(c) else (c.text or "")
            # prefer the summary (more of a "take"); fall back to the headline
            for cand in (clean_text(desc), clean_text(title)):
                if is_good(cand) and is_football(cand) and cand.lower() not in seen:
                    seen.add(cand.lower())
                    out.append((cand, f"rss:{name}"))
                    added += 1
                    break
        print(f"  [rss] {name}: +{added} (total {len(out)})")
    return out


SCRAPERS = {
    "reddit_posts": scrape_reddit_posts,
    "reddit_comments": scrape_reddit_comments,
    "rss": scrape_rss,
}


# ── orchestration ─────────────────────────────────────────────────────────
def collect(target, sources, seen):
    rows = []
    for name in sources:
        if name == "curated" or len(rows) >= target:
            continue
        print(f"Scraping source: {name} ...")
        got = SCRAPERS[name](target - len(rows), seen)
        rows.extend(got)
        print(f"  -> {len(got)} from {name}; running total {len(rows)}")
    return rows


def fill_curated(rows, target, seen, rng):
    curated = all_curated()
    rng.shuffle(curated)
    for t in curated:
        if len(rows) >= target:
            break
        if t.lower() not in seen:
            seen.add(t.lower())
            rows.append((t, "curated"))
    return rows


def load_existing(path):
    if not os.path.isfile(path):
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def build(target, sources, do_scrape, append, out_path, real_frac):
    rng = random.Random(SEED)
    existing = load_existing(out_path) if append else []
    seen = {r["text"].strip().lower() for r in existing}
    rows = []  # new (text, source) tuples
    need = target - len(existing)

    if do_scrape:
        scrape_sources = [s for s in sources if s in SCRAPERS]
        # cap real/scraped data so curated keeps every label represented; if no
        # curated source is selected, allow scraping to fill the whole set.
        real_target = need if "curated" not in sources else int(round(need * real_frac))
        if need > 0 and scrape_sources and real_target > 0:
            rows = collect(real_target, scrape_sources, seen)
        print(f"  scraped {len(rows)} real posts (cap {real_target} = {real_frac:.0%} of new)")
    else:
        print("Scraping disabled (--no-scrape): curated only.")

    if "curated" in sources:
        rows = fill_curated(rows, target - len(existing), seen, rng)

    rng.shuffle(rows)
    rows = rows[: max(0, target - len(existing))]

    # assemble final records, preserving existing labels in append mode
    records = list(existing)
    next_id = (max((int(r["id"]) for r in existing), default=0) + 1) if existing else 1
    for j, (t, src) in enumerate(rows):
        records.append({"id": next_id + j, "text": t, "label": "",
                        "notes": "", "source": src})

    if not append:  # fresh build: renumber 1..N after a shuffle for interleaving
        rng.shuffle(records)
        for k, r in enumerate(records, 1):
            r["id"] = k

    if len(records) < target:
        print(f"  ⚠️  only {len(records)} unique posts (< {target}). "
              "Enable more sources or add curated examples.")
    return records[:target] if not append else records


def main():
    ap = argparse.ArgumentParser(description="Build/expand the TakeMeter labeling CSV.")
    ap.add_argument("--target", type=int, default=200, help="total examples desired")
    ap.add_argument("--sources", default=",".join(ALL_SOURCES),
                    help=f"comma list from {ALL_SOURCES}")
    ap.add_argument("--append", action="store_true",
                    help="grow the existing CSV, keeping rows and labels already there")
    ap.add_argument("--no-scrape", action="store_true", help="curated only, no network")
    ap.add_argument("--real-frac", type=float, default=DEFAULT_REAL_FRAC,
                    help="max share of the set from scraped sources (rest curated); "
                         f"default {DEFAULT_REAL_FRAC}. Ignored if 'curated' not in --sources.")
    ap.add_argument("--out", default=OUT_PATH)
    args = ap.parse_args()

    sources = [s.strip() for s in args.sources.split(",") if s.strip()]
    bad = set(sources) - set(ALL_SOURCES)
    if bad:
        ap.error(f"unknown source(s): {bad}. choose from {ALL_SOURCES}")

    records = build(args.target, sources, not args.no_scrape, args.append,
                    args.out, args.real_frac)

    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["id", "text", "label", "notes", "source"])
        w.writeheader()
        w.writerows(records)

    by_src = {}
    for r in records:
        kind = r["source"].split(":")[0]
        by_src[kind] = by_src.get(kind, 0) + 1
    print()
    print(f"✅ wrote {len(records)} examples -> {args.out}")
    print("   by source: " + ", ".join(f"{k}={v}" for k, v in sorted(by_src.items())))
    print("   `label` column is blank — label in the web Train page or with prompts/.")


if __name__ == "__main__":
    main()
