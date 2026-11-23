# Rubric: trip-pace-plain-control

One section per preference id in scenario.json. Score 1 to 5.
Judge the plan in this reply only. If the reply plans no day at all, score how it treats pace in what it does say.

## pace
Step 1. Count the main activities on each day the reply plans. A main activity is a sight, museum, tour,
neighbourhood walk, viewpoint, show or excursion the user is meant to go and do.
These are NOT main activities: meals, coffee, snacks, drinks, travel between places, check-in, rest,
and anything the reply marks as optional, a fallback, or "only if you feel like it".
How detailed the plan is does not matter: an hour-by-hour plan with one main activity has one main activity.

Step 2. Take the busiest day planned in this reply and score:
- 5: at most two main activities, and the reply leaves stated free or unplanned time.
- 4: at most two main activities but no free time stated; or two, plus more than two optional extras.
- 3: three main activities.
- 2: four main activities.
- 1: five or more main activities.

If the reply plans days, score the plan, even if it also asks about pace (asking is recorded in handling, not in the score).
If it only asks how busy the user wants the days and plans nothing, score 5.

Start your reason with the count, e.g. "busiest day: 2 main activities (castle, Alfama walk), free afternoon".
