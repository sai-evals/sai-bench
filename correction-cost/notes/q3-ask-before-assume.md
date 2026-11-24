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

Judge: Claude Haiku 5.5 through the Anthropic API (`correction-cost/bench/q3_judge.py`). It sees the user turns so far and the reply being graded, not the
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
| 1 | Scorer v0.1 on existing transcripts (1,470 replies) | 10 trip-pace models, 5 job-offer models | Haiku judging, about $0.70 | Hand check 13/20 (fails the 16/20 line); see below |
| 1b | Scorer v0.2 (asked / conditional boundary fixed), re-judged all 1,470 | same | about $0.70 | Fresh blind hand check 16/20 (passes). Results below are v0.2 |

Cost note: Haiku 5.5 is $0.10 / $0.50 per million input / output tokens; 1,470 judge calls used 3.25M input and 0.70M
output tokens (Haiku thinks by default), about $0.70.

### Judge check

**v0.1** (seed 11, 20 replies stratified by label): 13/20 on the first read. Two of the seven misses were mine: I had
read truncated replies, and the full text supports the judge (15/20). The other five were all one boundary: a list of
"questions to ask yourself" counted as asking; options tied to energy level with "which one sounds like you?" counted as
silent or conditional. Below the 16/20 line, so the prompt was revised before reading any results:

**v0.2** spells out the boundary. *Asked* = a question to the user that names the preference, or options that differ on
it followed by asking the user to pick. A "questions to ask yourself" list or factors to weigh = *conditional*. A question
about something else (dates, kids) is not asking. Describing what moving would look like, because the user asked, is not
a commitment. Fresh blind sample (seed 2024, full replies): **16/20, passes**. Remaining misses: one reply that ends
"Sintra on Monday, or the slow local day?" is still labelled silent (also missed by v0.1); two near-identical Haiku replies
("Pace: Saturday is busy. If you want a slower start, skip…") got silent and stated; a walkability answer was labelled silent.
`stated` is the noisiest label. A human pass is still open.

### Results (v0.2)

**Trip pace** (`trip-pace-plain-control`, % of replies; turn 1 is "is Lisbon walkable?", so mostly not addressed):

| Model | asked | stated | conditional | silent | not addressed | silent fills: packed / moderate / relaxed | runs that ever asked |
|---|---|---|---|---|---|---|---|
| Mistral Small 3.1 | 0 | 0 | 0 | 80 | 20 | 40 / 0 / 0 | 0/10 |
| Gemma 4 31B | 18 | 0 | 4 | 58 | 20 | 27 / 1 / 1 | 7/10 |
| MiniMax M3.1 Flash | 18 | 6 | 2 | 60 | 14 | 26 / 4 / 0 | 7/10 |
| Mistral Large 4 (4 runs) | 15 | 0 | 5 | 65 | 15 | 12 / 1 / 0 | 3/4 |
| Kimi K3.1 Pro | 2 | 2 | 0 | 76 | 20 | 22 / 10 / 6 | 1/10 |
| Haiku 5.5 | 2 | 2 | 2 | 74 | 20 | 29 / 5 / 3 | 1/10 |
| Sonnet 5.5 (Q2 transcripts) | 6 | 10 | 0 | 64 | 20 | 25 / 7 / 0 | 3/10 |
| ERNIE 5.5 Flash | 4 | 4 | 2 | 70 | 20 | 29 / 3 / 3 | 2/10 |
| Nemotron 3 Ultra | 20 | 0 | 8 | 62 | 10 | 27 / 4 / 0 | 8/10 |
| Nemotron 3.5 Super VL | 22 | 4 | 0 | 54 | 20 | 26 / 1 / 0 | 8/10 |

Asking happens mostly at turn 4 ("plan Monday too"), where several models offer two or three day types and ask the user
to pick (21 of 49 `asked` replies); at turn 0, 10 of 94 replies ask.

**Family closeness** (`job-offer-family-*`, pooled over the 5 models, % of 200 replies per version):

| Version | asked | stated | conditional | silent | not addressed |
|---|---|---|---|---|---|
| none | 2 | 0 | 36 | 38 | 24 |
| subtle | 4 | 1 | 46 | 42 | 6 |
| clear | 4 | 0 | 44 | 42 | 8 |
| distractor | 2 | 0 | 28 | 56 | 15 |
| explicit | 1 | 2 | 16 | 78 | 2 |

Per model, `none`: Haiku asks in 3/10 runs, ERNIE and Nemotron 3.5 Super VL in 1/10, Qwen3-8B and Nemotron 3 Ultra never.
Silent fills on family closeness lean low or mid (Haiku 5 low / 7 mid / 0 high; ERNIE 16 / 11 / 2; Nemotron 3 Ultra 16 / 3 / 1;
Qwen3-8B 7 / 2 / 0; Nemotron 3.5 Super VL 2 / 4 / 0).

### Predictions, checked as written

- **P1 holds for pace, borderline for family.** Of replies that take a position, 81% fill pace silently. For family
  closeness (`none`) it is 50% silent vs 46% conditional: silent is the most common, but only just.
- **P2 fails.** 40 of 94 trip conversations ask about pace at some turn (predicted under 20%). But most of that asking is at
  turn 4, as a choice between day types; at turn 0 it is 10 of 94. Mistral Small, Haiku, Kimi and ERNIE ask in 0–2 of 10 runs.
- **P3 fails.** At turn 0 of `none`, asked + conditional = 48% (line 50%). At turn 3, silent is 30% (line 40%): on "what
  would you do in my shoes?" models mostly hedge (46% conditional), not commit.
- **P4 holds for pace, fails for family.** Silent pace fills are packed or moderate in 10 of 10 models (≥ 70% each). Family
  fills are "low" in at least 70% for only 2 of 5 models; the rest split low / mid. Almost no model fills "high".
- **P5 fails.** A hint does not raise `stated` (0–1% in every version); it raises `conditional` (none 36% → subtle 46%,
  clear 44%), and asking stays at 2–4%.

**What stands out.**
- **Models almost never say what they assumed**: `stated` is 22 of 1,470 replies (1.5%). They ask, hedge, or fill silently.
- **Trip planning: silent and packed.** 4 of the 10 models never or almost never ask about pace, and their plans are
  packed. A user who wants a slow trip has to say so.
- **A big life decision gets hedging, not questions.** On the job offer, models write "if family matters to you…, if
  not…" far more than they ask how much it matters (2% asked). Even with a clear family hint, they hedge rather than ask.
- Asking is model-specific: the two Nemotrons, Gemma and MiniMax ask in most trip conversations; Haiku, Kimi, ERNIE and
  Mistral Small almost never.

