import csv
import re
from pathlib import Path


ANALYSIS_REGEX = re.compile(r"\b(xg|xga|xgd|xg\+xa|xg\+xa|expected|per 90|per game|\d+%|\d+\.\d+ xG|\bgoals?\b.*\d|\b\d+ of \b)\b", re.I)
HOT_TAKE_WORDS = ["overrated", "fraud", "cope", "hot take", "never win", "always", "worst", "can't", "can't stand", "shouldn't", "trash", "bullshit"]
REACTION_WORDS = ["shaking", "cry", "crying", "heartbroken", "sobbing", "i'm shaking", "i am shaking", "!!!!!!", "!!!", "scenes", "i blacked out", "i lost my mind", "my guy scored", "get innnn", "we're in the final"]


def score_confidence(kind):
    if kind == 'analysis':
        return 0.92
    if kind == 'reaction':
        return 0.90
    if kind == 'hot_take':
        return 0.86
    if kind == 'mixed':
        return 0.82
    return 0.60


def label_text(text: str):
    t = text or ""
    t_low = t.lower()

    has_analysis = bool(ANALYSIS_REGEX.search(t))
    has_reaction = any(w in t_low for w in REACTION_WORDS) or (t.isupper() and len(t) < 200)
    has_hot = any(w in t_low for w in HOT_TAKE_WORDS) or 'hot take' in t_low

    # Mixed: both substantive evidence and emotional content
    if has_analysis and has_reaction:
        return 'mixed', score_confidence('mixed'), 'emotion plus verifiable evidence'
    if has_analysis and has_hot:
        return 'analysis', score_confidence('analysis'), 'specific stats or verifiable claim'
    if has_analysis:
        return 'analysis', score_confidence('analysis'), 'specific stats or verifiable claim'
    if has_reaction and has_hot:
        return 'hot_take', score_confidence('hot_take'), 'strong assertion with emotion'
    if has_hot:
        return 'hot_take', score_confidence('hot_take'), 'bold assertion, little evidence'
    if has_reaction:
        return 'reaction', score_confidence('reaction'), 'emotional in-the-moment response'

    # Fallback heuristics: numeric patterns without clear context -> analysis
    if re.search(r"\d+[\-–—]?\d+|\b\d{1,3}%\b|\b\d+\.\d+\b", t):
        return 'analysis', score_confidence('analysis'), 'numeric/statistical claim'

    # default: hot_take if it contains sweeping or normative language
    if re.search(r"\b(should|must|never|always|ban|boycott)\b", t_low):
        return 'hot_take', score_confidence('hot_take'), 'sweeping normative claim'

    # otherwise mixed low confidence
    return 'mixed', score_confidence('mixed'), 'ambiguous tone and content'


def main():
    src = Path('data') / 'examples_to_label.csv'
    out_dir = Path('labels') / 'copilot'
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / 'labeled.csv'

    with src.open(newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # label all rows (or limit to first 300)
    to_label = rows[:300]

    with out.open('w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['id', 'label', 'confidence', 'rationale'])
        for r in to_label:
            id_ = r.get('id')
            text = r.get('text', '')
            label, conf, rationale = label_text(text)
            writer.writerow([id_, label, f"{conf:.2f}", rationale])

    print(f'Wrote {out} with {len(to_label)} labels')


if __name__ == '__main__':
    main()
