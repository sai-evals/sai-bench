# sai-bench

An open bench that measures how much effort it takes a user to correct a model. Hongbee Park and Albert Lie are building it together, and anyone can join.

## What it measures

When a user leaves a preference unsaid, the model fills the gap with its own default. This bench records what the model filled, whether it said so, and how much the user has to say before the model follows them and stays there.

## Results so far

In early runs we have seen models fill unstated preferences with their own defaults, rarely say so, and sometimes drift back after a correction. Open results will land here as scenarios are added.

## Layout

Each topic is a folder. The first one is `correction-cost/`.

```
correction-cost/
  bench/
    providers.py     model API calls (anthropic, openai, google, deepseek, mock)
    runner.py        plays a scenario's user turns against a target model
    judge.py         scores every reply on every preference, one judge call each
  scenarios/
    _template/       empty scenario.json and rubric.md to copy
    trip-planning/   a toy example with two preferences
```

## Quick start

Python 3.9 or later, no extra packages. Mock runs need no API key.

```
python3 correction-cost/bench/runner.py --scenario trip-planning --target mock:mock
python3 correction-cost/bench/judge.py --scenario trip-planning --target mock:mock --judge mock:mock
```

For real models, copy `.env.example` to `.env`, add your own keys, and pass `provider:model`, for example `--target anthropic:<model-id>`. Results go to `results/`, which git ignores.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) and the open issues. Hongbee Park is the sole maintainer for now.

## License

Code is MIT (see [LICENSE](LICENSE)). Scenarios and rubrics under `scenarios/` are CC BY 4.0.
