# labels/

One folder per annotator. Each folder holds a `labeled.csv` with columns
`id,label,confidence,rationale` aligned to `data/examples_to_label.csv`.

| folder | who | how it's produced |
|---|---|---|
| `human/` | **you** (ground truth) | the web **Train** page exports here; this is what trains the model |
| `claude/` | Claude Code | run [`../prompts/claude_labeling_prompt.md`](../prompts/claude_labeling_prompt.md) |
| `codex/` | OpenAI Codex | run [`../prompts/codex_labeling_prompt.md`](../prompts/codex_labeling_prompt.md) |
| `copilot/` | GitHub Copilot | run [`../prompts/copilot_labeling_prompt.md`](../prompts/copilot_labeling_prompt.md) |
| `groq/` | Groq `llama-3.3-70b` | **automated:** `python labels/label_with_groq.py` |

## Auto-label with Groq (4th annotator + context hints)

```bash
pip install groq python-dotenv joblib       # GROQ_API_KEY read from ../.env
python labels/label_with_groq.py            # labels all 200 in parallel
python labels/label_with_groq.py --limit 20 # quick smoke test
```

Writes `labels/groq/labeled.csv` (with `sarcasm`/`verifiable` context columns) and
`data/context_hints.csv` (shown on the web Train page to help you judge sarcasm and
whether a claim is checkable). These are **pre-labels** — review them.

## Compare them (inter-annotator reliability stretch goal)

```bash
python labels/compare_labels.py
```

Prints pairwise **% agreement** and **Cohen's κ** for every pair of label files
present, plus the rows where annotators disagree most — useful for the disagreement
analysis the stretch goal asks for, and for spotting examples whose labels you
should re-examine.

> `human/labeled.csv` is the file you upload to the Colab notebook for training.
> The model files exist only for the agreement analysis and to speed up your first
> pass — never train directly on an unreviewed model's labels.
