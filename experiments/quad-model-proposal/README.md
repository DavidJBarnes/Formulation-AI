# Quad Model proposal prototype

Audition artifact for Jun Liu's skepticism on using an LLM-only proposal
generator as Phase 1 of Formulation-AI's DOE core. Operates on the synthetic
"Quad Model" Excel Jun shared on 2026-04-24.

## Run

```bash
ANTHROPIC_API_KEY=... python propose.py
# or with a custom target
ANTHROPIC_API_KEY=... python propose.py \
    --target "Minimize Output 1 magnitude; keep Output 3 near 20" \
    --n 8
```

Writes `proposals.xlsx` next to the script.

## What it does

1. Reads the 9 observations from `Quad Model.xlsx`.
2. Prompts Claude Opus 4.7 with the data, a target, and a structured-output schema.
3. Emits K novel candidate input vectors with predicted `(value, σ)` per output
   — same shape as Jun's "Sheet1 predictions", but new candidates rather than
   re-predictions of the observed rows.

## Why this, not a feature in the product

Self-contained audition. No backend coupling. Sendable to Jun verbatim as a
concrete answer to *"find an LLM engine that can propose something decent."*
