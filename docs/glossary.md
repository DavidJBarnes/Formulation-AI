# Formulation·AI — Glossary of Terms

Covers product vocabulary, domain language, and how the two map to each other.
Terms are grouped by concept cluster; cross-references are in *italics*.

---

## 1. The three-layer hierarchy

```
Portfolio
  └── Project  (also called "Program" interchangeably in conversation)
        └── Iteration  (one cycle of the DOE inner loop)
              └── Candidate  (one proposed formulation per iteration)
```

### Portfolio
The top-level view. A single R&D team's full collection of active and completed
*Projects*. Typically 5–10 concurrent projects across a 20-person team. The
portfolio surface shows Gantt timelines, objective trajectories, and targets-met
heatmaps across all projects at once.

### Project
A single formulation development effort with a defined goal and timeline (typically
6–18 months). A project has:
- One or more *Base Products* as the starting point
- A set of *Targets* to hit
- A sequence of *Iterations* that run the *DOE inner loop*
- A *Status* (Planning → Iterating → Converged | Flagged)

"Project" is the canonical term everywhere — UI, codebase, and conversation.

### Iteration
One full cycle of the DOE inner loop within a project:
1. AI proposes *K* candidates
2. Lab manually samples and tests them
3. Results are logged
4. Evaluator decides: iterate again, declare success (*Converged*), or raise a
   *Data Integrity Flag*

Iterations are numbered starting at 1. The POC scope is 3–6 iterations per
project (DOE inner loop 3→6).

### Candidate
One specific formulation proposed by the AI within an iteration. Each candidate
has:
- A full *Ingredient* recipe (amounts per component)
- Predicted *Property* values with 1-sigma uncertainty: `(value ± σ)`
- A plain-English *Rationale* explaining why the AI is proposing it

---

## 2. Formulation domain

### Formulation
The complete specification of a product as a mixture: which *Ingredients* are
present and in what amounts. Each formulation has measured or predicted *Property*
values. Formulations come in three kinds:

| Kind | Description |
|------|-------------|
| Base product | An existing reference formulation (e.g., incumbent, low-cost variant) |
| Tested | A candidate that has gone through the lab and has measured results |
| Proposed | A candidate the AI has generated but that hasn't been tested yet |

### Ingredient
A component of a formulation (e.g., Resin Acrylic, TiO₂, Coalescent). Specified
by name and unit (typically grams). In the upload template, columns are prefixed
`Ingredient: <name> (<unit>)`.

### Property  _(also: Output, Response)_
A measurable characteristic of a formulation (e.g., VOC, Scrub Resistance,
Hide/contrast ratio). In the upload template, columns are prefixed
`Property: <name> (<unit>)`. For *Proposed* candidates, properties carry a
1-sigma uncertainty (σ). "Output" and "Response" are equivalent terms from the
DOE literature.

### Base Product  _(also: Reference, Incumbent)_
An existing, already-tested formulation used as the starting benchmark. Targets
can be expressed relative to a base product (e.g., `+10%` means 10% better than
the base). A project can have multiple base products.

### Target  _(also: Goal, Objective constraint)_
A specification of what a *Property* must achieve. Expressed in a mini-DSL:

| Syntax | Meaning |
|--------|---------|
| `=N` | Must equal N (±3% tolerance) |
| `>=N` | Must be at least N |
| `<=N` | Must be at most N |
| `+N%` / `-N%` | Must be N% above/below a *Reference* base product |
| `[a,b]` | Must fall within the range [a, b] |

### Objective  _(also: Composite score)_
A single scalar that combines all *Targets* into one number for plotting and
comparison. Used in the trajectory scatter chart and iteration cards. Ranges 0→1,
where 1 = all targets fully met.

### VOC
Volatile Organic Compounds. A regulatory *Property* — lower is better. In the
paint example the target is `<=15 g/L`.

### Contrast Ratio  _(also: Hide)_
A *Property* measuring how opaque a paint is (how well it covers the surface
below). Value 0→1; higher is better. Also called "hide" colloquially.

---

## 3. Optimization concepts

### DOE  (Design of Experiments)
A structured approach to exploring a formulation space by testing a small,
well-chosen set of *Candidates* each *Iteration* rather than testing randomly.
The "inner loop" refers to the per-project DOE cycle (3→6 iterations). The
"outer loop" refers to portfolio-level reporting bookends (project-start and
project-end summaries).

### Proposal Engine  _(also: Optimizer)_
The component that takes *Base Products* + *Targets* + all prior tested results
and generates the next set of *Candidates*. In **Phase 1** this is Claude Opus
4.7 (LLM-only, reasoning from data). In **Phase 2** it is a classical Bayesian
optimizer (GP/BO) operating under the LLM.

### Bayesian Optimization  _(also: BO, GP/BO)_
A mathematical optimization strategy that builds a probabilistic model (usually
a Gaussian Process) of the objective surface and proposes candidates that balance
exploration (uncertain regions) with exploitation (regions likely to be good).
Phase 2 work — the `optimizer/` module boundary is kept clean so it can slot in
without changing the rest of the system.

### Gaussian Process  _(GP)_
The probabilistic model most commonly used inside Bayesian Optimization. Produces
predicted value + uncertainty (σ) for any untested formulation — exactly the
`(value ± σ)` output contract already used by the Phase 1 LLM.

### Uncertainty  _(σ, 1-sigma)_
The AI's confidence interval around a predicted *Property* value. A candidate
with `VOC = 12 ± 1.6 g/L` means the model expects VOC around 12 but could
easily be 10.4–13.6. Wider σ = less confident = higher exploration value.

### Converged
A project *Status* meaning the evaluator has declared that the targets have been
met and no further iteration is needed. Equivalent to "success."

### Data Integrity Flag  _(also: Anomaly, Escalation)_
A project *Status* raised when actual lab results deviate from what the AI
predicted by more than a noise threshold. Signals that either the AI model is
wrong, or there may be a measurement/process error that a human should
investigate before the next iteration proceeds.

---

## 4. Product & workflow concepts

### Phase 1  _(POC)_
The current build. LLM-only proposal engine (Claude Opus 4.7), CSV/Excel upload
(no Signals adapter), portfolio surface with three chart types, DOE inner loop
3→6. Shippable in 2–3 weeks.

### Phase 2
The planned follow-on. Real Bayesian optimizer (GP/BO) slots into the
`optimizer/` module behind the same API. The Signals ingestion adapter (an
AI-assisted per-team mapping wizard) is also Phase 2 work.

### Upload Template
The Phase 1 XLSX file users fill out to start a project. Three sheets:
- **README** — format spec
- **Products** — wide table, one row per base formulation, columns prefixed
  `Ingredient:` or `Property:`
- **Targets** — one row per goal, Goal column uses the mini-DSL

Lives at `docs/upload-template/`. The paint scenario is in `paint-example.xlsx`.

### Signals  _(Revvity Signals One, Signals Notebook)_
The ELN (Electronic Lab Notebook) platform used by Revvity customers to record
experiments. Formulation data in Signals is spread across experiments as free
text, tables, hierarchy tables, hyperlinks, and material library refs — not a
single "formulation" object. The Signals REST API is wrapped by
`../revvitysignals-mcp/`.

### Signals Adapter  _(also: Ingestion Adapter, Mapping Wizard)_
A Phase 2 sub-project: an AI-assisted, human-in-the-loop tool that reads a
team's Signals Notebook and maps their experiment structure to the wide table
that the optimizer consumes. Described by Jun as the hardest part — "loosely
connected SQL database without consistent data-logic-action mapping."

### ELN  (Electronic Lab Notebook)
Software used by scientists to record experimental procedures and results
digitally. Signals Notebook is the ELN this product integrates with.

---

## 5. People & roles

| Name | Role |
|------|------|
| **Jun Liu** | Senior PMM, Revvity Signals Software. Domain expert and co-designer. His skepticism that LLMs can do DOE is the core thing the `experiments/quad-model-proposal/` prototype answers. |
| **David Barnes** | Builder. Product and engineering lead on Formulation·AI. Also pursuing a Revvity role — this project doubles as an audition artifact. |

---

## 6. Key relationships at a glance

```
Portfolio   contains many  Projects
Project     runs through   Iterations (3–6)
Iteration   produces       Candidates (proposed) → Tested (after lab)
Candidate   specifies      Ingredients + predicted Properties ± σ
Project     has            Targets (one per Property of interest)
Target      is expressed   relative to a Base Product OR absolute
Evaluator   reads          Tested results vs Targets → Converged | Iterate | Flag
Optimizer   in Phase 1 =   Claude Opus 4.7 (LLM)
Optimizer   in Phase 2 =   GP/BO under the LLM
```
