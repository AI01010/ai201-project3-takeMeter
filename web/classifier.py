"""TakeMeter inference backends for the web app.

Three backends, tried in this order of preference (whichever is available wins):

  1. "model"     — your fine-tuned DistilBERT exported into web/model/. Real
                   softmax confidence. This is the Deployed-Interface stretch goal.
  2. "groq"      — zero-shot llama-3.3-70b via Groq (needs GROQ_API_KEY in ../.env).
                   No calibrated confidence; we report the LLM's single label.
  3. "heuristic" — keyword/style scoring. Always available, no deps, no network,
                   so the demo NEVER shows a blank page. Clearly badged as heuristic.

Every backend returns the same dict:
    {label, confidence, scores:{label->prob}, backend, note}
"""
from __future__ import annotations

import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
MODEL_DIR = os.path.join(HERE, "model")
LABELS = ["analysis", "hot_take", "reaction", "mixed"]

# Lazy singletons so we only pay the import/load cost once, on first request.
_pipe = None
_pipe_tried = False
_groq = None
_groq_tried = False


# ──────────────────────────────────────────────────────────────────────────
# Backend 1: fine-tuned model
# ──────────────────────────────────────────────────────────────────────────
def _model_ready() -> bool:
    return os.path.isfile(os.path.join(MODEL_DIR, "config.json"))


def _get_pipe():
    global _pipe, _pipe_tried
    if _pipe_tried:
        return _pipe
    _pipe_tried = True
    if not _model_ready():
        return None
    try:
        from transformers import (AutoModelForSequenceClassification,
                                   AutoTokenizer, TextClassificationPipeline)
        import torch  # noqa: F401
        tok = AutoTokenizer.from_pretrained(MODEL_DIR)
        mdl = AutoModelForSequenceClassification.from_pretrained(MODEL_DIR)
        _pipe = TextClassificationPipeline(
            model=mdl, tokenizer=tok, return_all_scores=True, truncation=True,
        )
    except Exception as e:  # transformers/torch missing or load failure
        print(f"[classifier] model present but failed to load ({e}); falling back.")
        _pipe = None
    return _pipe


def _classify_model(text: str):
    pipe = _get_pipe()
    if pipe is None:
        return None
    out = pipe(text)[0]  # list of {label, score}
    scores = {}
    for d in out:
        # HF labels may be "LABEL_0" if id2label wasn't saved — map by index.
        lab = d["label"]
        if lab.startswith("LABEL_"):
            lab = LABELS[int(lab.split("_")[1])]
        scores[lab] = float(d["score"])
    label = max(scores, key=scores.get)
    return {
        "label": label,
        "confidence": scores[label],
        "scores": scores,
        "backend": "model",
        "note": "Fine-tuned DistilBERT (web/model/) — calibrated softmax confidence.",
    }


# ──────────────────────────────────────────────────────────────────────────
# Backend 2: Groq zero-shot
# ──────────────────────────────────────────────────────────────────────────
GROQ_SYSTEM_PROMPT = """
You are classifying posts from a football (soccer) community (World Cup, MLS, clubs).
Assign each post to EXACTLY ONE category:

analysis: structured argument with specific, verifiable evidence (stats, history, tactics).
hot_take: bold confident opinion with NO real evidence; asserts rather than argues.
reaction: in-the-moment emotional response to a recent event; little/no argument.
mixed: a genuine blend where no single category dominates.

Respond with ONLY the category name, lowercase: analysis, hot_take, reaction, or mixed.
""".strip()


def _get_groq():
    global _groq, _groq_tried
    if _groq_tried:
        return _groq
    _groq_tried = True
    try:
        from dotenv import load_dotenv
        load_dotenv(os.path.join(REPO, ".env"))  # read-only; never modified
    except Exception:
        pass
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        return None
    try:
        import importlib.util
        if importlib.util.find_spec("groq") is None:
            return None  # key set but package not installed — quietly fall back
        from groq import Groq
        _groq = Groq(api_key=key)
    except Exception as e:
        print(f"[classifier] groq init failed ({e}); falling back.")
        _groq = None
    return _groq


def _classify_groq(text: str):
    client = _get_groq()
    if client is None:
        return None
    try:
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": GROQ_SYSTEM_PROMPT},
                {"role": "user", "content": f"Classify this post:\n\n{text}"},
            ],
            temperature=0,
            max_tokens=10,
        )
        raw = resp.choices[0].message.content.strip().lower()
        label = next((l for l in sorted(LABELS, key=len, reverse=True)
                      if raw == l or l in raw), None)
        if label is None:
            return None
        # Zero-shot LLM gives no probabilities; show a one-hot with a caveat.
        scores = {l: (1.0 if l == label else 0.0) for l in LABELS}
        return {
            "label": label,
            "confidence": None,
            "scores": scores,
            "backend": "groq",
            "note": "Zero-shot llama-3.3-70b — single label, no calibrated confidence.",
        }
    except Exception as e:
        print(f"[classifier] groq call failed ({e}); falling back.")
        return None


# ──────────────────────────────────────────────────────────────────────────
# Backend 3: transparent heuristic (always available)
# ──────────────────────────────────────────────────────────────────────────
_NUM = re.compile(r"\d")
_PCT_STAT = re.compile(r"\d+\s?%|\bxg\b|\bxga\b|\bppda\b|per 90|\.\d|xgd|npxg")
_ANALYSIS_KW = ("because", "the reason", "compared", "stats", "data", "average",
                "per game", "underlying", "regress", "sample", "structure",
                "tactical", "press", "build-up", "metric", "rate", "numbers")
_HOT_KW = ("overrated", "change my mind", "cope", "fraud", "washed", "scam",
           "anyone could", "not close", "hot take", "worst", "delusional",
           "should be benched", "anti-football", "and it's not even")
_REACT_KW = ("shaking", "heartbroken", "crying", "scenes", "buzzing", "gutted",
             "cannot breathe", "i can't", "screamed", "devastated", "goosebumps",
             "let's go", "up the", "i'm done", "speechless")
_REACT_PUNC = re.compile(r"!{2,}|[😭😱🔥⚽️]|\bWE\b|\bGET IN")


def _caps_ratio(text: str) -> float:
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return 0.0
    return sum(c.isupper() for c in letters) / len(letters)


def _softmax(d):
    import math
    mx = max(d.values())
    exps = {k: math.exp(v - mx) for k, v in d.items()}
    s = sum(exps.values()) or 1.0
    return {k: v / s for k, v in exps.items()}


def _classify_heuristic(text: str):
    t = text.lower()
    raw = {l: 0.0 for l in LABELS}

    # analysis: hard evidence cues
    raw["analysis"] += 2.2 * len(_PCT_STAT.findall(t))
    raw["analysis"] += 0.5 * sum(kw in t for kw in _ANALYSIS_KW)
    if len(_NUM.findall(t)) >= 3:
        raw["analysis"] += 1.0

    # hot_take: contrarian assertion cues
    raw["hot_take"] += 1.6 * sum(kw in t for kw in _HOT_KW)

    # reaction: emotion/style cues
    raw["reaction"] += 1.4 * sum(kw in t for kw in _REACT_KW)
    raw["reaction"] += 1.2 * len(_REACT_PUNC.findall(text))
    if _caps_ratio(text) > 0.30 and len(text) > 20:
        raw["reaction"] += 1.5

    # mixed: contrastive structure bridging emotion + argument. Scale the boost
    # with the competing signals so a strong reaction+stat post can actually beat
    # either pure class (otherwise a big xG signal always wins outright).
    has_emotion = raw["reaction"] > 0
    has_argument = raw["analysis"] > 0 or raw["hot_take"] > 0
    contrast = any(w in t for w in (" but ", " however ", " though", "let's be real",
                                    "be honest", "doesn't change", "credit where",
                                    "don't get me wrong", "and yet"))
    if contrast and has_emotion and has_argument:
        raw["mixed"] += 1.0 + 0.7 * (raw["reaction"] + raw["analysis"] + raw["hot_take"])

    # default gravity so an empty/neutral post isn't 100% one class
    if max(raw.values()) == 0:
        raw["hot_take"] += 0.3  # short bare opinions are the modal soccer post

    scores = _softmax(raw)
    label = max(scores, key=scores.get)
    return {
        "label": label,
        "confidence": scores[label],
        "scores": scores,
        "backend": "heuristic",
        "note": "Keyword/style heuristic (no trained model loaded). Indicative only — "
                "export your model into web/model/ for real predictions.",
    }


# ──────────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────────
def _importable(name: str) -> bool:
    import importlib.util
    return importlib.util.find_spec(name) is not None


def active_backend() -> str:
    """Report the backend classify() will ACTUALLY use (deps must be installed)."""
    if _model_ready() and _importable("transformers") and _importable("torch"):
        return "model"
    try:
        from dotenv import load_dotenv
        load_dotenv(os.path.join(REPO, ".env"))   # read-only
    except Exception:
        pass
    if os.environ.get("GROQ_API_KEY") and _importable("groq"):
        return "groq"
    return "heuristic"


def classify(text: str) -> dict:
    text = (text or "").strip()
    if not text:
        return {"label": None, "confidence": None, "scores": {l: 0.0 for l in LABELS},
                "backend": "none", "note": "Empty input."}
    for fn in (_classify_model, _classify_groq, _classify_heuristic):
        result = fn(text)
        if result is not None:
            return result
    return _classify_heuristic(text)  # unreachable, but safe
