# TakeMeter — Model Labeling Prompts

This folder holds the prompts used to **pre-label** the 200 examples with three
different AI tools, so we can (a) speed up annotation and (b) run the
**inter-annotator reliability** stretch goal by comparing each model against your
own human labels (Cohen's κ / % agreement).

> ⚠️ Per the project spec: **AI pre-labels are a starting point, not the answer.**
> You must review and correct every example yourself. Disclose this AI assistance
> in your README's AI-usage section. The "ground truth" used for training is your
> human-reviewed labels in [`../labels/human/`](../labels/human/), not any model's output.

## The four trainable labels (single source of truth: [`../taxonomy.json`](../taxonomy.json))

| label | one-line definition |
|---|---|
| `analysis` | Structured argument backed by **specific, verifiable** evidence (stats, history, tactics). Reasons toward a conclusion. |
| `hot_take` | Bold, confident opinion **asserted without real evidence**. Often contrarian/provocative. |
| `reaction` | **In-the-moment emotional** response to a recent event. Little to no argument. |
| `mixed` | A genuine blend (e.g. emotion **plus** a real argument) where no single label dominates. |

Plus `skip` — labeling-only escape hatch for unreadable / non-English / off-topic
rows. `skip` is **not** a training class.

### Decision rules (apply in order)
1. Specific, verifiable evidence that survives removing the opinion framing → **analysis**.
2. Evidence vague, cherry-picked, or decorative (just enough to sound credible) → **hot_take**.
3. In-the-moment emotional response to a recent event, no real argument → **reaction**.
4. Genuinely blends reaction + a real argument, neither dominates → **mixed**.
5. Tie / 50-50 after keyword check → **mixed**.

## Workflow

1. Input file: [`../data/examples_to_label.csv`](../data/examples_to_label.csv) — columns `id,text,label,notes,source` (`label` blank).
2. Run each model's prompt → it writes a CSV into its own folder:
   - [`../labels/claude/labeled.csv`](../labels/claude/)
   - [`../labels/codex/labeled.csv`](../labels/codex/)
   - [`../labels/copilot/labeled.csv`](../labels/copilot/)
3. You label by hand in the web **Train** page → exports to [`../labels/human/labeled.csv`](../labels/human/).
4. Compare with `python ../labels/compare_labels.py` → agreement rates + disagreement list.
5. The **human** file (your reviewed labels) is what you upload to the Colab notebook for training.

## Output format every model must produce

A CSV with **exactly** these columns and one row per input example:

```
id,label,confidence,rationale
1,hot_take,0.86,"Bold claim, no evidence, contrarian framing."
2,analysis,0.93,"Cites PPDA drop with specific numbers."
```

- `label` ∈ {`analysis`, `hot_take`, `reaction`, `mixed`, `skip`} — lowercase, exact.
- `confidence` ∈ [0,1] — the model's self-rated certainty (used for calibration analysis).
- `rationale` ≤ 15 words — which decision rule fired.
