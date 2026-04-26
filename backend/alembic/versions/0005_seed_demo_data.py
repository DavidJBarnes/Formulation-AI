"""seed demo portfolio, projects and paint formulations

Revision ID: 0005_seed_demo_data
Revises: 0004_portfolio_project_entities
Create Date: 2026-04-26

Adds owner_name column to projects and seeds the full MVP demo dataset:
  - 1 portfolio
  - 7 projects with iterations
  - 7 ingredients + 3 output properties (global registries)
  - Full paint-low-voc detail: project_ingredients, project_targets,
    4 iterations, 2 base + 5 tested + 3 proposed formulations with
    all ingredient amounts and property measurements.

Idempotent: all inserts use ON CONFLICT DO NOTHING.
Downgrade deletes seeded rows by known IDs; does NOT drop owner_name column.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005_seed_demo_data"
down_revision: str | Sequence[str] | None = "0004_portfolio_project_entities"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# ---------------------------------------------------------------------------
# Hard-coded UUIDs (generated once, never change)
# ---------------------------------------------------------------------------
PORTFOLIO_ID = "b0fb3d4c-9963-4f46-8310-8dfba07bb579"

PROJECT_PAINT = "430d11eb-48a4-43a3-857f-6239cd65d59f"
PROJECT_EPOXY = "7a7b9c7e-1be6-4d9a-9c24-98e47a6dd665"
PROJECT_DETERGENT = "26a02ee0-ee08-4f30-8ad3-ce53aac7f5b4"
PROJECT_LIPSTICK = "badc7ef8-38d2-443d-949e-31e62b7059cd"
PROJECT_LUBRICANT = "1f55cfcc-c0b8-45f3-a2a7-d368d5913266"
PROJECT_SUNSCREEN = "aacff876-1eec-4a0a-b7ed-1379c9623abb"
PROJECT_SEALANT = "5a7be232-4caa-4247-89cc-0abb3b2b72bd"

INGR_RESIN = "8d727ece-8ba5-4dd0-a4f1-47f8e523cbc9"
INGR_TIO2 = "32b5f2ab-68ab-4710-967d-b65614371167"
INGR_CACO3 = "6a9cd258-49aa-441a-aa6e-e4b276ecafb0"
INGR_COAL = "027a0e62-a500-43c2-b6bd-8945cb3513da"
INGR_WATER = "a31a54be-dca2-4c22-9d84-49895b2fafb5"
INGR_DEFOAM = "dd796824-c079-4848-9500-3771fdd001ae"
INGR_THICK = "f5260fe5-6a1f-4a9b-8226-03cbcde70803"

PROP_HIDE = "7f1e9f0b-8959-4675-bd7b-0a799d847880"
PROP_SCRUB = "b384fe2c-1e45-4a98-a427-1bbe6dd81675"
PROP_VOC = "91dc9f25-93ac-412b-8ac5-f9e432db2064"

PI_RESIN = "e8a6fb48-2df4-4264-bedd-f5f5046b60f1"
PI_TIO2 = "80034b8c-b438-4e93-89da-491fdf2a7deb"
PI_CACO3 = "3f99ff69-a070-4779-80d9-ce1e1d68fb9d"
PI_COAL = "57b6869f-a22d-4976-acab-269f5d14c04c"
PI_WATER = "40b2bcb8-a016-4512-b9d5-5c692dae3d12"
PI_DEFOAM = "20a15450-bb9b-41c9-8964-2dd01a1b52e3"
PI_THICK = "cb61fe6f-bbd0-4c8e-bc12-62cebe8700d7"

PT_HIDE = "e7c5202f-82a1-42ea-a651-5f2a19e256bc"
PT_SCRUB = "498683c4-ffd2-4f8f-b4f7-2cd318a0a889"
PT_VOC = "6c713d15-1882-449e-90a7-00620f9c7b2a"

ITER_PAINT_1 = "b5061a9e-f6ba-43f0-bf15-eab732e400e2"
ITER_PAINT_2 = "432f2d3e-39b4-4f26-bc17-9592df7ee0f4"
ITER_PAINT_3 = "faf4cb2a-44ac-46bc-bc95-4afa247bb2e7"
ITER_PAINT_4 = "b5f84dd5-0d69-4b70-82b6-ca60e54aa5a1"

ITER_EPOXY_1 = "3d88f541-963e-4c87-957e-6eba7078b515"
ITER_EPOXY_2 = "ed7e13a9-7c65-4dbf-8ca5-67340155dfe9"
ITER_EPOXY_3 = "8997afe5-654d-430c-ab8d-e76b86ba03c5"

ITER_DETERGENT_1 = "317063f8-e57f-4ad7-89f9-de79eef57042"
ITER_DETERGENT_2 = "5349affb-3a69-49c8-9927-f774cd0d0dd0"
ITER_DETERGENT_3 = "f2b3539b-92a2-4bff-8078-99588129b056"
ITER_DETERGENT_4 = "350a9dfa-2ca3-424f-bf98-1a4d944b721f"
ITER_DETERGENT_5 = "c8a010dd-44bd-4c62-81bd-8f83c3d3de05"

ITER_LIPSTICK_1 = "9f75cd2f-531d-425f-ab52-b77c4b745444"
ITER_LIPSTICK_2 = "c6ce588d-1ae3-42d5-8ae4-b5d47934aacb"

ITER_LUBRICANT_1 = "1e8124b9-77bb-4849-92f4-9c31094633c6"

ITER_SEALANT_1 = "5b8bf5bd-851e-4391-9d59-29ebec777517"
ITER_SEALANT_2 = "3dea8c70-a797-47a9-827c-09812b405f80"
ITER_SEALANT_3 = "43cd6e19-6822-4df6-a770-348b25c8223c"

FORM_BASE_A = "430b6fb1-2eb8-4ae1-a60c-d9634f65ecf3"
FORM_BASE_B = "d7d2440c-2d5e-4645-bcbb-590161a23c2b"
FORM_I1C1 = "2303b77c-2ce4-423a-b286-c5fb4a313fb7"
FORM_I1C2 = "131c8aa5-26df-49a1-a740-2c7f10a5c398"
FORM_I2C1 = "ff62cf0f-bf4e-4b15-a34d-1a67b18e5261"
FORM_I2C2 = "0f145e47-1f2c-43bf-964c-de740cd9ddbc"
FORM_I3C1 = "8eea68f3-c601-4aed-8650-7dc765a6e372"
FORM_I4C1 = "cd8944e2-c6c9-4e37-a2a3-cc24f6c3420c"
FORM_I4C2 = "ad595004-09f2-4418-8b7a-37388bf2ce26"
FORM_I4C3 = "2b251e5f-65fd-42d6-9757-66278314d5d8"

# IDs for formulation_ingredients and formulation_properties rows
# (generated inline in the upgrade function via uuid module, but kept static)

_FI_SEED = "aabb0001-0000-0000-0000-"  # prefix for formulation_ingredient rows
_FP_SEED = "ccdd0001-0000-0000-0000-"  # prefix for formulation_property rows


def _fi(idx: int) -> str:
    return f"{_FI_SEED}{idx:012d}"


def _fp(idx: int) -> str:
    return f"{_FP_SEED}{idx:012d}"


def upgrade() -> None:
    bind = op.get_bind()

    # ------------------------------------------------------------------
    # 1. Add owner_name column to projects
    # ------------------------------------------------------------------
    op.add_column("projects", sa.Column("owner_name", sa.String(256), nullable=True))

    # ------------------------------------------------------------------
    # 2. Portfolio
    # ------------------------------------------------------------------
    bind.execute(
        sa.text(
            "INSERT INTO portfolios (id, name, description) "
            "VALUES (:id, :name, :desc) ON CONFLICT DO NOTHING"
        ),
        {"id": PORTFOLIO_ID, "name": "R&D Portfolio 2026", "desc": "Active formulation projects across the team."},
    )

    # ------------------------------------------------------------------
    # 3. Projects
    # ------------------------------------------------------------------
    projects = [
        {
            "id": PROJECT_PAINT,
            "name": "Low-VOC Architectural Paint",
            "team": "Coatings",
            "owner_name": "Jun Liu",
            "status": "iterating",
            "domain": "Coatings",
            "started_at": "2026-02-10",
            "ends_at": "2026-08-10",
            "max_iterations": 6,
        },
        {
            "id": PROJECT_EPOXY,
            "name": "High-Temp Epoxy Adhesive",
            "team": "Adhesives",
            "owner_name": "Mira Patel",
            "status": "iterating",
            "domain": "Adhesives",
            "started_at": "2026-01-05",
            "ends_at": "2026-07-20",
            "max_iterations": 6,
        },
        {
            "id": PROJECT_DETERGENT,
            "name": "Cold-Wash Detergent",
            "team": "Home Care",
            "owner_name": "Sam Okafor",
            "status": "converged",
            "domain": "Surfactants",
            "started_at": "2025-11-15",
            "ends_at": "2026-04-30",
            "max_iterations": 5,
        },
        {
            "id": PROJECT_LIPSTICK,
            "name": "Matte Lipstick Reformulation",
            "team": "Personal Care",
            "owner_name": "Ava Bernal",
            "status": "flagged",
            "domain": "Cosmetics",
            "started_at": "2026-03-01",
            "ends_at": "2026-09-15",
            "max_iterations": 6,
        },
        {
            "id": PROJECT_LUBRICANT,
            "name": "Bio-Based Industrial Lubricant",
            "team": "Lubricants",
            "owner_name": "Heinrich Voss",
            "status": "iterating",
            "domain": "Lubricants",
            "started_at": "2026-03-22",
            "ends_at": "2026-12-01",
            "max_iterations": 6,
        },
        {
            "id": PROJECT_SUNSCREEN,
            "name": "Clear Mineral Sunscreen",
            "team": "Personal Care",
            "owner_name": "Ava Bernal",
            "status": "planning",
            "domain": "Cosmetics",
            "started_at": "2026-04-15",
            "ends_at": "2026-11-10",
            "max_iterations": 6,
        },
        {
            "id": PROJECT_SEALANT,
            "name": "Marine-Grade Sealant",
            "team": "Adhesives",
            "owner_name": "Mira Patel",
            "status": "iterating",
            "domain": "Sealants",
            "started_at": "2026-02-20",
            "ends_at": "2026-09-30",
            "max_iterations": 6,
        },
    ]
    for p in projects:
        bind.execute(
            sa.text(
                "INSERT INTO projects "
                "  (id, portfolio_id, name, team, owner_name, status, domain, started_at, ends_at, max_iterations) "
                "VALUES "
                "  (:id, :portfolio_id, :name, :team, :owner_name, :status, :domain, :started_at, :ends_at, :max_iterations) "
                "ON CONFLICT DO NOTHING"
            ),
            {**p, "portfolio_id": PORTFOLIO_ID},
        )

    # ------------------------------------------------------------------
    # 4. Global ingredients
    # ------------------------------------------------------------------
    ingredients = [
        {"id": INGR_RESIN, "name": "Resin Acrylic", "default_unit": "g"},
        {"id": INGR_TIO2, "name": "TiO₂", "default_unit": "g"},
        {"id": INGR_CACO3, "name": "Calcium Carbonate", "default_unit": "g"},
        {"id": INGR_COAL, "name": "Coalescent", "default_unit": "g"},
        {"id": INGR_WATER, "name": "Water", "default_unit": "g"},
        {"id": INGR_DEFOAM, "name": "Defoamer", "default_unit": "g"},
        {"id": INGR_THICK, "name": "Thickener", "default_unit": "g"},
    ]
    for row in ingredients:
        bind.execute(
            sa.text(
                "INSERT INTO ingredients (id, name, default_unit) "
                "VALUES (:id, :name, :default_unit) ON CONFLICT DO NOTHING"
            ),
            row,
        )

    # ------------------------------------------------------------------
    # 5. Global output properties
    # ------------------------------------------------------------------
    output_properties = [
        {"id": PROP_HIDE, "name": "Hide (contrast ratio)", "default_unit": ""},
        {"id": PROP_SCRUB, "name": "Scrub Resistance", "default_unit": "cycles"},
        {"id": PROP_VOC, "name": "VOC", "default_unit": "g/L"},
    ]
    for row in output_properties:
        bind.execute(
            sa.text(
                "INSERT INTO output_properties (id, name, default_unit) "
                "VALUES (:id, :name, :default_unit) ON CONFLICT DO NOTHING"
            ),
            row,
        )

    # ------------------------------------------------------------------
    # 6. Project ingredients for paint-low-voc
    # ------------------------------------------------------------------
    project_ingredients = [
        {"id": PI_RESIN, "ingredient_id": INGR_RESIN, "unit": "g", "sort_order": 0},
        {"id": PI_TIO2, "ingredient_id": INGR_TIO2, "unit": "g", "sort_order": 1},
        {"id": PI_CACO3, "ingredient_id": INGR_CACO3, "unit": "g", "sort_order": 2},
        {"id": PI_COAL, "ingredient_id": INGR_COAL, "unit": "g", "sort_order": 3},
        {"id": PI_WATER, "ingredient_id": INGR_WATER, "unit": "g", "sort_order": 4},
        {"id": PI_DEFOAM, "ingredient_id": INGR_DEFOAM, "unit": "g", "sort_order": 5},
        {"id": PI_THICK, "ingredient_id": INGR_THICK, "unit": "g", "sort_order": 6},
    ]
    for row in project_ingredients:
        bind.execute(
            sa.text(
                "INSERT INTO project_ingredients (id, project_id, ingredient_id, unit, sort_order) "
                "VALUES (:id, :project_id, :ingredient_id, :unit, :sort_order) "
                "ON CONFLICT DO NOTHING"
            ),
            {**row, "project_id": PROJECT_PAINT},
        )

    # ------------------------------------------------------------------
    # 7. Project targets for paint-low-voc
    # ------------------------------------------------------------------
    project_targets = [
        {
            "id": PT_HIDE,
            "output_property_id": PROP_HIDE,
            "goal": "+10%",
            "reference_label": "Paint A (incumbent)",
            "sort_order": 0,
        },
        {
            "id": PT_SCRUB,
            "output_property_id": PROP_SCRUB,
            "goal": "+10%",
            "reference_label": "Paint A (incumbent)",
            "sort_order": 1,
        },
        {
            "id": PT_VOC,
            "output_property_id": PROP_VOC,
            "goal": "<=15",
            "reference_label": None,
            "sort_order": 2,
        },
    ]
    for row in project_targets:
        bind.execute(
            sa.text(
                "INSERT INTO project_targets "
                "  (id, project_id, output_property_id, goal, reference_label, sort_order) "
                "VALUES "
                "  (:id, :project_id, :output_property_id, :goal, :reference_label, :sort_order) "
                "ON CONFLICT DO NOTHING"
            ),
            {**row, "project_id": PROJECT_PAINT},
        )

    # ------------------------------------------------------------------
    # 8. Iterations
    # ------------------------------------------------------------------
    all_iterations = [
        # paint-low-voc
        {"id": ITER_PAINT_1, "project_id": PROJECT_PAINT, "n": 1, "status": "done", "best_objective": 0.62, "started_at": "2026-02-18"},
        {"id": ITER_PAINT_2, "project_id": PROJECT_PAINT, "n": 2, "status": "done", "best_objective": 0.78, "started_at": "2026-03-04"},
        {"id": ITER_PAINT_3, "project_id": PROJECT_PAINT, "n": 3, "status": "done", "best_objective": 0.86, "started_at": "2026-03-22"},
        {"id": ITER_PAINT_4, "project_id": PROJECT_PAINT, "n": 4, "status": "in_progress", "best_objective": 0.86, "started_at": "2026-04-12", "note": "Awaiting lab results on I4·C1–C3"},
        # epoxy-bond
        {"id": ITER_EPOXY_1, "project_id": PROJECT_EPOXY, "n": 1, "status": "done", "best_objective": 0.42},
        {"id": ITER_EPOXY_2, "project_id": PROJECT_EPOXY, "n": 2, "status": "done", "best_objective": 0.61},
        {"id": ITER_EPOXY_3, "project_id": PROJECT_EPOXY, "n": 3, "status": "done", "best_objective": 0.70},
        # detergent-cold
        {"id": ITER_DETERGENT_1, "project_id": PROJECT_DETERGENT, "n": 1, "status": "done", "best_objective": 0.70},
        {"id": ITER_DETERGENT_2, "project_id": PROJECT_DETERGENT, "n": 2, "status": "done", "best_objective": 0.81},
        {"id": ITER_DETERGENT_3, "project_id": PROJECT_DETERGENT, "n": 3, "status": "done", "best_objective": 0.88},
        {"id": ITER_DETERGENT_4, "project_id": PROJECT_DETERGENT, "n": 4, "status": "done", "best_objective": 0.94},
        {"id": ITER_DETERGENT_5, "project_id": PROJECT_DETERGENT, "n": 5, "status": "done", "best_objective": 0.98},
        # lipstick-matte
        {"id": ITER_LIPSTICK_1, "project_id": PROJECT_LIPSTICK, "n": 1, "status": "done", "best_objective": 0.45},
        {"id": ITER_LIPSTICK_2, "project_id": PROJECT_LIPSTICK, "n": 2, "status": "done", "best_objective": 0.40},
        # lubricant-bio
        {"id": ITER_LUBRICANT_1, "project_id": PROJECT_LUBRICANT, "n": 1, "status": "done", "best_objective": 0.30},
        # sealant-marine
        {"id": ITER_SEALANT_1, "project_id": PROJECT_SEALANT, "n": 1, "status": "done", "best_objective": 0.50},
        {"id": ITER_SEALANT_2, "project_id": PROJECT_SEALANT, "n": 2, "status": "done", "best_objective": 0.62},
        {"id": ITER_SEALANT_3, "project_id": PROJECT_SEALANT, "n": 3, "status": "done", "best_objective": 0.74},
    ]
    for row in all_iterations:
        note = row.get("note")
        started = row.get("started_at")
        bind.execute(
            sa.text(
                "INSERT INTO iterations (id, project_id, n, status, best_objective, note, started_at) "
                "VALUES (:id, :project_id, :n, :status, :best_objective, :note, :started_at) "
                "ON CONFLICT DO NOTHING"
            ),
            {
                "id": row["id"],
                "project_id": row["project_id"],
                "n": row["n"],
                "status": row["status"],
                "best_objective": row.get("best_objective"),
                "note": note,
                "started_at": started,
            },
        )

    # ------------------------------------------------------------------
    # 9. Formulations (paint only)
    # ------------------------------------------------------------------
    rationale_i4c1 = (
        "Pushes resin further (+2.3% vs I3·C1) and trims coalescent another 33%, "
        "riding the trend that lower coalescent has improved both scrub and VOC without hurting hide. "
        "Calcium carbonate dropped slightly to keep total volume balanced."
    )
    rationale_i4c2 = (
        "Bumps TiO₂ to chase the +10% hide target while leaving coalescent at the I2·C2 "
        "sweet spot — a hedge against I4·C1 in case the low-coalescent trend reverses."
    )
    rationale_i4c3 = (
        "Conservative exploration around the I2 cluster — useful as a noise-control sample "
        "if I4·C1 over-shoots and we need to triangulate."
    )

    formulations = [
        {"id": FORM_BASE_A, "iteration_id": None, "label": "Paint A (incumbent)", "kind": "base", "rationale": None},
        {"id": FORM_BASE_B, "iteration_id": None, "label": "Paint B (low-cost)", "kind": "base", "rationale": None},
        {"id": FORM_I1C1, "iteration_id": ITER_PAINT_1, "label": "I1·C1", "kind": "tested", "rationale": None},
        {"id": FORM_I1C2, "iteration_id": ITER_PAINT_1, "label": "I1·C2", "kind": "tested", "rationale": None},
        {"id": FORM_I2C1, "iteration_id": ITER_PAINT_2, "label": "I2·C1", "kind": "tested", "rationale": None},
        {"id": FORM_I2C2, "iteration_id": ITER_PAINT_2, "label": "I2·C2", "kind": "tested", "rationale": None},
        {"id": FORM_I3C1, "iteration_id": ITER_PAINT_3, "label": "I3·C1", "kind": "tested", "rationale": None},
        {"id": FORM_I4C1, "iteration_id": ITER_PAINT_4, "label": "I4·C1", "kind": "proposed", "rationale": rationale_i4c1},
        {"id": FORM_I4C2, "iteration_id": ITER_PAINT_4, "label": "I4·C2", "kind": "proposed", "rationale": rationale_i4c2},
        {"id": FORM_I4C3, "iteration_id": ITER_PAINT_4, "label": "I4·C3", "kind": "proposed", "rationale": rationale_i4c3},
    ]
    for row in formulations:
        bind.execute(
            sa.text(
                "INSERT INTO formulations (id, project_id, iteration_id, label, kind, rationale) "
                "VALUES (:id, :project_id, :iteration_id, :label, :kind, :rationale) "
                "ON CONFLICT DO NOTHING"
            ),
            {**row, "project_id": PROJECT_PAINT},
        )

    # ------------------------------------------------------------------
    # 10. Formulation ingredients
    # ------------------------------------------------------------------
    # (formulation_id, pi_id, amount)
    fi_rows = [
        # Paint A (incumbent)
        (FORM_BASE_A, PI_RESIN, 280), (FORM_BASE_A, PI_TIO2, 180), (FORM_BASE_A, PI_CACO3, 220),
        (FORM_BASE_A, PI_COAL, 18), (FORM_BASE_A, PI_WATER, 280), (FORM_BASE_A, PI_DEFOAM, 4), (FORM_BASE_A, PI_THICK, 18),
        # Paint B (low-cost)
        (FORM_BASE_B, PI_RESIN, 240), (FORM_BASE_B, PI_TIO2, 140), (FORM_BASE_B, PI_CACO3, 280),
        (FORM_BASE_B, PI_COAL, 14), (FORM_BASE_B, PI_WATER, 308), (FORM_BASE_B, PI_DEFOAM, 4), (FORM_BASE_B, PI_THICK, 14),
        # I1·C1
        (FORM_I1C1, PI_RESIN, 270), (FORM_I1C1, PI_TIO2, 175), (FORM_I1C1, PI_CACO3, 230),
        (FORM_I1C1, PI_COAL, 12), (FORM_I1C1, PI_WATER, 295), (FORM_I1C1, PI_DEFOAM, 4), (FORM_I1C1, PI_THICK, 14),
        # I1·C2
        (FORM_I1C2, PI_RESIN, 290), (FORM_I1C2, PI_TIO2, 170), (FORM_I1C2, PI_CACO3, 235),
        (FORM_I1C2, PI_COAL, 8), (FORM_I1C2, PI_WATER, 285), (FORM_I1C2, PI_DEFOAM, 4), (FORM_I1C2, PI_THICK, 18),
        # I2·C1
        (FORM_I2C1, PI_RESIN, 300), (FORM_I2C1, PI_TIO2, 178), (FORM_I2C1, PI_CACO3, 220),
        (FORM_I2C1, PI_COAL, 6), (FORM_I2C1, PI_WATER, 280), (FORM_I2C1, PI_DEFOAM, 4), (FORM_I2C1, PI_THICK, 16),
        # I2·C2
        (FORM_I2C2, PI_RESIN, 285), (FORM_I2C2, PI_TIO2, 172), (FORM_I2C2, PI_CACO3, 240),
        (FORM_I2C2, PI_COAL, 4), (FORM_I2C2, PI_WATER, 290), (FORM_I2C2, PI_DEFOAM, 5), (FORM_I2C2, PI_THICK, 18),
        # I3·C1
        (FORM_I3C1, PI_RESIN, 305), (FORM_I3C1, PI_TIO2, 182), (FORM_I3C1, PI_CACO3, 215),
        (FORM_I3C1, PI_COAL, 3), (FORM_I3C1, PI_WATER, 280), (FORM_I3C1, PI_DEFOAM, 4), (FORM_I3C1, PI_THICK, 18),
        # I4·C1
        (FORM_I4C1, PI_RESIN, 312), (FORM_I4C1, PI_TIO2, 184), (FORM_I4C1, PI_CACO3, 210),
        (FORM_I4C1, PI_COAL, 2), (FORM_I4C1, PI_WATER, 278), (FORM_I4C1, PI_DEFOAM, 4), (FORM_I4C1, PI_THICK, 18),
        # I4·C2
        (FORM_I4C2, PI_RESIN, 300), (FORM_I4C2, PI_TIO2, 186), (FORM_I4C2, PI_CACO3, 220),
        (FORM_I4C2, PI_COAL, 4), (FORM_I4C2, PI_WATER, 280), (FORM_I4C2, PI_DEFOAM, 4), (FORM_I4C2, PI_THICK, 16),
        # I4·C3
        (FORM_I4C3, PI_RESIN, 295), (FORM_I4C3, PI_TIO2, 178), (FORM_I4C3, PI_CACO3, 225),
        (FORM_I4C3, PI_COAL, 5), (FORM_I4C3, PI_WATER, 285), (FORM_I4C3, PI_DEFOAM, 4), (FORM_I4C3, PI_THICK, 18),
    ]
    for idx, (form_id, pi_id, amount) in enumerate(fi_rows):
        bind.execute(
            sa.text(
                "INSERT INTO formulation_ingredients (id, formulation_id, project_ingredient_id, amount) "
                "VALUES (:id, :formulation_id, :project_ingredient_id, :amount) "
                "ON CONFLICT DO NOTHING"
            ),
            {"id": _fi(idx), "formulation_id": form_id, "project_ingredient_id": pi_id, "amount": float(amount)},
        )

    # ------------------------------------------------------------------
    # 11. Formulation properties
    # ------------------------------------------------------------------
    # (formulation_id, pt_id, value, sigma)
    fp_rows = [
        # Paint A (incumbent): Hide=0.93, Scrub=580, VOC=38
        (FORM_BASE_A, PT_HIDE, 0.93, None),
        (FORM_BASE_A, PT_SCRUB, 580.0, None),
        (FORM_BASE_A, PT_VOC, 38.0, None),
        # Paint B (low-cost): Hide=0.88, Scrub=410, VOC=32
        (FORM_BASE_B, PT_HIDE, 0.88, None),
        (FORM_BASE_B, PT_SCRUB, 410.0, None),
        (FORM_BASE_B, PT_VOC, 32.0, None),
        # I1·C1
        (FORM_I1C1, PT_HIDE, 0.91, None),
        (FORM_I1C1, PT_SCRUB, 510.0, None),
        (FORM_I1C1, PT_VOC, 26.0, None),
        # I1·C2
        (FORM_I1C2, PT_HIDE, 0.92, None),
        (FORM_I1C2, PT_SCRUB, 540.0, None),
        (FORM_I1C2, PT_VOC, 22.0, None),
        # I2·C1
        (FORM_I2C1, PT_HIDE, 0.94, None),
        (FORM_I2C1, PT_SCRUB, 600.0, None),
        (FORM_I2C1, PT_VOC, 18.0, None),
        # I2·C2
        (FORM_I2C2, PT_HIDE, 0.93, None),
        (FORM_I2C2, PT_SCRUB, 590.0, None),
        (FORM_I2C2, PT_VOC, 16.0, None),
        # I3·C1
        (FORM_I3C1, PT_HIDE, 0.95, None),
        (FORM_I3C1, PT_SCRUB, 640.0, None),
        (FORM_I3C1, PT_VOC, 14.0, None),
        # I4·C1 (proposed, with sigma)
        (FORM_I4C1, PT_HIDE, 0.955, 0.012),
        (FORM_I4C1, PT_SCRUB, 670.0, 35.0),
        (FORM_I4C1, PT_VOC, 12.0, 1.6),
        # I4·C2 (proposed, with sigma)
        (FORM_I4C2, PT_HIDE, 0.96, 0.01),
        (FORM_I4C2, PT_SCRUB, 625.0, 30.0),
        (FORM_I4C2, PT_VOC, 16.0, 1.4),
        # I4·C3 (proposed, with sigma)
        (FORM_I4C3, PT_HIDE, 0.94, 0.014),
        (FORM_I4C3, PT_SCRUB, 605.0, 40.0),
        (FORM_I4C3, PT_VOC, 19.0, 1.8),
    ]
    for idx, (form_id, pt_id, value, sigma) in enumerate(fp_rows):
        bind.execute(
            sa.text(
                "INSERT INTO formulation_properties (id, formulation_id, project_target_id, value, sigma) "
                "VALUES (:id, :formulation_id, :project_target_id, :value, :sigma) "
                "ON CONFLICT DO NOTHING"
            ),
            {"id": _fp(idx), "formulation_id": form_id, "project_target_id": pt_id, "value": value, "sigma": sigma},
        )


def downgrade() -> None:
    bind = op.get_bind()

    # Delete in reverse dependency order
    # formulation_properties
    fp_ids = [_fp(i) for i in range(30)]
    if fp_ids:
        bind.execute(
            sa.text(f"DELETE FROM formulation_properties WHERE id IN ({', '.join(repr(x) for x in fp_ids)})"),
        )

    # formulation_ingredients
    fi_ids = [_fi(i) for i in range(70)]
    if fi_ids:
        bind.execute(
            sa.text(f"DELETE FROM formulation_ingredients WHERE id IN ({', '.join(repr(x) for x in fi_ids)})"),
        )

    # formulations
    form_ids = [FORM_BASE_A, FORM_BASE_B, FORM_I1C1, FORM_I1C2, FORM_I2C1, FORM_I2C2,
                FORM_I3C1, FORM_I4C1, FORM_I4C2, FORM_I4C3]
    bind.execute(
        sa.text(f"DELETE FROM formulations WHERE id IN ({', '.join(repr(x) for x in form_ids)})"),
    )

    # iterations
    iter_ids = [
        ITER_PAINT_1, ITER_PAINT_2, ITER_PAINT_3, ITER_PAINT_4,
        ITER_EPOXY_1, ITER_EPOXY_2, ITER_EPOXY_3,
        ITER_DETERGENT_1, ITER_DETERGENT_2, ITER_DETERGENT_3, ITER_DETERGENT_4, ITER_DETERGENT_5,
        ITER_LIPSTICK_1, ITER_LIPSTICK_2,
        ITER_LUBRICANT_1,
        ITER_SEALANT_1, ITER_SEALANT_2, ITER_SEALANT_3,
    ]
    bind.execute(
        sa.text(f"DELETE FROM iterations WHERE id IN ({', '.join(repr(x) for x in iter_ids)})"),
    )

    # project targets + ingredients
    bind.execute(sa.text(f"DELETE FROM project_targets WHERE id IN ({repr(PT_HIDE)}, {repr(PT_SCRUB)}, {repr(PT_VOC)})"))
    pi_ids = [PI_RESIN, PI_TIO2, PI_CACO3, PI_COAL, PI_WATER, PI_DEFOAM, PI_THICK]
    bind.execute(
        sa.text(f"DELETE FROM project_ingredients WHERE id IN ({', '.join(repr(x) for x in pi_ids)})"),
    )

    # output properties + ingredients
    bind.execute(sa.text(f"DELETE FROM output_properties WHERE id IN ({repr(PROP_HIDE)}, {repr(PROP_SCRUB)}, {repr(PROP_VOC)})"))
    ingr_ids = [INGR_RESIN, INGR_TIO2, INGR_CACO3, INGR_COAL, INGR_WATER, INGR_DEFOAM, INGR_THICK]
    bind.execute(
        sa.text(f"DELETE FROM ingredients WHERE id IN ({', '.join(repr(x) for x in ingr_ids)})"),
    )

    # projects + portfolio
    proj_ids = [PROJECT_PAINT, PROJECT_EPOXY, PROJECT_DETERGENT, PROJECT_LIPSTICK,
                PROJECT_LUBRICANT, PROJECT_SUNSCREEN, PROJECT_SEALANT]
    bind.execute(
        sa.text(f"DELETE FROM projects WHERE id IN ({', '.join(repr(x) for x in proj_ids)})"),
    )
    bind.execute(sa.text(f"DELETE FROM portfolios WHERE id = {repr(PORTFOLIO_ID)}"))

    # NOTE: owner_name column is intentionally left in place on downgrade
    # to avoid data loss if any non-seed data was added.
