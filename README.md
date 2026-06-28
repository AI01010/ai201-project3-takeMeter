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
  human/                          # MY reviewed labels — the only file used for training
  claude/ codex/ copilot/ groq/   # the original 4 AI annotators
  llama-3.3-70b/ deepseek-v3.1/ deepseek-v3.2/ gemma-4-31b/ gpt-oss-120b/  # SambaNova
  gemini/                         # Google Gemini
  label_with_groq.py              # auto-labels with Groq + emits context_hints.csv
  label_with_sambanova.py         # one batched call per SambaNova model (all 200 at once)
  label_with_gemini.py            # one batched call to Gemini
  _batch_label.py                 # shared rubric + lenient JSON parser for the batch labelers
  compare_labels.py               # % agreement + Cohen's kappa across every annotator folder

stretch_calibration.py            # stretch goals: confidence calibration + error patterns (5-fold OOF)
stretch_results.json              # calibration (ECE) + error-pattern numbers
reliability_diagram.png           # confidence vs accuracy (calibration curve)

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

### 3. (Optional) Pre-label with the AI annotators, then compare
I label the same 200 with a bunch of models so I can measure inter-annotator
reliability against my own labels. Claude Code / Codex / Copilot run from the prompts
in [`prompts/`](prompts/); the rest are automated:
```bash
pip install groq requests
python labels/label_with_groq.py        # Groq (per-post calls) + emits context_hints.csv
python labels/label_with_sambanova.py   # 5 SambaNova models, ONE batched call each
python labels/label_with_gemini.py      # Gemini, one batched call
python labels/compare_labels.py         # % agreement + Cohen's kappa across every folder
```
SambaNova and Gemini each label all 200 in **a single request per model** — one prompt
in, a JSON array of 200 labels out — so a single (shared, rate-limited) SambaNova key is
only hit once per model. `compare_labels.py` auto-discovers every `labels/<name>/` folder,
so new annotators show up automatically. Keys live in `.env`
(`GROQ_API_KEY`, `SAMBA_NOVA_API_KEY`, `GEMINI_API_KEY`). The Groq run also writes
`data/context_hints.csv` — per-example **sarcasm** and **verifiable-claim** signals shown
on the web Train page to help me judge each post. ⚠️ Every AI label is a starting point —
my reviewed `labels/human/` file is the ground truth that trains the model.

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
- **Annotators:** added SambaNova (5 models, one batched 200-label call each) and Gemini
  labelers + a shared batch parser; `compare_labels.py` now auto-discovers annotator folders.
- **Stretch goals:** confidence calibration (5-fold out-of-fold, ECE + reliability diagram)
  and a systematic error-pattern analysis on top of the inter-annotator reliability work.
- **Web app:** keyboard-driven labeling page and a live classifier page.

---

## Evaluation report

I labeled all 200, dropped the 89 `skip` rows (pure news), and trained on the **111 real
takes**. So I could report numbers I actually saw instead of placeholders, I ran the
notebook's whole train → evaluate → baseline loop locally with
[`notebook_eval_local.py`](notebook_eval_local.py) — same data, same stratified 70/15/15
split (`random_state=42` → train 77 / val 17 / **test 17**), same metrics, same Groq
baseline prompt. It writes [`evaluation_results.json`](evaluation_results.json) and
[`confusion_matrix.png`](confusion_matrix.png), exactly like the Colab cells. It's a CPU
run; the T4 notebook reproduces it at scale. 17 test rows is tiny, so for the stretch
section I re-checked everything with 5-fold cross-validation over all 111 (below).

### Accuracy — my fine-tune vs the zero-shot baseline

| model | accuracy | macro-F1 |
|---|---:|---:|
| Zero-shot baseline — Groq `llama-3.3-70b` | **0.941** | **0.953** |
| My fine-tuned DistilBERT (5 epochs) | 0.824 | 0.637 |
| Δ (fine-tune − baseline) | −0.118 | −0.316 |

Straight up: **my fine-tune lost to the baseline.** With 77 training rows and a 4-class
taxonomy that's mostly about nuance, a 66M-param model can't catch a 70B model that
already knows this stuff zero-shot. I'd rather report that than fake a win.

### Per-class (fine-tuned, 17-row test)

| class | precision | recall | F1 | support |
|---|---:|---:|---:|---:|
| analysis | 1.00 | 0.80 | 0.89 | 5 |
| hot_take | 0.80 | 0.80 | 0.80 | 5 |
| reaction | 0.75 | 1.00 | 0.86 | 6 |
| **mixed** | **0.00** | **0.00** | **0.00** | 1 |

`mixed` is dead — 8% of the data, ~6 training rows, and the model never predicts it once.
Groq got every class on the test set except one `hot_take` (per-class F1: analysis 1.00,
hot_take 0.89, reaction 0.92, mixed 1.00).

### Confusion matrix (fine-tuned, test set) — rows = true, cols = predicted

| true ↓ / pred → | analysis | hot_take | reaction | mixed |
|---|---:|---:|---:|---:|
| **analysis** | 4 | 1 | 0 | 0 |
| **hot_take** | 0 | 4 | 1 | 0 |
| **reaction** | 0 | 0 | 6 | 0 |
| **mixed** | 0 | 0 | 1 | 0 |

Everything spills toward `reaction` or between `analysis`/`hot_take` — the boundaries I
already flagged as hardest. `reaction` is a magnet (recall 1.00, precision 0.75). Full
picture in [`confusion_matrix.png`](confusion_matrix.png).

### Three wrong predictions

1. **id 31** — *"He glides past three players then passes it backwards. Most frustrating
   talented player I've ever watched, all the ability and none of the end product."*
   True `hot_take` → predicted `reaction` (conf 0.34). It's an evidence-free opinion dressed
   in emotional language, and the model keyed on the feeling instead of the missing
   argument. Fix: more emotionally-worded-but-argument-free `hot_take` examples.

2. **id 151** — *"LeBron of football lol but seriously Mbappe's playoff record against top
   seeds is below .500 if you actually check the knockout games."*
   True `analysis` → predicted `hot_take` (conf 0.32). A checkable stat wrapped in slang
   ("lol", "LeBron of football"). Genuinely borderline — a cherry-picked stat can read as
   decorative — and the casual tone tipped it to `hot_take`. This one's a real grey area in
   my own rubric, not just a model miss.

3. **id 30** — *"I'm buzzing but also nervous, weird mix. Beating the leaders feels huge,
   except … six games against the bottom half … This means nothing if we slip up."*
   True `mixed` → predicted `reaction` (conf 0.37). It opens with emotion before the
   analytical caveat, and the model had ~6 `mixed` rows total to learn from. The only real
   fix is more `mixed` data.

Side note: every confidence sat at **0.30–0.39** (uniform for 4 classes is 0.25) and val
macro-F1 flatlined at **0.469 after epoch 2**. The model is underfit, not overfit — it
grabbed the obvious cues (numbers → analysis, CAPS/emotion → reaction, sweeping claim →
hot_take) and never got sharper. Expected with 77 rows.

### Sample classifications

| id | post (truncated) | predicted | conf | correct? |
|---|---|---|---:|:--:|
| 155 | "Watch how Leverkusen built their unbeaten run: Xabi alternates a 3-4-2-1 …" | analysis | 0.31 | ✅ |
| 72 | "94th minute equaliser and I have lost my entire mind, the dog is hiding …" | reaction | 0.39 | ✅ |
| 156 | "Vinicius is more flair than end product. Strip out the diving …" | hot_take | 0.34 | ✅ |
| 151 | "LeBron of football lol but seriously Mbappe's playoff record …" | hot_take | 0.32 | ❌ (analysis) |
| 30 | "I'm buzzing but also nervous, weird mix. Beating the leaders feels huge …" | reaction | 0.37 | ❌ (mixed) |

**One correct, explained:** id 155 (analysis ✅) is a pure tactical breakdown — formation
names, a mechanism, a claim about how opponents failed to press it, zero emotion. Even
underfit, the model reliably routes "numbers + tactics + no feeling" to `analysis`
(precision 1.00 for the class). That's the one distinction it nailed.

### Did it clear my own "good enough" bar?

In `planning.md` I wrote down what "good enough" meant *before* training. Checking it honestly:

- ❌ **Beat the baseline on accuracy AND macro-F1** — no, lost both.
- ❌ **macro-F1 ≥ 0.65** — no (0.637 on the test split, 0.578 over 5-fold).
- ❌ **Every per-class F1 ≥ 0.50, no dead class** — no, `mixed` is 0.00.
- ⚠️ **analysis vs hot_take confused < 30%** — the pair-swap rate is 17% (11 of those 66
  posts), so technically it clears this one. But the leak is entirely one-directional —
  38% of analysis posts (11/29) get called `hot_take` — so it's the next thing I'd fix.

So by my own bar it fails on basically every count. Per the plan I wrote, that means the
thing to fix is the **data and the labels, not the training setup**.

### Reflection — what it learned vs what I wanted

I wanted a discourse-*quality* classifier: tell structured evidence (analysis) from
confident assertion (hot_take) from raw emotion (reaction) from a real blend (mixed). It
learned the easy three-quarters — it sorts analysis/hot_take/reaction by surface signals —
and none of the hard part. It can't tell an emotionally-phrased opinion from an emotional
outburst, it wobbles when a real stat shows up in a flippant post, and it has no concept of
`mixed` at all. It learned **topic and tone shortcuts**, not the evidence-vs-assertion
*judgment* the taxonomy is actually about — which is exactly why the 70B model, which can
reason, beat it. If I shipped this today the honest call is: **use the Groq backend, not my
fine-tune**, until I have a lot more data (especially `mixed`).

### Reflection on the spec / taxonomy

Labeling the data showed me where the *spec itself* is hard, regardless of any model:

- **`mixed` is under-defined and under-represented.** I only used it for 9 of 111 rows
  because I hold a high bar (real emotion *and* a real argument, neither dominant). The
  inter-annotator numbers below show that's the single biggest disagreement — every other
  model reaches for `mixed` where I say `reaction`. The taxonomy needs a sharper
  tie-breaker (e.g. "specific stat in the argument → mixed; vibe-level critique →
  reaction") and a minimum count per class.
- **analysis vs hot_take is about judging the evidence, not spotting numbers.** id 151
  proves a checkable stat can still feel like a hot take. "Evidence that would stand if you
  stripped the opinion framing → analysis" is the right rule, but it asks the reader to
  *evaluate* the claim, which a small model just won't do.
- **`skip` earned its keep.** 89/200 rows were pure news; dropping them stopped the model
  from cheating on news-vs-take style.
- **What held up:** the four-class core is genuinely useful, and the decision-rule order
  matched how the strong annotators behaved in practice (human/Claude κ=0.90).

## Stretch goals

All four from `planning.md`. Here's where each landed.

### 1. Inter-annotator reliability ✅

I had **11 models** label the same 200 and scored each against my labels with Cohen's κ
([`labels/compare_labels.py`](labels/compare_labels.py)):

| annotator | agreement | Cohen's κ | strength |
|---|---:|---:|---|
| claude | 93.0% | 0.90 | almost perfect |
| llama-3.3-70b | 92.0% | 0.89 | almost perfect |
| deepseek-v3.1 | 91.0% | 0.88 | almost perfect |
| gemini-2.5-flash | 91.0% | 0.88 | almost perfect |
| deepseek-v3.2 | 90.0% | 0.86 | almost perfect |
| gemma-4-31b | 89.5% | 0.85 | almost perfect |
| codex | 88.5% | 0.84 | almost perfect |
| gpt-oss-120b | 83.5% | 0.78 | substantial |
| groq (llama-3.3-70b) | 76.0% | 0.67 | substantial |
| copilot | 24.0% | 0.15 | slight |

Two things jump out:

- **The models agree with each other more than with me.** deepseek-v3.1 vs v3.2 is 98%
  (κ0.97), llama vs deepseek 97%, claude vs gemini/gemma/llama all ~96% — but every one of
  them only hits ~90% against my labels. They share a house style; I don't quite share it.
- **That gap is one specific boundary.** On ids **82, 70, 49, 20, 184, 119, 113** I said
  `reaction` and **every single model said `mixed`**. Same on id 55 (I said hot_take) and
  id 35 (I said analysis). I keep `mixed` for a genuine emotion+argument tie; the models
  grab it whenever a post has any of both, even when the feeling clearly dominates. That's
  the whole disagreement, and it's the same boundary my fine-tune chokes on.
- Copilot is the outlier (24%, κ0.15) — it answered `mixed` for nearly everything, a good
  reminder not to trust any single annotator as truth. (MiniMax-M2.7 isn't here — SambaNova
  returns HTTP 402 for it without a paid plan.)

### 2. Confidence calibration ✅

17 test rows is too few to say anything real about calibration, so I retrained with 5-fold
cross-validation and collected an out-of-fold prediction + confidence for all 111 takes
([`stretch_calibration.py`](stretch_calibration.py) → [`stretch_results.json`](stretch_results.json),
[`reliability_diagram.png`](reliability_diagram.png)).

The literal "does a 90%-confident prediction beat a 60% one?" question doesn't even apply:
**the model never gets more confident than 0.45.** Everything lands in 0.30–0.45. So:

- It's badly **underconfident** — ECE = **0.38**. When it says ~0.35 it's actually right
  71% of the time; the 0.40–0.45 bin is right 100%. The reliability diagram is a wall of
  points sitting way above the diagonal.
- Confidence barely separates right from wrong: mean **0.364 when correct vs 0.346 when
  wrong**.
- But the *ranking* has a little signal — its most-confident third is right **84%** vs
  **60%** for its least-confident third. So sorting by confidence is weakly useful even
  though the raw number is meaningless. I would not show these confidences to a user as-is.

### 3. Error-pattern analysis ✅

Beyond the three individual misses, the 5-fold run over all 111 shows three *systematic*
patterns (not one-offs):

- **`mixed` is invisible.** Predicted **0 times out of 111**. All 9 true-`mixed` posts went
  elsewhere — **7 to `reaction`, 2 to `hot_take`**. It's not that mixed is hard; the model
  has no representation of it.
- **analysis leaks into hot_take.** **11 of 29** analysis posts (38%) get called
  `hot_take`. analysis recall is only 0.62, and hot_take precision drops to 0.65 because so
  much gets dumped there. The model spots a "take" but can't judge whether the evidence
  behind it is real (id 151 is the poster child).
- **It falls apart on long posts.** Short posts (≤135 chars) → **93%** accuracy; long posts
  → **55%**. The long ones are the analysis and the blends; the short ones are clean
  reactions and one-line hot takes. So the "length" effect is really a nuance effect.

### 4. Deployed interface ✅

The Flask app ([`web/`](web/)) is the interface: a **Test** page that takes a new post and
returns a label + confidence, and a **Train** page for labeling. It serves my fine-tuned
model from `web/model/` when present and falls back to Groq zero-shot, then a keyword
heuristic, so it always answers. Run it with `cd web && python app.py` (steps 2 & 5 above).

## AI usage

- **Completing the human label set (disclosed).** Of the 200 rows, **56 reuse my own
  labels** from an earlier curated-only pass, verbatim — they carry my personal calibration.
  The other **144 were drafted by Claude applying this repo's taxonomy and my demonstrated
  calibration**, cross-checked against the independent annotator files, then written to
  `labels/human/labeled.csv` for review in the web Train page. I corrected one stray `skip`
  (id 52, a clear emotion+xG blend) to `mixed` and flagged it in `notes`. I disclose this
  because the "human" file is the training ground truth.
- **11-way pre-labeling for reliability.** Claude Code / Codex / Copilot labeled from the
  prompts in [`prompts/`](prompts/); Groq, 5 SambaNova models, and Gemini are automated
  (`label_with_groq.py`, `label_with_sambanova.py`, `label_with_gemini.py` — the SambaNova
  and Gemini labelers send one batched call per model to respect the shared key's limits).
  `compare_labels.py` scores them all against my labels (table above).
- **Label stress-testing.** Boundary posts between analysis/hot_take and reaction/mixed
  were LLM-generated; the genuinely ambiguous ones live in the EDGE/curated set and
  sharpened the decision rules.
- **Evaluation, calibration + failure analysis.** Claude wrote
  [`notebook_eval_local.py`](notebook_eval_local.py) and
  [`stretch_calibration.py`](stretch_calibration.py) so this report runs on *observed*
  numbers, and helped surface the systematic error patterns above — each verified by
  re-reading the actual examples before writing it up.
