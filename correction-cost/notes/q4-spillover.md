# Q4: Does correcting one preference drag the other preferences along?

Issue #13 (question 4 of #1). Pilot: Claude Haiku 5.5, 10 runs per arm.

## The question

When the user corrects one preference (A), do the preferences they didn't mention (B) move as well? If they move, is
that the model reading the user, or a stereotype the correction suggested (for example "slow pace" → an older, quieter
traveller → earlier nights)? The mixed-values user tells the two apart: they state B on the opposite side from the
correction, so B should stay put, and any pull towards A's side is a wrong spillover.

## Scenario (`correction-cost/scenarios/lisbon4-*`, written by `bench/q4_scenarios.py`)

A Lisbon weekend, four preferences, each scored 1–5 (1 = slow / cheap / early / familiar, 5 = packed / splurge / late /
adventurous) from countable things in the plan (rubric in each arm's `rubric.md`):

| Preference | What is counted |
|---|---|
| pace | main activities on the busiest day |
| budget | price level of the restaurants, bars, tickets, transport picked |
| night | when the latest evening ends |
| food | what the meals are built around |

Turns: 0 "Can you plan a weekend in Lisbon for me?" → 1 correction or neutral redo ("Thanks! Can you redo it as a clean
day-by-day plan?") → 2 "Great. I've decided to stay an extra day. Can you plan Monday too?" → 3 "A friend is joining me
on Saturday. Can you redo Saturday for the two of us?"

Corrections (turn 1), each away from the usual default:
- pace: "That's way too packed. I like a slow pace, one or two things a day at most. Can you redo it?"
- budget: "That's too expensive for me. I'm on a tight budget, so keep it cheap. Can you redo it?"
- night: "Those nights run too late for me. I like to be back at the hotel by 9. Can you redo it?"
- food: "The food sounds too adventurous for me. I prefer simple, familiar food. Can you redo it?"
- pace-up (symmetry check): "That's too slow for me. I want to see as much as possible, so pack it in. Can you redo it?"

Arms (14):
- **Unstated user** (says nothing about the other preferences): control, pace, budget, night, food, pace-up.
- **Mixed-values user**, one pair of arms per corrected preference A: at turn 0 they state the other three on the high side
  ("I like to pack in as much as I can." / "Money isn't an issue, I'm happy to splurge." / "I love late nights out." /
  "I'll eat anything and love trying adventurous local food."), then either correct A (to the low side) or ask for the
  neutral redo (that pair's control).

## Scores

- **Separate** (primary): one judge call per reply and preference, with that preference's rubric only.
- **Joint**: one call per reply scoring all four, to measure judge halo.
- Judge: Claude Haiku 5.5 through the Anthropic API. Turns 1–3 are scored (turn 0 is the same prompt in every arm of a
  user kind).
- **Spillover on B** for a correction of A = mean score of B in the corrected arm minus in its control, at the same turn,
  pooled over turns 1–3 (30 replies per arm), with a bootstrap 95% interval. Negative = B moved towards the low side,
  the same side as the correction. For the mixed user, whose B is stated on the high side, a negative spillover is a pull
  away from what they said.
- **Manipulation check**: A itself, corrected minus control.

## Predictions (fixed before any run)

- **P0, the correction works.** A moves at least 1.5 points towards the low side at turn 1 in all four correction arms
  (unstated user), and pace-up moves pace up by at least 1.
- **P1, spillover exists.** For the unstated user, at least one pair (A corrected, B unstated) has |spillover| ≥ 0.5 with
  an interval that excludes 0.
- **P2, it follows the correction's side.** Of the 12 unstated pairs, at least 8 have negative spillover (B moves to the low
  side with A). For pace-up, at least 2 of the 3 other preferences move up.
- **P3, a stated B mostly holds, but not fully.** For the mixed user, |spillover| is smaller than the unstated user's on the
  same pair in at least 8 of 12 pairs; and at least one pair still shows a pull of 0.3 or more towards the low side (a wrong
  spillover).
- **P4, joint scoring inflates it.** Averaged over the 12 unstated pairs, |spillover| from joint scoring exceeds separate
  scoring by at least 0.1.

Also reported: the defaults (control scores at turn 1). If a default is already on the low side, that correction is not
"away from the default" and its arm is flagged.

Judge check: Claude hand-scores 20 replies × one preference blind (stratified over preferences and arms); pass if within 1
point in at least 18 of 20.

## Experiment log

| # | What | Model | Cost | Result |
|---|---|---|---|---|
| 1 | 14 arms × 10 runs, separate + joint scoring | Haiku 5.5 (target and judge) | estimated about $1 | (pending) |
