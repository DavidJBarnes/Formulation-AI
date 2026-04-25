# Upload template

The XLSX shape Formulation-AI ingests for Phase 1. Skips the Signals Notebook
adapter (which is a Phase 2 build) and lets users upload base products and
targets directly.

## Files

- **template.xlsx** — empty, ready to fill in. Three sheets: README, Products, Targets.
- **paint-example.xlsx** — same shape, filled in with Jun's paint scenario from the
  2026-04-23 email thread (Paint A/B/C/D, viscosity/opacity/adhesion/durability).
- **generate.py** — regenerates both. Run with `python generate.py`.

## Conventions

**Products sheet:**

```
Product | Ingredient: <name> (<unit>) | … | Property: <name> (<unit>) | …
```

- One row per product. First column is the product ID.
- Column-header prefix `Ingredient:` vs `Property:` declares the role.
- Unit is in parentheses on the column header — change the unit, change the column.
- Blank ingredient cells = ingredient absent. Property cells should be filled (measured outcomes).

**Targets sheet:**

```
Property | Goal | Reference | Notes
```

Goal operators (mini-DSL):

| Operator | Meaning                                       |
|----------|-----------------------------------------------|
| `=N`     | Hit absolute value N                          |
| `>=N`    | Minimum N                                     |
| `<=N`    | Maximum N                                     |
| `+N%`    | Increase by N% versus the Reference            |
| `-N%`    | Decrease by N% versus the Reference            |
| `[a,b]`  | Stay within range [a, b]                      |

`Reference` is only required for relative goals (`+%` / `-%`). Use a product
ID like `Paint A` or an aggregate like `average of base`.
