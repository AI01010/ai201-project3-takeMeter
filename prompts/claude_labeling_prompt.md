# Claude Code — Labeling Prompt (agentic, file-in / file-out)

> Paste this whole message into **Claude Code** running in the repo root.
> Claude can read and write files directly, so it processes all 200 rows in one go.

---

You are an expert annotator for **TakeMeter**, a classifier of football (soccer)
discourse quality from r/soccer-style communities (World Cup, MLS, clubs).

## Your task
Read `data/examples_to_label.csv` (columns: `id,text,label,notes,source`). For every
row, assign **exactly one** label to the post in the `text` column, then write the
results to `labels/claude/labeled.csv`.

## Labels (choose exactly one)
- **analysis** — A structured argument backed by *specific, verifiable* evidence:
  statistics, historical comparison, or tactical observation. It reasons toward a
  conclusion instead of just asserting one.
  - e.g. *"City's PPDA dropped from 11.2 to 8.7 because Rodri drops between the CBs and the fullbacks invert."*
- **hot_take** — A bold, confident opinion **asserted without real evidence**. The
  claim might be true, but the post asserts rather than argues; usually contrarian.
  - e.g. *"Pep is overrated, anyone could win with that budget."*
- **reaction** — An **immediate emotional response** to a specific recent event
  (≈ within a month). Little to no argument — a feeling in the moment.
  - e.g. *"97th-minute winner in the derby I AM SHAKING I cannot breathe."*
- **mixed** — A genuine **combination** (e.g. an emotional reaction that *also*
  carries a real argument) where no single label clearly dominates.
  - e.g. *"Gutted we lost but the xG was 0.4 to 2.1, same midfield problem all season."*
- **skip** — Only for unreadable, non-English, or off-topic rows. Not a real class.

## Decision rules (apply in order)
1. Specific, verifiable evidence that would stand even if you removed the opinion framing → **analysis**.
2. Evidence vague, cherry-picked, or decorative (just enough to sound credible) → **hot_take**.
3. In-the-moment emotional response to a recent event, no real argument → **reaction**.
4. Genuinely blends an emotional reaction with a real argument, neither dominates → **mixed**.
5. Tie / 50-50: scan for keyword cues (numbers/percentages → analysis; ALL-CAPS/"!!!" → reaction; "overrated"/"change my mind" → hot_take). If still unresolved → **mixed**.

## Important judgment notes
- A single decorative stat does **not** make a post analysis — ask whether it's
  *reasoning* or just *flavor*. ("He's washed, one goal in nine, cope" = hot_take.)
- All-caps and emoji alone signal reaction, but reaction + a substantive critique = mixed.
- Don't reward topic. A post *about* tactics that only asserts is still hot_take.

## Output
Write `labels/claude/labeled.csv` with **exactly** these columns:

```
id,label,confidence,rationale
```

- `id` — copy from the input row.
- `label` — one of `analysis|hot_take|reaction|mixed|skip` (lowercase, exact).
- `confidence` — your certainty in [0,1], two decimals.
- `rationale` — ≤ 15 words naming which rule fired.

Process **all 200 rows**, do not truncate, do not add commentary outside the CSV.
After writing, print the label distribution (count per label) so I can sanity-check
the balance.
