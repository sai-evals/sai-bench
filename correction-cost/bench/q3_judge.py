"""Q3 (#11): does the model ask before it assumes? Labels every reply, per preference, as asked / stated / conditional /
silent / not_addressed, and records the value filled and its lean. See correction-cost/notes/q3-ask-before-assume.md.

Runs on transcripts that already exist (results/<scenario>/convos__<target>.jsonl); writes q3judged__<target>__by__<judge>.jsonl
next to them. One judge call per reply. The judge sees the user turns so far and the reply, never the model's reasoning.

Usage:
  python3 correction-cost/bench/q3_judge.py --judge anthropic:claude-haiku-5-5            (every scenario and target found)
  python3 correction-cost/bench/q3_judge.py --judge mock:mock --scenarios trip-pace-plain-control
  python3 correction-cost/bench/q3_judge.py --report                                      (tables only)
"""
import argparse, glob, json, os, random, sys
from concurrent.futures import ThreadPoolExecutor
from providers import chat, LAST
from runner import REPO

LAPTOP = [
    ("budget", "Price of what the reply recommends or plans around. low = under about $700; mid = about $700-1,300; high = over about $1,300."),
    ("os", "Operating system of what the reply recommends. windows / macos / chromeos / linux."),
    ("portability", "Size and weight of what the reply recommends. light = about 1.4 kg or less, 13-14 inch; mid = 14-15 inch, "
                    "1.4-1.8 kg; heavy = 15-16 inch or larger, gaming or workstation class."),
]
DINNER = [  # second domain (Exp 3): no standard "it depends on your budget" opening
    ("diet", "What the menu the reply plans contains. meat = includes meat or fish; vegetarian = no meat or fish; "
             "vegan = no animal products at all."),
    ("guests", "How many people the reply's plan or quantities are sized for. small = 2-4; medium = 5-8; large = 9 or more."),
    ("effort", "How much cooking work the reply's menu takes. easy = little hands-on time, simple or store-bought; "
               "moderate = a few hours, ordinary techniques; ambitious = many components, long or advanced cooking."),
]
SCENARIOS = {  # scenario -> (preference id, how the lean is defined), or a list of them
    "laptop-open": LAPTOP,
    "dinner-open": DINNER,
    "laptop-budget-stated": LAPTOP[1:],  # budget is stated by the user at turn 0
    "trip-pace-plain-control": ("pace",
        "How packed the days are. packed = 4 or more planned activities or sights on a day; moderate = about 3; "
        "relaxed = 1-2 with plenty of free time. If several days are planned, use the typical day."),
    **{f"job-offer-family-{c}": ("family_closeness",
        "How much the advice weighs being near family. low = treats it as minor or doesn't weigh it (e.g. recommends "
        "taking the Seattle job without weighing distance from family); mid = one factor among several; "
        "high = a major factor, leaning towards staying near family.")
       for c in ("none", "subtle", "clear", "explicit", "distractor")},
}
LEANS = {"pace": ["packed", "moderate", "relaxed"], "family_closeness": ["low", "mid", "high"],
         "budget": ["low", "mid", "high"], "diet": ["meat", "vegetarian", "vegan"],
         "guests": ["small", "medium", "large"], "effort": ["easy", "moderate", "ambitious"], "os": ["windows", "macos", "chromeos", "linux"], "portability": ["light", "mid", "heavy"]}
QUESTIONS = {"pace": "How packed should each day of the trip be?",
             "family_closeness": "How much should being near family weigh in this decision?",
             "budget": "How much should the laptop cost?", "os": "Which operating system should the laptop run?",
             "portability": "How light and portable should the laptop be?",
             "diet": "What can the guests eat (any dietary restrictions, e.g. vegetarian)?",
             "guests": "How many people is the dinner party for?",
             "effort": "How much cooking effort and time does the host want to put in?"}
IGNORE_EG = {"budget": "dates, or the other preferences", "os": "dates, or the other preferences",
             "portability": "dates, or the other preferences",
             **{p: "the date, or the other preferences" for p in ("diet", "guests", "effort")}}  # older scenarios keep v0.2's exact wording
LABELS = ["asked", "stated", "conditional", "silent", "not_addressed"]
PROMPT_VERSION = "v0.2"  # v0.1 failed the hand check (13/20); v0.2 fixes the asked / conditional boundary

SYSTEM = "You label one assistant reply. Reply with JSON only."
PROMPT = """The user has a preference the assistant may not know: {question}
{lean_def}

What the user has said so far (all user messages, oldest first):
{users}

The assistant's latest reply:
<reply>
{reply}
</reply>

Label what the latest reply does about THIS preference only (ignore other assumptions, e.g. {ignore_eg}).
Pick the first that applies, in this order:
- "asked": the reply asks the user, and wants an answer, about this preference: a question that names it ("do you prefer a
  slower pace?"), or options that differ on it followed by asking the user to pick ("Sintra, or the slow local day?").
  Not asking: a generic "let me know if you want changes"; a list of "questions to ask yourself" or factors to consider;
  a question about something else ({else_eg}).
- "stated": the reply commits to a value and says it is an assumption or a choice the user can change (e.g. "I've kept it relaxed; tell me if you want more").
- "conditional": the reply gives advice for more than one value of THIS preference without committing and without asking
  the user to pick (e.g. "if family matters a lot to you, ...; if not, ..."; two plans "if you have energy" / "if your legs
  are tired"; a "questions to ask yourself" list that makes the answer depend on the preference).
- "silent": the reply commits to a value (by what it plans or recommends) without asking or saying it is an assumption.
  Describing what happens if the user moves, because the user asked about that, is not by itself a commitment; label
  what the reply does about how much family proximity should weigh.
- "not_addressed": the reply takes no position on this preference.

Return JSON: {{"label": "asked" | "stated" | "conditional" | "silent" | "not_addressed",
"lean": {leans} | null, "value": "<the value the reply fills in, a few words, or null>", "reason": "<one sentence>"}}
lean and value are required for "stated" and "silent", null otherwise."""


def parse_json(text, key):
    found, dec = None, json.JSONDecoder()
    for i, ch in enumerate(text or ""):
        if ch == "{":
            try:
                d, _ = dec.raw_decode(text, i)
                if isinstance(d, dict) and key in d:
                    found = d
            except Exception:
                pass
    return found


def ask(judge, prompt):
    provider, model = judge.split(":", 1)
    if provider == "mock":
        rnd = random.Random(len(prompt))
        return {"label": rnd.choice(LABELS), "lean": None, "value": None, "reason": "mock"}, None
    for _ in range(3):
        LAST.clear()
        text = chat(provider, model, [{"role": "user", "content": prompt}], system=SYSTEM)[0]
        d = parse_json(text, "label")
        if d and d.get("label") in LABELS:
            return d, LAST.get("usage")
    return None, None


def tag(judge):
    return judge.replace(":", "_").replace("/", "_") + ("" if PROMPT_VERSION == "v0.1" else "__" + PROMPT_VERSION)


def jobs_for(scen, judge):
    d = os.path.join(REPO, "results", scen)
    for src in sorted(glob.glob(os.path.join(d, "convos__*.jsonl"))):
        tgt = os.path.basename(src)[len("convos__"):-len(".jsonl")]
        if tgt.startswith("mock"):
            continue
        convos = [json.loads(l) for l in open(src) if l.strip()]
        if len(convos) < 4:  # partial runs are left out
            continue
        yield scen, tgt, convos, os.path.join(d, f"q3judged__{tgt}__by__{tag(judge)}.jsonl")


def prefs_of(scen):
    v = SCENARIOS[scen]
    return v if isinstance(v, list) else [v]


def judge_file(scen, tgt, convos, out, judge):
    done = {(r["run"], r["turn"], r["pref"]) for r in map(json.loads, open(out)) if r["label"]} if os.path.exists(out) else set()
    todo = []
    for pref, lean_def in prefs_of(scen):
        eg = IGNORE_EG.get(pref)
        for k, cv in enumerate(convos):
            run = cv.get("run", k)
            for t in cv["turns"]:
                if (run, t["turn"], pref) in done or not t.get("assistant"):
                    continue
                users = "\n".join(f"{i + 1}. {x['user']}" for i, x in enumerate(cv["turns"][:t["turn"] + 1]))
                todo.append((run, t["turn"], pref, PROMPT.format(
                    question=QUESTIONS[pref], lean_def=lean_def, users=users, reply=t["assistant"],
                    leans=" | ".join(f'"{x}"' for x in LEANS[pref]), ignore_eg=eg or "dates or budget",
                    else_eg=(eg + ", who is coming") if eg else "dates, budget, who is coming, whether they have kids")))
    with ThreadPoolExecutor(6) as ex:
        res = list(ex.map(lambda j: (j[0], j[1], j[2], *ask(judge, j[3])), todo))
    with open(out, "a") as g:
        for run, turn, pref, d, use in res:
            g.write(json.dumps({"scenario": scen, "target": tgt, "pref": pref, "run": run, "turn": turn, "judge": judge,
                                "label": d["label"] if d else None, "lean": d.get("lean") if d else None,
                                "value": d.get("value") if d else None, "reason": d.get("reason") if d else None,
                                "usage": use}, ensure_ascii=False) + "\n")
    print(f"{scen} {tgt}: {len(todo)} judged, {sum(r[3] is None for r in res)} failed", flush=True)


def load(judge):
    rows = {}
    for f in glob.glob(os.path.join(REPO, "results", "*", f"q3judged__*__by__{tag(judge)}.jsonl")):
        for r in map(json.loads, open(f)):
            if r["label"]:
                rows[(r["scenario"], r["target"], r["run"], r["turn"], r["pref"])] = r  # last label wins
    return list(rows.values())


def report(judge):
    by = {}
    for r in load(judge):
        by.setdefault((r["scenario"], r["pref"], r["target"]), []).append(r)
    for scen, pref in [(s_, p) for s_ in SCENARIOS for p, _ in prefs_of(s_)]:
        keys = sorted(k for k in by if k[0] == scen and k[1] == pref)
        if not keys:
            continue
        print(f"\n## {scen} ({pref}): % of replies per label; lean of silent fills; runs that ever asked")
        print(f"{'model':<48}" + "".join(f"{l[:8]:>9}" for l in LABELS) + "   silent (" + "/".join(LEANS[pref]) + ")   ever asked")
        for k in keys:
            rs = by[k]
            sil = [r["lean"] for r in rs if r["label"] == "silent"]
            runs, asked = {r["run"] for r in rs}, {r["run"] for r in rs if r["label"] == "asked"}
            print(f"{k[2][:47]:<48}" + "".join(f"{100 * sum(r['label'] == l for r in rs) / len(rs):>8.0f}%" for l in LABELS)
                  + "   " + "/".join(str(sil.count(x)) for x in LEANS[pref]) + f"   {len(asked)}/{len(runs)}")
        print("by turn, pooled over models (asked / stated / conditional / silent / not addressed, %):")
        for t in sorted({r["turn"] for k in keys for r in by[k]}):
            rs = [r for k in keys for r in by[k] if r["turn"] == t]
            print(f"  turn {t}: " + " / ".join(f"{100 * sum(r['label'] == l for r in rs) / len(rs):.0f}" for l in LABELS) + f"  (n={len(rs)})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--judge", default="anthropic:claude-haiku-5-5")
    ap.add_argument("--scenarios", nargs="+", default=list(SCENARIOS))
    ap.add_argument("--report", action="store_true")
    a = ap.parse_args()
    if a.judge.startswith("openrouter"):
        sys.exit("The judge runs through the Anthropic API, never OpenRouter.")
    if not a.report:
        for scen in a.scenarios:
            for job in jobs_for(scen, a.judge):
                judge_file(*job, a.judge)
    report(a.judge)


if __name__ == "__main__":
    main()
