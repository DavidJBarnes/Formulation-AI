# Epoxy Adhesive — Fake Lab Results Script

Use this to run a realistic end-to-end demo with `epoxy-adhesive-sample.xlsx`.

## Project setup reminder

**Targets to beat:**
| Property | Goal | Baseline |
|---|---|---|
| Peel Strength | +15% vs Epoxy Base A | 6.2 N/mm → need **>7.13** |
| Tensile Strength | >=55 MPa | — |
| Max Service Temp | >=200 °C | — |
| Cure Time | <=35 min | — |

**Optimizer note:** The first iteration uses the LLM only (no training data yet). After you log 3+ tested formulations, the Gaussian Process takes over and the badge in the UI changes to **Bayesian GP**.

---

## Iteration 1 — LLM proposes, you "measure"

Click **Run first iteration**. The LLM will propose 3 candidates. Regardless of the exact ingredient amounts it generates, enter these measured values when you click **Log results**:

| | Peel Strength (N/mm) | Tensile Strength (MPa) | Max Service Temp (°C) | Cure Time (min) |
|---|---|---|---|---|
| **Candidate 1** | 7.0 | 53 | 197 | 36 |
| **Candidate 2** | 6.5 | 57 | 203 | 30 |
| **Candidate 3** | 7.6 | 50 | 194 | 39 |

**What this represents:** The LLM's predictions have ~10–20% error — typical for a cold-start where it reasons only from base product patterns. Candidate 2 hits temperature and cure time but falls short on peel. Candidate 3 has great peel but weak tensile and slow-ish cure. No candidate hits all four targets yet.

The 2σ anomaly flag will likely trigger on Candidate 1 or 3 if the LLM predicted peel around 7.4+ — that's expected and normal at I1.

---

## Iteration 2 — GP activates (3 training points now)

Click **Run next iteration**. You should now see the **Bayesian GP** badge — the optimizer has real data to work with. Enter these measured values:

| | Peel Strength (N/mm) | Tensile Strength (MPa) | Max Service Temp (°C) | Cure Time (min) |
|---|---|---|---|---|
| **Candidate 1** | 7.4 | 58 | 204 | 32 |
| **Candidate 2** | 7.2 | 56 | 205 | 31 |
| **Candidate 3** | 7.6 | 58 | 201 | 33 |

**What this represents:** The GP has learned that high silica filler + higher amine hardener + more cure accelerator simultaneously improves all four properties. All three candidates now hit every target. The AI evaluator should declare **success** or recommend one more iteration to confirm.

Predicted sigma values from the GP should be noticeably tighter than I1 (±2–4 vs ±5–10 range) — that's the surrogate model converging.

---

## Iteration 3 — Confirmation (optional)

If the evaluator iterates instead of declaring success, enter these values to confirm the win:

| | Peel Strength (N/mm) | Tensile Strength (MPa) | Max Service Temp (°C) | Cure Time (min) |
|---|---|---|---|---|
| **Candidate 1** | 7.5 | 59 | 206 | 31 |
| **Candidate 2** | 7.8 | 61 | 208 | 29 |
| **Candidate 3** | 7.3 | 57 | 202 | 33 |

At this point all candidates exceed all targets comfortably. The project should transition to **success**.

---

## What to watch for

- **I1 → I2:** GP badge appears in the proposed formulation cards (violet pill with flask icon)
- **Tighter sigma:** GP uncertainty should shrink from ~±8°C to ~±3°C on Max Service Temp
- **2σ flag:** If any actual value deviates >2σ from predicted, the system flags it — this is expected at I1, less so at I2+
