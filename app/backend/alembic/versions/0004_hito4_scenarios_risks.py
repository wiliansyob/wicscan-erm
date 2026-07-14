"""Hito 4 — F3 escenarios + scoring determinista

Revision ID: 0004_hito4
Revises: 0003_hito3
Create Date: 2026-06-17

Tables created:
  risk_scenarios
  scenario_finding_links

Columns added to risks:
  scenario_id, factor_access_vector, factor_complexity,
  factor_privileges, factor_exploit_evidence, prob_level,
  impact_operational, impact_financial, impact_normative,
  impact_reputational, impact_level
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0004_hito4"
down_revision = "0003_hito3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── risk_scenarios ────────────────────────────────────────────────────
    op.create_table(
        "risk_scenarios",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "project_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False, index=True,
        ),
        sa.Column("scenario_code", sa.String(20), nullable=True),
        sa.Column("consequence",   sa.String(512), nullable=False),
        sa.Column("group_key",     sa.String(200), nullable=False),
        sa.Column(
            "asset_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("assets.id", ondelete="SET NULL"), nullable=True,
        ),
        sa.Column(
            "business_process_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("business_processes.id", ondelete="SET NULL"), nullable=True,
        ),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("project_id", "group_key", name="uq_scenario_per_project_group"),
    )
    # (indexes ix_risk_scenarios_project_id and ix_risk_scenarios_group_key
    #  are created automatically by index=True on the Column definitions above)

    # ── scenario_finding_links ────────────────────────────────────────────
    op.create_table(
        "scenario_finding_links",
        sa.Column(
            "scenario_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("risk_scenarios.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "finding_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("findings.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "contextual_finding_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("contextual_findings.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # ── ALTER TABLE risks — add ISO 31000 columns ─────────────────────────
    op.add_column("risks", sa.Column(
        "scenario_id", postgresql.UUID(as_uuid=True),
        sa.ForeignKey("risk_scenarios.id", ondelete="SET NULL"),
        nullable=True,
    ))
    op.create_index("ix_risks_scenario_id", "risks", ["scenario_id"])

    for col in (
        sa.Column("factor_access_vector",    sa.String(50),  nullable=True),
        sa.Column("factor_complexity",       sa.String(50),  nullable=True),
        sa.Column("factor_privileges",       sa.String(50),  nullable=True),
        sa.Column("factor_exploit_evidence", sa.String(50),  nullable=True),
        sa.Column("prob_level",              sa.String(20),  nullable=True),
        sa.Column("impact_operational",      sa.String(20),  nullable=True),
        sa.Column("impact_financial",        sa.String(20),  nullable=True),
        sa.Column("impact_normative",        sa.String(20),  nullable=True),
        sa.Column("impact_reputational",     sa.String(20),  nullable=True),
        sa.Column("impact_level",            sa.String(20),  nullable=True),
    ):
        op.add_column("risks", col)


def downgrade() -> None:
    # Remove new risks columns
    for col_name in (
        "impact_level", "impact_reputational", "impact_normative",
        "impact_financial", "impact_operational", "prob_level",
        "factor_exploit_evidence", "factor_privileges",
        "factor_complexity", "factor_access_vector",
    ):
        op.drop_column("risks", col_name)
    op.drop_index("ix_risks_scenario_id", table_name="risks")
    op.drop_column("risks", "scenario_id")

    op.drop_table("scenario_finding_links")
    op.drop_table("risk_scenarios")
