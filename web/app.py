"""TakeMeter web app.

Two pages:
  /        Home / Test page  — paste a new post, get a predicted label + confidence.
  /train   Train page        — label the 200 examples fast (keyboard-driven).

The Train page reads data/examples_to_label.csv and writes your reviewed labels to
labels/human/labeled.csv (the file you upload to the Colab notebook for training).
The Test page classifies with the best available backend (see classifier.py).

Run:  cd web && python app.py   →   http://127.0.0.1:5000
"""
from __future__ import annotations

import csv
import io
import json
import os
import threading

from flask import (Flask, Response, jsonify, render_template, request,
                   send_file)

import classifier

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
EXAMPLES_CSV = os.path.join(REPO, "data", "examples_to_label.csv")
HINTS_CSV = os.path.join(REPO, "data", "context_hints.csv")
HUMAN_DIR = os.path.join(REPO, "labels", "human")
HUMAN_CSV = os.path.join(HUMAN_DIR, "labeled.csv")
TAXONOMY = os.path.join(REPO, "taxonomy.json")

VALID_LABELS = {"analysis", "hot_take", "reaction", "mixed", "skip"}

app = Flask(__name__)
_lock = threading.Lock()   # guards the in-memory label store + CSV writes


# ── Data loading ───────────────────────────────────────────────────────────
def load_examples() -> list[dict]:
    if not os.path.isfile(EXAMPLES_CSV):
        return []
    with open(EXAMPLES_CSV, newline="", encoding="utf-8") as f:
        return [{"id": str(r["id"]), "text": r["text"], "source": r.get("source", "")}
                for r in csv.DictReader(f)]


def load_taxonomy() -> dict:
    with open(TAXONOMY, encoding="utf-8") as f:
        return json.load(f)


def load_labels() -> dict[str, dict]:
    """id -> {label, notes} from the human labeled.csv (if it exists)."""
    out: dict[str, dict] = {}
    if os.path.isfile(HUMAN_CSV):
        with open(HUMAN_CSV, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                out[str(r["id"])] = {"label": r.get("label", ""),
                                     "notes": r.get("notes", "")}
    return out


def load_hints() -> dict[str, dict]:
    """id -> {sarcasm, verifiable, note} context hints from Groq, if generated.

    Produced by labels/label_with_groq.py. Shown on the Train page to help you
    judge sarcasm / whether a claim is checkable — supports faster, better labels.
    """
    out: dict[str, dict] = {}
    if os.path.isfile(HINTS_CSV):
        with open(HINTS_CSV, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                out[str(r["id"])] = {
                    "sarcasm": str(r.get("sarcasm", "")).strip().lower() == "true",
                    "verifiable": str(r.get("verifiable", "")).strip().lower() == "true",
                    "note": r.get("note", ""),
                }
    return out


EXAMPLES = load_examples()
EXAMPLE_TEXT = {e["id"]: e["text"] for e in EXAMPLES}
LABELS = load_labels()           # mutable in-memory store, write-through to disk
HINTS = load_hints()             # optional Groq context hints (sarcasm/verifiable)
TAX = load_taxonomy()


def save_labels() -> None:
    """Persist the full labeled set to labels/human/labeled.csv (id,text,label,notes).

    Includes `text` so the file is directly uploadable to the Colab notebook,
    and `id` so labels/compare_labels.py can align annotators.
    """
    os.makedirs(HUMAN_DIR, exist_ok=True)
    with open(HUMAN_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["id", "text", "label", "notes"])
        w.writeheader()
        for ex in EXAMPLES:
            rec = LABELS.get(ex["id"])
            if rec and rec.get("label"):
                w.writerow({"id": ex["id"], "text": ex["text"],
                            "label": rec["label"], "notes": rec.get("notes", "")})


# ── Pages ──────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html", backend=classifier.active_backend(),
                           taxonomy=TAX)


@app.route("/train")
def train():
    return render_template("train.html", taxonomy=TAX, total=len(EXAMPLES))


# ── API ────────────────────────────────────────────────────────────────────
@app.route("/api/taxonomy")
def api_taxonomy():
    return jsonify(TAX)


@app.route("/api/examples")
def api_examples():
    rows = []
    for e in EXAMPLES:
        row = {**e, **LABELS.get(e["id"], {"label": "", "notes": ""})}
        if e["id"] in HINTS:
            row["hint"] = HINTS[e["id"]]
        rows.append(row)
    counts: dict[str, int] = {}
    for r in rows:
        if r["label"]:
            counts[r["label"]] = counts.get(r["label"], 0) + 1
    return jsonify({"examples": rows, "counts": counts, "has_hints": bool(HINTS),
                    "labeled": sum(counts.values()), "total": len(rows)})


@app.route("/api/label", methods=["POST"])
def api_label():
    data = request.get_json(force=True) or {}
    ex_id = str(data.get("id", "")).strip()
    label = str(data.get("label", "")).strip().lower()
    notes = str(data.get("notes", "")).strip()

    if ex_id not in EXAMPLE_TEXT:
        return jsonify({"ok": False, "error": f"unknown id {ex_id!r}"}), 400
    if label and label not in VALID_LABELS:
        return jsonify({"ok": False, "error": f"invalid label {label!r}"}), 400

    with _lock:
        if not label:
            LABELS.pop(ex_id, None)          # clearing a label
        else:
            LABELS[ex_id] = {"label": label, "notes": notes}
        save_labels()
        labeled = sum(1 for v in LABELS.values() if v.get("label"))

    return jsonify({"ok": True, "id": ex_id, "label": label, "labeled": labeled,
                    "total": len(EXAMPLES)})


@app.route("/api/export")
def api_export():
    """Download labels/human/labeled.csv (regenerated fresh)."""
    with _lock:
        save_labels()
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=["id", "text", "label", "notes"])
    w.writeheader()
    for ex in EXAMPLES:
        rec = LABELS.get(ex["id"])
        if rec and rec.get("label"):
            w.writerow({"id": ex["id"], "text": ex["text"],
                        "label": rec["label"], "notes": rec.get("notes", "")})
    return Response(
        buf.getvalue(), mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=labeled.csv"})


@app.route("/api/classify", methods=["POST"])
def api_classify():
    data = request.get_json(force=True) or {}
    text = str(data.get("text", "")).strip()
    if not text:
        return jsonify({"ok": False, "error": "empty text"}), 400
    return jsonify({"ok": True, **classifier.classify(text)})


@app.route("/api/status")
def api_status():
    with _lock:
        labeled = sum(1 for v in LABELS.values() if v.get("label"))
    return jsonify({"backend": classifier.active_backend(),
                    "labeled": labeled, "total": len(EXAMPLES)})


if __name__ == "__main__":
    print("=" * 60)
    print(" TakeMeter web app")
    print(f"   examples : {len(EXAMPLES)} loaded from data/examples_to_label.csv")
    print(f"   labeled  : {sum(1 for v in LABELS.values() if v.get('label'))} already in labels/human/")
    print(f"   backend  : {classifier.active_backend()}  (model > groq > heuristic)")
    print("   open     : http://127.0.0.1:5000   (/ = test,  /train = label)")
    print("=" * 60)
    app.run(host="127.0.0.1", port=5000, debug=True)
