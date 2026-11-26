# Second judge: does Haiku's scoring hold up under a judge from another company?

Covers Q1–Q4 (#1). Written 2026-11-24.

## Why

Haiku 5.5 is the judge in every question, and in most of them it also judges its own replies. Claude's blind hand checks
agreed with it, but Claude is from the same company. A judge from another company, given the exact same prompt, is the
check that rules out "Haiku likes Haiku's style".

## Setup

`bench/cross_judge.py`. A fixed sample (seed 0), Haiku-target replies only, each question's own judge prompt unchanged:

| Question | Sample | What is compared |
|---|---|---|
| Q1 | 40 answer scores, 8 per condition (`job-offer-family-*`) | 1–5 family-closeness score |
| Q2 | 40 pace scores, 10 per turn 1–4 (`trip-pace-corrected`) | 1–5 pace score |
| Q3 | 60 labels from the trip, job-offer, laptop and dinner scenarios, stratified by Haiku's label (12 each; 10 `stated` exist) | asked / stated / conditional / silent / not addressed |
| Q4 | 30 Lisbon replies × 4 preferences, separate scoring | 1–5 per preference |

Second judge: **Gemma 4 31B** (Google), on NVIDIA NIM's free API, never OpenRouter. 260 items, 0 unparsed, free.
(gpt-oss-120b on Groq was also started; its free tier ran at about 10 minutes per item, so it was stopped at 103 items
and is not used.)

## Results

| Question | Agreement with Haiku | Mean difference (Gemma − Haiku) | Rank correlation |
|---|---|---|---|
| Q1 | 100% within 1 point, 62% exact | +0.03 | 0.91 |
| Q2 | **45% within 1 point**, 45% exact | **+1.15** | 0.18 |
| Q3 | 77% same label, Cohen's κ 0.71 | – | – |
| Q4 budget | 100% within 1, 70% exact | +0.17 | 0.89 |
| Q4 food | 97% within 1, 60% exact | +0.33 | 0.79 |
| Q4 night | 93% within 1, 53% exact | +0.30 | 0.88 |
| Q4 pace | 83% within 1, 63% exact | +0.00 | 0.83 |

Q3, Haiku's label (rows) against Gemma's (columns):

| | asked | stated | conditional | silent | not addressed |
|---|---|---|---|---|---|
| asked | **12** | 0 | 0 | 0 | 0 |
| stated | 0 | **6** | 6 | 0 | 0 |
| conditional | 0 | 0 | **12** | 0 | 0 |
| silent | 0 | 0 | 4 | **7** | 1 |
| not addressed | 0 | 0 | 2 | 1 | **9** |

By scenario: dinner 13/13, job offer 16/21, laptop 17/26.

## Reading it

- **Q1 and Q4 hold.** Gemma agrees with Haiku as closely as Claude's hand checks did. On Q4 it scores food and night about
  0.3 higher across the board; spillover is a difference between arms, so a constant offset cancels.
- **Q3 holds where it matters most, and is noisy where we already knew.** Every `asked` label is confirmed (12/12), so
  "models rarely ask" is not a judge artefact. The disagreements are all on the boundaries already flagged by the hand
  checks: `stated` vs `conditional` (6 of 12) and `silent` vs `conditional` (4 of 12). Gemma reads more replies as hedging;
  so Q3's `silent` shares are, if anything, an upper bound.
- **Q2: Gemma fails the rubric, not Haiku.** The Q2 rubric asks for a count of main activities, and its example reason
  starts "busiest day: 2 main activities". Gemma wrote "2 main activities" for every disagreeing reply and scored 5.
  Counting three of those replies by hand gave 3 main activities each (for example Jerónimos, a riverfront walk to Belém
  Tower, and a sunset viewpoint), which is Haiku's score. So Q2 still has no valid second judge; its check remains Claude's
  hand check and the Sonnet/Haiku cross-check in the Q2 notes.

## Limits

- One outside judge, on one sample; Q2 not covered.
- The sample is Haiku-target replies only (the self-judging case); other targets are not re-checked.
- Claude's hand checks are from the same company as Haiku; a human pass is still open.
