# Paint (Low-VOC) — Fake Lab Results Script

Use this to run a realistic end-to-end demo with `paint-example.xlsx`.

## Project setup reminder

**Targets to beat:**
| Property | Goal | Baseline |
|---|---|---|
| Viscosity | =105 KU | base average ≈103.5 KU |
| Opacity | +10% vs average base | avg=87.25% → need **>96.0%** |
| Adhesion | >=4.5 MPa | — |
| Durability | +10% vs average base | avg=8.75 yr → need **>9.6 yr** |

The viscosity **exact-match** target (=105) is the trickiest — the optimizer must avoid overshooting in both directions. This makes the paint scenario a good demo of why iterative refinement beats one-shot guessing.

**Optimizer note:** The first iteration uses the LLM only. GP activates after 3+ tested formulations are logged.

---

## Iteration 1 — LLM proposes, you "measure"

Click **Run first iteration**. Enter these measured values when you click **Log results**:

| | Viscosity (KU) | Opacity (%) | Adhesion (MPa) | Durability (years) |
|---|---|---|---|---|
| **Candidate 1** | 106 | 94 | 4.5 | 10.5 |
| **Candidate 2** | 103 | 95 | 4.4 | 9.8 |
| **Candidate 3** | 109 | 92 | 4.8 | 11.2 |

**What this represents:**
- Candidate 1: Viscosity slightly high, opacity just misses the 96% threshold
- Candidate 2: Viscosity low, adhesion misses 4.5 MPa floor
- Candidate 3: Viscosity too high, opacity below target, but adhesion and durability excellent

The LLM correctly identifies that TiO₂ drives opacity and acrylic resin drives adhesion/durability, but struggles to land viscosity at exactly 105 while simultaneously improving opacity above 96%.

---

## Iteration 2 — GP activates

Click **Run next iteration** — **Bayesian GP** badge should appear. Enter these measured values:

| | Viscosity (KU) | Opacity (%) | Adhesion (MPa) | Durability (years) |
|---|---|---|---|---|
| **Candidate 1** | 105 | 97 | 4.6 | 10.8 |
| **Candidate 2** | 106 | 96 | 4.5 | 10.2 |
| **Candidate 3** | 104 | 96 | 4.5 | 10.7 |

**What this represents:** The GP has learned that a specific TiO₂/acrylic/water/thickener ratio simultaneously achieves the viscosity target and exceeds the opacity floor. Candidates 1 and 3 hit all four targets. Candidate 2 is 1 KU high on viscosity but otherwise passes.

The AI evaluator should declare **success** on Candidate 1 (105 KU is a direct hit).

---

## Iteration 3 — Confirmation (optional)

| | Viscosity (KU) | Opacity (%) | Adhesion (MPa) | Durability (years) |
|---|---|---|---|---|
| **Candidate 1** | 105 | 97 | 4.7 | 11.0 |
| **Candidate 2** | 105 | 98 | 4.6 | 10.8 |
| **Candidate 3** | 104 | 96 | 4.5 | 10.5 |

Two candidates hit 105 KU exactly. All exceed opacity, adhesion, and durability targets. Project transitions to **success**.

---

## What to watch for

- **Viscosity exact-match difficulty:** The LLM at I1 will usually bracket 105 (one candidate above, one below) but miss it. That's the natural outcome of a cold-start. Highlight this to Jun as "the LLM knows the direction but not the exact landing point — that's what the GP solves."
- **GP sigma tightening:** At I1, expect Viscosity predictions at ±5–7 KU. At I2, that should compress to ±1–2 KU — the GP's surrogate has learned the TiO₂–thickener interaction.
- **Opacity gap:** 87.25% → 96.0% is a 10% relative jump, which requires meaningfully more TiO₂. The LLM at I1 often undershoots here (logs 93–95%) while also running the viscosity too high. This trade-off is the core story of why Bayesian optimization earns its keep.
- **2σ flags at I1:** If the LLM predicts Opacity=96±3 and you log 92, that's a ~1.3σ miss — no flag. If it predicts 96±2 and actual is 92, that triggers the 2σ flag — good for demo if you want to show the anomaly detection path.
