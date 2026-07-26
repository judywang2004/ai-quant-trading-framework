# Market Knowledge Base

A catalogued library of real chart patterns observed in the markets we
trade. Each entry is one concrete case: a specific symbol, timeframe,
and date, with the chart, what happened, and why it matters.

**Knowledge → Code, not Code → Knowledge.** Every production trading
rule in this framework should be traceable back to one or more
documented market cases here. We don't write a rule and then look for
examples that support it; we observe enough real cases first, and the
rule falls out of what they have in common. If a rule can't be pointed
back to cases in this knowledge base, that's a sign it isn't ready for
production yet.

## Why this exists

Trading rules in this framework (see the root `CLAUDE.md`) are meant to
be objective and testable. But before a rule can be written and
backtested, it has to come from somewhere - usually a pattern a human
noticed on a chart. This directory is where that raw observation gets
written down *before* it becomes code, so that:

- Pattern ideas are captured with evidence (a real chart, a real date)
  instead of vague recollection.
- The same case can be revisited later when deciding whether a rule is
  worth implementing, or when debugging why a strategy did/didn't fire.
- Failed setups are kept alongside winners, not just success stories.

This is a research/documentation artifact, not code. Nothing here is
imported or executed by the framework.

### Failed patterns matter as much as winners

A `failed_breakout` case is not a lesser citizen of this knowledge base.
The goal here is understanding market behavior, not assembling a
highlight reel of winning trades. A setup that failed tells us just as
much about *why* price behaves the way it does as one that worked -
often more, since it's where an intuitive rule usually breaks. Every
case, win or loss, should improve the quality of the pattern
definitions and detectors that eventually get built from this
knowledge base. When in doubt, document the failure.

## Framework Philosophy

The purpose of this knowledge base is not to predict markets. Its
purpose is to describe markets using a consistent, shared vocabulary.

A shared vocabulary is what makes everything downstream possible:
objective discussion between humans, repeatable research, automated
pattern detection, and eventually machine learning. "High base" has to
mean the same specific thing every time it's used, in every case file,
by everyone - that consistency is the actual product of this directory,
independent of any single pattern turning out to be tradeable.

## Research Pipeline

The Market Knowledge Base is the first stage of a longer pipeline that
turns observation into production code:

```
Market Observation
        ↓
Pattern Case              <- you are here (market_knowledge/)
        ↓
Pattern Definition
        ↓
Pattern Detector
        ↓
Backtesting
        ↓
Strategy Rule
        ↓
Production EA
```

A single case is just one data point. A **Pattern Definition** emerges
once enough cases in a category agree on the objective criteria that
define it - that definition is what eventually gets implemented as a
**Pattern Detector** (code), validated in **Backtesting**, and, if it
holds up, promoted into a **Strategy Rule** and shipped in a
**Production EA**. Nothing skips a stage: code is not written until the
knowledge that justifies it exists here.

*(As this pipeline gains more detail - e.g. exactly how multiple cases
converge into a pattern definition - it may be worth splitting into its
own `research/pipeline.md` document rather than growing this README
further.)*

## Structure

```
market_knowledge/
├── README.md            # this file
├── pattern_index.csv     # one row per case, across all categories
├── templates/
│   └── pattern_case.md   # copy this to start a new case
├── high_base/            # tight consolidation before a breakout
├── pullback/             # retracement within an established trend
├── ema_ride/             # trend continuation riding an EMA
├── flag/                 # brief counter-trend consolidation ("flag")
└── failed_breakout/      # breakouts that reversed - failure cases
```

Each category directory holds one Markdown file per case (e.g.
`high_base/HB-001.md`) plus an optional `screenshots/` folder for the
chart images that file references.

## Adding a new case

1. Copy `templates/pattern_case.md` into the right category directory.
2. Name it `<PREFIX>-<NNN>.md`, incrementing from the last case in that
   category (see prefixes below).
3. Save any chart screenshot(s) into that category's `screenshots/`
   folder and reference them from the case file.
4. Fill in every section of the template - especially *why it worked
   or failed*, not just what happened.
5. Add one row to `pattern_index.csv` so the case is searchable without
   opening every file.

## Category prefixes (for file naming and the index)

| Category         | Prefix |
|-------------------|--------|
| high_base          | HB     |
| pullback           | PB     |
| ema_ride           | ER     |
| flag               | FL     |
| failed_breakout    | FB     |

These categories are working hypotheses, not a fixed taxonomy. They
exist to organize today's understanding, and they should evolve as
research accumulates - expect them to be split, merged, renamed, or
added to over time. For example, `high_base` may later prove to be
several distinct patterns (`Tight Base`, `Wide Base`, `Multi-leg Base`)
once enough cases exist to justify the split. When a category splits,
keep the old prefix meaningful in the index rather than renumbering
history.

## Relationship to `research/notes/`

`market_knowledge/` holds *validated* observations: concrete, evidenced
cases that follow the template above. `research/notes/` holds *active
thinking* that hasn't reached that bar yet, including:

- early research ideas and half-formed observations
- trading psychology notes
- hypotheses not yet backed by enough cases
- future experiment ideas
- open questions worth coming back to

Once a note in `research/notes/` is concrete enough to be a well-defined,
evidenced case, it graduates into `market_knowledge/`.
