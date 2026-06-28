"""Label all 200 examples with several SambaNova models — the 4th+ annotators.

ONE batched request per model (all 200 posts in, one JSON array out), run
sequentially with a pause between models, because a single SambaNova API key is
shared across every model and is rate-limited. Each model writes its own
labels/<slug>/labeled.csv so labels/compare_labels.py can score them.

SambaNova is OpenAI-compatible, so we hit /v1/chat/completions with `requests`
(no SDK needed). The model list is whatever this key can actually reach — query
it with `--list` if SambaNova rotates its registry.

Requires: SAMBA_NOVA_API_KEY in ../.env

Usage:
    python labels/label_with_sambanova.py            # label with all models below
    python labels/label_with_sambanova.py --list      # just print available models
    python labels/label_with_sambanova.py --only gpt-oss-120b
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

BASE = "https://api.sambanova.ai/v1"

# (model id on SambaNova, folder slug, extra request params). Edit if --list differs.
# gpt-oss is a reasoning model: cap its reasoning_effort so the chain-of-thought
# doesn't eat the token budget before it emits the JSON answer.
# MiniMax-M2.7 is intentionally omitted — it returns HTTP 402 (paid plan required)
# on the free key. Add ("MiniMax-M2.7", "minimax-m2.7", {}) back if you enable billing.
MODELS = [
    ("Meta-Llama-3.3-70B-Instruct", "llama-3.3-70b", {}),
    ("DeepSeek-V3.1",               "deepseek-v3.1", {}),
    ("DeepSeek-V3.2",               "deepseek-v3.2", {}),
    ("gemma-4-31B-it",              "gemma-4-31b",   {}),
    ("gpt-oss-120b",                "gpt-oss-120b",  {"reasoning_effort": "low"}),
]

PAUSE_BETWEEN_MODELS = 4   # seconds — gentle on the shared key's rate limit


def list_models(key: str) -> None:
    r = requests.get(f"{BASE}/models",
                     headers={"Authorization": f"Bearer {key}"}, timeout=30)
    r.raise_for_status()
    print("Available SambaNova models for this key:")
    for m in sorted(d["id"] for d in r.json().get("data", [])):
        print("  ", m)


def call_model(key: str, model_id: str, messages: list[dict],
               extra: dict | None = None) -> str:
    """One chat completion. Retries on 429/5xx with backoff; max_tokens fallback.

    16000 tokens first (reasoning models need headroom for thoughts + the JSON),
    then 8000 as a fallback for any backend that caps lower.
    """
    extra = extra or {}
    for max_tok in (16000, 8000):
        for attempt in range(4):
            try:
                r = requests.post(
                    f"{BASE}/chat/completions",
                    headers={"Authorization": f"Bearer {key}",
                             "Content-Type": "application/json"},
                    json={"model": model_id, "messages": messages,
                          "temperature": 0, "max_tokens": max_tok, **extra},
                    timeout=300)
                if r.status_code == 200:
                    return r.json()["choices"][0]["message"]["content"] or ""
                if r.status_code in (429, 500, 502, 503, 504) and attempt < 3:
                    time.sleep(2 ** attempt * 3)
                    continue
                # 400 with a token cap → try the smaller max_tokens
                if r.status_code == 400 and max_tok == 16000:
                    break
                print(f"    HTTP {r.status_code}: {r.text[:160]}")
                return ""
            except Exception as e:
                if attempt < 3:
                    time.sleep(2 ** attempt * 3)
                else:
                    print(f"    request error: {str(e)[:160]}")
                    return ""
    return ""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true", help="print available models and exit")
    ap.add_argument("--only", help="label with just this model id")
    args = ap.parse_args()

    key = load_env("SAMBA_NOVA_API_KEY")["SAMBA_NOVA_API_KEY"]
    if args.list:
        list_models(key)
        return

    rows = load_examples()
    ids = [str(r["id"]) for r in rows]
    messages = build_messages(rows)
    targets = [m for m in MODELS if (not args.only or m[0] == args.only)]
    if not targets:
        sys.exit(f"--only {args.only!r} not in MODELS")

    print(f"Labeling {len(rows)} posts with {len(targets)} SambaNova model(s), "
          f"one batched call each...\n")
    for i, (model_id, slug, extra) in enumerate(targets):
        t0 = time.time()
        print(f"[{i+1}/{len(targets)}] {model_id}  -> labels/{slug}/")
        reply = call_model(key, model_id, messages, extra)
        labels, n = parse_labels(reply, ids)
        dist = write_csv(slug, rows, labels, model_id)
        print(f"    parsed {n}/{len(rows)} in {time.time()-t0:.0f}s  dist={dist}")
        if i < len(targets) - 1:
            time.sleep(PAUSE_BETWEEN_MODELS)
    print("\n✅ done — run: python labels/compare_labels.py")


if __name__ == "__main__":
    main()
