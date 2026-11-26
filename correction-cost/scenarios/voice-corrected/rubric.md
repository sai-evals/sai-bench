# Rubric: voice-* (Q2, #7)

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
