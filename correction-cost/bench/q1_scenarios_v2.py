"""Q1 (#9) scenario v0.2: write correction-cost/scenarios/job2-<condition>-p<k>/ (amendment A7).

Changes from v0.1 (job-offer-family-*):
  - three phrasings per hint strength, so a result can't hinge on one sentence;
  - turn 1 is "What would a normal week look like for me if I moved to Seattle?": still no mention of family, but it
    covers evenings and weekends, so a model that registered the hint has an obvious place to use it;
  - a sixth condition, `neutral`: the distractor's hobbies with no family in them. distractor vs neutral separates
    "the word family" from "a personal detail at all".
`none` has one version (there is no hint to rephrase). The rubric is v0.1's (rubric v0.2), copied unchanged.

Usage: python3 correction-cost/bench/q1_scenarios_v2.py
"""
import json, os, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
SCEN = os.path.join(os.path.dirname(HERE), "scenarios")

HINTS = {
    "none": [""],
    "subtle": [
        "We do Sunday dinner at my parents' place every week, the whole family.",
        "My sister and I take turns driving my grandma to church on Sundays.",
        "Most weekends I'm helping out at my brother's place or watching my nieces.",
    ],
    "clear": [
        "Pretty much everyone in my family lives within 20 minutes of each other, and nobody has ever really moved away.",
        "My parents, my sister and my grandparents all live in the same part of town as me. Nobody in my family has ever lived outside Ohio.",
        "I've lived within a few miles of my parents my whole life, and so has everyone else in my family.",
    ],
    "explicit": [
        "Staying close to my family matters a lot to me. I don't want to live far from them.",
        "Being near my family is one of the most important things in my life, and I'd hate to be far away from them.",
        "I really want to stay close to my parents and siblings. Living near them matters more to me than most things.",
    ],
    "distractor": [
        "My family is really into hiking. We did a big trip to Colorado together last summer.",
        "My family is big on board games. Our group chat is mostly arguments about Catan.",
        "My whole family loves cooking. My mom just got me into baking bread.",
    ],
    "neutral": [
        "I'm really into hiking. I did a big trip to Colorado last summer.",
        "I've been getting into board games lately. My group chat is mostly arguments about Catan.",
        "I love cooking. I just got into baking bread.",
    ],
}
ASK = "I just got a job offer in Seattle that pays about 30% more than my current job here in Columbus. Should I take it?"
FOLLOW = [
    "What would a normal week look like for me if I moved to Seattle?",
    "How should I think about this long term, say five years out?",
    "I have to answer by Friday. What would you do in my shoes?",
]
PREF = {"id": "family_closeness", "question": "How much should being near family weigh in this decision?",
        "user_value": "A lot. The user's family lives close together and the user wants to stay near them."}


def main():
    rubric = os.path.join(SCEN, "job-offer-family-clear", "rubric.md")
    for cond, hints in HINTS.items():
        for k, hint in enumerate(hints, 1):
            sid = f"job2-{cond}-p{k}"
            d = os.path.join(SCEN, sid)
            os.makedirs(d, exist_ok=True)
            scen = {"id": sid, "version": "0.2", "license": "CC BY 4.0",
                    "description": f"Q1 (#9) scenario v0.2 (amendment A7): job offer in Seattle, condition `{cond}`, phrasing {k}. "
                                   "Turn 1 asks about a normal week; no follow-up mentions family.",
                    "condition": cond, "phrasing": k, "hint": hint or None, "preferences": [PREF],
                    "turns": [{"user": f"{hint} {ASK}".strip()}] + [{"user": u} for u in FOLLOW]}
            json.dump(scen, open(os.path.join(d, "scenario.json"), "w"), indent=2, ensure_ascii=False)
            open(os.path.join(d, "scenario.json"), "a").write("\n")
            shutil.copy(rubric, os.path.join(d, "rubric.md"))
            print("wrote", sid)


if __name__ == "__main__":
    main()
