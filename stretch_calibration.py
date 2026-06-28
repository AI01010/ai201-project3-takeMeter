"""Stretch goals: confidence calibration + systematic error-pattern analysis.

A single 17-row test set (notebook_eval_local.py) is too small to say anything
honest about calibration, so this trains the SAME DistilBERT setup with 5-fold
cross-validation and collects an out-of-fold prediction + confidence for ALL 111
trainable examples. From those OOF predictions it reports:

  * calibration — reliability table + Expected Calibration Error (ECE), and the
    "does a 90%-confident prediction beat a 60%-confident one?" check
  * error patterns — OOF confusion matrix, per-class recall, the mixed-class
    collapse, and accuracy split by post length

Writes stretch_results.json + reliability_diagram.png at the repo root.

Usage:  .venv/Scripts/python.exe stretch_calibration.py [--epochs 5]
"""
from __future__ import annotations

import argparse
import json
import os
import time

import numpy as np
import pandas as pd
import torch
from sklearn.metrics import (accuracy_score, classification_report,
                             confusion_matrix, f1_score)
from sklearn.model_selection import StratifiedKFold

HERE = os.path.dirname(os.path.abspath(__file__))
HUMAN_CSV = os.path.join(HERE, "labels", "human", "labeled.csv")
OUT_JSON = os.path.join(HERE, "stretch_results.json")
DIAGRAM = os.path.join(HERE, "reliability_diagram.png")

MODEL_NAME = "distilbert-base-uncased"
LABEL_MAP = {"analysis": 0, "hot_take": 1, "reaction": 2, "mixed": 3}
ID2LAB = {v: k for k, v in LABEL_MAP.items()}
NAMES = [ID2LAB[i] for i in range(4)]
NON_TRAINING = {"skip", "unlabeled", "popular", "", "nan"}
SEED = 42


def load_df():
    df = pd.read_csv(HUMAN_CSV)
    df["text"] = df["text"].astype(str).str.strip()
    df["label"] = df["label"].astype(str).str.strip().str.lower()
    df = df[~df["label"].isin(NON_TRAINING)].copy()
    df["label_id"] = df["label"].map(LABEL_MAP).astype(int)
    return df.reset_index(drop=True)


def train_predict(train_df, test_df, epochs, lr=2e-5, batch=16, max_len=128, seed=SEED):
    from transformers import (AutoModelForSequenceClassification, AutoTokenizer,
                              get_linear_schedule_with_warmup)
    np.random.seed(seed); torch.manual_seed(seed)
    tok = AutoTokenizer.from_pretrained(MODEL_NAME)

    def enc(t):
        return tok(list(t), truncation=True, padding=True, max_length=max_len,
                   return_tensors="pt")

    tr, tr_y = enc(train_df["text"]), torch.tensor(train_df["label_id"].values)
    te = enc(test_df["text"])
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME, num_labels=4)
    model.train()
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=0.01)
    n = len(tr_y)
    steps = (n + batch - 1) // batch * epochs
    sched = get_linear_schedule_with_warmup(opt, int(0.1 * steps), steps)
    g = torch.Generator().manual_seed(seed)
    for _ in range(epochs):
        perm = torch.randperm(n, generator=g)
        for i in range(0, n, batch):
            idx = perm[i:i + batch]
            opt.zero_grad()
            out = model(input_ids=tr["input_ids"][idx],
                        attention_mask=tr["attention_mask"][idx], labels=tr_y[idx])
            out.loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step(); sched.step()
    model.eval()
    with torch.no_grad():
        logits = model(input_ids=te["input_ids"],
                       attention_mask=te["attention_mask"]).logits
    probs = torch.softmax(logits, dim=-1).numpy()
    return probs.argmax(-1), probs.max(-1)


def ece(confs, correct, n_bins=10):
    """Expected Calibration Error over equal-width confidence bins."""
    confs, correct = np.array(confs), np.array(correct, dtype=float)
    edges = np.linspace(0, 1, n_bins + 1)
    e, rows = 0.0, []
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (confs > lo) & (confs <= hi)
        if m.sum() == 0:
            continue
        acc, conf = correct[m].mean(), confs[m].mean()
        e += (m.sum() / len(confs)) * abs(acc - conf)
        rows.append({"bin": f"{lo:.1f}-{hi:.1f}", "n": int(m.sum()),
                     "mean_conf": round(float(conf), 3), "accuracy": round(float(acc), 3)})
    return round(e, 4), rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=5)
    args = ap.parse_args()
    df = load_df()
    print(f"OOF over {len(df)} trainable examples, 5 folds, {args.epochs} epochs each")

    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)
    oof_pred = np.zeros(len(df), dtype=int)
    oof_conf = np.zeros(len(df))
    t0 = time.time()
    for k, (tr_idx, te_idx) in enumerate(skf.split(df["text"], df["label_id"])):
        pred, conf = train_predict(df.iloc[tr_idx], df.iloc[te_idx], args.epochs,
                                   seed=SEED + k)
        oof_pred[te_idx] = pred
        oof_conf[te_idx] = conf
        print(f"  fold {k+1}/5 done ({time.time()-t0:.0f}s elapsed)")

    true = df["label_id"].values
    correct = (oof_pred == true)
    acc = accuracy_score(true, oof_pred)
    mf1 = f1_score(true, oof_pred, average="macro", zero_division=0)
    print(f"\nOOF accuracy={acc:.3f}  macro_f1={mf1:.3f}")
    print(classification_report(true, oof_pred, target_names=NAMES, zero_division=0))

    e, bins = ece(oof_conf, correct)
    conf_correct = float(oof_conf[correct].mean())
    conf_wrong = float(oof_conf[~correct].mean()) if (~correct).any() else float("nan")
    # tercile check (proxy for "90% vs 60%")
    order = np.argsort(oof_conf)
    third = len(order) // 3
    low_acc = correct[order[:third]].mean()
    high_acc = correct[order[-third:]].mean()
    cm = confusion_matrix(true, oof_pred, labels=list(range(4)))

    # error pattern: mixed collapse + length effect
    mixed_idx = np.where(true == LABEL_MAP["mixed"])[0]
    mixed_pred_to = {ID2LAB[c]: int((oof_pred[mixed_idx] == c).sum()) for c in range(4)}
    n_mixed_predicted = int((oof_pred == LABEL_MAP["mixed"]).sum())
    lengths = df["text"].str.len().values
    med = float(np.median(lengths))
    short, long = lengths <= med, lengths > med
    rep = classification_report(true, oof_pred, target_names=NAMES,
                                output_dict=True, zero_division=0)

    results = {
        "method": "5-fold stratified out-of-fold predictions (distilbert-base-uncased, CPU)",
        "n": len(df), "epochs": args.epochs,
        "oof_accuracy": round(acc, 4), "oof_macro_f1": round(mf1, 4),
        "per_class_recall": {l: round(rep[l]["recall"], 3) for l in NAMES},
        "per_class_precision": {l: round(rep[l]["precision"], 3) for l in NAMES},
        "per_class_support": {l: int(rep[l]["support"]) for l in NAMES},
        "confusion_matrix": cm.tolist(), "confusion_matrix_labels": NAMES,
        "calibration": {
            "ece": e, "bins": bins,
            "mean_conf_when_correct": round(conf_correct, 3),
            "mean_conf_when_wrong": round(conf_wrong, 3),
            "acc_low_conf_third": round(float(low_acc), 3),
            "acc_high_conf_third": round(float(high_acc), 3),
            "conf_min": round(float(oof_conf.min()), 3),
            "conf_max": round(float(oof_conf.max()), 3),
        },
        "error_patterns": {
            "mixed_true_count": int(len(mixed_idx)),
            "mixed_predicted_count": n_mixed_predicted,
            "true_mixed_predicted_as": mixed_pred_to,
            "acc_short_posts": round(float(correct[short].mean()), 3),
            "acc_long_posts": round(float(correct[long].mean()), 3),
            "length_median_chars": med,
        },
    }
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nECE={e}  conf|correct={conf_correct:.3f}  conf|wrong={conf_wrong:.3f}")
    print(f"acc low-third={low_acc:.3f}  high-third={high_acc:.3f}")
    print(f"mixed: {len(mixed_idx)} true, predicted {n_mixed_predicted} times, "
          f"true-mixed went to {mixed_pred_to}")
    print(f"Saved {OUT_JSON}")

    # reliability diagram
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    xs = [b["mean_conf"] for b in bins]
    ys = [b["accuracy"] for b in bins]
    ns = [b["n"] for b in bins]
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.plot([0, 1], [0, 1], "--", color="gray", label="perfect calibration")
    ax.scatter(xs, ys, s=[max(30, n * 12) for n in ns], color="#1f6feb", zorder=3)
    for b in bins:
        ax.annotate(f"n={b['n']}", (b["mean_conf"], b["accuracy"]),
                    textcoords="offset points", xytext=(6, -10), fontsize=8)
    ax.set_xlabel("mean predicted confidence (max softmax)")
    ax.set_ylabel("actual accuracy")
    ax.set_title(f"Reliability diagram (5-fold OOF, ECE={e})")
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.legend(); plt.tight_layout()
    plt.savefig(DIAGRAM, dpi=150)
    print(f"Saved {DIAGRAM}")


if __name__ == "__main__":
    main()
