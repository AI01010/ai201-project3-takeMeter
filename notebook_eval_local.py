"""Local reproduction of the notebook's evaluation loop (Sections 4-7).

Runs the REAL pipeline end-to-end on the reviewed human labels so the README can
report numbers that were actually observed, not placeholders:

  * loads labels/human/labeled.csv, drops `skip`, maps the 4 trainable classes
  * the same stratified 70/15/15 split as the notebook (random_state=42)
  * fine-tunes distilbert-base-uncased (CPU here; T4 fp16 in the Colab notebook)
  * runs the Groq llama-3.3-70b zero-shot baseline on the same test set
  * writes evaluation_results.json + confusion_matrix.png at the repo root
    (identical schema/filenames to notebook cells 16 & 25) and a companion
    evaluation_details.json with the wrong predictions + sample classifications
    used in the README write-up.

This is the local/CPU mirror of the Colab notebook — same data, same split, same
metrics. Re-running the notebook on a T4 reproduces the methodology at scale.

Usage:  .venv/Scripts/python.exe notebook_eval_local.py [--epochs 5]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np
import pandas as pd
import torch
from sklearn.metrics import (accuracy_score, classification_report,
                             confusion_matrix, f1_score)
from sklearn.model_selection import train_test_split

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
HUMAN_CSV = os.path.join(HERE, "labels", "human", "labeled.csv")
RESULTS_JSON = os.path.join(HERE, "evaluation_results.json")
DETAILS_JSON = os.path.join(HERE, "evaluation_details.json")
CM_PNG = os.path.join(HERE, "confusion_matrix.png")

MODEL_NAME = "distilbert-base-uncased"
LABEL_MAP = {"analysis": 0, "hot_take": 1, "reaction": 2, "mixed": 3}
ID_TO_LABEL = {v: k for k, v in LABEL_MAP.items()}
LABEL_NAMES = [ID_TO_LABEL[i] for i in range(len(LABEL_MAP))]
NON_TRAINING = {"skip", "unlabeled", "popular", "", "nan"}

SEED = 42


def set_seed(s=SEED):
    np.random.seed(s)
    torch.manual_seed(s)


# ── Data ─────────────────────────────────────────────────────────────────────
def load_split():
    df = pd.read_csv(HUMAN_CSV)
    df["text"] = df["text"].astype(str).str.strip()
    df["label"] = df["label"].astype(str).str.strip().str.lower()
    df = df[~df["label"].isin(NON_TRAINING)].copy()
    df["label_id"] = df["label"].map(LABEL_MAP)
    df = df.dropna(subset=["label_id"])
    df["label_id"] = df["label_id"].astype(int)

    train_df, temp_df = train_test_split(
        df, test_size=0.30, random_state=SEED, stratify=df["label_id"])
    val_df, test_df = train_test_split(
        temp_df, test_size=0.50, random_state=SEED, stratify=temp_df["label_id"])
    return (df,
            train_df.reset_index(drop=True),
            val_df.reset_index(drop=True),
            test_df.reset_index(drop=True))


# ── Fine-tune (manual loop; transformers 5.x Trainer API differs from notebook) ─
def fine_tune(train_df, val_df, test_df, epochs, lr=2e-5, batch=16, max_len=128):
    from transformers import (AutoModelForSequenceClassification,
                              AutoTokenizer, get_linear_schedule_with_warmup)
    set_seed()
    tok = AutoTokenizer.from_pretrained(MODEL_NAME)

    def encode(texts):
        return tok(list(texts), truncation=True, padding=True,
                   max_length=max_len, return_tensors="pt")

    tr = encode(train_df["text"]); tr_y = torch.tensor(train_df["label_id"].values)
    va = encode(val_df["text"]);   va_y = torch.tensor(val_df["label_id"].values)
    te = encode(test_df["text"])

    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_NAME, num_labels=len(LABEL_MAP))
    model.train()
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=0.01)
    n = len(tr_y)
    steps = (n + batch - 1) // batch * epochs
    sched = get_linear_schedule_with_warmup(opt, int(0.1 * steps), steps)

    def val_macro_f1():
        model.eval()
        with torch.no_grad():
            logits = model(input_ids=va["input_ids"],
                           attention_mask=va["attention_mask"]).logits
        model.train()
        pred = logits.argmax(-1).numpy()
        return f1_score(va_y.numpy(), pred, average="macro", zero_division=0)

    best_f1, best_state = -1.0, None
    g = torch.Generator().manual_seed(SEED)
    for ep in range(epochs):
        perm = torch.randperm(n, generator=g)
        tot = 0.0
        for i in range(0, n, batch):
            idx = perm[i:i + batch]
            opt.zero_grad()
            out = model(input_ids=tr["input_ids"][idx],
                        attention_mask=tr["attention_mask"][idx],
                        labels=tr_y[idx])
            out.loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step(); sched.step()
            tot += out.loss.item()
        vf1 = val_macro_f1()
        print(f"  epoch {ep+1}/{epochs}  train_loss={tot:.3f}  val_macro_f1={vf1:.3f}")
        if vf1 >= best_f1:
            best_f1, best_state = vf1, {k: v.clone() for k, v in model.state_dict().items()}

    if best_state:
        model.load_state_dict(best_state)   # load_best_model_at_end (by val macro-F1)
    model.eval()
    with torch.no_grad():
        logits = model(input_ids=te["input_ids"],
                       attention_mask=te["attention_mask"]).logits
    probs = torch.softmax(logits, dim=-1).numpy()
    preds = logits.argmax(-1).numpy()
    return preds, probs


# ── Groq zero-shot baseline (same prompt/model as labels/label_with_groq.py) ───
GROQ_SYSTEM = """
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
{"label": "<one label>", "confidence": <0..1>, "rationale": "<<=15 words>"}
""".strip()


def groq_baseline(test_df):
    try:
        from dotenv import load_dotenv
        load_dotenv(os.path.join(HERE, ".env"))
    except Exception:
        pass
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        print("  (no GROQ_API_KEY — skipping baseline)")
        return None
    try:
        from groq import Groq
    except ImportError:
        print("  (groq not installed — skipping baseline)")
        return None
    client = Groq(api_key=key)

    def one(text):
        for attempt in range(5):
            try:
                r = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "system", "content": GROQ_SYSTEM},
                              {"role": "user", "content": f"Classify this post:\n\n{text}"}],
                    temperature=0, max_tokens=120,
                    response_format={"type": "json_object"})
                lab = str(json.loads(r.choices[0].message.content).get("label", "")).strip().lower()
                if lab not in LABEL_MAP and lab != "skip":
                    lab = next((l for l in list(LABEL_MAP) + ["skip"] if l in lab), None)
                return lab
            except Exception as e:
                if attempt < 4:
                    time.sleep(2 ** attempt)
                else:
                    print(f"    groq error: {str(e)[:80]}")
                    return None
        return None

    preds = []
    for t in test_df["text"]:
        preds.append(one(t))
        time.sleep(0.8)   # gentle on the rate limit
    return preds


# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=5)
    ap.add_argument("--no-baseline", action="store_true")
    args = ap.parse_args()

    full, train_df, val_df, test_df = load_split()
    print(f"Trainable examples: {len(full)}  (train {len(train_df)} / "
          f"val {len(val_df)} / test {len(test_df)})")
    print("Test label distribution:", dict(test_df["label"].value_counts()))

    print(f"\nFine-tuning {MODEL_NAME} (CPU, {args.epochs} epochs)...")
    t0 = time.time()
    ft_pred, ft_probs = fine_tune(train_df, val_df, test_df, args.epochs)
    print(f"  done in {time.time()-t0:.0f}s")

    ft_true = test_df["label_id"].values
    ft_acc = accuracy_score(ft_true, ft_pred)
    ft_f1 = f1_score(ft_true, ft_pred, average="macro", zero_division=0)
    print(f"\nFine-tuned accuracy={ft_acc:.3f}  macro_f1={ft_f1:.3f}")
    print(classification_report(ft_true, ft_pred, target_names=LABEL_NAMES,
                                zero_division=0))
    ft_report = classification_report(ft_true, ft_pred, target_names=LABEL_NAMES,
                                      output_dict=True, zero_division=0)
    cm = confusion_matrix(ft_true, ft_pred, labels=list(range(len(LABEL_MAP))))

    # Baseline
    bl_block = None
    if not args.no_baseline:
        print("\nRunning Groq zero-shot baseline on the test set...")
        bl_raw = groq_baseline(test_df)
        if bl_raw is not None:
            valid = [(p, t) for p, t in zip(bl_raw, test_df["label_id"])
                     if p in LABEL_MAP]
            if valid:
                bl_pred = [LABEL_MAP[p] for p, _ in valid]
                bl_true = [t for _, t in valid]
                bl_acc = accuracy_score(bl_true, bl_pred)
                bl_rep = classification_report(bl_true, bl_pred,
                                               target_names=LABEL_NAMES,
                                               output_dict=True, zero_division=0)
                print(f"Baseline accuracy={bl_acc:.3f} on {len(valid)}/{len(test_df)} parsed")
                bl_block = {
                    "accuracy": round(bl_acc, 4),
                    "macro_f1": round(bl_rep["macro avg"]["f1-score"], 4),
                    "per_class_f1": {l: round(bl_rep[l]["f1-score"], 4) for l in LABEL_NAMES},
                    "parsed": len(valid),
                    "raw_preds": bl_raw,
                }

    # Confusion matrix PNG (same as notebook cell 16)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from sklearn.metrics import ConfusionMatrixDisplay
    disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=LABEL_NAMES)
    fig, ax = plt.subplots(figsize=(7, 5))
    disp.plot(ax=ax, cmap="Blues", colorbar=False)
    ax.set_title("Fine-Tuned DistilBERT — Confusion Matrix (Test Set)")
    plt.tight_layout()
    plt.savefig(CM_PNG, dpi=150)
    print(f"\nSaved {CM_PNG}")

    results = {
        "model": MODEL_NAME,
        "run_environment": "local CPU mirror of the Colab notebook (same data/split/metrics)",
        "epochs": args.epochs,
        "test_set_size": int(len(test_df)),
        "label_map": LABEL_MAP,
        "baseline": bl_block,
        "finetuned": {
            "accuracy": round(ft_acc, 4),
            "macro_f1": round(ft_report["macro avg"]["f1-score"], 4),
            "per_class_f1": {l: round(ft_report[l]["f1-score"], 4) for l in LABEL_NAMES},
            "per_class_precision": {l: round(ft_report[l]["precision"], 4) for l in LABEL_NAMES},
            "per_class_recall": {l: round(ft_report[l]["recall"], 4) for l in LABEL_NAMES},
            "per_class_support": {l: int(ft_report[l]["support"]) for l in LABEL_NAMES},
        },
        "improvement_accuracy": (round(ft_acc - bl_block["accuracy"], 4)
                                 if bl_block else None),
        "confusion_matrix": cm.tolist(),
        "confusion_matrix_labels": LABEL_NAMES,
    }
    with open(RESULTS_JSON, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"Saved {RESULTS_JSON}")

    # Companion: wrong predictions + sample classifications for the README
    wrong, samples = [], []
    for i in range(len(test_df)):
        row = test_df.iloc[i]
        rec = {
            "id": int(row["id"]),
            "text": row["text"],
            "true": ID_TO_LABEL[int(ft_true[i])],
            "pred": ID_TO_LABEL[int(ft_pred[i])],
            "confidence": round(float(ft_probs[i][ft_pred[i]]), 3),
        }
        samples.append(rec)
        if ft_pred[i] != ft_true[i]:
            wrong.append(rec)
    with open(DETAILS_JSON, "w", encoding="utf-8") as f:
        json.dump({"wrong": wrong, "all_test": samples,
                   "baseline_raw": bl_block["raw_preds"] if bl_block else None},
                  f, indent=2)
    print(f"Saved {DETAILS_JSON}  ({len(wrong)} wrong / {len(test_df)})")


if __name__ == "__main__":
    main()
