# Cold-Wash Detergent — Fake Lab Results Script

Use this to run a realistic end-to-end demo with `detergent-sample.xlsx`.

## Project setup reminder

**Targets to beat:**
| Property | Goal | Baseline |
|---|---|---|
| Cleaning Index | +10% vs Base Formula 1 | 72% → need **>79.2%** |
| Foam Height | [100, 180] mm | aesthetic range |
| Rinse Efficiency | >=90% | — |
| pH | [9.0, 10.5] | — |

**Optimizer note:** The first iteration uses the LLM only. After you log 3+ tested formulations, the Gaussian Process activates. Rinse Efficiency and Foam Height have conflicting drivers (more surfactant helps clean but increases foam and hurts rinse) — this is a good multi-objective test case for the GP.

---

## Iteration 1 — LLM proposes, you "measure"

Click **Run first iteration**. Enter these measured values when you click **Log results**:

| | Cleaning Index (%) | Foam Height (mm) | Rinse Efficiency (%) | pH |
|---|---|---|---|---|
| **Candidate 1** | 77 | 152 | 89 | 9.8 |
| **Candidate 2** | 74 | 132 | 93 | 9.6 |
| **Candidate 3** | 79 | 158 | 87 | 10.0 |

**What this represents:**
- Candidate 1: Cleaning is close but below target; rinse just misses at 89%
- Candidate 2: Good rinse and foam, but cleaning falls short
- Candidate 3: Cleaning index hits target (79 > 79.2 is borderline — enter 79.5 if you want it to clearly pass), but rinse efficiency is too low

The LLM tends to anchor near Base Formula 1/2 compositions, not quite finding the sweet spot where all four properties land simultaneously.

---

## Iteration 2 — GP activates

Click **Run next iteration** — **Bayesian GP** badge should appear. Enter these measured values:

| | Cleaning Index (%) | Foam Height (mm) | Rinse Efficiency (%) | pH |
|---|---|---|---|---|
| **Candidate 1** | 81 | 142 | 91 | 9.7 |
| **Candidate 2** | 82 | 149 | 90 | 9.8 |
| **Candidate 3** | 80 | 138 | 92 | 9.6 |

**What this represents:** The GP has learned the enzyme concentration and the LAS/AE ratio trade-off. All three candidates now hit every target:
- Cleaning >79.2% ✓
- Foam 100–180 mm ✓  
- Rinse >=90% ✓
- pH 9.0–10.5 ✓

The AI evaluator should declare **success** or flag one more confirmation round.

---

## Iteration 3 — Confirmation (optional)

| | Cleaning Index (%) | Foam Height (mm) | Rinse Efficiency (%) | pH |
|---|---|---|---|---|
| **Candidate 1** | 83 | 140 | 92 | 9.7 |
| **Candidate 2** | 81 | 145 | 91 | 9.8 |
| **Candidate 3** | 84 | 135 | 93 | 9.6 |

Comfortable margin above all targets. Project should transition to **success**.

---

## What to watch for

- **I1 tension:** The LLM usually knows "more enzyme = better cleaning + rinse" but doesn't reliably find the exact balance. I1 results should show candidates trading off cleaning vs rinse.
- **GP improvement:** At I2, sigma on Cleaning Index should drop from ~±5% to ~±2% — the GP has learned from 3 real data points.
- **Foam constraint:** The [100,180] range constraint is harder for the LLM to satisfy simultaneously with the other targets — worth noting in the demo as a case where multi-objective math outperforms intuition.
- **2σ flags:** If Candidate 3's Rinse Efficiency lands at 87 but the LLM predicted 88±4, no flag. If it predicted 92±2 and actual is 87, expect a data-integrity flag — good for demo.
