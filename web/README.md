# TakeMeter Web App

A tiny Flask app with two pages:

| page | route | what it does |
|---|---|---|
| **Test a post** | `/` | Paste a new football post → predicted label + confidence bars. (Deployed-interface stretch goal.) |
| **Label data** | `/train` | Label the 200 examples fast, keyboard-driven, auto-saving to `labels/human/labeled.csv`. |

## Run it

```bash
cd web
python -m pip install -r requirements.txt
python app.py
# open http://127.0.0.1:5000
```

That's all you need for labeling. The Test page also works immediately — see backends below.

## Test-page backends (auto-selected, best first)

1. **model** — your fine-tuned DistilBERT in `web/model/` (real softmax confidence).
   Export it from the notebook's Section 7, then `pip install transformers torch`.
2. **groq** — zero-shot `llama-3.3-70b` if `GROQ_API_KEY` is in the repo-root `.env`
   (label only, no calibrated confidence).
3. **heuristic** — keyword/style scoring. No model, no network — guarantees the demo
   always shows a label + confidence. Clearly badged so you don't mistake it for the
   trained model.

The active backend is shown as a badge on the Test page and via `GET /api/status`.

## Labeling workflow (Train page)

- Loads `data/examples_to_label.csv` and resumes at the first unlabeled example.
- Keys: `1`/`a` analysis · `2`/`h` hot_take · `3`/`r` reaction · `4`/`m` mixed ·
  `0`/`s` skip · `←`/`→` move · `Tab` next unlabeled. Labels **auto-save and advance**.
- Notes field captures difficult-case reasoning (feeds your README's hard-cases section).
- **Export labeled.csv** downloads the file you upload to the Colab notebook for training.
- Every label is written through to `labels/human/labeled.csv` immediately, so progress
  survives a restart.

## API

| method | route | body / returns |
|---|---|---|
| GET | `/api/examples` | all examples + current labels + counts |
| POST | `/api/label` | `{id, label, notes}` → upserts to `labels/human/labeled.csv` |
| GET | `/api/export` | downloads `labeled.csv` (`id,text,label,notes`) |
| POST | `/api/classify` | `{text}` → `{label, confidence, scores, backend, note}` |
| GET | `/api/status` | active backend + labeled/total counts |

The app never touches `.env` except to read `GROQ_API_KEY`.
