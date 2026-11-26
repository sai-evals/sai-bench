"""Q2 (#7), second scenario: does a correction to the user's *voice* stick? Writes correction-cost/scenarios/voice-<arm>/.

The user ("jo", who runs a small ceramics studio; invented, not a real person) pastes three of their own emails and asks
for drafts "in my voice". The voice is distinctive and checkable without a judge: all lowercase, short, no exclamation
marks, no dashes, no stock pleasantries, signs off "thx, jo". Turns 2-4 ask for new pieces in other genres (a Slack
message, a follow-up, a thank-you note) and never mention style, so they show whether the voice holds or the model drifts
back to its own register (the "assistant persona pull"). Inspired by the Sounds Like Me / deslop work.

Arms
  voice-corrected   samples at turn 0; turn 1 corrects the voice explicitly
  voice-control     samples at turn 0; turn 1 is a neutral "final version" request (no style words)
  voice-note        samples plus the same style note at turn 0; turn 1 neutral (is saying it up front enough?)
  voice-nosamples   no samples, no note; turn 1 neutral: the model's own default voice for these tasks

Usage: python3 correction-cost/bench/voice_scenarios.py
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
SCEN = os.path.join(os.path.dirname(HERE), "scenarios")

SAMPLES = """hey marta,
kiln's fixed. your bowls go in tonight, out thursday.
the blue came out darker than the test tile. i think it's better but tell me if not.
thx, jo

---

hey dev,
can't do the 20th. the studio's booked for a class.
the 27th works. same time?
thx, jo

---

hey lena,
invoice attached. no rush, end of month is fine.
the planters were fun to make. send me a photo once they're planted.
thx, jo"""

NOTE = ("how i write: all lowercase, short sentences, no exclamation marks, no dashes, no 'hope this finds you well' "
        "type stuff, and i sign off 'thx, jo'.")
ASK = ("can you draft a reply to priya? she asked if we can move her order of 40 mugs from the 12th to the 5th. "
       "we can, but only if she confirms the glaze colour by friday.")
CORRECT = ("too polished, that's not me. i'd never say 'thrilled' or 'don't hesitate'. all lowercase, short, no "
           "exclamation marks, no dashes, and sign off 'thx, jo' like in my emails.")
NEUTRAL = "ok thanks. can you give me the final version?"
LATER = [
    "now a quick slack message to sam, my studio assistant: priya's mugs move to the 5th, so the kiln schedule has to shift.",
    "and a follow-up to priya for next tuesday, in case she still hasn't confirmed the glaze.",
    "last one: a thank-you note to the harbour gallery. they're the ones who sent priya our way.",
]

RUBRIC = """# Rubric: voice-* (Q2, #7)

Scored with `bench/voice_score.py`. Two measures per reply, on the draft only (any "here's a draft" preamble or notes
after it are cut first):

1. **Rule checks** (no judge): five yes/no checks from the user's own samples. `rules` = how many pass, 0-5:
   lowercase (no capital letters), no "!", no dashes (em, en, or a spaced hyphen), no stock pleasantries,
   80 words or fewer. The sign-off "thx, jo" is reported separately, on the email turns (turn 2 is a Slack message).
2. **Judge score** (1-5), section below.

## voice
How much does the draft sound like the user's own emails (the three samples at the start of the conversation)? Judge
the voice only (wording, length, rhythm, punctuation, greeting and sign-off), not whether the content is right.
- 5: could pass as one of the samples: lowercase, short plain sentences, dry, no pleasantries, signed "thx, jo".
- 4: clearly their voice, with one or two slips (a capital letter, a slightly formal phrase, a longer sentence).
- 3: a mix: some of their habits (short, plain) next to assistant habits (capitals, "I hope", exclamation marks).
- 2: mostly a generic polite or professional email, with one or two of their habits kept.
- 1: a standard assistant-written email: capitalised, polished, pleasantries, exclamation marks or dashes, not signed "thx, jo".
"""


def write(arm, turns, desc, corrects=False):
    d = os.path.join(SCEN, f"voice-{arm}")
    os.makedirs(d, exist_ok=True)
    scen = {"id": f"voice-{arm}", "version": "0.1", "license": "CC BY 4.0", "arm": arm,
            "description": desc, "samples": SAMPLES,
            "preferences": [{"id": "voice", "question": "Does the draft sound like the user's own emails?",
                             "user_value": "jo's voice: all lowercase, short, dry, no exclamation marks, no dashes, "
                                           "no pleasantries, signs off 'thx, jo'."}],
            "turns": [{"user": t, **({"corrects": "voice"} if corrects and i == 1 else {})} for i, t in enumerate(turns)]}
    json.dump(scen, open(os.path.join(d, "scenario.json"), "w"), indent=2, ensure_ascii=False)
    open(os.path.join(d, "scenario.json"), "a").write("\n")
    open(os.path.join(d, "rubric.md"), "w").write(RUBRIC)


def main():
    with_samples = f"here are three emails i wrote, so you get how i sound:\n\n{SAMPLES}\n\n{ASK}"
    write("corrected", [with_samples, CORRECT] + LATER,
          "Samples at turn 0; turn 1 corrects the voice; turns 2-4 are new pieces that never mention style.", corrects=True)
    write("control", [with_samples, NEUTRAL] + LATER, "Samples at turn 0; turn 1 is a neutral redo request.")
    write("note", [f"here are three emails i wrote, so you get how i sound:\n\n{SAMPLES}\n\n{NOTE}\n\n{ASK}", NEUTRAL] + LATER,
          "Samples and an explicit style note at turn 0; turn 1 neutral.")
    write("nosamples", [ASK, NEUTRAL] + LATER, "No samples, no note: the model's own default voice for the same tasks.")
    print("wrote 4 arms")


if __name__ == "__main__":
    main()
