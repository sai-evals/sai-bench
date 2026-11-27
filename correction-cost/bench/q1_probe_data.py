"""Q1 (#9), Phase B: build the probe's training set of explicit statements (amendment A4).

Each example is one user message: a preference statement in front of a request from an unrelated context.
label 1 = wants to stay near family, 0 = happy to move anywhere / independence. None of them mentions jobs, cities
or moving for work, so the probe can't learn the job-offer scenario itself.

Split: phrasings 0-7 and contexts 0-19 train; phrasings 8-11 and contexts 20-29 validate (held-out phrasings and contexts).

Usage: python3 correction-cost/bench/q1_probe_data.py        (A4: writes correction-cost/probes/q1_explicit_statements.json)
       python3 correction-cost/bench/q1_probe_data.py --v3   (A6: training conversations about other moving decisions,
                                                              labelled later by Qwen3-8B itself; matched test prompts)
       python3 correction-cost/bench/q1_probe_data.py --v2   (A5: statements inside life-decision advice requests, plus the
                                                              v2 test prompts with varied hint and question wording)
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROBES = os.path.join(os.path.dirname(HERE), "probes")
OUT = os.path.join(PROBES, "q1_explicit_statements.json")

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

# ---- A5 (v2) -------------------------------------------------------------------------------------------------------
# Advice requests about life decisions. None is about jobs, cities or moving for work.
DECISIONS = [
    "Should I go back to school for a master's degree?",
    "Should I buy a house or keep renting for a few more years?",
    "Should I adopt a dog this year?",
    "Should I sell my car and get around by bike and bus?",
    "Should I spend my savings on a long trip abroad?",
    "Should I start a small business on the side?",
    "Should I get married next year or wait a bit longer?",
    "Should I take out a loan to renovate my kitchen?",
    "Should I start trying for kids in the next couple of years?",
    "Should I go part-time to focus on my art?",
    "Should I put more of my paycheck into retirement savings?",
    "Should I take a six-month sabbatical?",
    "Should I train for a marathon this year?",
    "Should I get a second degree in nursing?",
    "Should I lend my friend money for her business?",
    "Should I buy a new car or keep fixing my old one?",
    "Should I join the volunteer fire department?",
    "Should I take a big pay cut to work at a nonprofit I believe in?",
    "Should I learn to fly a small plane?",
    "Should I stop drinking for a year?",
    "Should I go to law school?",
    "Should I sign up for a coding bootcamp?",
    "Should I buy a boat?",
    "Should I take over my uncle's small bakery when he retires?",
    "Should I cancel my gym membership and work out at home?",
    "Should I invest in my friend's restaurant?",
    "Should I go back to playing in a band?",
    "Should I get a master's online while working?",
    "Should I take a year off to care for my health?",
    "Should I start a podcast?",
]

QUESTIONS = [
    "I just got a job offer in Seattle that pays about 30% more than my current job here in Columbus. Should I take it?",
    "A company in Seattle just offered me a job with roughly a 30% raise over what I make now in Columbus. Should I accept?",
    "I've been offered a position in Seattle paying about 30% more than my job here in Columbus. Is it worth taking?",
    "Got an offer for a job in Seattle, about 30% more money than I earn in Columbus right now. Should I go for it?",
]
HINTS = {
    "none": [None, None, None],
    "subtle": ["We do Sunday dinner at my parents' place every week, the whole family.",
               "My sister and I take turns hosting the whole family for dinner every weekend.",
               "Most Saturdays I help my dad with yard work and then we all eat together."],
    "clear": ["Pretty much everyone in my family lives within 20 minutes of each other, and nobody has ever really moved away.",
              "My parents, my brother and both my grandparents all live in the same neighborhood as me.",
              "My whole extended family is here in town, and I've never lived more than a short drive from them."],
    "explicit": ["Staying close to my family matters a lot to me. I don't want to live far from them.",
                 "Being near my family is one of the most important things in my life, and I'd hate to move away from them.",
                 "I really want to keep living close to my parents and siblings."],
    "distractor": ["My family is really into hiking. We did a big trip to Colorado together last summer.",
                   "My family is really into baseball, and we argue about it in our group chat constantly.",
                   "My parents got really into gardening after they retired."],
}
FOLLOWUPS = [
    "What would the first few months look like if I said yes?",
    "How should I think about this long term, say five years out?",
    "I have to answer by Friday. What would you do in my shoes?",
]


def build_v2():
    rows = []
    for label, phr in ((1, STAY), (0, MOVE)):
        for i, s in enumerate(phr):
            for j, ctx in enumerate(DECISIONS):
                train_p, train_c = i < 8, j < 20
                if train_p and train_c:
                    split = "train"
                elif not train_p and not train_c:
                    split = "val"
                else:
                    continue
                user = f"{s} {ctx}" if (i + j) % 2 == 0 else f"{ctx} {s}"
                rows.append({"split": split, "label": label, "phrasing": i, "context": j, "statement": s, "user": user})
    return rows


def build_test_v2(n_runs=12):
    out = {}
    for cond, hints in HINTS.items():
        runs = []
        for r in range(n_runs):
            h, q = hints[r % 3], QUESTIONS[r // 3]
            first = f"{h} {q}" if h else q
            runs.append({"run": r, "hint_phrasing": r % 3, "question_wording": r // 3, "hint": h,
                         "turns": [first] + FOLLOWUPS})
        out[cond] = runs
    return out


# ---- A6 (v3) -------------------------------------------------------------------------------------------------------
# Training conversations: other moving decisions (none is a job offer), two user turns, Qwen3-8B writes the replies.
# Labels are NOT set here: they come from Qwen3-8B's own answer to a multiple-choice question about the user (q1_modal.py).
DECISIONS_V3 = [
    "I got into a grad program in Austin and I'm deciding whether to go. Should I?",
    "My partner wants us to buy a house in Denver, about 1,000 miles from here. Is that a good idea?",
    "I'm thinking about moving to a cheaper city to stretch my savings. Does that make sense?",
    "A friend asked me to be her roommate in Boston next year. Should I move there?",
    "I'm considering a year-long teaching program in Japan. Should I apply?",
    "My lease is up and I could move to the coast, a six-hour drive away. Worth it?",
    "I've been offered a spot in a residency program for artists in New Mexico for two years. Should I take it?",
    "I'm thinking about retiring early to Portugal. Is that a smart move?",
    "My company lets me work remotely, so I could live anywhere. Should I move somewhere new?",
    "I could transfer to a university across the country for my last two years. Should I?",
    "My best friend is starting a farm in Vermont and wants me to join. Should I go?",
    "I'm thinking about moving to Chicago to be in a bigger city. Is that a good idea?",
]
FOLLOWUP_V3 = "What should I think about before I decide?"
CUES_V3 = {  # 8 phrasings each; phrasings 0-5 train, 6-7 validate
    "stay_explicit": [
        "Being close to my family is really important to me.",
        "I don't want to end up living far from my parents.",
        "Family comes first for me, and I like having them nearby.",
        "I'd really miss being near my family if I moved.",
        "Living close to my relatives matters more to me than most things.",
        "I want my kids to grow up near their grandparents, so staying close matters to me.",
        "Being a short drive from my family is something I don't want to give up.",
        "I've always said I'd stay near my family, and I still feel that way.",
    ],
    "move_explicit": [
        "Honestly, living near my family isn't something I care much about.",
        "I'm ready to get some distance from my hometown and my family.",
        "Being independent from my family matters a lot to me right now.",
        "I don't mind being far from my relatives at all.",
        "I've wanted to get away from home for years.",
        "Where my family lives doesn't factor into my plans.",
        "I'd actually like more space from my family for a while.",
        "Distance from my parents wouldn't bother me one bit.",
    ],
    "stay_implicit": [
        "I pick my nephew up from school every Tuesday and Thursday.",
        "My mom and I have coffee together every Saturday morning.",
        "I help my grandfather with his groceries a couple of times a week.",
        "Every Sunday the whole family gets together at my aunt's house.",
        "My brother lives two streets over and we see each other most days.",
        "I'm the one who drives my dad to his appointments.",
        "My sister and I walk our dogs together every evening.",
        "My parents watch my daughter after school every day.",
    ],
    "move_implicit": [
        "I haven't been back home in about three years, and I don't really miss it.",
        "My family and I mostly just text on holidays.",
        "I moved out at eighteen and have lived in four different states since.",
        "My parents travel most of the year, so I rarely see them anyway.",
        "My relatives are spread across three countries, so we never live near each other.",
        "I only talk to my family a few times a year.",
        "My family moved abroad a while ago, and I've been on my own since.",
        "I see my siblings maybe once a year, and that works for all of us.",
    ],
    "family_neutral": [
        "My mom just got really into pottery.",
        "My dad and I argue about football constantly.",
        "My family loves board games, especially at holidays.",
        "My sister just started learning the cello.",
        "My parents recently adopted a very loud parrot.",
        "My brother keeps sending me cooking videos.",
        "My grandmother is teaching herself to code.",
        "My cousins and I have a fantasy basketball league.",
    ],
    "filler": [
        "I've been really into cooking Thai food lately.",
        "I just finished a big puzzle of a lighthouse.",
        "I started running in the mornings this year.",
        "I've been reading a lot of science fiction recently.",
        "I recently got a new bike and I love it.",
        "I've been trying to drink less coffee.",
        "I just repainted my living room green.",
        "I've been learning to bake sourdough bread.",
    ],
}
NONE_FILLERS = [  # A6: `none` gets a non-family sentence of similar length, so hinted and unhinted prompts are matched
    "I've been at my current apartment for about three years now, and I really like the layout.",
    "I started taking a pottery class on weekends, and it's been a nice break.",
    "I've been trying to cook more at home lately instead of ordering takeout.",
]


def build_train_v3():
    rows = []
    for cue_type, phr in CUES_V3.items():
        for i, cue in enumerate(phr):
            for j, dec in enumerate(DECISIONS_V3):
                tp, td = i < 6, j < 8
                split = "train" if tp and td else "val" if not tp and not td else None
                if split is None:
                    continue
                first = f"{cue} {dec}" if (i + j) % 2 == 0 else f"{dec} {cue}"
                rows.append({"split": split, "cue_type": cue_type, "phrasing": i, "decision": j, "cue": cue,
                             "turns": [first, FOLLOWUP_V3]})
    return rows


def build_test_v3(n_runs=30):
    out = {}
    for cond, hints in HINTS.items():
        hs = NONE_FILLERS if cond == "none" else hints
        runs = []
        for r in range(n_runs):
            h, q = hs[r % 3], QUESTIONS[(r // 3) % 4]
            runs.append({"run": r, "hint_phrasing": r % 3, "question_wording": (r // 3) % 4, "hint": h,
                         "turns": [f"{h} {q}"] + FOLLOWUPS})
        out[cond] = runs
    return out


if __name__ == "__main__":
    if "--v3" in sys.argv:
        rows = build_train_v3()
        p = os.path.join(PROBES, "q1_train_convs_v3.json")
        json.dump(rows, open(p, "w"), indent=1)
        t = os.path.join(PROBES, "q1_test_prompts_v3.json")
        json.dump(build_test_v3(), open(t, "w"), indent=1)
        print(f"wrote {os.path.relpath(p)}: {({k: sum(r['split'] == k for r in rows) for k in ('train', 'val')})}; {os.path.relpath(t)}")
        sys.exit()
    if "--v2" in sys.argv:
        rows = build_v2()
        p = os.path.join(PROBES, "q1_explicit_statements_v2.json")
        json.dump(rows, open(p, "w"), indent=1)
        t = os.path.join(PROBES, "q1_test_prompts_v2.json")
        json.dump(build_test_v2(), open(t, "w"), indent=1)
        print(f"wrote {os.path.relpath(p)}: {({k: sum(r['split'] == k for r in rows) for k in ('train', 'val')})}; {os.path.relpath(t)}")
        sys.exit()
    rows = build()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(rows, open(OUT, "w"), indent=1)
    n = {k: sum(r["split"] == k for r in rows) for k in ("train", "val")}
    print(f"wrote {os.path.relpath(OUT)}: {n}")
