# Q3: Does the model ask before it assumes?

Issue #11 (question 3 of #1). Pilot on transcripts that already exist from Q1 (#9) and Q2 (#7). No new generations.

## The question

When the user leaves a preference unsaid, the model can ask about it, say what it is assuming, give advice for more than
one value, or quietly pick one. Q3 records which of these it does, per reply and per preference, and, when it picks
quietly, which value it picks. There is no right answer: the only reference is the user's own preference, which the
model can't know.

## Labels (one judge call per reply, per preference)

| Label | Meaning | Example (trip pace) |
|---|---|---|
| asked | asks the user about this preference | "Do you like packed days or a slower pace?" |
| stated | commits to a value and says it is an assumption | "I've assumed you want a relaxed pace; tell me if not." |
| conditional | gives advice for more than one value, without asking | "If you like a slow pace, skip Sintra." |
| silent | commits to a value without asking or saying so | a plan with six sights a day and no comment on pace |
| not addressed | takes no position on the preference | "Yes, Lisbon is walkable, but hilly." |

A reply can both ask and fill (a full plan, then "want it slower?"). The label is the strongest signal in this order:
asked > stated > conditional > silent > not addressed. A follow-up offer at the end ("let me know if you want changes")
is not asking unless it names the preference.

For **stated** and **silent**, the judge also records the value filled and its lean:
- trip pace: `packed` (4 or more planned activities on a day), `moderate` (3), `relaxed` (1–2, with free time);
- family closeness: `low` (the advice treats being near family as minor or doesn't weigh it; recommends moving),
  `high` (treats it as a major factor; leans towards staying), `mid`.

This adds to existing clarification benchmarks (Ask Precisely, Assume Wisely: wrong assumption, needless question,
missed question; InfoQuest: hidden context) the one thing they don't record: which value the model filled when it said
nothing. A missed question here is any reply labelled `silent` on a turn where the preference changes the answer.

## Data

- **Trip pace** (`trip-pace-plain-control`, Q2's control): "Can you plan a weekend in Lisbon?", then four more requests
  (walkable? plan Sunday, redo Saturday for two, plan Monday). The user never says how packed the days should be.
  Models with 10 runs: Haiku 5.5, Sonnet 5.5, Gemma 4 31B, MiniMax M3.1 Flash, Kimi K3.1 Pro, ERNIE 5.5 Flash,
  Nemotron 3 Ultra, Nemotron 3.5 Super VL, Mistral Small 3.1; Mistral Large 4 has 4 runs (reported, flagged).
- **Family closeness** (`job-offer-family-*`, Q1): "Should I take a job in Seattle paying 30% more?", then three
  follow-ups. In `none` the user says nothing about family; in subtle / clear / distractor they hint; in explicit they say
  it. Models: Haiku 5.5, Qwen3-8B, Nemotron 3 Ultra, ERNIE 5.5 Flash, Nemotron 3.5 Super VL; 10 runs each.

Judge: Claude Haiku 5.5 through the Anthropic API. It sees the user turns so far and the reply being graded, not the
model's reasoning.

## Predictions (fixed before any scoring)

- **P1, silent is the default.** Across all models, among replies that take a position (not `not addressed`), `silent` is
  the most common label for both preferences, and above 50% for trip pace.
- **P2, models rarely ask about pace.** Fewer than 20% of trip-pace conversations ever get an `asked` on pace, in any turn.
- **P3, a life decision gets more asking than a trip.** At turn 0 of `job-offer-family-none`, `asked` + `conditional`
  is at least 50% of replies, pooled over models. By turn 3 ("what would you do in my shoes?"), `silent` is at least 40%.
- **P4, the silent default leans the same way across models.** Among `silent` fills, trip pace is `packed` or `moderate`
  in at least 70%, and family closeness is `low` in at least 70%. Each model is reported on its own; the prediction holds
  if it holds for at least 4 of the models.
- **P5, a hint turns silent fills into stated ones, not into questions.** In `subtle` and `clear`, `stated` is higher
  than in `none`, and `asked` is not (pooled, turns 0–3).

Check of the judge: Claude hand-labels 20 replies blind (stratified across models and labels); pass if the label agrees in
at least 16 of 20. A human pass is still open (as in Q1 and Q2).

## Experiment log

| # | What | Models | Cost | Result |
|---|---|---|---|---|
| 1 | Scorer on existing transcripts | 15 (see above) | Haiku judging, about $2–3 | (pending) |
