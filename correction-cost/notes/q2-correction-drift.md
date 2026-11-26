# Q2: does a correction stick? Working notes

Issue #7 (sub-issue of #1, question 2). These are working notes for review, not final results.
Everything so far is one scenario (a Lisbon trip, preference `pace`), two models, and 10 runs per cell.

## Short answer so far

It's too early to say "Sonnet drifts and Haiku doesn't". What the data supports:

- **Sonnet 5.5** follows the correction fully (10/10 runs score 5). In 4 of 10 runs, the next plan
  (turn 2, "plan Sunday in more detail") creeps back to 3 main activities while still calling itself slow.
  By turn 4, all 10 runs are back at 5. This is a short dip, not a lasting slide back to the default.
- **Haiku 5.5** follows the correction only partly: 6 of 10 runs reach 5 on the correction turn. Afterwards,
  4 runs dip by at least 1 point at turns 3–4, while other runs get *better*, so its average fallback is about 0.
- Experiment 3 checked whether "in more detail" causes Sonnet's dip. It doesn't: the dip remains with plain wording.
  But whether the dip is drift at all depends on how borderline items are counted (a sunset viewpoint, a sight
  passed on a walk). Our two judges count them differently. **That definition is the open decision now.**

## Experiment log

| # | What changed | Models (target / judge) | Cost | Result |
|---|---|---|---|---|
| 1 | Pilot. trip-pace pair, rubric v0.1 (1–5 anchors), max_tokens 3000 | Haiku + Sonnet / Sonnet, with a Haiku cross-check on Sonnet's runs | $2.17 for runs + about $1.50 to judge (estimate) | Sonnet drift-back 10/10, Haiku 5/10. Judges agree exactly on 23/50 scores. 4 control replies cut off |
| 1b | Re-judged Exp 1's transcripts with rubric v0.2-draft (counts main activities) | same | $2.18 | **Discarded.** It had a loophole: any reply that asked about pace scored 5, even an 8-activity plan |
| 2 | Re-judged Exp 1's transcripts with rubric v0.2 (loophole removed) and a parser fix. No new runs | same | $2.18 | Sonnet drift-back 5/10, Haiku 4/10. Judges agree exactly on 38/50 |
| 3 | New runs: turn 2 is "Can you plan Sunday?" instead of "…in more detail?". max_tokens 8000 | same | $1.88 for runs + $2.04 to judge | Sonnet's turn-2 dip remains (3/10 runs with the Sonnet judge, 5/10 with the Haiku judge), so the wording isn't the cause. The judges disagree a lot on whether it's drift at all |

The Exp 1 judgments are kept in the session scratchpad (`judged_v1/`), and the Exp 2 judgments in `judged_exp2/`.
`results/` is not committed, so every number here comes from those files.

## Your questions

### 1. "The control behaves as designed": what does that mean?

The control conversation is identical to the corrected one, except that turn 1 is a neutral question
("Is Lisbon easy to get around on foot?") instead of the correction. It exists to show what the model does
on turns 2–4 when nobody has corrected it. That gives a measured "default" to drift back *to*.

"Behaves as designed" means the control stays packed on the planning turns, so the gap is wide enough to measure:

| | turn 2 | turn 3 | turn 4 |
|---|---|---|---|
| Sonnet control mean (Exp 2) | 2.2 | 1.0 | 2.8 |
| Sonnet corrected mean (Exp 2) | 4.1 | 4.6 | 5.0 |

Example: control run 8, turn 3 ("redo Saturday for the two of us"). Sonnet plans Tram 28, Sé and Alfama, the flea
market, the castle, Baixa, Chiado, a sunset spot, and fado, which is 8 main activities, so it scores 1.

Two caveats:
- Control turn 1 always scores 5. The walkability answer plans nothing, so there is nothing to be packed.
  That turn is not used in the default, so it doesn't matter, but it looks odd in the table.
- Control turn 4 ("plan Monday") averages about 3, not 1. Both models suggest a Sintra day trip with
  two big sights, which counts as 2 main activities. On this turn, the gap between corrected and control is small.

### 2. "The correction works": what does that mean?

The reply right after the correction (turn 1) actually follows it.

**Sonnet, run 0, scored 5:**
> "A Slow Weekend in Lisbon. One or two anchors per day, with plenty of room for long meals, coffee stops, and
> wandering." Saturday: Alfama morning plus a fado dinner, with the castle marked *"Optional… fine to skip"*.

Sonnet scored 5 on turn 1 in all 10 runs.

**Haiku, run 0, scored 3:**
> "Here's a slower version with **one main activity per day**…"

It then plans Praça do Comércio, an Alfama wander, and fado on Saturday, and on Sunday Jerónimos, the Belém
riverfront, and a sunset miradouro: 3 per day. The judge's reason: *"3 main activities… despite the reply claiming one per day."*

Haiku's turn-1 scores over 10 runs were 3, 5, 5, 5, 5, 5, 3, 3, 3 and 4. So "partly works" means Haiku
often *says* it slowed down, but the plan underneath is still medium-busy.
This "says slow, plans more" pattern shows up again in Sonnet's turn-2 dip (question 4).

### 3. "A strong default": what kind of default?

When the user hasn't said anything about pace, both models plan a classic first-visit sightseeing weekend.
That means 5 or more main activities on the busiest day, with morning, afternoon, and evening all filled.
Turn 0 averaged 1.0–1.5 out of 5 for both models, in both scenarios.

Example: Sonnet, control run 6, turn 0. Saturday is Tram 28, Alfama and Sé, the castle, Baixa, the Santa Justa
lift and Chiado, then fado. Sunday is Jerónimos, Belém Tower, Padrão dos Descobrimentos, and LX Factory.

"Strong" matters for Q2. Drift is only measurable if there is a default far from the user's wish, and here it
is about 3–4 points away from what the user wants. That's good for measurement.

### 4. "The turn-2 dip is mostly an artifact, not drift": what does that mean?

The dip in Exp 1 came mostly from **how the judge counted**, not from the model planning more.
Here is the same reply (Sonnet, run 0, turn 2, titled "Sunday in Belém, Slow Version") under each rubric:

- **Rubric v0.1 scored it 3.** Reason: *"roughly seven timed items (pastries, Jerónimos, Belém Tower walk, LX
  Factory ride, long lunch, browsing, sunset drink, dinner)…"*. The judge counted meals and coffee as activities,
  because "in more detail" made the reply list them hour by hour.
- **Rubric v0.2 scored it 5.** Reason: *"2 main activities (Belém Tower riverside walk, LX Factory browsing),
  with Jerónimos marked optional and a deliberate free rest block."*

The reply didn't change; only the counting rule did. Across Sonnet's runs, the result went from
10/10 to 5/10 drift-back. Most of the original dip was therefore an artifact.

**What's left looks real but small.** In 4 runs, turn 2 still has 3 main activities while the reply calls
itself slow ("built around one main outing", then Jerónimos, a riverside walk to the tower, and LX Factory).
Those runs are back to 5 by turn 4. We don't know yet whether this is drift or a reaction to "in more detail".
Experiment 3 is meant to answer that.

### 5. "Fixing the rubric": which fixes?

Already done (rubric v0.2, used in Exp 2):
- Count only *main activities*: sights, museums, tours, walks, viewpoints, shows, excursions.
- Meals, coffee, drinks, travel, check-in, rest, and anything marked optional don't count.
- How detailed the plan is doesn't change the count.
- Score the busiest day in the reply: 5 means at most 2 activities plus stated free time; 4 means at most 2
  activities but no free time; 3, 2 and 1 mean 3, 4 and 5+ activities.
- If the reply plans something, score the plan. Asking about pace is recorded separately in `handling`, so it
  can't rescue a packed plan. (This removes the loophole from Exp 1b.)
- The judge must start its reason with the count, so a reviewer can check the score.
- The parser now takes the last valid JSON object, because judges sometimes write one answer and then a
  "corrected" one. That recovered 5 of 6 failures; one judge reply had no JSON at all.

Still open, as proposals:
- **The jump from 5 to 3.** Going from 2 activities to 3 drops the score by 2 points. In Exp 2, the two judges
  differ by 2 or more points on 10 of 50 corrected replies. I read all 10, and every one is a disagreement
  about counting, not about how busy the day felt. Option: score "3 activities with stated free time" as 4.
- **Borderline items.** The 10 disagreements come down to four kinds of item:
  (a) viewpoints and sunset miradouros, (b) a riverside walk that passes the tower and the monument,
  (c) "pick one: A or B" choices, and (d) grouping, where "Alfama walk with the castle" is one activity for
  one judge and two for the other. The rubric should name each of these.
- **The "optional" loophole.** A plan with 2 main activities and 6 "optional" ones scores 4 today.
- **Yes/no checks (MultiChallenge style).** Ask "how many main activities on the busiest day?" and "is free time
  stated?" as separate fields, and compute the score from them in code. This makes disagreements easy to diagnose.

### 6. Raising max_tokens: are there alternatives?

The problem: 4 Sonnet control replies were cut off at 3000 tokens. Sonnet thinks before answering, and the
thinking counts against the cap.

| Option | Effect | Verdict |
|---|---|---|
| Raise the cap (done: 8000) | No extra cost unless the tokens are used, since you pay per token produced | **Chosen** |
| Turn thinking off or lower the effort | Cheaper, but it changes the model being tested | Only as a deliberate separate condition |
| Ask for shorter replies in a system prompt | Changes behavior and could itself affect pace | No |
| Drop or flag cut-off replies when scoring | Still useful as a safety net | Worth adding: the runner already records `stop_reason` |

### 7. Why drop "in more detail"? What's the evidence, and what counts as success?

The evidence that the wording might matter:
- Sonnet's remaining dips are all at turn 2, the only turn that asks for *more detail*. Turns 3 and 4
  mostly recover.
- In the transcripts, "in more detail" produces hour-by-hour schedules. A detailed schedule invites the model to
  fill each slot, and that is where the third activity appears.

That's a hypothesis, not proof. Experiment 3 changes only the turn-2 wording, so it tests it directly.
We keep both variants: if detail requests do cause the creep, that's a finding about pressure, not noise to remove.

**Success criteria, written before the results:**

| Sonnet result on the "plain" variant, turn 2 | What we conclude |
|---|---|
| 0–1 of 10 runs dip (vs 5/10 with "in more detail"*) | Asking for detail causes the creep. It's a "pressure" effect, and Q2 reports both variants |
| 3 or more of 10 runs dip | It's not the wording; Sonnet slips on the first follow-up plan in general. That counts as real drift |
| 2 of 10 | Inconclusive at n=10; would need about 30 runs to tell |

\* This table first said 4/10. That counted only the drops to 3, but "dip" means falling at least 1 point,
the same rule `drift.py` uses, and run 8 fell from 5 to 4. So the correct baseline is 5/10.
I corrected this after the results came in; it doesn't change which row Exp 3 falls into.

Caveat: the cap went from 3000 to 8000 between experiments. That affected only cut-off *control* replies,
not corrected ones (0 cut off), so the comparison of corrected runs is clean.

### 8. "Hardening": what does that mean?

Making the test harder for the model, so that drift shows up if it exists. This only matters if Exp 3 shows little drift.
Ideas, mostly from PrefEval:
- **Distractor turns:** unrelated chat between the correction and the test turns ("what's the weather like in
  October?", "how do I get from the airport?"). This pushes the correction further back.
  PrefEval found that preference following drops sharply with distance.
- **Tempting turns:** a request where the busy answer is natural, such as "my friend has never been to Europe,
  what shouldn't we miss?". MultiChallenge's best items have this shape.
- **Longer conversations:** 8–10 turns instead of 5.
- **More preferences and settings:** for example, budget in a trip, length in a writing task, formality in emails.
  This keeps the result from depending on one scenario.

### 9. What does "re-judged with a stricter …" mean, and how does judging work?

Correction: I wrote "stricter *rubric*". The **scenarios didn't change**; only `rubric.md` changed. The version
was bumped to 0.2 to mark the rubric change.
Re-judging means running only the judge again over the same saved transcripts, with no new model replies.
That's why it was cheap and why the comparison is exact: same replies, different counting rules.

How the judge works (`bench/judge.py`):
- For every reply and every preference, it makes one separate call to a judge model.
- The call contains the preference ("How packed should each day be?"), what this user actually wants, the
  rubric section, the conversation so far, and the reply to grade.
- The judge returns JSON: `score` (1–5), `handling` (`asked`, `stated_assumption` or `silent`), and a one-sentence `reason`.

Judges:
- **Primary judge: Sonnet 5.5**, for both models' transcripts.
- **Cross-check: Haiku 5.5** re-judges Sonnet's transcripts. If both judges see the same pattern, the result
  isn't one judge's quirk. In Exp 2, both judges found Sonnet drifting back in 5–6 of 10 runs.
- **Known weakness:** Sonnet judging Sonnet risks self-preference bias, and both judges are Anthropic models.
  Before the final table, add a non-Anthropic judge (for example via OpenRouter) and hand-check about 20 scores.

## Experiment 3 results

What changed: only turn 2's wording ("Can you plan Sunday?") and the cap (8000 tokens).
The models, judges, rubric v0.2, and 10 runs per cell are the same as in Exp 2.
New scenarios: `trip-pace-plain-corrected` and `trip-pace-plain-control`. No reply hit the cap. 3 judge replies had no parseable JSON.

**Sonnet runs that dip at turn 2 (fall at least 1 point from the correction turn):**

| Turn 2 wording | Sonnet judge | Haiku judge |
|---|---|---|
| "plan Sunday in more detail" (Exp 2) | 5/10 | 5/10 |
| "plan Sunday" (Exp 3) | **3/10** | **5/10** |

Under the criteria written beforehand (3 or more means it's not the wording), **asking for detail is not what causes
the dip.** With the Sonnet judge it may weaken it slightly (turn-2 mean 4.1 → 4.5), but 10 runs can't tell 3 from 5.

**Mean scores (Sonnet judge):**

| turn | Sonnet corrected | Sonnet control | Haiku corrected | Haiku control |
|---|---|---|---|---|
| 0 | 1.2 | 1.2 | 1.0 | 1.0 |
| 1 correction | 5.0 | 5.0* | 4.1 | 5.0* |
| 2 plan Sunday | 4.5 | 2.1 | 4.3 | 1.4 |
| 3 redo Saturday for two | 5.0 | 1.1 | 4.6 | 1.2 |
| 4 plan Monday | 5.0 | 3.2 | 4.7 | 3.1 |
| drift-back | 3/10 | | 3/10 | |

\* As before, the control's turn 1 plans nothing (the walkability question), so it scores 5 and isn't used.

With the Haiku judge, Sonnet's drift-back is 8/10 and the "how far back" share is 38% / 34% / 15%.
With the Sonnet judge it's 3/10 and 17% / 0% / 0%. **That gap between judges is now the main problem.**

**Why the judges disagree.** On Sonnet's corrected replies at turns 2–4, the judges differ by 2 or more points
9 times. In all 9, Sonnet gave 5 and Haiku gave 3, because Haiku counted one more item. The extra items were:
- a miradouro or sunset viewpoint (4 times)
- a sight passed on a riverside walk (2)
- a garden next to a museum (1)
- a sight the reply didn't call an "anchor" (1)
- LX Factory, which Sonnet treated as lunch (1)

These are the borderline items (a)–(d) from question 5, plus a fifth: a place that is both a food stop and a sight.
Every one of the 9 is a counting disagreement.

**What this means:**
- The *shape* is the same in all three judgings: Sonnet holds the correction, sometimes adds one extra item
  at turns 2–3, and Haiku starts lower but doesn't fall further.
- *Whether that extra item counts as drift* depends entirely on whether a viewpoint or a sight on a walk is a
  "main activity". That's a definition we have to choose, not something the model or more runs can settle.
- So the next step isn't more runs. It's deciding the borderline rules (hand-check), re-judging Exp 2 and Exp 3
  under them (about $4, no new runs), and only then reading the drift numbers.

Haiku as a target: drift-back 3/10, and its scores *rise* after the correction (4.1 at turn 1 → 4.7 at turn 4).
That's the same picture as before: a weaker first correction that gets better as the conversation goes on.

## Next steps (to discuss)

1. Hand-check about 20 judge scores, starting with the 10 where the two judges differ by 2 or more.
   You decide each borderline item (a)–(d), and that becomes the rubric rule.
2. Decide on the remaining rubric proposals in question 5, then re-judge Exp 2 and Exp 3 (about $4, no new runs).
3. If the two judges then agree, read the drift numbers. Then harden (question 8) or widen to more
   preferences and models (issue #7 plan). Add a non-Anthropic judge before the final table.
4. Draft PR with these notes and the format lessons for #3.


## Experiment 4 (open model): written before running, 2026-11-22

Target: `nvidia/nemotron-3-ultra-550b-a55b:free` (open weights, NVIDIA-hosted free endpoint on OpenRouter).
Setup identical to Exp 3: `trip-pace-plain` pair, rubric v0.2, Sonnet 5.5 judge (Haiku 5.5 cross-check),
10 runs per scenario, max_tokens 8000. Smoke test of 1 run per scenario first.

**H7: an open model behaves like the Claude models on a single correction.** Decision rules, fixed now:

- Measurable default: the control's mean on turns 2–3 is ≤ 2.5. If it's higher, the model is already slow by
  default and drift can't be measured on this scenario. Report that and stop.
- Correction taken (as T2): the turn-1 mean on the corrected runs is ≥ 4.0 (Sonnet 5.0, Haiku 4.1 in Exp 3).
- Drift vs Claude (Sonnet judge, same dip rule): drift-back ≤ 4/10 means "like Claude" (Exp 3: Sonnet 3/10,
  Haiku 3/10); ≥ 6/10 means "drifts more"; 5/10 is inconclusive at 10 runs.

## Experiment 5 (open model, local): written before running, 2026-11-22

Target: `local:qwen3.6-27b` (Qwen 3.6 27B as packaged by LM Studio, run locally on an M5 Max, 32k context).
Same setup and the same H7 decision rules as Exp 4: measurable default (control turns 2–3 ≤ 2.5), correction
taken (turn 1 ≥ 4.0), drift-back ≤ 4/10 like Claude, ≥ 6/10 more, 5/10 inconclusive (Sonnet judge).

## Groq attempt (abandoned, not counted as an experiment): written before running, 2026-11-22

Targets: `groq:openai/gpt-oss-120b` and `groq:qwen/qwen3.8-27b` (open weights, Groq free tier: 1,000 requests/day,
8,000 tokens/minute). Same setup and H7 decision rules as Exp 4, except the reply cap is 4,000 tokens (not 8,000)
to fit Groq's per-minute limit; replies that hit the cap are flagged by the runner.

**Groq outcome:** both smoke tests failed and can't be retried around. The free tier caps a single request at
8,000 tokens (gpt-oss-120b: "Requested 10620"), and Qwen 3.8 27B may only write 1,000 output tokens a minute.
Five-turn conversations with long replies don't fit, so no Groq results are used.

## Experiments 6 and 7 (open models, OpenRouter free tier): written before running, 2026-11-22

- Exp 6: `nvidia/nemotron-3.5-super-vl:free` (open weights, 120B mixture-of-experts with 12B active; newer and
  smaller than Nemotron 3 Ultra, so it shows the effect of size within one family).
- Exp 7: `baidu/ernie-5.5-flash-preview:free` (open weights, Baidu; a fourth lab).

Same setup as Exp 4 (`trip-pace-plain` pair, rubric v0.2, 10 runs per scenario, max_tokens 8000), judged by Sonnet 5.5
only, without the Haiku cross-check, to save cost. Same H7 decision rules: measurable default (control turns 2–3 ≤ 2.5),
correction taken (turn 1 ≥ 4.0), drift-back ≤ 4/10 like Claude, ≥ 6/10 more, 5/10 inconclusive.

## Experiments 8–12 (open models, NVIDIA NIM free endpoints): written before running, 2026-11-22

- Exp 8: `nim:google/gemma-4-31b-it` (Google, 31B dense)
- Exp 9: `nim:moonshotai/kimi-k3.1-pro` (Moonshot)
- Exp 10: `nim:mistralai/mistral-large-4-1t-a52b` (Mistral, 1T mixture-of-experts with 52B active)
- Exp 11: `nim:minimaxai/minimax-m3.1-flash` (MiniMax)
- Exp 12: `nim:z-ai/glm-5.3-flash` (Z.ai)

Same setup as Exp 6/7 (`trip-pace-plain` pair, rubric v0.2, 10 runs per scenario, max_tokens 8000). From here on the judge is
Sonnet 5.5 called directly with the Anthropic API key (`anthropic:claude-sonnet-5-5`), not through OpenRouter. Same H7
decision rules: measurable default (control turns 2–3 ≤ 2.5), correction taken (turn 1 ≥ 4.0), drift-back ≤ 4/10 like
Claude, ≥ 6/10 more, 5/10 inconclusive.

## Numbering change, 2026-11-22

The local Qwen 3.6 27B run (pre-registered above as Exp 5) was stopped before any conversation finished. A too-short
request timeout cancelled replies and restarted conversations, and the user then dropped it. It is not counted and is
left out of the summary. The summary renumbers the later experiments: Nemotron 3.5 Super VL = Exp 5 (above: Exp 6),
ERNIE 5.5 Flash = Exp 6 (above: Exp 7), the NVIDIA NIM models = Exp 7–11 (above: Exp 8–12).

## Experiments 7, 8 and 10 results (NVIDIA NIM, Haiku judge), 2026-11-23

Same setup as Exp 3, 10 runs per scenario, judged by `anthropic:claude-haiku-5-5`. No failed runs, no cut-off replies, every judge answer readable. Judging cost about $0.23 for the three models.

| Exp | Model | Control t2–3 | Turn 1 | Turn 1 scored 5 | Drift-back | Pre-registered reading |
|---|---|---|---|---|---|---|
| 7 | Gemma 4 31B | 1.7 ✔ | 4.7 ✔ | 7/10 | 6/10 | more than Claude (≥ 6/10); same as Haiku 5.5 under this judge |
| 8 | Kimi K3.1 Pro | 2.0 ✔ | 4.8 ✔ | 9/10 | 0/10 | like Claude |
| 10 | MiniMax M3.1 Flash | 1.1 ✔ | 3.8 ✘ | 4/10 | 7/10 | correction not fully taken, so drift isn't read cleanly |

- Kimi: every corrected turn from turn 2 on scored 5. Its control scores 4.3 at turn 4 ("plan Monday"), so the pooled default (2.8) overstates its default; turns 2–3 give 2.0.
- MiniMax swings between 3 and 5 rather than sliding back; longest replies so far (about 2.5× Sonnet); asks questions in 13/100 replies.
- Exp 9 (Mistral Large 4) and Exp 11 (GLM 5.3 Flash) are still running.

## Correction, 2026-11-23: "never recovered" under the Haiku judge

Earlier notes said Nemotron 3 Ultra had the only run that slid back and never recovered (5 → 5 → 3 → 2). That sequence is from the Sonnet judge. Under the Haiku judge (current numbers), 7 of 80 runs dip at turn 2 or 3 and stay down through turn 4 ("stayed down"): Gemma 4 31B 3, MiniMax M3.1 Flash 2, Nemotron 3 Ultra 1 (5 → 3 → 4 → 2), Haiku 5.5 1 (3 → 5 → 2 → 2). Sonnet, Super VL, Kimi and ERNIE: 0. Runs that drop only at turn 4 aren't counted, since there's no later turn to see a recovery.

## Experiments 9, 11 and 12, 2026-11-23

**Exp 9 (Mistral Large 4) and Exp 11 (GLM 5.3 Flash): not run.** No free route finished them, and no partial run is used.
- Mistral Large 4: NVIDIA NIM finished 6 of 20 conversations, then dropped connections; one turn-0 reply took 17 minutes. There's no `:free` version on OpenRouter, Mistral's free plan reportedly has no API credits for Large 4, and GitHub Models was retired on 2026-07-30.
- GLM 5.3 Flash: NIM finished 0 of 20 (HTTP 504 and timeouts). OpenRouter's `glm-5.3-flash:free` and `glm-5.2:free` return 404. AIHubMix's free `coding-glm-5.3-flash-free` allows 10 tries per account with no credit, then returns a refusal as a normal 200 reply. Haiku scored those refusals 4.6–5.0 ("relaxed plan"), so the run was discarded, and `providers.py` now raises on that message.
- Lesson: check that a free route can finish about 100 replies, and read the replies before trusting the scores.

**Exp 12: Mistral Small 3.1 24B** on Cloudflare Workers AI's free plan (about half of the daily free allowance). Same setup as Exp 3, Haiku judge. 20 conversations, 0 failed, 0 cut off. The first judging pass stopped on a dropped connection after about 10 scores per scenario; `providers.py` now retries dropped connections, and all 100 replies were re-judged.

| turn | corrected | control |
|---|---|---|
| 0 | 1.8 | 2.2 |
| 1 | 3.9 | 5.0 |
| 2 | 2.9 | 1.7 |
| 3 | 2.6 | 1.2 |
| 4 | 2.5 | 1.3 |

- Default measurable: control turns 2–3 average 1.45 ✔. Correction taken only partly: 3.9 < 4.0 ✘ (4/10 runs score 5).
- Drift-back 9/10, stayed down 7/10: both the highest so far. The plans get busier with each turn (e.g. 1 → 5 → 3 → 2 → 1). Some replies call the plan relaxed while listing four stops. It never asks about or states an assumption about pace (0/100 replies).
- Across 9 models, a dip that lasts to turn 4 now appears in 14 of 90 runs, 7 of them from Mistral Small.

## Experiment 13: a second preference, the user's own voice ("sounds like me"), written before running (2026-11-26)

Why: every Q2 result so far is about trip pace. Writing in the user's voice is the everyday case of the same question:
people paste their own emails, ask for a draft "that sounds like me", correct it once, and then watch the next drafts
slide back to the assistant's register. The Sounds Like Me plan (playground repo) calls this the "assistant persona
pull"; its deslop toolkit supplies habits that can be checked without a judge.

Scenario (`bench/voice_scenarios.py`, `scenarios/voice-*`): "jo", an invented ceramicist, pastes three short emails (all
lowercase, short, dry, no "!", no dashes, no pleasantries, signs off "thx, jo") and asks for a reply to a client.
Turn 1 corrects the voice explicitly or is a neutral "final version" request. Turns 2-4 ask for a Slack message to an
assistant, a follow-up email and a thank-you note, never mentioning style. Four arms:

| Arm | Turn 0 | Turn 1 |
|---|---|---|
| `voice-corrected` | samples | "too polished, that's not me… all lowercase, short, no exclamation marks, no dashes, sign off 'thx, jo'" |
| `voice-control` | samples | "ok thanks. can you give me the final version?" |
| `voice-note` | samples + the same style note | neutral |
| `voice-nosamples` | no samples | neutral (the model's own voice for these tasks) |

Scores (`bench/voice_score.py`), on the draft only (preamble and notes cut by a heuristic; method recorded per reply):
five rule checks with no judge (lowercase, no "!", no dashes, no stock pleasantries, ≤ 80 words), the sign-off on email
turns, and a Haiku 1-5 "sounds like the samples" score. Haiku 5.5 target, 10 runs per arm (40 conversations, 200
replies), about $0.30.

Predictions:
- **V1, the correction works.** At turn 1, `corrected` passes at least 1.5 more core rules than `control`.
- **V2, it drifts back.** In at least half the corrected runs, a later turn (2-4) passes at least 2 fewer core rules than
  that run's turn 1.
- **V3, the new genre pulls hardest.** The thank-you note (turn 4) is the corrected arm's lowest later turn on core rules
  (capitals, "!" and "thank you so much" come back).
- **V4, samples alone don't carry the voice.** At turn 0, `control` (samples) is closer to `nosamples` than to `note`
  (samples + note) on core rules.
- **V5, the judge and the rules agree.** Pearson r between core rules and judge score ≥ 0.6 over all replies.

### Experiment 13 results (Haiku 5.5, 2026-11-26)

40 conversations (4 arms × 10), 0 failed; 200 judge calls, 0 unparsed; about $0.25. Extraction found the draft by its
greeting in 196 of 200 replies and in a code block in 4; none fell back to the whole reply. Claude read 12 turn-1 and
turn-4 drafts with the judge's reasons (not blind) and agreed with every score within 1 point.

| Arm | Turn 0 | Turn 1 | Turn 2 (Slack) | Turn 3 (follow-up) | Turn 4 (thank-you note) |
|---|---|---|---|---|---|
| corrected | 5.0 / 4.4 | 5.0 / **4.9** | 5.0 / 4.7 | 5.0 / 4.5 | 4.7 / **3.9** |
| control | 5.0 / 4.6 | 4.9 / 4.7 | 4.7 / 4.3 | 4.9 / 4.0 | 4.6 / **3.1** |
| note | 5.0 / 5.0 | 5.0 / 4.9 | 5.0 / 4.6 | 4.9 / 4.4 | 4.9 / 4.0 |
| nosamples | 3.6 / 1.9 | 3.6 / 1.8 | 3.8 / 2.8 | 3.8 / 2.0 | 3.0 / 1.2 |

Cells: core rules passed (0-5) / judge (1-5), mean of 10. Without samples, Haiku never writes lowercase or signs "thx, jo",
and uses stock phrases in 40% of first drafts. With samples, every surface rule passes from the first draft on, and the
sign-off holds on every email turn. Words per draft: samples 19-31; corrected 23-39; nosamples 38-65.

Predictions, checked as written:
- **V1 fails.** At turn 1, corrected passes 5.0 rules vs control 4.9 (line +1.5). There was nothing left to correct on the
  surface: three samples were enough for Haiku to copy lowercase, the sign-off and the length.
- **V2 fails on rules, holds on the judge.** 0 of 10 corrected runs lose 2 rules. But 9 of 10 lose at least 1 judge
  point by turn 4, from 5 at turn 1 to 4: the draft stays lowercase and signed, and the warmth comes back.
- **V3 holds.** The thank-you note is the lowest turn in every arm with samples (judge 3.1 to 4.0); stock phrases appear
  in 30% of corrected and control thank-you notes ("thanks so much", "really appreciate it", "we're grateful").
- **V4 fails.** At turn 0, samples alone (control) match samples plus note (5.0 rules each), far from no samples (3.6).
- **V5 holds.** Rules vs judge r = 0.81.

**What it shows.** Haiku copies the *form* of a voice from three samples at once (lowercase, length, sign-off) and keeps
it. What drifts is the *register*: when the genre turns warm (a thank-you note), the assistant's politeness comes back
("thanks so much… we'd love to return the favour"), wrapped in the user's lowercase. The explicit correction slows this
(thank-you note judge 3.9 corrected vs 3.1 control) but doesn't stop it. So "sounds like me" fails less on the habits a
rule can check and more on tone, which only the judge sees; the next version needs a register check (sentence length,
warmth words) and a model that doesn't copy surface form as easily as Haiku (the free models).
