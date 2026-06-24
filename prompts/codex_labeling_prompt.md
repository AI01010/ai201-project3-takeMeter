# Codex (OpenAI) — Labeling Prompt (script-generating / agentic)

> Use with the **Codex CLI** or **ChatGPT Codex** in the repo. Codex is strongest
> when asked to *write and run a script*, so this prompt has it generate a small
> deterministic labeler it then executes — keeping the labeling auditable.

---

You are an expert annotator for **TakeMeter**, a classifier of football (soccer)
discourse quality (r/soccer-style: World Cup, MLS, clubs).

## Deliverable
Read `data/examples_to_label.csv` (`id,text,label,notes,source`) and produce
`labels/codex/labeled.csv` with columns `id,label,confidence,rationale`, one row
per input row, all 200 labeled.

You may either (a) reason over each row directly, or (b) write a Python script that
calls your judgment per row — but the final artifact must be the CSV above.

## Label definitions (pick exactly one per post)
| label | rule |
|---|---|
| `analysis` | Structured argument with **specific, verifiable** evidence — stats, history, tactics. Reasons toward a conclusion. |
| `hot_take` | Bold, confident opinion **with no real evidence**. Asserts, doesn't argue. Often contrarian ("overrated", "change my mind", "cope"). |
| `reaction` | **In-the-moment emotional** response to a recent event. ALL-CAPS, "!!!", "I'm shaking". Little/no argument. |
| `mixed` | Genuine blend — e.g. emotional reaction **and** a real argument — where neither dominates. |
| `skip` | Unreadable / non-English / off-topic only. Not a training class. |

## Decision procedure (in order)
1. Does it give specific, verifiable evidence that survives removing the opinion? → `analysis`.
2. Is the "evidence" vague, cherry-picked, or decorative? → `hot_take`.
3. Is it an emotional in-the-moment response with no real argument? → `reaction`.
4. Does it truly combine reaction + argument with neither dominant? → `mixed`.
5. Still tied after keyword scan? → `mixed`.

## Calibration
Set `confidence` honestly:
- 0.90–1.00 — textbook example of the label.
- 0.60–0.85 — leans clearly one way but has a competing signal.
- 0.40–0.59 — genuine edge case you resolved with rule 4/5.

## Hard cases to get right
- One decorative stat ≠ analysis. *"He's a fraud, big numbers vs nobodies, eye test never lies"* → `hot_take`.
- Emotion + real critique → `mixed`, not `reaction`. *"Buzzing but we had 31% possession and one shot, riding the keeper"* → `mixed`.
- Tactics topic but pure assertion → `hot_take`, not `analysis`.

## Output format (exact)
```
id,label,confidence,rationale
1,hot_take,0.88,"Contrarian assertion, no evidence"
```
Lowercase labels, exact strings, ≤15-word rationale, no extra columns, no prose
outside the CSV. Cover **all 200 rows**. End by printing the per-label counts.
