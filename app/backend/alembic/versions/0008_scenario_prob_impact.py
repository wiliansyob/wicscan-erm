"""Hito 8 — probabilidad e impacto en risk_scenarios

Revision ID: 0008_scenario_prob_impact
Revises: 0007_bp_to_risks
Create Date: 2026-06-19
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0008_scenario_prob_impact"
down_revision = "0007_bp_to_risks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = [c["name"] for c in inspector.get_columns("risk_scenarios")]

    cols = {
        "title":                  sa.Column("title", sa.String(512), nullable=True),
        "probability":            sa.Column("probability", sa.Integer, nullable=True),
        "prob_level":             sa.Column("prob_level", sa.String(20), nullable=True),
        "probability_rationale":  sa.Column("probability_rationale", sa.Text, nullable=True),
        "impact":                 sa.Column("impact", sa.Integer, nullable=True),
        "impact_level":           sa.Column("impact_level", sa.String(20), nullable=True),
        "impact_rationale":       sa.Column("impact_rationale", sa.Text, nullable=True),
        "impact_operational":     sa.Column("impact_operational", sa.String(20), nullable=True),
        "impact_financial":       sa.Column("impact_financial", sa.String(20), nullable=True),
        "impact_normative":       sa.Column("impact_normative", sa.String(20), nullable=True),
        "impact_reputational":    sa.Column("impact_reputational", sa.String(20), nullable=True),
    }
    for name, col in cols.items():
        if name not in existing:
            op.add_column("risk_scenarios", col)


def downgrade() -> None:
    for col in [
        "title", "probability", "prob_level", "probability_rationale",
        "impact", "impact_level", "impact_rationale",
        "impact_operational", "impact_financial", "impact_normative", "impact_reputational",
    ]:
        op.drop_column("risk_scenarios", col)
