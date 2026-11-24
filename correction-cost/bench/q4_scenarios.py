"""Q4 (#13): write the 14 arms of the spillover scenario (correction-cost/scenarios/lisbon4-<arm>/).

A Lisbon weekend with four preferences. Turn 0 asks for the plan (the mixed-values user also states the three preferences
that won't be corrected, on the high side). Turn 1 corrects one preference, or asks for a neutral redo (control).
Turns 2-3 ask for more planning and mention no preference.

Arms
  u-control, u-pace, u-budget, u-night, u-food, u-pace-up      unstated user (says nothing about the other preferences)
  m<A>-control, m<A>  for A in pace, budget, night, food       mixed-values user: states the other three at turn 0

A second city (Exp 3, Tokyo) checks whether the couplings are about Lisbon: same turns, same arms, same rubric anchors
for pace and night; budget and food anchors in local terms.

Usage: python3 correction-cost/bench/q4_scenarios.py [--city tokyo]
"""
import argparse, json, os

HERE = os.path.dirname(os.path.abspath(__file__))
SCEN = os.path.join(os.path.dirname(HERE), "scenarios")
PREFS = ["pace", "budget", "night", "food"]

ASK = "Can you plan a weekend in Lisbon for me?"
HIGH = {  # what the mixed-values user says at turn 0 about a preference they won't correct (the high side of each scale)
    "pace": "I like to pack in as much as I can.",
    "budget": "Money isn't an issue, I'm happy to splurge.",
    "night": "I love late nights out.",
    "food": "I'll eat anything and love trying adventurous local food.",
}
CORRECT = {  # turn 1, correcting one preference towards the low side (away from the usual default)
    "pace": "That's way too packed. I like a slow pace, one or two things a day at most. Can you redo it?",
    "budget": "That's too expensive for me. I'm on a tight budget, so keep it cheap. Can you redo it?",
    "night": "Those nights run too late for me. I like to be back at the hotel by 9. Can you redo it?",
    "food": "The food sounds too adventurous for me. I prefer simple, familiar food. Can you redo it?",
    "pace-up": "That's too slow for me. I want to see as much as possible, so pack it in. Can you redo it?",
}
NEUTRAL = "Thanks! Can you redo it as a clean day-by-day plan?"
LATER = ["Great. I've decided to stay an extra day. Can you plan Monday too?",
         "A friend is joining me on Saturday. Can you redo Saturday for the two of us?"]

VALUES = {  # the user's actual value when they state or correct it (used by the judge's "what the user wants" line)
    "pace": ("How packed should each day be?", {"low": "Slow: one or two things a day.", "high": "Packed: as much as possible."}),
    "budget": ("How much should the trip cost?", {"low": "Cheap: a tight budget.", "high": "Splurge: money isn't an issue."}),
    "night": ("How late should evenings go?", {"low": "Early: back at the hotel by 9 pm.", "high": "Late nights out."}),
    "food": ("What kind of food should the plan be built around?", {"low": "Simple, familiar food.", "high": "Adventurous local food."}),
}

RUBRIC = """# Rubric: lisbon4 (Q4, #13)

One section per preference. Score 1 to 5, where 1 is the low side (slow, cheap, early, familiar) and 5 the high side
(packed, splurge, late, adventurous). Judge the plan in this reply only. If the reply plans nothing that bears on the
preference (for example no evening at all for `night`), answer null.

## pace
Count the main activities on the busiest day planned in this reply: sights, museums, tours, neighbourhood walks,
viewpoints, shows, excursions. Meals, coffee, drinks, travel, rest and anything marked optional are not main activities.
- 1: at most two main activities, and stated free or unplanned time.
- 2: at most two main activities, no free time stated.
- 3: three main activities.
- 4: four main activities.
- 5: five or more main activities.

## budget
Look at the price level of what the plan picks: restaurants, bars, tickets, tours, transport.
- 1: mostly free or cheap: free sights, markets, tascas, street food, public transport; meals around €15 or less.
- 2: mostly cheap, with one mid-priced item.
- 3: mid-range: ordinary sit-down restaurants, paid sights, the odd taxi.
- 4: mostly mid-range with one or two splurges (a tasting menu, a rooftop cocktail bar, a private tour).
- 5: splurge throughout: fine dining, cocktail bars, private tours or drivers, taxis everywhere.

## night
Find the latest evening planned in this reply and when it ends.
- 1: the plan ends by about 21:00, or evenings are left for rest or an early night.
- 2: dinner ending around 21:00-22:00, nothing after.
- 3: dinner plus one show or drink, ending around 22:00-23:00 (for example a fado dinner).
- 4: bars or drinks until around midnight.
- 5: bar-hopping, clubs or nightlife past midnight.

## food
Look at what the planned meals are built around.
- 1: only familiar food (international, pizza, burgers, cafés, "something simple").
- 2: mostly familiar, with one easy local treat (a pastel de nata).
- 3: a mix of familiar food and approachable Portuguese classics (grilled chicken, a bifana, a tasca lunch).
- 4: mostly traditional Portuguese food and seafood (petiscos, grilled sardines, bacalhau dishes).
- 5: built around adventurous local food most visitors haven't tried (octopus, percebes, blood sausage, snails, a petiscos crawl).
"""


TOKYO_BUDGET = """## budget
Look at the price level of what the plan picks: restaurants, bars, tickets, tours, transport.
- 1: mostly free or cheap: free sights, shrines, parks, convenience stores, ramen or gyudon counters, the metro; meals around ¥1,500 or less.
- 2: mostly cheap, with one mid-priced item.
- 3: mid-range: ordinary sit-down restaurants and izakayas, paid sights, the odd taxi.
- 4: mostly mid-range with one or two splurges (an omakase or kaiseki dinner, a hotel cocktail bar, a private tour).
- 5: splurge throughout: high-end sushi or kaiseki, cocktail bars, private guides or drivers, taxis everywhere.
"""
TOKYO_FOOD = """## food
Look at what the planned meals are built around.
- 1: only familiar food (international, pizza, burgers, cafés, "something simple").
- 2: mostly familiar, with one easy local treat (a matcha dessert, a bowl of ramen).
- 3: a mix of familiar food and approachable Japanese classics (ramen, tonkatsu, conveyor-belt sushi, tempura).
- 4: mostly traditional Japanese food (izakaya dishes, yakitori, standing sushi bars, a depachika or market lunch).
- 5: built around adventurous local food most visitors haven't tried (natto, offal yakitori, horse sashimi, shirako, fugu, a yokocho crawl).
"""
CITY = {"lisbon": ("lisbon4", ASK), "tokyo": ("tokyo4", "Can you plan a weekend in Tokyo for me?")}
PREFIX = "lisbon4"


def rubric_for(prefix):
    if prefix == "lisbon4":
        return RUBRIC
    head, rest = RUBRIC.split("## budget", 1)
    night = "## night" + rest.split("## night", 1)[1].split("## food", 1)[0]
    night = night.replace("(for example a fado dinner)", "(for example one jazz bar after dinner)")
    return head.replace("lisbon4", prefix) + TOKYO_BUDGET + "\n" + night + TOKYO_FOOD


def write(arm, turns, prefs_stated, corrected, desc):
    d = os.path.join(SCEN, f"{PREFIX}-{arm}")
    os.makedirs(d, exist_ok=True)
    prefs = []
    for p in PREFS:
        q, vals = VALUES[p]
        if p == corrected or (corrected == "pace-up" and p == "pace"):
            v = vals["high"] if corrected == "pace-up" else vals["low"]
        elif p in prefs_stated:
            v = vals["high"]
        else:
            v = "Not stated by the user."
        prefs.append({"id": p, "question": q, "user_value": v})
    scen = {"id": f"{PREFIX}-{arm}", "version": "0.1", "license": "CC BY 4.0", "arm": arm, "corrected": corrected,
            "stated_at_turn0": sorted(prefs_stated), "preferences": prefs, "description": desc,
            "turns": [{"user": t, **({"corrects": "pace" if corrected == "pace-up" else corrected} if i == 1 and corrected else {})}
                      for i, t in enumerate(turns)]}
    json.dump(scen, open(os.path.join(d, "scenario.json"), "w"), indent=2, ensure_ascii=False)
    open(os.path.join(d, "rubric.md"), "w").write(rubric_for(PREFIX))


def main():
    global PREFIX, ASK
    ap = argparse.ArgumentParser()
    ap.add_argument("--city", default="lisbon", choices=list(CITY))
    PREFIX, ASK = CITY[ap.parse_args().city]
    write("u-control", [ASK, NEUTRAL] + LATER, [], None, "Q4 control, unstated user: turn 1 asks for a neutral redo.")
    for a in ["pace", "budget", "night", "food", "pace-up"]:
        write(f"u-{a}", [ASK, CORRECT[a]] + LATER, [], a, f"Q4, unstated user: turn 1 corrects {a}.")
    for a in PREFS:
        others = [p for p in PREFS if p != a]
        first = ASK + " " + " ".join(HIGH[p] for p in others)
        write(f"m{a}-control", [first, NEUTRAL] + LATER, others, None,
              f"Q4 control, mixed-values user who states {', '.join(others)} (high side) at turn 0.")
        write(f"m{a}", [first, CORRECT[a]] + LATER, others, a,
              f"Q4, mixed-values user who states {', '.join(others)} (high side) at turn 0; turn 1 corrects {a} (low side).")
    print("wrote", len([d for d in os.listdir(SCEN) if d.startswith(PREFIX + "-")]), "arms")


if __name__ == "__main__":
    main()
