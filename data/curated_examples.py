"""Curated, realistic r/soccer-style posts for the TakeMeter labeling task.

These are hand-authored to span the four trainable labels
(analysis / hot_take / reaction / mixed) plus deliberately ambiguous edge
cases. They are written to *look and feel* like real football discourse
(varied length, slang, emoji, all-caps, typos) WITHOUT being copied from any
real user, so they are safe to commit.

Data-integrity note — the grouping is author-time scaffolding, not a label.
The lists below (ANALYSIS, HOT_TAKE, …) exist only so the corpus stays balanced
across the label space while it is being written. The intended label is the one
thing that must NOT reach the annotation process: it is never written to the
exported CSV (which carries only `text` + a data-source tag like `curated`/`rss`,
with the `label` column empty), and `all_curated()` returns the posts
DETERMINISTICALLY SHUFFLED so the by-label authoring order can't leak into
whatever consumes them. Every post is judged on its own wording at annotation
time — by a human in the web Train page, or by the model prompts in prompts/.
"""

import random

# Posts that *lean* analysis — specific, verifiable evidence / tactics / stats.
ANALYSIS = [
    "City changed their build-up this season: Rodri drops between the centre-backs, both fullbacks invert into midfield, and their PPDA dropped from 11.2 to 8.7. That's why they're winning the ball 10 yards higher than last year.",
    "Haaland's npxG is 0.78 per 90 but he's finishing at 1.05 per 90 across 12 games. That overperformance regresses to the mean almost every time. Penciling him in for 30+ league goals again is reading variance as skill.",
    "Arsenal's set-piece numbers are not a fluke. 14 of their 41 goals came from dead balls, they've got the tallest average starting XI in the league, and Nicolas Jover runs the most rehearsed near-post routines in the division.",
    "People say Madrid 'got lucky' in the Champions League but they were +6 in xG across the two legs against City. You don't generate that margin over 180 minutes by accident — the low block plus Vinicius in transition is a real, repeatable plan.",
    "The reason United's midfield gets overrun is spacing, not effort. Casemiro and Bruno occupy the same vertical lane in build-up, so the pivot is effectively one player. Watch the wide CB always has to step into midfield to cover.",
    "Look at the USMNT's pressing triggers under the new staff: they jump the moment the ball goes back to the keeper's weaker foot. Against Mexico they forced 7 turnovers in the final third doing exactly that.",
    "Inter Miami's possession share is inflated by garbage-time passing. In high-leverage minutes (tied or one-goal games) their pass completion in the final third drops to 61%. Messi is creating, but the structure around him is thin.",
    "Liverpool's fullbacks combined for 4.1 progressive carries per 90 last season vs 2.3 this season. The drop-off in chance creation isn't the forwards — it's that the width and progression from the back has fallen off a cliff.",
    "If you watch Bellingham's heat map he's not a No. 10, he's a late-arriving No. 8 who times runs into the box. That's why his goals look 'easy' — he's consistently the free man at the back post because he starts deeper than the defense tracks.",
    "Comparing eras: prime Henry averaged a goal involvement every 96 minutes in the league; prime Haaland is at one every 78. Different leagues and service, but the raw output gap is real and worth stating before we crown anyone.",
    "Saudi Pro League xG models are basically useless right now — the sample is tiny and the defensive quality variance is enormous. Anyone quoting xGD tables from that league with a straight face doesn't understand the error bars.",
    "Spurs concede most goals in the 15 minutes after they score. Ange's line stays at the halfway mark regardless of game state, so a single ball over the top turns into a 1v1. It's a coaching choice, not a fitness problem.",
    "VAR overturned 3 of their last 5 conceded penalties, but the underlying issue is the defensive midfielder stepping out and leaving the channel. Even when the calls go their way the structural hole is the same.",
    "MLS roster rules matter more than people admit: the three-DP cap plus targeted allocation money means most teams are top-heavy. That's why depth collapses in the playoffs when a DP gets injured.",
    "The reason the World Cup expansion to 48 teams favors bigger nations isn't the group stage, it's the extra knockout round. More matches means squad depth and rotation become decisive, which structurally disadvantages one-star teams.",
    "Onana's distribution numbers are elite (88% under pressure) but his claim success rate on crosses is bottom-five among starting keepers. United's issues from set pieces trace directly back to that, not to the centre-backs.",
    "Watch how Leverkusen built their unbeaten run: Xabi alternates a 3-4-2-1 in possession and a 4-4-2 mid-block out of possession. The full-back-to-wing-back transition is the whole trick and almost nobody pressed it correctly.",
    "Pulisic's left-half-space heat map at Milan is nearly identical to his best Dortmund season. He was never a winger who beats you on the touchline — he's an inside forward, and Chelsea kept misusing him wide.",
    "Penalty conversion regresses hard. A team converting 90%+ over half a season is almost never doing something repeatable — they're riding a hot streak. Build your over/under model on the long-run 76% league average, not the recent run.",
    "The data on high lines: PSG conceded 0.4 xG per game from through balls under the old setup and 0.9 now. Pushing 8 yards higher created more turnovers but the goals-against from balls in behind more than cancel the gain.",
    "Argentina's 2022 run was built on game management, not dominance. They led for 71% of their knockout minutes and sat in a 4-4-2 to protect leads. Calling it the 'best team' ignores how they actually won — control, not territory.",
    "Brentford's throw-in routine is genuinely a tactical weapon. They generate ~0.9 xG per game from long throws and set pieces combined, which for a mid-table side is the difference between 40 and 52 points.",
    "Vardy aged so well because his game was never about athleticism in the first place — it was timing of runs and first-touch direction. Those don't decay like top speed, which is why he kept scoring at 35.",
    "The reason possession stats lie: holding 65% of the ball in your own half is a defensive statistic, not an attacking one. Look at final-third entries per possession instead — that separates control from sterile domination.",
    "Foden's best position is debatable but the numbers aren't: he creates 2.6 chances per 90 from the left vs 1.4 centrally. Pep keeps playing him as a false 9 and the creation output halves every time.",
    "Newcastle's xGD was top-four-level for 18 months; the league position lagged because of finishing variance and an injury list that hit the spine. The underlying process was always better than the table said.",
    "If you actually chart Mbappe's touches, 70% come in the left channel. Madrid asking him to lead the line centrally is a stylistic mismatch — his entire game is built on starting wide and attacking the diagonal.",
    "Counter-pressing only works with the right rest defense. Klopp's best Liverpool kept a 2-3 base behind the ball so they could swarm immediately. The current side breaks with 4 forward, which is why one lost duel becomes a clean break.",
    "The 'small sample' problem with new managers: a 6-game bounce is almost always tactical surprise plus motivation, not a fixed improvement. Judge the underlying shot quality, which usually hasn't moved as much as the results.",
    "De Bruyne's decline is real and measurable: his line-breaking pass completion fell from 81% to 68% post-injury, and his sprint count per game is down a third. Still elite on dead balls, but the open-play engine has changed.",
    "Mexico's problem at the last World Cup wasn't talent, it was chance quality. They out-shot opponents but averaged 0.08 xG per shot — lots of low-percentage efforts from outside the box, almost no penetration of the six-yard area.",
    "Atletico under Simeone allow the fewest 'big chances' in La Liga almost every year. It's not luck — the two banks of four compress the central zone so everything gets funneled wide into low-value crosses.",
    "Wing-back systems live and die by the No. 6's lateral coverage. When Chelsea ran a 3-4-3, the single pivot had to cover sideline to sideline; teams that beat them simply switched play fast enough that one player couldn't.",
    "Look at goalkeeper post-shot xG: the league's best shot-stoppers save about 5-7 goals above expected per season. That's roughly 4-6 points. It's a real edge but smaller than the 'world-class keeper wins you the league' narrative claims.",
    "The reason build-up from the back keeps failing for them is the keeper's split-second hesitation. He receives, takes an extra touch, and the press arrives. It's a decision-speed issue, fixable with reps, not a personnel one.",
    "Fixture congestion data is clear: teams in their third game in seven days concede ~0.3 more xG and complete 4% fewer passes. The 'we were just tired' excuse is actually backed by the numbers more often than fans assume.",
    "Salah's underlying numbers are still top-three in the league for a winger — 0.55 xG+xA per 90. The 'he's finished' takes are reacting to a finishing cold spell, not a drop in chance creation.",
    "Promoted teams that survive almost always do it with set pieces and a low xGA, not by trying to play out. The data on the last decade is brutal: the possession-based promoted sides get relegated at nearly double the rate.",
    "Italy missing the World Cup twice in a row isn't bad luck, it's a structural pipeline issue: the share of minutes given to Italian U-21s in Serie A is the lowest among the big five leagues. You can chart the talent drought.",
    "The expected-threat (xT) model shows their left side generates 60% of their dangerous progression. Any opponent that doubles the left winger cuts their attack in half — and the good teams already do exactly that.",
]

# Posts that *lean* hot_take — bold, confident, evidence-free / contrarian.
HOT_TAKE = [
    "Messi in MLS is just a marketing stunt. He's washed and Miami would be a mid team without the hype. Change my mind.",
    "Pep is the most overrated manager alive. Anyone could win with that budget. Give me a striker and a billion dollars too.",
    "Ronaldo is the GOAT and it's not close. Messi never did it in a real league or for his country until everything was handed to him.",
    "The Premier League is overrated and slow. La Liga has better technical football and you all know it but won't admit it.",
    "Mbappe will never win a Ballon d'Or at Madrid. He's a flat-track bully who disappears in the games that actually matter.",
    "Hot take: the 2010s Barcelona team would get bullied by any modern Premier League midtable side. The game has moved on, they'd get pressed off the park.",
    "Saka is carried by the system. Put him at a bottom-half club and he's a 7-goal winger, nothing special.",
    "Klopp is a vibes manager. Take away the crowd and the press conferences and his tactics are just 'run a lot'.",
    "Modern football is unwatchable. Every team plays the same boring possession nonsense. Bring back actual wingers and tackling.",
    "The Champions League means more than the World Cup now. Higher quality every single week, the international game is a relic.",
    "Bellingham is the most overhyped player on the planet. One good half-season and everyone lost their minds.",
    "Spending big on a goalkeeper is always a waste. You could play a championship keeper behind a good defense and never notice.",
    "Italy not qualifying is good for football. Their style is anti-football and nobody outside Italy will miss them.",
    "The USMNT will never win a World Cup with the current development system. Pay-to-play killed the talent pipeline forever.",
    "Neymar wasted the most talent of any player in history. Pure laziness. He could've been top three all time.",
    "VAR has completely ruined the sport and we should scrap it tomorrow. The game was better when refs just got things wrong.",
    "Any team that parks the bus deserves to lose. It's cowardly football and Mourinho set the sport back ten years.",
    "Erling Haaland is a flat-track bully. He's invisible against elite defenses and only feasts on relegation fodder.",
    "Premier League refs are the worst in the world by a mile. It's not even a debate at this point.",
    "Tiki-taka is dead and good riddance. It was always boring sideways passing dressed up as genius.",
    "The MLS is a retirement league and pretending otherwise is delusional. The standard is barely Championship level.",
    "Vinicius is more flair than end product. Strip out the diving and he's an average winger with a good highlight reel.",
    "International football is basically meaningless now. Club football is where all the real quality is and everyone knows it.",
    "Real Madrid don't win, they get gifted things by refs and 'mentality'. It's the most overrated dynasty in sports.",
    "Goalkeepers being forced to play out from the back is the dumbest trend in football. Just kick it long, cowards.",
    "The Ballon d'Or is a popularity contest and always has been. It tells you nothing about who actually played best.",
    "Half the 'world class' defenders today wouldn't survive against an actual No. 9 from the 2000s. Soft era.",
    "Hot take: relegation is the only thing keeping the bottom half honest, and the playoff format is more exciting than the title race.",
    "Pep ruined a generation of English coaches by making everyone copy a system that only works with the best players alive.",
    "Messi's international trophies all came when the rest of the world got worse, not when he got better. Timing, not greatness.",
    "Big clubs buying up every wonderkid and loaning them out is killing competitive balance and nobody in charge cares.",
    "The German national team has been irrelevant for a decade and it's because their academies all produce the same robotic midfielder.",
    "Wingers who don't track back should be benched, full stop. I don't care how many goals they score, it's not worth it.",
    "The transfer market is completely broken when a Championship full-back costs 40 million. Clubs have lost their minds.",
    "South American leagues produce more raw talent than all of Europe combined and Europe just buys the finished product and takes credit.",
    "If your team needs a sporting director and 14 analysts to pick a striker, the manager isn't actually doing his job.",
    "Penalty shootouts are a coin flip and deciding a World Cup on them is a joke. Replay the match or share the trophy.",
    "Honestly the women's game is growing faster than the men's and in ten years the gap in entertainment will be gone. Screenshot this.",
    "Every 'tactical genius' manager is one bad season from being exposed as a guy who got lucky with a great squad.",
    "Brazil hasn't produced a real midfielder in 20 years and that's the whole reason they keep flaming out. Flair isn't football.",
]

# Posts that *lean* reaction — immediate emotional response to a recent event.
REACTION = [
    "I AM SHAKING. 97th-minute winner in the derby, I literally cannot breathe right now. WHAT A GAME.",
    "Heartbroken. Don't talk to me. We threw away a two-goal lead again and I'm done with this club for the week.",
    "WEMBLEY HERE WE COME!!! I'm crying in the office, my coworkers think I've lost it. UP THE TOON.",
    "that miss. THAT MISS. open goal, six yards out, in the 89th minute. I have never been angrier at a television.",
    "BRO WE ACTUALLY DID IT. ten men, down a goal, and we won in stoppage time. football is the greatest thing ever made.",
    "I can't even type properly my hands are still shaking from that penalty save. GET INNNNN.",
    "Relegated. After 19 years in the top flight. I'm sitting in my car in the parking lot just staring at nothing.",
    "the ref just blew for full time and I screamed so loud the neighbors knocked. 3-2 COMEBACK ARE YOU KIDDING ME.",
    "i'm not okay. that was supposed to be our year. one kick away. i need to lie down.",
    "GOOSEBUMPS. the whole stadium singing after the equalizer in the 90th. nights like this are why I love this sport.",
    "absolutely buzzing!!! first derby win in four years and I will NOT be sleeping tonight. let's gooooo.",
    "devastated isn't a strong enough word. injury in the warmup to our best player before the final. why does this keep happening to us.",
    "I have watched the winner forty times. forty. I'm going to be late for work and I do not care even a little bit.",
    "we got absolutely battered 5-0 and I sat through every minute. why do I do this to myself. anyway see you all next week.",
    "VAR disallowed it after THREE MINUTES. I aged ten years standing in that away end. football is pain.",
    "MY GUY SCORED ON HIS DEBUT. eighteen years old, came on in the 80th, smashed it top corner. I'm so proud I could cry.",
    "knocked out on penalties again. of course it was penalties. of course it was. I'm numb.",
    "the noise when that free kick went in. I've never heard the stadium like that. still got chills typing this.",
    "promotion confirmed!!! grown men crying in the stands, including me. best day of the season by a mile.",
    "we lost to a 95th minute own goal. an OWN GOAL. I don't even have words I just want to scream into a pillow.",
    "Just got back from the match and my voice is completely gone. Worth it. WHAT a performance from the lads today.",
    "I literally jumped over my sofa when that went in. there's a lamp casualty. no regrets. SCENES.",
    "watching my team on a grainy stream at 3am and we just scored a 90th minute winner and I woke up the whole house. SORRY NOT SORRY.",
    "the keeper saved the last penalty and I blacked out for a second. we're in the final. WE'RE IN THE FINAL.",
    "two own goals and a red card in 20 minutes. I'm laughing because if I don't I'll cry. classic us.",
    "I traveled six hours for an away day and we lost in the last minute to a deflection. football owes me nothing and gives me less.",
    "THAT volley. I will be thinking about that volley on my deathbed. greatest goal I've ever seen live.",
    "we conceded in the first 30 seconds. THIRTY SECONDS. I hadn't even sat down. unreal.",
    "captain lifted the trophy and I just lost it completely. forty years of waiting. I'm a wreck and I'm happy.",
    "I cannot believe we let them score four. four! at home! the boos at full time said it all. embarrassing night.",
    "my heart is still pounding. last kick of the game, free kick, top bins, we stay up. I think I need a doctor.",
    "the manager got sacked an hour after the final whistle and honestly I cheered. enough was enough. fresh start please.",
    "watching the lads do a lap of honor after relegation hit different. I was sobbing. proud of them anyway.",
    "5-4 after extra time. FIVE-FOUR. I don't know what just happened but I feel like I ran a marathon.",
    "the equalizer in the 96th and the away fans went absolutely feral. I lost my scarf and possibly my mind.",
    "I told myself I wouldn't get my hopes up and then we scored twice in five minutes and now look at me, fully invested again.",
    "kid in front of me at his first match saw the winner go in and just turned around with the biggest smile. THIS is football.",
    "we're top of the league for the first time in my entire life and I had to pull the car over because I couldn't see straight.",
    "lost the cup final on penalties and walked out of the stadium in total silence with 30,000 people. you could hear a pin drop.",
    "absolutely scenes in my living room right now last minute winner I have woken the baby and it was 100% worth it",
]

# Posts that *lean* mixed — a real combination (reaction + argument, etc.).
MIXED = [
    "Gutted we lost, genuinely sick to my stomach — but the xG was 0.4 to 2.1, we got battered and deserved nothing. Same broken midfield all season, the emotion doesn't change the fact we're structurally a mess.",
    "I'm hyped, don't get me wrong, but let's be real: beating a ten-man side 1-0 at home after three straight losses doesn't fix a defensive line that's leaked nine goals in four games.",
    "What a winner, I lost my mind — but if we're honest the manager got bailed out again. We were second best for 70 minutes and the substitution that 'changed the game' was forced by an injury, not a plan.",
    "Buzzing for the three points but that was smash-and-grab. We had 31% possession and one shot on target. You can't keep riding the keeper having the game of his life and call it a system.",
    "Heartbroken, but credit where it's due: their press was better coached than ours, they pinned our fullbacks and we had no out-ball. I'm upset and impressed at the same time, weird feeling.",
    "Love this club but the ownership has to go. The atmosphere tonight was electric and it papered over the fact we haven't signed a striker in three windows while revenue went up 40%.",
    "Massive win and I'm thrilled — but be careful crowning us. We've beaten the bottom three back to back; the underlying numbers against top-half sides are still ugly and that's the real test.",
    "I cried at the final whistle, no shame. Still, the truth is we got promoted on set pieces and a hot finishing run that the xG says regresses next season. Enjoy tonight, worry tomorrow.",
    "Furious at the red card but rewatching it, it was the right call — stupid challenge, studs up, he left him no choice. We can be angry and wrong at the same time and tonight we were both.",
    "Over the moon with the comeback, genuinely one of the best nights as a fan. But two-nil down at home to that lot should never happen, and the first-half pressing structure was non-existent.",
    "Proud of the effort tonight, the lads ran themselves into the ground. Doesn't change that effort without a plan is why we're 14th — heart isn't a tactic and we've leaned on it for two years.",
    "Ecstatic we won the derby but I'll say it: the penalty was soft and we'd be screaming if it went the other way. Three points are three points, the performance was a 5/10.",
    "Devastated, but this is on recruitment, not the players. You can't sell your two best midfielders and replace them with loanees and expect to compete. The fans in the ground deserved better planning.",
    "Unreal atmosphere and a deserved win — and yet the bigger story is the academy kid who came on and changed the game. We've spent 200m and our best moment came from a free homegrown 19-year-old. Says a lot.",
    "Thrilled with the result, gutted about the injury. Realistically losing our only fit striker for three months means the January window now decides our season, hype or not.",
    "I'm buzzing but also nervous, weird mix. Beating the leaders feels huge, except we've now got six games against the bottom half and that's where we've dropped most of our points all year. This means nothing if we slip up there.",
    "Great win, terrible sign. We were carved open at will and only survived because they missed three sitters. Celebrate the points, but the defensive line being that high with our slow CBs is asking to get punished by a better side.",
    "Honestly relieved more than happy. We were awful, the manager's setup was too passive again, and we won on a deflection. I'll take the luck because we're in a relegation fight, but let's not pretend that was good football.",
    "So proud of the away end tonight, sang for 90 minutes through a 3-0 loss. The fans showed up; the board hasn't in a decade. That contrast is the whole story of this club right now.",
    "Yes we won and yes I screamed, but the captain's interview after was telling — even he admitted we 'rode our luck'. When your own leader says that, the warning signs are flashing under the celebration.",
    "Buzzing for the lads but the table doesn't lie: one win in eight before this. A single good night doesn't erase a pattern, and the fixtures get harder from here, not easier.",
    "Mixed feelings. The 4-3 was thrilling and I'll remember it forever, but conceding three at home twice in a month is a genuine tactical problem, not just 'an entertaining game'.",
    "Delighted to qualify but we backed into it — we lost our last two and got through on goal difference because rivals dropped points. I'm not going to overrate a campaign that limped over the line.",
    "Happy with the point away from home, that's a decent result on paper. But we sat so deep we invited 24 shots, and against anyone clinical that's three goals conceded. Pragmatism is fine; passivity that deep isn't.",
]

# Genuinely ambiguous edge cases — sit between two labels on purpose.
EDGE = [
    "LeBron of football lol but seriously Mbappe's playoff record against top seeds is below .500 if you actually check the knockout games.",
    "He's washed and the stats back me up: one goal in his last nine. Cope.",
    "Unreal goal but anyone defending that badly deserves to concede it, it's not even that impressive when you watch the markers ball-watch.",
    "We never win there and today proved it again, 0-4, the gap is just real and people need to stop pretending it's close.",
    "Best player in the world and it's not close, 30 goals already, what else does he have to do for you people.",
    "Typical us, bottling it when it matters, third year running we collapse in April. At this point it's a mentality thing you can almost predict.",
    "Refs again. Two clear penalties not given. Same every week against the big clubs and somehow it's always 'marginal'.",
    "Genuinely the worst signing in our history, can't trap a ball, can't track a runner, 25 million down the drain.",
    "That's why he's captain. Down a goal, grabs it, drives us up the pitch, scores. Leaders do that and the numbers don't capture it.",
    "I don't care what the xG says we were the better team and we got robbed, models don't watch the game.",
    "Their whole gameplan is fouling and time-wasting, 14 fouls in the first half, it's anti-football and the league lets them get away with it.",
    "Won 1-0, scrappy, ugly, I'll take it every single day of the week, pretty football doesn't win you anything in a relegation scrap.",
    "Knew we'd lose the second the lineup dropped, no holding midfielder against the best counter-attacking side in the league, baffling team selection.",
    "Big game, big player. Always shows up when it matters and that's worth more than all the pretty stats people throw around.",
    "Four shots on target, four goals, and people are calling us lucky. Take your chances and the 'xG' takes care of itself, simple game.",
]


# Extra batch to push the standalone (offline) corpus comfortably past 200.
EXTRA = [
    # analysis-lean
    "Their full-back overlaps 12 times a game but only completes 2 crosses into the box. That's not width, that's running into a dead end — opponents have figured out to show him the byline and crowd the cutback.",
    "Goal contributions per 90 are misleading for a deep playmaker. Look at xA from open play specifically: he's first in the league once you strip out the dead-ball assists that any decent set-piece taker would rack up.",
    "The reason their counter-press fails is the striker doesn't set the trap. He presses the centre-back's strong side, which opens the switch every time. One small cue change and that whole structure tightens up.",
    "Promotion-winning xGD last season was +0.6 a game; this season in the top flight it's -0.4. The squad didn't get worse, the league got better, and the wage bill says they were always going to scrap for survival.",
    "Penalty-area touches tell the story: their striker gets 6 a game at home and 2 away. They're a completely different, far more passive team on the road and the away record reflects exactly that split.",
    "If you isolate minutes with both their first-choice centre-backs on the pitch, their xGA per 90 is top four. The problem isn't the system, it's that the pair has started together 9 times all season.",
    "Corner conversion of 14% over a season is unsustainable — the league average is around 3%. Their points tally is inflated by a set-piece run that the underlying delivery quality doesn't support long term.",
    "He's not slow, he's badly positioned. His recovery speed is fine in isolation; he just starts five yards too narrow, so the diagonal in behind is always open. That's coachable, which is why I'd still buy him.",
    "Watch the No. 6 when they lose the ball: he steps to the ball-carrier instead of screening the pass into the 10. That single habit is why teams keep playing through their first line so easily.",
    "The keeper's xGoT-prevented is +6 this season — basically he's the reason they're mid-table not bottom three. Every other defensive metric is relegation-level and the table is flattering them badly.",
    # hot_take-lean
    "Possession stats are a scam invented to make boring teams feel clever. Nobody remembers who had the ball, they remember who scored.",
    "Half these 'generational talents' would be average in the 90s when defenders were allowed to actually defend. Soft era, protected forwards.",
    "Loyalty in football is dead and any player who kisses the badge then leaves in the summer should be booed for life, no exceptions.",
    "Your 'tactical masterclass' is just having better players. Sack the pundits, it's almost always that simple and everyone overthinks it.",
    "Big six fans complaining about fixture congestion while playing 11 internationals is the funniest thing in the sport. You wanted the squad, deal with it.",
    "Streaming has ruined match-going culture and the atmospheres prove it. Half the ground is filming on their phones instead of singing.",
    "A draw is a loss. I don't want 'a hard-earned point away from home', I want three points or I want to be angry, there is no in-between.",
    "Every wonderkid is 'the next big thing' until they have to do it on a wet Tuesday and 90% of them never do. Stop hyping teenagers.",
    "Modern goalkeepers are outfield players who happen to wear gloves and it's made the position worse, not better. Just save the ball.",
    "If your club's whole identity is 'we develop young players and sell them', you're not a football club, you're a finishing school with a stadium.",
    # reaction-lean
    "94th minute equaliser and I have lost my entire mind, the dog is hiding, the neighbors are concerned, I regret nothing.",
    "We're going down and I just sat in silence for ten minutes staring at the badge on my shirt. brutal.",
    "MY TEAM IS IN A FINAL. I have supported them for 22 years and we are in a FINAL. I'm shaking typing this.",
    "Sent off in the first ten minutes and we held on for the draw with TEN MEN, I have never been prouder, what a backs-to-the-wall job.",
    "I muted the stream after the third goal went in. couldn't take the commentary gloating. dark night to be a fan.",
    "the away end is bouncing on the stream and I'm sat at home doing the celebration alone in my kitchen like a lunatic. UP THE CLUB.",
    "lost in the 119th minute to a worldie free kick. nothing you can do about that one. still want to lie face down on the floor though.",
    "first goal at the new stadium and the roof nearly came off, goosebumps all over, what a moment to be there for.",
    "we scored, I jumped, I hit my head on the ceiling fan, the goal got chalked off for offside. a perfect summary of this season.",
    "the final whistle went and grown men around me were hugging strangers and crying. I'll never get tired of nights like this.",
    # mixed-lean
    "Great three points and I'm buzzing, but be honest with yourselves: that was 90 minutes of defending and one counter-attack. Against the top sides that approach gets you beaten 3-0.",
    "Love the fight tonight, genuinely. But 'fighting spirit' is what you praise when the football isn't good enough, and ours hasn't been for two months. The effort masked a real lack of ideas in the final third.",
    "Thrilled we won, gutted at how. A 30-yard screamer bailed out a flat performance and the manager will use it to justify a setup that isn't working. Wins like this hide problems instead of fixing them.",
    "I'll celebrate tonight and worry tomorrow, but worry I will: we've now won three on the bounce with a negative xGD in all three. The process is bad even when the results are good and that catches up with you.",
    "So happy for the kid scoring his first, real lump in the throat — but it also exposes that we're relying on a 19-year-old to dig us out because the 80-million striker still hasn't scored from open play since August.",
    # edge
    "Carried by VAR again, two of their goals should've been chalked off, but yeah sure 'great win', cope harder.",
    "He's a fraud, simple as. Big numbers against nobodies, vanishes in the games that decide trophies, the eye test never lies.",
    "We bossed that and lost. football makes no sense. 22 shots, one goal, sums up our whole miserable season honestly.",
    "Manager out. Bored of the excuses, bored of the 'project', three years and we're worse than when he started, the data and the eye test agree for once.",
    "Best atmosphere I've ever been part of and we still lost 2-1, kind of says everything about this club, brilliant fans propping up a broken team.",
    "Their xG was 1.9 to our 0.3 and we won 1-0, so spare me the 'deserved' chat, the scoreboard is the only stat that hangs in the trophy room.",
    "He glides past three players then passes it backwards. Most frustrating talented player I've ever watched, all the ability and none of the end product.",
    "Top of the league at Christmas means nothing and I'll keep saying it until people stop posting the table like it's a trophy. May is the only month that counts.",
    "We sold the academy graduate to a rival for 20 million and 'reinvested' it in a 31-year-old on huge wages. Whoever runs our recruitment is actively trolling the fanbase at this point.",
    "Penalty in the 98th minute to win it and I have genuinely never felt my heart beat like that, I had to sit on the floor of my own living room.",
    "The board put out a statement about 'the project' the same week we went out of two cups. Read the room. Nobody believes the PowerPoint anymore.",
]


def all_curated(shuffle=True, seed=1234):
    """Return the full curated corpus as a flat list of unique strings.

    The posts are concatenated by intended label only so this code is easy to
    maintain — but that authoring order is a label hint, so by default the list
    is shuffled with a fixed seed before it is returned. This strips the
    grouping (and therefore any "expected label" signal) at the function
    boundary, deterministically and independently of the caller, so nothing
    downstream can re-derive the intended label from position. Pass
    `shuffle=False` only for authoring/inspection, never for annotation.
    """
    combined = ANALYSIS + HOT_TAKE + REACTION + MIXED + EDGE + EXTRA
    seen, out = set(), []
    for t in combined:
        key = t.strip().lower()
        if key not in seen:
            seen.add(key)
            out.append(t.strip())
    if shuffle:
        random.Random(seed).shuffle(out)
    return out


if __name__ == "__main__":
    posts = all_curated()
    print(f"curated posts: {len(posts)}")
    print(f"  analysis-lean : {len(ANALYSIS)}")
    print(f"  hot_take-lean : {len(HOT_TAKE)}")
    print(f"  reaction-lean : {len(REACTION)}")
    print(f"  mixed-lean    : {len(MIXED)}")
    print(f"  edge cases    : {len(EDGE)}")
