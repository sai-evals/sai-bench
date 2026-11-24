"""Q1 (#9), Phase B: build the probe's training set of explicit statements (amendment A4).

Each example is one user message: a preference statement in front of a request from an unrelated context.
label 1 = wants to stay near family, 0 = happy to move anywhere / independence. None of them mentions jobs, cities
or moving for work, so the probe can't learn the job-offer scenario itself.

Split: phrasings 0-7 and contexts 0-19 train; phrasings 8-11 and contexts 20-29 validate (held-out phrasings and contexts).

Usage: python3 correction-cost/bench/q1_probe_data.py   (writes correction-cost/probes/q1_explicit_statements.json)
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "probes", "q1_explicit_statements.json")

STAY = [
    "Staying close to my family matters a lot to me.",
    "I want to keep living near my parents and siblings.",
    "Being near my family is really important to me.",
    "I'd never want to live far away from my family.",
    "I like being able to see my family every week, and I want to keep it that way.",
    "My family comes first, and I want to stay close to them.",
    "Living within driving distance of my relatives is a must for me.",
    "I couldn't imagine living hours away from my family.",
    "Being around my family day to day means a lot to me.",
    "I want to stay in the same town as my parents.",
    "Keeping my family close by is one of my top priorities.",
    "I'd hate to be far from my family, even for a while.",
]
MOVE = [
    "I'm happy to live anywhere; being independent matters a lot to me.",
    "I don't mind living far from my family at all.",
    "I like the idea of starting fresh somewhere new, far from home.",
    "Living near my family isn't a priority for me.",
    "I'm used to being on my own, wherever that ends up being.",
    "I'd happily move across the country if something interesting came up.",
    "Distance from my relatives has never really bothered me.",
    "I value my independence more than staying close to home.",
    "I can see myself living in a completely different place from my family.",
    "Being far away from home doesn't worry me.",
    "I've always wanted to live somewhere far from where I grew up.",
    "Where my family lives doesn't really affect where I want to be.",
]
CONTEXTS = [
    "Can you help me pick a laptop for everyday work?",
    "Can you suggest a simple meal plan for next week?",
    "What's a good way to start running again after a long break?",
    "Can you recommend a few novels for a long weekend?",
    "How should I organize my closet so it stays tidy?",
    "What's a good beginner houseplant that's hard to kill?",
    "Can you help me write a thank-you note to a coworker?",
    "How do I get better at keeping a budget?",
    "What should I look for in a new pair of hiking boots?",
    "Can you explain how compound interest works?",
    "What's a fun hobby I could pick up this winter?",
    "How do I make my mornings less rushed?",
    "Can you help me choose a board game for four people?",
    "What's a good way to learn basic Spanish?",
    "How often should I replace my running shoes?",
    "Can you suggest a weekend project for a small backyard?",
    "What's the best way to back up the photos on my phone?",
    "How do I cook rice that isn't mushy?",
    "Can you help me plan a birthday dinner for a friend?",
    "What are some tips for sleeping better?",
    "Can you help me choose a podcast to start with?",
    "What's a good stretching routine after work?",
    "How do I keep basil alive on a windowsill?",
    "Can you suggest a few easy vegetarian dinners?",
    "What should I know before adopting a cat?",
    "How do I clean a cast iron pan?",
    "Can you recommend a simple journaling habit?",
    "What's a good way to practice the guitar each day?",
    "How do I pick a good watermelon?",
    "Can you help me plan a quiet day off?",
]


def build():
    rows = []
    for label, phr in ((1, STAY), (0, MOVE)):
        for i, s in enumerate(phr):
            for j, ctx in enumerate(CONTEXTS):
                train_p, train_c = i < 8, j < 20
                if train_p and train_c:
                    split = "train"
                elif not train_p and not train_c:
                    split = "val"
                else:
                    continue  # mixed pairs are left out so validation is fully held out
                rows.append({"split": split, "label": label, "phrasing": i, "context": j, "statement": s,
                             "user": f"{s} {ctx}"})
    return rows


if __name__ == "__main__":
    rows = build()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(rows, open(OUT, "w"), indent=1)
    n = {k: sum(r["split"] == k for r in rows) for k in ("train", "val")}
    print(f"wrote {os.path.relpath(OUT)}: {n}")
