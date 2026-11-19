# Contributing

## Pick an issue

Look at the board's Ready column or issues labeled `good first issue`. Comment on the issue to say you're taking it.

## Branches and pull requests

- Branch from `main` as `<issue-number>-<short-name>`, for example `3-workplace-scenario`.
- One issue per pull request. Write `Closes #<number>` in the description.
- Keep pull requests small. Hongbee reviews and merges.
- Run the mock pipeline from the README before you open a pull request.

## New scenario checklist

- [ ] Copy `correction-cost/scenarios/_template/` to `correction-cost/scenarios/<your-scenario>/`.
- [ ] Every preference has an `id`, a `question` and a `user_value`.
- [ ] The first user turn leaves the preferences unsaid. Correction turns carry `corrects`.
- [ ] `rubric.md` has one `## <preference-id>` section per preference, with anchors for 1, 3 and 5.
- [ ] Synthetic text only. No real user conversations, even anonymized.
- [ ] It runs end to end with `mock:mock` and with one real model.
- [ ] The scenario is shared under CC BY 4.0.

## API keys

Everyone runs models with their own keys. Put them in `.env`, which git ignores. Never commit keys or anything in `results/`.
