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
>> Use Claude Code, Codex, and Copilot to label the data and compare the results with your own labels. Have prompts and separate folder for each model's labels. Report the agreement rate and analyze where you disagreed.

- Confidence calibration: Report whether your model's confidence scores are meaningful — does a 90% confident prediction actually get it right more often than a 60% confident one?
- Error pattern analysis: Go beyond listing individual wrong predictions — identify a systematic pattern in the errors (e.g., "the model consistently misclassifies sarcastic posts" or "it can't distinguish X from Y when the post is short").
- Deployed interface: Build a simple interface that accepts a new post, runs it through the classifier, and displays the label and confidence. Commit the interface code to your repo and document how to run it in your README.

Specs and requirements:
 - data: 200+ labeled examples, with at least 30 examples per label. You can use more data if you want, but you must have at least 30 examples per label.
 - workflow: You must use a workflow that includes data collection, annotation, model fine-tuning, and evaluation. You can use any tools you want, but you must document your workflow in your README.
 - return label prediction on a "take"

Evaluation:
