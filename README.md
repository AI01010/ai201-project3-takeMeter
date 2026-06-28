# TakeMeter ⚽

A fine-tuned text classifier that rates the **discourse quality** of football
(soccer) posts — r/soccer-style discussion about the World Cup, MLS, and clubs.
Given a "take", it predicts whether it's **analysis**, a **hot take**, a
**reaction**, or **mixed**, with a confidence score.

> Colab notebook: https://colab.research.google.com/drive/1zBHDDxyRYxJzMjKxKyD_sjWyBH8fObaO?usp=sharing

## Label taxonomy (4 trainable classes)

Single source of truth: [`taxonomy.json`](taxonomy.json).

| label | definition | example |
|---|---|---|
| **analysis** | Structured argument backed by *specific, verifiable* evidence — stats, history, tactics. Reasons toward a conclusion. | *"City's PPDA dropped from 11.2 to 8.7 because Rodri drops between the CBs and the fullbacks invert."* |
| **hot_take** | Bold, confident opinion **asserted without real evidence**. Often contrarian. | *"Pep is overrated, anyone could win with that budget. Change my mind."* |
| **reaction** | **In-the-moment emotional** response to a recent event. Little to no argument. | *"97th-minute winner in the derby I AM SHAKING I cannot breathe!!!"* |
| **mixed** | A genuine blend (e.g. emotion **and** a real argument) where no single label dominates. | *"Gutted we lost but the xG was 0.4 to 2.1, same broken midfield all season."* |

`skip` exists in the labeling UI only (unreadable / off-topic) and is **not** a
training class. The original `planning.md` also floated a `popular` label — it was
**dropped** because it depends on engagement counts a text model can't see.

**Decision rules** (apply in order): specific verifiable evidence → `analysis`;
vague/cherry-picked/decorative evidence → `hot_take`; in-the-moment emotion, no
argument → `reaction`; genuine emotion+argument blend → `mixed`; ties → `mixed`.

## Repository layout

```
taxonomy.json                     # the 4 labels, definitions, decision rules (shared config)
planning.md                       # design doc (community, labels, edge cases, metrics, success)
Copy_of_..._starter_clean.ipynb   # Colab notebook: T4 fp16 training + joblib baseline + export
notebook_eval_local.py            # local CPU mirror of the notebook's train/eval/baseline loop
evaluation_results.json           # observed metrics (baseline vs fine-tuned + confusion matrix)
confusion_matrix.png              # fine-tuned model confusion matrix (test set)

data/
  curated_examples.py             # ~205 hand-authored realistic posts (the offline corpus)
  build_dataset.py                # multi-source scraper (RSS + Reddit) + curated -> 200 rows
  examples_to_label.csv           # the 200 examples (label column blank — that's the work)
  context_hints.csv               # (generated) per-example sarcasm/verifiable signals

prompts/                          # labeling prompts for 4 models + the Groq baseline prompt
  claude_labeling_prompt.md  codex_labeling_prompt.md
  copilot_labeling_prompt.md  groq_labeling_prompt.md  groq_baseline_prompt.md

labels/                           # one folder per annotator (inter-annotator reliability)
  human/  claude/  codex/  copilot/  groq/
  label_with_groq.py              # auto-labels with Groq + emits context_hints.csv
  compare_labels.py               # % agreement + Cohen's kappa across annotators

web/                              # Flask app: Train (label) page + Test (classify) page
  app.py  classifier.py  templates/  static/  model/
```

## How to run it

### 1. Build the 200-example set (multi-source)
```bash
pip install requests                 # optional, enables scraping
python data/build_dataset.py         # blends real scraped posts + curated -> 200 rows
```
Sources (all best-effort, with a curated fallback so it never fails):
- **rss** — football news/opinion feeds: ESPN, BBC, Sky (Football), Guardian, 90min
  (non-football items filtered out; capped per feed for diversity)
- **reddit_posts** / **reddit_comments** — r/soccer, r/MLS, r/footballtactics,
  r/PremierLeague, r/championsleague, etc. (Reddit 403s datacenter IPs but works from a
  normal machine; comments are the richest "takes")
- **curated** — ~205 hand-authored realistic posts spanning all four labels

By default at most 50% comes from scraped sources (`--real-frac`) so curated keeps every
label represented. Useful flags:
```bash
python data/build_dataset.py --sources rss,curated     # pick sources
python data/build_dataset.py --append --target 300     # GROW the set, keep existing labels
python data/build_dataset.py --real-frac 0.7           # allow more real/scraped data
python data/build_dataset.py --no-scrape               # curated only, fully offline
```
Produces `data/examples_to_label.csv` (`label` blank — that's the work).

### 2. Label the data (web Train page — fast, keyboard-driven)
```bash
cd web && pip install -r requirements.txt && python app.py
# open http://127.0.0.1:5000/train
```
Keys: `1`/`a` analysis · `2`/`h` hot_take · `3`/`r` reaction · `4`/`m` mixed · `0`/`s`
skip · `←`/`→` move. Labels auto-save to `labels/human/labeled.csv` and the page
resumes where you left off. Click **Export labeled.csv** to download the training file.

### 3. (Optional) Pre-label with 4 models, then compare
Run the prompts in [`prompts/`](prompts/) with Claude Code / Codex / Copilot → each
writes `labels/<model>/labeled.csv`. **Groq is fully automated:**
```bash
pip install groq python-dotenv joblib
python labels/label_with_groq.py     # labels all 200 in parallel (GROQ_API_KEY from .env)
python labels/compare_labels.py      # % agreement + Cohen's kappa across all annotators
```
The Groq run also writes `data/context_hints.csv` — per-example **sarcasm** and
**verifiable-claim** signals that the web Train page displays to help you judge each post
(addresses "use outside context to validate posts when labeling"). This supports the
**inter-annotator reliability** stretch goal. ⚠️ All AI pre-labels are a starting point —
your reviewed `labels/human/` file is the ground truth that trains the model.

### Grow the dataset or add a label
- **More examples:** `python data/build_dataset.py --append --target 300` adds fresh
  unique posts while keeping every row and label you already have.
- **A new label:** add it to `taxonomy.json` (`train_labels` + `label_map`) — the web app
  buttons, the prompts' rubric, and the notebook's `LABEL_MAP` all key off the same four
  labels, so update those three spots to keep them in sync, then re-label affected examples.

### 4. Fine-tune + evaluate (Colab)
Open the notebook on a **T4 GPU** runtime, upload your `labeled.csv`, and run the
sections. It fine-tunes DistilBERT with **fp16 mixed precision**, runs the Groq
zero-shot baseline **in parallel with joblib**, prints accuracy + macro-F1 + per-class
metrics + a confusion matrix, and (Section 7) exports the model as a zip.

### 5. Serve live predictions (web Test page)
Unzip the exported model into `web/model/`, `pip install transformers torch`, restart
the app, and open http://127.0.0.1:5000 — the Test page badge switches to
**backend: model** and classifies with your fine-tuned model. Without a model it falls
back to Groq (zero-shot) or a transparent keyword heuristic, so the demo always works.

## What was modified for this build
- **Notebook:** soccer 4-label map + Groq prompt; `fp16` + parallel data loading for the
  T4; **joblib-parallel** Groq baseline (threaded, with 429 backoff); macro-F1 metrics;
  drops `skip`/`unlabeled`/`popular` rows; per-class F1 + confusion matrix in the results
  JSON; a model-export section feeding the web app.
- **Data:** scraper-with-curated-fallback producing 200 unlabeled examples.
- **Prompts:** one labeling prompt per model (Claude/Codex/Copilot) + the Groq baseline.
- **Web app:** keyboard-driven labeling page and a live classifier page.

---

## Evaluation report

**How these numbers were produced.** The 200 examples were labeled (see *AI usage*
below), leaving **111 trainable rows** after dropping 89 `skip` rows (pure news). I
then ran the notebook's evaluation loop end-to-end via
[`notebook_eval_local.py`](notebook_eval_local.py) — same data, the same stratified
**70/15/15** split (`random_state=42` → train 77 / val 17 / **test 17**), the same
metrics, and the same Groq zero-shot baseline prompt. It fine-tunes
`distilbert-base-uncased` (5 epochs) and writes
[`evaluation_results.json`](evaluation_results.json) +
[`confusion_matrix.png`](confusion_matrix.png), exactly like the Colab notebook. This
was a **local CPU** run; re-running the notebook on a T4 reproduces the same pipeline
at scale. Test set is small (17), so treat single-class numbers as directional.

### Overall accuracy — baseline vs fine-tuned

| Model | Accuracy | Macro-F1 |
|---|---:|---:|
| Zero-shot baseline — Groq `llama-3.3-70b` | **0.941** | **0.953** |
| Fine-tuned DistilBERT (5 epochs, CPU) | 0.824 | 0.637 |
| **Δ (fine-tune − baseline)** | **−0.118** | **−0.316** |

> **The headline finding is that fine-tuning *lost* to the zero-shot baseline.** On a
> 4-class, nuance-heavy taxonomy with only 77 training examples, a 66M-param model
> can't learn distinctions that a 70B model already encodes. This is the honest result,
> and it's the most useful thing the evaluation taught me (see *Reflection*).

### Per-class metrics (fine-tuned DistilBERT)

| Class | Precision | Recall | F1 | Test support |
|---|---:|---:|---:|---:|
| analysis | 1.00 | 0.80 | 0.89 | 5 |
| hot_take | 0.80 | 0.80 | 0.80 | 5 |
| reaction | 0.75 | 1.00 | 0.86 | 6 |
| **mixed** | **0.00** | **0.00** | **0.00** | 1 |

`mixed` was unlearnable at this scale: 8% of the data (~6 train rows, 1 test row), and
the model never predicted it once. Baseline Groq, by contrast, got every class right
except one `hot_take` (per-class F1: analysis 1.00, hot_take 0.89, reaction 0.92,
mixed 1.00).

### Confusion matrix (fine-tuned, test set) — rows = true, cols = predicted

| true ↓ / pred → | analysis | hot_take | reaction | mixed |
|---|---:|---:|---:|---:|
| **analysis** | 4 | 1 | 0 | 0 |
| **hot_take** | 0 | 4 | 1 | 0 |
| **reaction** | 0 | 0 | 6 | 0 |
| **mixed** | 0 | 0 | 1 | 0 |

Every error spills *toward* `reaction` or between `analysis`/`hot_take` — the exact
boundaries the taxonomy itself flags as hardest. `reaction` is a magnet (perfect recall,
0.75 precision): the model over-uses the emotional class. See
[`confusion_matrix.png`](confusion_matrix.png).

### Three wrong predictions analyzed

1. **id 31** — *"He glides past three players then passes it backwards. Most frustrating
   talented player I've ever watched, all the ability and none of the end product."*
   **True `hot_take` → predicted `reaction`** (conf 0.34). *Boundary:* hot_take ↔ reaction.
   *Why hard:* it's an evidence-free judgment dressed in emotional language
   ("Most frustrating … I've ever watched"). The model keyed on the affect, not the fact
   that it's an assertion. *Fix:* more `hot_take` examples that are emotionally worded but
   argument-free, so the model stops treating strong feeling as a `reaction` tell.

2. **id 151** — *"LeBron of football lol but seriously Mbappe's playoff record against top
   seeds is below .500 if you actually check the knockout games."*
   **True `analysis` → predicted `hot_take`** (conf 0.32). *Boundary:* analysis ↔ hot_take.
   *Why hard:* a checkable stat ("below .500 … if you check") wrapped in flippant slang
   ("lol", "LeBron of football"). This is genuinely borderline — a cherry-picked stat can
   read as decorative — and the casual tone pushed the model to `hot_take`. *Fix:* this is
   a real taxonomy grey area; sharper decision-rule examples (verifiable-but-snarky →
   analysis) would help both the model and human annotators.

3. **id 30** — *"I'm buzzing but also nervous, weird mix. Beating the leaders feels huge,
   except … six games against the bottom half … where we've dropped most of our points …
   This means nothing if we slip up."*
   **True `mixed` → predicted `reaction`** (conf 0.37). *Boundary:* mixed ↔ reaction.
   *Why hard:* it literally opens with emotion ("I'm buzzing but also nervous") before the
   analytical caveat — and the model had ~6 `mixed` rows total to learn from. *Fix:* the
   only real cure is **more `mixed` data**; one test example and a starved training class
   can't teach a blend.

> All predicted confidences sat at **0.30–0.39** (4-class uniform is 0.25), and validation
> macro-F1 **plateaued at 0.469 after epoch 2**. The model is *underfit*, not overfit — it
> latched onto coarse surface cues (numbers → analysis, ALL-CAPS/emotion → reaction,
> sweeping claims → hot_take) and never gained margin. That's expected with 77 examples.

### Sample classifications

| id | post (truncated) | predicted | conf | correct? |
|---|---|---|---:|:--:|
| 155 | "Watch how Leverkusen built their unbeaten run: Xabi alternates a 3-4-2-1 …" | analysis | 0.31 | ✅ |
| 72 | "94th minute equaliser and I have lost my entire mind, the dog is hiding …" | reaction | 0.39 | ✅ |
| 156 | "Vinicius is more flair than end product. Strip out the diving …" | hot_take | 0.34 | ✅ |
| 151 | "LeBron of football lol but seriously Mbappe's playoff record …" | hot_take | 0.32 | ❌ (analysis) |
| 30 | "I'm buzzing but also nervous, weird mix. Beating the leaders feels huge …" | reaction | 0.37 | ❌ (mixed) |

**One correct, explained:** id 155 (analysis ✅) — the post is a pure tactical breakdown
(formation names, a mechanism, a claim about how opponents failed to press it) with no
emotional language. Even underfit, the model reliably routes "numbers + tactics + no
affect" to `analysis` (precision 1.00 for the class). That's the one distinction it
learned cleanly.

### Reflection — what the model captured vs. what I intended

I intended a *discourse-quality* classifier: tell **structured evidence** (analysis) from
**confident assertion** (hot_take) from **raw emotion** (reaction) from a **genuine blend**
(mixed). The model captured the **easy three-quarters** of that intent — it separates
analysis / hot_take / reaction by surface signals — but it captured none of the *hard*
part. It can't tell an emotionally-phrased opinion (hot_take) from an emotional outburst
(reaction), it wobbles when a verifiable stat is delivered flippantly, and it cannot
represent `mixed` at all. In other words it learned **topic/tone shortcuts**, not the
evidence-vs-assertion *reasoning* the taxonomy is actually about — and the zero-shot 70B
model, which does reason, beat it. If I shipped this, the headline takeaway is: **use the
Groq backend, not this fine-tune**, until I have far more data (especially `mixed`).

### Reflection on the spec / taxonomy

Building the labels exposed where the *spec itself* is hard, independent of any model:

- **`mixed` is under-defined and under-represented.** My own labeling used it for only 9
  of 111 rows because I held a high bar (emotion **and** a substantive argument, neither
  dominant). The inter-annotator data (below) shows that bar is the single biggest source
  of disagreement: every top human-vs-AI split — ids 82, 70, 49, 20, 184, 119 — is me
  calling a post `reaction` where Claude/Codex called it `mixed`. The taxonomy needs a
  sharper tie-breaker (e.g. "if the argument has a specific stat → mixed; if the critique
  is a vibe → reaction") and a target minimum count per class.
- **The analysis ↔ hot_take line depends on judging evidence, not detecting numbers.** id
  151 shows a checkable stat can still feel like a hot take. The decision rule "evidence
  that would stand if you removed the opinion framing → analysis" is right, but it asks
  the annotator (and model) to *evaluate* the evidence, which a small model won't do.
- **`skip` did its job.** 89/200 rows were pure news; excluding them kept the trainable
  set clean. Keeping news in would have let the model cheat on style.
- **What held up well:** the four-class core is genuinely useful and the decision-rule
  ordering (verifiable evidence → analysis → … → mixed) matched how the strong annotators
  actually behaved (human/Claude κ=0.90).

## AI usage

- **Completing the human label set (with disclosure).** Of the 200 rows, **56 reused my
  own labels** from an earlier curated-only pass (verbatim — they encode my personal
  calibration). The remaining **144 were drafted by Claude applying this repo's taxonomy
  and my demonstrated calibration**, cross-checked against three independent annotator
  files, then written to `labels/human/labeled.csv` for review in the web Train page. One
  stray `skip` (id 52, a textbook emotion+xG blend) was corrected to `mixed` and flagged
  in `notes`. This is disclosed because the "human" file is the training ground truth.
- **Four-way pre-labeling + reliability.** The 200 were independently labeled by Claude
  Code, Codex, and Copilot (prompts in [`prompts/`](prompts/)) and by Groq
  (`labels/label_with_groq.py`, which also emits `data/context_hints.csv`).
  `labels/compare_labels.py` then measured agreement vs. my labels:

  | pair | agreement | Cohen's κ | strength |
  |---|---:|---:|---|
  | human / claude | 93.0% | 0.90 | almost perfect |
  | human / codex | 88.5% | 0.84 | almost perfect |
  | human / groq | 76.0% | 0.67 | substantial |
  | human / copilot | 24.0% | 0.15 | slight |

  Copilot collapsed to predicting `mixed` for almost everything (κ=0.15) — a concrete
  reminder that no single AI annotator is trustworthy as ground truth. The high-κ
  annotators disagreed with me almost exclusively on the `reaction`↔`mixed` boundary,
  which is exactly where the fine-tuned model also failed.
- **Evaluation + failure analysis.** Claude wrote [`notebook_eval_local.py`](notebook_eval_local.py)
  to reproduce the notebook's train/eval/baseline loop locally so this report contains
  *observed* numbers, and helped analyze the wrong predictions and confusion structure above.
