"""Auto-label the dataset with Groq (the 4th annotator) + emit context hints.

Reads data/examples_to_label.csv and, for every post, asks llama-3.3-70b (JSON mode)
for a label PLUS two "outside-context" signals that help judge the post:
  - sarcasm    : is it ironic / saying the opposite of what it means?
  - verifiable : does it contain a specific, checkable factual claim?

Writes:
  labels/groq/labeled.csv     id,label,confidence,sarcasm,verifiable,rationale
  data/context_hints.csv      id,sarcasm,verifiable,note   (shown in the web Train page)

These are PRE-labels and CONTEXT to speed up your own annotation — review them.
The reviewed labels/human/labeled.csv is still the only file used for training.

Requires: pip install groq python-dotenv joblib   (GROQ_API_KEY read from ../.env)

Usage:
    python labels/label_with_groq.py                 # all examples, 8 parallel calls
    python labels/label_with_groq.py --limit 20      # quick smoke test on 20
    python labels/label_with_groq.py --jobs 4        # gentler on the rate limit
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
EXAMPLES = os.path.join(REPO, "data", "examples_to_label.csv")
GROQ_DIR = os.path.join(HERE, "groq")
GROQ_CSV = os.path.join(GROQ_DIR, "labeled.csv")
HINTS_CSV = os.path.join(REPO, "data", "context_hints.csv")
LABELS = ["analysis", "hot_take", "reaction", "mixed", "skip"]

SYSTEM_PROMPT = """
You are an expert annotator for TakeMeter, classifying football (soccer) discourse
quality (World Cup, MLS, clubs). Assign each post EXACTLY ONE label, using outside
knowledge as context (don't take posts at face value):

analysis: structured argument with specific, verifiable evidence (stats/history/tactics).
hot_take: bold confident opinion with NO real evidence; asserts, doesn't argue; or a
          sarcastic / cherry-picked / made-up "stat" used just to sound credible.
reaction: in-the-moment emotional response to a recent event; little/no argument.
mixed:    a genuine blend (emotion AND a real argument) where neither dominates.
skip:     not English / unreadable / pure news report with no opinion or argument.

Judge sarcasm by real intent. Judge "analysis" by whether the evidence is the kind of
specific claim that could be checked, not whether you can confirm the exact number.

Respond with ONLY a JSON object:
{"label": "<one label>", "confidence": <0..1>, "sarcasm": <true|false>,
 "verifiable": <true|false>, "rationale": "<<=15 words>"}
""".strip()


def get_client():
    try:
        from dotenv import load_dotenv
        load_dotenv(os.path.join(REPO, ".env"))   # read-only
    except Exception:
        pass
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        sys.exit("GROQ_API_KEY not found in ../.env — add it (read-only) and retry.")
    try:
        from groq import Groq
    except ImportError:
        sys.exit("groq not installed — run: pip install groq python-dotenv joblib")
    return Groq(api_key=key)


def label_one(client, text, max_retries=4):
    for attempt in range(max_retries):
        try:
            resp = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "system", "content": SYSTEM_PROMPT},
                          {"role": "user", "content": f"Classify this post:\n\n{text}"}],
                temperature=0, max_tokens=120,
                response_format={"type": "json_object"},
            )
            d = json.loads(resp.choices[0].message.content)
            label = str(d.get("label", "")).strip().lower()
            if label not in LABELS:
                label = next((l for l in LABELS if l in label), "skip")
            return {
                "label": label,
                "confidence": round(float(d.get("confidence", 0.5)), 2),
                "sarcasm": bool(d.get("sarcasm", False)),
                "verifiable": bool(d.get("verifiable", False)),
                "rationale": str(d.get("rationale", ""))[:120],
            }
        except Exception as e:
            msg = str(e).lower()
            if ("429" in msg or "rate" in msg or "timeout" in msg) and attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            return {"label": "skip", "confidence": 0.0, "sarcasm": False,
                    "verifiable": False, "rationale": f"error: {e}"[:120]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="label only the first N (0 = all)")
    ap.add_argument("--jobs", type=int, default=8, help="parallel API calls")
    args = ap.parse_args()

    with open(EXAMPLES, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if args.limit:
        rows = rows[: args.limit]

    client = get_client()
    from joblib import Parallel, delayed

    print(f"Labeling {len(rows)} examples with Groq ({args.jobs} parallel)...")
    t0 = time.time()
    results = Parallel(n_jobs=args.jobs, backend="threading")(
        delayed(label_one)(client, r["text"]) for r in rows
    )
    print(f"Done in {time.time() - t0:.1f}s")

    os.makedirs(GROQ_DIR, exist_ok=True)
    with open(GROQ_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["id", "label", "confidence", "sarcasm",
                                          "verifiable", "rationale"])
        w.writeheader()
        for r, res in zip(rows, results):
            w.writerow({"id": r["id"], **res})

    with open(HINTS_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["id", "sarcasm", "verifiable", "note"])
        w.writeheader()
        for r, res in zip(rows, results):
            w.writerow({"id": r["id"], "sarcasm": res["sarcasm"],
                        "verifiable": res["verifiable"], "note": res["rationale"]})

    from collections import Counter
    dist = Counter(res["label"] for res in results)
    print(f"✅ wrote {GROQ_CSV}")
    print(f"✅ wrote {HINTS_CSV} (context hints for the web Train page)")
    print("   label distribution:", dict(dist))
    print("   ⚠️  these are PRE-labels — review them; train on labels/human/ only.")


if __name__ == "__main__":
    main()
