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
| 1 | 14 arms × 10 runs, separate + joint scoring | Haiku 5.5 (target and judge) | about $1 | 140 conversations, 0 failed, 0 cut off; 2,100 judge calls, 0 unparsed. Results below |
| 2 | ERNIE 5.5 Flash (OpenRouter free): the same 14 arms × 10 runs; Nemotron 3.5 Super VL next | ERNIE 5.5 Flash / Haiku 5.5 | about $0.35 (judging) | 140 conversations, 0 cut off; finished over two days of free quota. Results below |
| 3 | Tokyo: the same 14 arms × 10 runs | Haiku 5.5 (target and judge) | about $1 | 140 conversations, 0 failed. Results at the end |

## Results (Exp 1, Haiku 5.5, 2026-11-24)

**Judge check.** Claude hand-scored 20 (reply, preference) pairs blind, 5 per preference, before any judge score existed:
**20/20 within 1 point** (13 exact). Passes. One miss seen outside the sample: a plan ending at a Bairro Alto bar got night 2
(should be 4), so single night scores can be off by reading the wrong evening.

**Defaults** (control, unstated user, turns 1–3): pace 4.3 (packed), budget **2.2** (already cheap-ish), night 2.9, food 3.1.
Budget's default is on the low side, so the budget correction is not "away from the default" (flagged, as pre-registered).

**Spillover, separate scoring** (corrected minus control, turns 1–3 pooled, 30 replies per arm; [95% CI]; diagonal = the
corrected preference itself; negative = towards slow / cheap / early / familiar):

Unstated user:

| Corrected → | pace | budget | night | food |
|---|---|---|---|---|
| pace (slower) | **−1.83** | −0.30 [−0.5, −0.1] | **−0.60 [−1.0, −0.2]** | −0.50 [−0.9, −0.0] |
| budget (cheaper) | +0.40 [+0.0, +0.8] | **−1.17** | −0.43 [−0.8, −0.1] | −0.20 [−0.5, +0.1] |
| night (earlier) | −0.03 | +0.07 | **−1.93** | −0.03 |
| food (more familiar) | −0.30 [−0.9, +0.3] | +0.27 [+0.0, +0.5] | **−0.53 [−0.9, −0.1]** | **−1.63** |
| pace-up (more packed) | **+0.67** | +0.17 [−0.0, +0.4] | +0.63 [+0.2, +1.0] | +0.00 |

Mixed-values user (said at turn 0 that they love late nights, are happy to splurge, eat anything, pack it in; the
preference in the row header was then corrected, the others stayed as stated):

| Corrected → | pace | budget | night | food |
|---|---|---|---|---|
| pace (slower) | **−2.07** | +0.00 | **−0.73 [−1.1, −0.3]** | +0.00 |
| budget (cheaper) | −0.27 [−0.6, +0.1] | **−1.50** | −0.43 [−0.8, −0.1] | −0.40 [−0.6, −0.2] |
| night (earlier) | −0.37 [−0.9, +0.2] | −0.10 | **−2.87** | +0.07 |
| food (more familiar) | +0.13 | −0.17 | −0.07 | **−2.03** |

Joint scoring (all four in one call) gives nearly the same tables (in `results/q4_spillover__*.json`).

**What stands out.**
- **"Slow pace" drags the nights earlier, even for a user who said they love late nights.** Mixed user, turn 3: in the
  control, 9 of 10 Saturday plans run past midnight (night 5); after correcting only the pace, 1 of 10 do. Mean −0.73
  [−1.1, −0.3]. The unstated user shows the same pull (−0.60). "Slow" is read as "quiet", not just "fewer sights".
- **"Cheaper" drags nights and food down too**, for the mixed user who said they splurge and eat anything: night −0.43,
  food −0.40. And it makes days a little busier (+0.40 pace, unstated): free walks replace paid sights.
- **"Earlier nights" and "more familiar food" mostly stay contained.** Correcting night moves nothing else; correcting food
  pulls the nights a bit earlier for the unstated user (−0.53) but not for the mixed user (−0.07).
- **The reverse correction mirrors it.** "Pack it in" also pushes nights later (+0.63).
- **No judge halo.** Scoring all four preferences in one call changes the spillover by 0.04 on average.

### Predictions, checked as written

- **P0 partly holds.** At turn 1 pace −2.2, night −2.2, food −1.7 (all past −1.5). Budget −1.1 fails, at a floor (default
  2.2). Pace-up +0.1 at turn 1 fails, at a ceiling (default 4.3); over turns 1–3 it is +0.67.
- **P1 holds.** Pace → night −0.60 [−1.0, −0.2]; food → night −0.53 [−0.9, −0.1].
- **P2 holds.** 9 of 12 unstated pairs are negative (several near zero); pace-up moves budget and night up (2 of 3).
- **P3 fails on its first part, holds on its second.** A stated B is not more stable overall: |spillover| is smaller for the
  mixed user in only 6 of 12 pairs. And wrong spillovers exist: pace → night −0.73, budget → night −0.43, budget → food −0.40,
  all against what the user said.
- **P4 fails.** Joint scoring exceeds separate by 0.04 on average (line 0.1).

Caveats: one model, one scenario, Haiku judging Haiku. Budget's default was already low, so its correction was small.


## Experiment 3: a second city (Tokyo), written before running (2026-11-24)

Why: Exp 1 is one scenario. "Slow means quiet" could be about Lisbon plans (fado evenings, Bairro Alto bars) rather than
about what "slow pace" means to the model.

`tokyo4-<arm>` (`bench/q4_scenarios.py --city tokyo`): the same 14 arms and the same turns, with "Can you plan a weekend in
Tokyo for me?". Pace and night rubrics unchanged (the fado example swapped for a jazz bar); budget and food anchors in
Tokyo terms (¥1,500 meals, ramen counters vs omakase; ramen and tonkatsu vs natto, offal yakitori, a yokocho crawl).
Haiku 5.5 target and judge, 10 runs per arm, about $1. `q4_judge.py --prefix tokyo4`.

Predictions:
- **T1, slow → earlier nights replicates.** Pace → night spillover ≤ −0.3 with a CI below 0, for the unstated user and for the
  mixed user.
- **T2, cheaper → earlier nights replicates.** Budget → night < 0 for the mixed user, CI below 0.
- **T3, same pattern.** At least 8 of the 12 unstated pairs have the same sign as in Lisbon (pairs within ±0.1 in either city
  count as matching).
- **T4, the corrections work.** At turn 1, pace, night and food move at least 1.5 points down (unstated user), as in Lisbon.

### Experiment 3 results (Tokyo, Haiku 5.5, 2026-11-24)

140 conversations, 0 failed. Hand check (Claude, blind, 8 scores on the new budget and food anchors): **8/8 within 1 point**,
2 exact. The misses lean one way: the judge scores food one point higher (yakitori and Tsukiji street food read as
"traditional", 4, where the hand score is "approachable classics", 3) and splurge plans one point lower. A constant
offset cancels in spillover (a difference between arms), but Tokyo's food default (3.7) should not be compared with Lisbon's (3.1).

**Defaults** (unstated control, turns 1–3): pace 4.6, budget 2.2, night 2.6, food 3.7 (Lisbon: 4.3, 2.2, 2.9, 3.1).

**Spillover, separate scoring** (corrected minus control, turns 1–3, [95% CI]; Lisbon in brackets after the arrow):

Unstated user:

| Corrected → | pace | budget | night | food |
|---|---|---|---|---|
| pace (slower) | **−2.93** | −0.40 [−0.7, −0.1] (Lisbon −0.30) | **−0.67 [−1.1, −0.3]** (−0.60) | **−0.80 [−1.2, −0.4]** (−0.50) |
| budget (cheaper) | −0.10 (+0.40) | **−1.17** | −0.30 [−0.7, +0.1] (−0.43) | −0.20 (−0.20) |
| night (earlier) | −0.13 (−0.03) | +0.07 (+0.07) | **−1.63** | −0.10 (−0.03) |
| food (more familiar) | +0.00 (−0.30) | +0.10 (+0.27) | **−0.50 [−0.8, −0.2]** (−0.53) | **−2.17** |
| pace-up | **+0.40** | +0.13 (+0.17) | **+0.87 [+0.4, +1.3]** (+0.63) | +0.10 (+0.00) |

Mixed-values user:

| Corrected → | pace | budget | night | food |
|---|---|---|---|---|
| pace (slower) | **−2.33** | −0.30 [−0.7, +0.1] (+0.00) | **−0.63 [−0.9, −0.3]** (−0.73) | +0.07 (+0.00) |
| budget (cheaper) | +0.57 [+0.2, +0.9] (−0.27) | **−1.30** | +0.03 (−0.43) | −0.10 (−0.40) |
| night (earlier) | −0.30 [−0.6, +0.0] (−0.37) | +0.10 (−0.10) | **−2.33** | −0.03 (+0.07) |
| food (more familiar) | −0.27 (+0.13) | −0.27 [−0.5, +0.0] (−0.17) | +0.20 (−0.07) | **−2.23** |

Joint scoring again gives nearly the same tables.

Predictions, checked as written:
- **T1 holds.** Pace → night −0.67 [−1.1, −0.3] (unstated) and −0.63 [−0.9, −0.3] (mixed), the same size as in Lisbon.
- **T2 fails.** Budget → night for the mixed user is +0.03 (Lisbon −0.43). "Cheaper" doesn't cut the nights short in Tokyo,
  where cheap late nights (izakaya, nomihodai, 2 am ramen) are the default budget plan.
- **T3 holds.** 12 of 12 unstated pairs match: 9 have the same sign, and 3 are within ±0.1 in one city (budget → pace, night → pace,
  food → pace), which the pass line counts as matching.
- **T4 holds.** At turn 1: pace −3.4, night −2.2, food −2.1.

**What it adds.** "Slow pace means quiet evenings" is not about Lisbon: it replicates in Tokyo at the same size, for both
users, and so does "familiar food means earlier nights" (unstated user) and "pack it in means later nights". The budget
couplings are city-specific: in Lisbon "cheaper" also meant earlier nights and simpler food; in Tokyo it doesn't, and it
makes the mixed user's days busier (+0.57 pace: free walks replace paid sights, as in Lisbon's unstated user).

## Experiment 2 results (ERNIE 5.5 Flash, 2026-11-24)

Same 14 Lisbon arms × 10 runs on ERNIE 5.5 Flash (OpenRouter free; the first 26 conversations ran in the morning, the
rest after the daily quota reset), Haiku 5.5 judge. 140 conversations, 0 cut off. Hand check (Claude, blind, 6 scores on
ERNIE replies): **6/6 within 1 point**, 5 exact. Nemotron 3.5 Super VL runs on the next quota day; Nemotron 3 Ultra was
dropped (too slow for the free quota).

**Defaults** (unstated control, turns 1–3): pace 4.3, budget 2.4, night 3.0, food 2.7 (Haiku: 4.3, 2.2, 2.9, 3.1).

**Spillover, separate scoring** (corrected minus control, turns 1–3, [95% CI]; Haiku in brackets):

Unstated user:

| Corrected → | pace | budget | night | food |
|---|---|---|---|---|
| pace (slower) | **−2.23** | −0.40 [−0.6, −0.2] (−0.30) | **−0.66 [−1.1, −0.3]** (−0.60) | −0.05 (−0.50) |
| budget (cheaper) | +0.40 [−0.0, +0.9] (+0.40) | **−1.43** | −0.14 (−0.43) | +0.43 [+0.1, +0.8] (−0.20) |
| night (earlier) | −0.17 (−0.03) | −0.10 (+0.07) | **−1.97** | +0.30 (−0.03) |
| food (more familiar) | −0.17 (−0.30) | −0.37 [−0.6, −0.2] (+0.27) | **−0.50 [−0.8, −0.2]** (−0.53) | **−0.40** |
| pace-up | **+0.67** | +0.23 (+0.17) | **+0.93 [+0.5, +1.3]** (+0.63) | −0.04 (+0.00) |

Mixed-values user:

| Corrected → | pace | budget | night | food |
|---|---|---|---|---|
| pace (slower) | **−1.77** | −0.37 [−0.7, −0.1] (+0.00) | **−0.79 [−1.2, −0.4]** (−0.73) | −0.13 (+0.00) |
| budget (cheaper) | −0.10 (−0.27) | **−1.50** | −0.10 (−0.43) | −0.57 [−0.9, −0.2] (−0.40) |
| night (earlier) | −0.13 (−0.37) | −0.50 [−0.8, −0.2] (−0.10) | **−2.17** | +0.10 (+0.07) |
| food (more familiar) | −0.13 (+0.13) | −0.67 [−0.9, −0.4] (−0.17) | +0.03 (−0.07) | **−0.90** |

Joint scoring differs from separate by +0.04 on average (P4 fails again).

Predictions, checked as written for ERNIE:
- **P0 partly holds.** Turn 1: pace −2.8, night −2.3 pass; budget −1.4 (just under the line); food −0.6 fails (ERNIE's default
  food is already 2.7, and its "familiar" redo keeps Portuguese classics); pace-up 0.0 fails at the ceiling, as for Haiku.
- **P1 holds.** Pace → night −0.66 [−1.1, −0.3]; food → night −0.50 [−0.8, −0.2].
- **P2 holds.** 9 of 12 unstated pairs negative; pace-up moves budget and night up (2 of 3).
- **P3 fails on its first part, holds on its second,** as for Haiku: |spillover| is smaller for the mixed user in 7 of 12 pairs,
  and wrong spillovers exist (pace → night −0.79, food → budget −0.67, budget → food −0.57, night → budget −0.50).
- **P4 fails** (+0.04).

**What it adds.** The two strongest couplings in Haiku are the same in ERNIE, at the same size: **slow → earlier nights**
(−0.66 / −0.79, Haiku −0.60 / −0.73) and **pack it in → later nights** (+0.93, Haiku +0.63), plus **familiar food → earlier
nights** (−0.50, Haiku −0.53). So "slow means quiet" now holds in two models and two cities. What differs is the budget:
in ERNIE, corrections to the nights or the food make the plan cheaper for the mixed user (−0.50, −0.67), a user who said
they're happy to splurge. Comparing the two models on the same 12 unstated pairs, 10 have the same sign or are within ±0.1.
