"""Label all 200 examples with Google Gemini — a separate annotator.

Kept separate from the SambaNova script because Gemini is its own provider/key.
One batched request (all 200 posts in, one JSON array out) → labels/gemini/labeled.csv.
Tries a short list of current Gemini models and uses the first one that responds, so
it keeps working as Google rotates model names.

Requires: GEMINI_API_KEY in ../.env

Usage:
    python labels/label_with_gemini.py
    python labels/label_with_gemini.py --model gemini-2.5-flash
"""
from __future__ import annotations

import argparse
import sys
import time

import requests

from _batch_label import (build_messages, load_env, load_examples,
                          parse_labels, write_csv)

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

BASE = "https://generativelanguage.googleapis.com/v1beta/models"
# first one that returns 200 wins
CANDIDATES = ["gemini-2.5-flash", "gemini-flash-latest", "gemini-2.0-flash",
              "gemini-2.5-flash-lite", "gemini-2.0-flash-001", "gemini-1.5-flash"]


def call_gemini(key: str, model: str, prompt: str) -> tuple[int, str]:
    """Return (http_status, text). Disables 'thinking' so it doesn't eat the budget."""
    url = f"{BASE}/{model}:generateContent?key={key}"
    base_cfg = {"temperature": 0, "maxOutputTokens": 8192}
    for cfg in ({**base_cfg, "thinkingConfig": {"thinkingBudget": 0}}, base_cfg):
        for attempt in range(4):
            try:
                r = requests.post(url, json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": cfg}, timeout=300)
                if r.status_code == 200:
                    d = r.json()
                    try:
                        parts = d["candidates"][0]["content"]["parts"]
                        return 200, "".join(p.get("text", "") for p in parts)
                    except Exception:
                        return 200, ""
                if r.status_code in (429, 500, 503) and attempt < 3:
                    time.sleep(2 ** attempt * 3)
                    continue
                if r.status_code == 400 and "thinkingConfig" in r.text:
                    break   # retry without thinkingConfig
                return r.status_code, r.text[:200]
            except Exception as e:
                if attempt < 3:
                    time.sleep(2 ** attempt * 3)
                else:
                    return 0, str(e)[:200]
    return 400, "exhausted config fallbacks"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", help="force a specific Gemini model id")
    args = ap.parse_args()

    key = load_env("GEMINI_API_KEY")["GEMINI_API_KEY"]
    rows = load_examples()
    ids = [str(r["id"]) for r in rows]
    prompt = build_messages(rows)[0]["content"]

    candidates = [args.model] if args.model else CANDIDATES
    for model in candidates:
        print(f"Trying {model} (one batched call for {len(rows)} posts)...")
        t0 = time.time()
        status, text = call_gemini(key, model, prompt)
        if status != 200:
            print(f"    {model} -> HTTP {status}: {text[:140]}")
            continue
        labels, n = parse_labels(text, ids)
        if n == 0:
            print(f"    {model} returned no parseable labels; trying next.")
            continue
        dist = write_csv("gemini", rows, labels, model)
        print(f"✅ {model}: parsed {n}/{len(rows)} in {time.time()-t0:.0f}s -> "
              f"labels/gemini/  dist={dist}")
        print("Run: python labels/compare_labels.py")
        return
    sys.exit("No Gemini model worked — check GEMINI_API_KEY / model names.")


if __name__ == "__main__":
    main()
