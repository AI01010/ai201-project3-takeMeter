# labels/

One folder per annotator. Each folder holds a `labeled.csv` with columns
`id,label,confidence,rationale` aligned to `data/examples_to_label.csv`.

| folder | who | how it's produced |
|---|---|---|
| `human/` | **you** (ground truth) | the web **Train** page exports here; this is what trains the model |
| `claude/` | Claude Code | run [`../prompts/claude_labeling_prompt.md`](../prompts/claude_labeling_prompt.md) |
| `codex/` | OpenAI Codex | run [`../prompts/codex_labeling_prompt.md`](../prompts/codex_labeling_prompt.md) |
| `copilot/` | GitHub Copilot | run [`../prompts/copilot_labeling_prompt.md`](../prompts/copilot_labeling_prompt.md) |

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
