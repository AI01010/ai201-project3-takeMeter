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

> ⏳ **Fill after training.** The notebook prints these numbers and writes
> `evaluation_results.json` + `confusion_matrix.png`. Drop them in here:

- [ ] Overall accuracy — baseline (Groq) vs fine-tuned
- [ ] Per-class precision/recall/F1 (fine-tuned)
- [ ] Confusion matrix as a markdown table
- [ ] 3 analyzed wrong predictions (which boundary, why it's hard, fix)
- [ ] Sample classifications (3–5 posts, predicted label + confidence; one correct explained)
- [ ] Reflection: what the model captured vs. what you intended

## AI usage

- [ ] **Annotation assistance:** pre-labeled the 200 examples with Claude Code, Codex,
  and Copilot via the prompts in `prompts/`, then reviewed/corrected every label by hand
  in the web Train page. Disagreements analyzed with `labels/compare_labels.py`.
- [ ] (add your other AI-assisted steps — label stress-testing, failure-pattern analysis)
