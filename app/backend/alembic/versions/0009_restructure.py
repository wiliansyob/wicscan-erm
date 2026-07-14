"""0009 — Reestructuración: drop tablas obsoletas + legacy

Revision ID: 0009_restructure
Revises: 0008_scenario_prob_impact
Create Date: 2026-06-19

Estrategia: create_all() ya creó las nuevas tablas (escenarios, riesgos, etc.)
en el arranque; esta migración elimina las tablas heredadas que ya no se usan.
Los datos existentes se descartan (restructuración limpia).
"""
from __future__ import annotations

from alembic import op

revision = "0009_restructure"
down_revision = "0008_scenario_prob_impact"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Eliminar tablas obsoletas ────────────────────────────────────────────
    # Flujo viejo de riesgo por motor
    op.execute("DROP TABLE IF EXISTS risk_engine_runs CASCADE")

    # Cruce contextual F1×F2 eliminado del flujo
    op.execute("DROP TABLE IF EXISTS contextual_findings CASCADE")

    # Tablas heredadas renombradas (las nuevas ya existen por create_all)
    op.execute("DROP TABLE IF EXISTS scenario_finding_links CASCADE")
    op.execute("DROP TABLE IF EXISTS risk_scenarios CASCADE")
    op.execute("DROP TABLE IF EXISTS risk_treatments CASCADE")
    op.execute("DROP TABLE IF EXISTS risks CASCADE")
    op.execute("DROP TABLE IF EXISTS bia_estimates CASCADE")
    op.execute("DROP TABLE IF EXISTS asset_process_links CASCADE")
    op.execute("DROP TABLE IF EXISTS business_processes CASCADE")
    op.execute("DROP TABLE IF EXISTS questionnaire_answers CASCADE")
    op.execute("DROP TABLE IF EXISTS context_questionnaires CASCADE")
    op.execute("DROP TABLE IF EXISTS normative_profiles CASCADE")


def downgrade() -> None:
    # Downgrade no recupera datos; solo documenta el reverso de schema.
    pass
