"""Hito 2 — BIA simplificado (business_processes, bia_estimates)

Revision ID: 0002_hito2
Revises: 0001_hito1
Create Date: 2026-06-17

Tables created:
  business_processes
  bia_estimates
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002_hito2"
down_revision = "0001_hito1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ─── business_processes ──────────────────────────────────────────────────
    op.create_table(
        "business_processes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("owner", sa.String(200), nullable=True),
        sa.Column("criticality", sa.String(20), nullable=False, server_default="important"),
        sa.Column("revenue_dependency", sa.String(10), nullable=False, server_default="<20"),
        sa.Column("manual_alternative", sa.String(20), nullable=False, server_default="none"),
        sa.Column("contractual_commitment", postgresql.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # ─── bia_estimates ────────────────────────────────────────────────────────
    op.create_table(
        "bia_estimates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("process_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("business_processes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("impact_2h", sa.Float(), nullable=True),
        sa.Column("impact_8h", sa.Float(), nullable=True),
        sa.Column("impact_24h", sa.Float(), nullable=True),
        sa.Column("sn_active", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("mtpd_hours", sa.Float(), nullable=True),
        sa.Column("rto_hours", sa.Float(), nullable=True),
        sa.Column("rpo_hours", sa.Float(), nullable=True),
        sa.Column("breakdown", postgresql.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("bia_estimates")
    op.drop_table("business_processes")
