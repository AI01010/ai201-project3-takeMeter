"""Shared helpers for one-shot batch labeling (SambaNova + Gemini annotators).

Both providers label ALL 200 posts in a SINGLE request per model — one prompt in,
one JSON array of {id,label} out. That keeps us to one API call per model so a
single (shared, rate-limited) key is never hammered. Output is parsed leniently so
chatty / reasoning models that wrap the JSON in prose or fences still work.
"""
from __future__ import annotations

import csv
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
EXAMPLES = os.path.join(REPO, "data", "examples_to_label.csv")
VALID = ["analysis", "hot_take", "reaction", "mixed", "skip"]

# Same rubric the human/Groq annotators used — verbatim so the comparison is fair.
RUBRIC = """You are an expert annotator for TakeMeter, rating the discourse quality of
football (soccer) posts (World Cup, MLS, clubs). Assign each post EXACTLY ONE label,
using outside knowledge as context (don't take posts at face value):

analysis : structured argument with specific, verifiable evidence (stats/history/tactics).
hot_take : bold, confident opinion with NO real evidence; asserts instead of arguing;
           often contrarian, or props itself up with a cherry-picked/decorative "stat".
reaction : in-the-moment emotional response to a recent event; little or no argument.
mixed    : a genuine blend (real emotion AND a real argument) where neither dominates.
skip     : not English / unreadable / a pure news report with no opinion or argument.

Decision order: specific verifiable evidence -> analysis; vague/decorative evidence ->
hot_take; in-the-moment emotion, no argument -> reaction; genuine emotion+argument blend
-> mixed; pure news/unreadable -> skip. Judge sarcasm by real intent."""


def load_env(*names: str) -> dict[str, str]:
    """Read KEY=VALUE pairs from repo-root .env, stripping surrounding quotes."""
    env: dict[str, str] = {}
    path = os.path.join(REPO, ".env")
    if os.path.isfile(path):
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    missing = [n for n in names if not env.get(n)]
    if missing:
        raise SystemExit(f"Missing in .env: {', '.join(missing)}")
    return env


def load_examples() -> list[dict]:
    with open(EXAMPLES, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def build_messages(rows: list[dict]) -> list[dict]:
    """One user message listing all posts; strict JSON-array instruction."""
    lines = []
    for r in rows:
        text = " ".join(str(r["text"]).split())   # flatten any internal newlines
        lines.append(f'{r["id"]}\t{text}')
    posts = "\n".join(lines)
    instruction = (
        f"{RUBRIC}\n\n"
        f"Below are {len(rows)} posts, one per line as `id<TAB>text`. Label EVERY one.\n"
        "Respond with ONLY a JSON array of objects, no prose and no code fences:\n"
        '[{"id": 1, "label": "analysis"}, {"id": 2, "label": "skip"}, ...]\n'
        f"Return exactly {len(rows)} objects, ids 1..{len(rows)}, label from "
        "[analysis, hot_take, reaction, mixed, skip].\n\n"
        f"POSTS:\n{posts}"
    )
    return [{"role": "user", "content": instruction}]


def parse_labels(text: str, ids: list[str]) -> tuple[dict[str, str], int]:
    """Lenient extraction of {id: label} from a model reply. Returns (map, n_parsed)."""
    out: dict[str, str] = {}
    if not text:
        return out, 0
    # 1) try to load the JSON array directly (strip fences first)
    body = text.strip()
    body = re.sub(r"^```(?:json)?|```$", "", body.strip(), flags=re.MULTILINE).strip()
    m = re.search(r"\[.*\]", body, flags=re.DOTALL)
    if m:
        try:
            for obj in json.loads(m.group(0)):
                _add(out, obj.get("id"), obj.get("label"))
        except Exception:
            pass
    # 2) regex fallback for any {... "id": N ... "label": "x" ...} (either key order)
    if len(out) < len(ids):
        for a, b in re.findall(
                r'"id"\s*:\s*(\d+)\s*,\s*"label"\s*:\s*"([a-zA-Z_]+)"', body):
            _add(out, a, b)
        for b, a in re.findall(
                r'"label"\s*:\s*"([a-zA-Z_]+)"\s*,\s*"id"\s*:\s*(\d+)', body):
            _add(out, a, b)
    return out, len(out)


def _add(out: dict, rid, label) -> None:
    if rid is None or label is None:
        return
    rid = str(rid).strip()
    lab = str(label).strip().lower()
    if lab not in VALID:
        lab = next((v for v in VALID if v in lab), "skip")
    if rid:
        out[rid] = lab


def write_csv(folder: str, rows: list[dict], labels: dict[str, str],
              model_id: str) -> dict[str, int]:
    """Write labels/<folder>/labeled.csv; fill any missing id with skip."""
    out_dir = os.path.join(HERE, folder)
    os.makedirs(out_dir, exist_ok=True)
    dist: dict[str, int] = {}
    with open(os.path.join(out_dir, "labeled.csv"), "w", newline="",
              encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["id", "label", "confidence", "rationale"])
        w.writeheader()
        for r in rows:
            rid = str(r["id"])
            lab = labels.get(rid)
            note = f"one-shot batch ({model_id})" if lab else "missing from batch reply"
            lab = lab or "skip"
            w.writerow({"id": rid, "label": lab, "confidence": "",
                        "rationale": note})
            dist[lab] = dist.get(lab, 0) + 1
    return dist
