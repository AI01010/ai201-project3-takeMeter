"""Inter-annotator reliability for TakeMeter.

Compares the human (ground-truth) labels against each model's labels and against
each other, reporting % agreement and Cohen's kappa per pair, plus a list of the
biggest disagreements (where the models split). Supports the "inter-annotator
reliability" stretch goal and the AI-pre-labeling disclosure.

Expects, where present:
    labels/human/labeled.csv      <- your reviewed labels (ground truth)
    labels/claude/labeled.csv
    labels/codex/labeled.csv
    labels/copilot/labeled.csv

Each file: columns `id,label,...` (extra columns ignored).

Usage:
    python labels/compare_labels.py
"""
from __future__ import annotations

import csv
import os
import sys
from itertools import combinations

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
ANNOTATORS = ["human", "claude", "codex", "copilot", "groq"]
TRAIN_LABELS = ["analysis", "hot_take", "reaction", "mixed"]


def load(annotator: str) -> dict[str, str]:
    path = os.path.join(HERE, annotator, "labeled.csv")
    if not os.path.exists(path):
        return {}
    out = {}
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            lid = str(row.get("id", "")).strip()
            lab = str(row.get("label", "")).strip().lower()
            if lid and lab:
                out[lid] = lab
    return out


def cohen_kappa(pairs: list[tuple[str, str]]) -> float:
    """Cohen's kappa from a list of (a_label, b_label) pairs. No deps."""
    n = len(pairs)
    if n == 0:
        return float("nan")
    labels = sorted({l for p in pairs for l in p})
    # observed agreement
    po = sum(1 for a, b in pairs if a == b) / n
    # expected agreement from marginals
    from collections import Counter
    ca, cb = Counter(a for a, _ in pairs), Counter(b for _, b in pairs)
    pe = sum((ca[l] / n) * (cb[l] / n) for l in labels)
    if pe == 1.0:
        return 1.0
    return (po - pe) / (1 - pe)


def interpret(k: float) -> str:
    if k != k:  # nan
        return "n/a"
    if k < 0.0:
        return "worse than chance"
    if k < 0.20:
        return "slight"
    if k < 0.40:
        return "fair"
    if k < 0.60:
        return "moderate"
    if k < 0.80:
        return "substantial"
    return "almost perfect"


def main() -> None:
    data = {a: load(a) for a in ANNOTATORS}
    present = [a for a in ANNOTATORS if data[a]]
    if len(present) < 2:
        print("Need at least two label files to compare. Found:",
              present or "none")
        print("Label some examples first (web Train page -> labels/human/, "
              "or run the model prompts in prompts/).")
        return

    print("=" * 60)
    print("INTER-ANNOTATOR RELIABILITY")
    print("=" * 60)
    print(f"{'pair':<22}{'n':>5}{'agree%':>9}{'kappa':>8}  strength")
    print("-" * 60)
    for a, b in combinations(present, 2):
        ids = sorted(set(data[a]) & set(data[b]))
        pairs = [(data[a][i], data[b][i]) for i in ids]
        if not pairs:
            continue
        agree = sum(1 for x, y in pairs if x == y) / len(pairs)
        k = cohen_kappa(pairs)
        print(f"{a+'/'+b:<22}{len(pairs):>5}{agree*100:>8.1f}%{k:>8.2f}  {interpret(k)}")

    # Disagreement spotlight vs human (or first annotator if no human file)
    ref = "human" if data["human"] else present[0]
    others = [a for a in present if a != ref]
    if others:
        print()
        print(f"Biggest disagreements vs '{ref}' (first 15):")
        ids = sorted(set(data[ref]))
        rows = []
        for i in ids:
            votes = {o: data[o].get(i) for o in others if i in data[o]}
            disagree = sum(1 for v in votes.values() if v and v != data[ref][i])
            if disagree:
                rows.append((disagree, i, data[ref][i], votes))
        rows.sort(reverse=True)
        for disagree, i, refl, votes in rows[:15]:
            others_str = ", ".join(f"{o}={v}" for o, v in votes.items())
            print(f"  id {i:>4}: {ref}={refl:<10} | {others_str}")
        if not rows:
            print("  (no disagreements — suspiciously high agreement, double-check)")


if __name__ == "__main__":
    main()
