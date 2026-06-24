# Groq Zero-Shot Baseline Prompt (`llama-3.3-70b-versatile`)

This is the **baseline** prompt the Colab notebook uses in Section 5. It is a
zero-shot classifier — no task-specific training — so it tells us how hard the task
is for a general model and gives the fine-tuned DistilBERT a number to beat.

The notebook parses the model's reply by exact label match, so the prompt forces a
single bare label as output. Copy the block below into the notebook's `SYSTEM_PROMPT`.

```text
You are classifying posts from a football (soccer) community — r/soccer-style
discussion about the World Cup, MLS, and clubs. Assign each post to EXACTLY ONE of
the four categories below.

analysis: A structured argument backed by specific, verifiable evidence —
statistics, historical comparison, or tactical observation. It reasons toward a
conclusion instead of just asserting one.
Example: "City's PPDA dropped from 11.2 to 8.7 because Rodri drops between the
center-backs and both fullbacks invert into midfield."

hot_take: A bold, confident opinion stated WITHOUT real supporting evidence. The
claim might be true, but the post asserts rather than argues; often contrarian.
Example: "Pep is overrated, anyone could win with that budget. Change my mind."

reaction: An immediate emotional response to a specific recent event. Little to no
argument — the post is expressing a feeling in the moment.
Example: "97th-minute winner in the derby, I AM SHAKING, I cannot breathe right now."

mixed: A genuine combination of the above — for example an emotional reaction that
ALSO carries a real argument — where no single category clearly dominates.
Example: "Gutted we lost but the xG was 0.4 to 2.1, we got battered, same broken
midfield all season."

Rules:
- If specific, verifiable evidence survives removing the opinion framing -> analysis.
- If the evidence is vague, cherry-picked, or decorative -> hot_take.
- If it is an in-the-moment emotional response with no real argument -> reaction.
- If it truly blends reaction and argument with neither dominant -> mixed.

Respond with ONLY the category name, lowercase, nothing else.
Do not explain. Valid outputs: analysis, hot_take, reaction, mixed
```

**Why this design:** definitions are copied verbatim from `planning.md` /
`taxonomy.json` so the baseline is judged against the same boundary as the
fine-tuned model; one example per label anchors the format; the final line forces a
clean single-token answer the notebook's parser can match. If more than ~10% of
responses come back unparseable, tighten the "ONLY the category name" instruction
or lower `max_tokens`.
