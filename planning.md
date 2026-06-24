Show What You Know: TakeMeter

TakeMeter: a fine-tuned text classifier that evaluates discourse quality in an online community of your choosing. You'll define the labels, collect and annotate the data, fine-tune a model, and then honestly assess where it works and where it falls apart.

Choosen category: Discourse quality in online communities in Soccer (football) discussions, specifically around the FIFA World Cup, MLS, and Clubs.

Src:
- https://www.reddit.com/r/soccer/
- https://www.google.com/search?q=FIFA+World+Cup+2026&rlz=1C1VDKB_enUS1147US1147&oq=fif&gs_lcrp=EgZjaHJvbWUqDggAEEUYJxg7GIAEGIoFMg4IABBFGCcYOxiABBiKBTIQCAEQLhiDARixAxjJAxiABDIGCAIQRRg5MgYIAxBFGDwyBggEEEUYPTIGCAUQRRg8MgYIBhBFGDwyBggHEEUYQdIBCDE3NjlqMGo3qAIAsAIA&sourceid=chrome&ie=UTF-8
- https://www.fifa.com/en/tournaments/mens/worldcup/canadamexicousa2026
- https://www.foxsports.com/soccer/fifa-world-cup
- https://www.youtube.com/channel/UCpcTrCXblq78GZrTUTLWeBw
- https://www.youtube.com/fifa
- https://blog.youtube/news-and-events/fifa-world-cup-2026-youtube-partnership/
- https://www.youtube.com/Foxsoccer
- https://www.espn.com/soccer/
- https://www.mlssoccer.com/
- youtube.com
- instagram.com


✅ Strong taxonomy (precise and grounded):

analysis — the post makes a structured argument backed by statistics, historical comparison, or tactical observation. Evidence is specific and verifiable.
hot_take — a bold, confident opinion stated without supporting evidence. The claim might be true, but the post asserts rather than argues. It also is usually infamous and not very well liked or agreed apon opinion. Its controversial
reaction — an immediate emotional response to a specific event. Little to no argument — the post is expressing a feeling in the moment. It can only be relating to recent events like within a months time, not reviewing/analyzing old events/content.
popular - any post that has a lot of positive engagement. For this project sake, to avoid overlap with "hot_take" it will only include famous examples with postive agreement from a large group (determine large by the relative percent of people responding to the post positively out of the total members or a post that has relatively more positive engagement than others in the that media platform) This should have over 75-100+ people reponses to qualify.
mixed - some combination of the above labels (excluding "unlabled" and this lable "mixed")
unlabeled - post does not fit any above label

These work because: (1) you can state the decision boundary in a sentence, (2) two people reading the definitions would agree on most examples, and (3) the distinctions reflect how people in the community actually talk about discourse quality.
For ties: 50/50 try key-word searches to aid in decision and if that deosnt work label as mixed

Stretch goals:
- Inter-annotator reliability: Have at least one other person label 30+ of your examples independently, and report your agreement rate (Cohen's kappa or simple percentage agreement). Analyze where you disagreed. 
>> Use Claude Code, Codex, Copilot, and Groq to label the data and compare the results with your own labels. Have prompts and separate folder for each model's labels. Report the agreement rate and analyze where you disagreed.

- Confidence calibration: Report whether your model's confidence scores are meaningful — does a 90% confident prediction actually get it right more often than a 60% confident one?
- Error pattern analysis: Go beyond listing individual wrong predictions — identify a systematic pattern in the errors (e.g., "the model consistently misclassifies sarcastic posts" or "it can't distinguish X from Y when the post is short").
- Deployed interface: Build a simple interface that accepts a new post, runs it through the classifier, and displays the label and confidence. Commit the interface code to your repo and document how to run it in your README.

Specs and requirements:
 - data: 200+ labeled examples, with at least 30 examples per label. You can use more data if you want, but you must have at least 30 examples per label.
 - workflow: You must use a workflow that includes data collection, annotation, model fine-tuning, and evaluation. You can use any tools you want, but you must document your workflow in your README.
 - return label prediction on a "take"

Finalized trainable taxonomy (decision, 2026-06-24):
The model trains on FOUR mutually-exclusive labels — analysis, hot_take, reaction, mixed
— defined in taxonomy.json (the shared config used by the notebook, web app, and prompts).
- "popular" was dropped from the trainable set: it depends on engagement/response counts,
  which the text classifier cannot observe, so it cannot be learned from text alone.
- "unlabeled" became a "skip" option in the labeling UI only (unreadable / off-topic /
  non-English). It is filtered out before training, not predicted.
This keeps us inside the spec's 2–4 label requirement and ensures every class is learnable
from the post text.

Data collection (executed):
- Source strategy: best-effort scrape of public r/soccer-style listings (r/soccer, r/MLS,
  r/footballtactics, r/PremierLeague JSON) via data/build_dataset.py, with a hand-authored
  curated corpus (data/curated_examples.py, ~205 realistic posts) as fallback/supplement to
  guarantee 200 examples even offline. Output: data/examples_to_label.csv (label blank).
- Underrepresentation plan: the web Train page shows live per-label counts; if any class
  trails after a first pass, collect/curate more of that class before training. The notebook
  warns if any single label exceeds 70% of the set.

AI Tool Plan:
- Label stress-testing: had an LLM generate boundary posts between analysis/hot_take and
  reaction/mixed; the genuinely ambiguous ones live in the EDGE/curated set and sharpened
  the decision rules above.
- Annotation assistance: pre-label all 200 with Claude Code, Codex, and Copilot using the
  prompts in prompts/ (each writes labels/<model>/labeled.csv). Every pre-label is reviewed
  and corrected by hand in the web Train page; the reviewed labels/human/labeled.csv is the
  only file used for training. Disclosed in the README AI-usage section.
- Failure analysis: after evaluation, paste the misclassified test examples into an LLM to
  surface patterns (label pair confused, post length, sarcasm), then verify each pattern by
  re-reading the examples before writing it up.

Evaluation:
- Metrics: overall accuracy (headline, comparable to the Groq baseline) PLUS macro-F1 and
  per-class precision/recall/F1, because the classes are imbalanced and subjective — accuracy
  alone would hide a class the model ignores. A confusion matrix shows WHICH boundary fails
  (e.g. analysis→hot_take) and in which direction.
- Baseline: zero-shot llama-3.3-70b via Groq on the same locked test set, so fine-tuning's
  gain is measured honestly.
- Definition of "good enough": fine-tuned model beats the zero-shot baseline on both accuracy
  and macro-F1, reaches macro-F1 ≥ 0.65 with every per-class F1 ≥ 0.50 (no dead class), and on
  the hardest boundary (analysis vs hot_take) confuses them in < 30% of that pair's cases.
  Below that, the labels or data — not the training setup — are what to fix.
