"""Hito 3 — F2.C mapeo contextual (contextual_findings)

Revision ID: 0003_hito3
Revises: 0002_hito2
Create Date: 2026-06-17

Tables created:
  contextual_findings
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003_hito3"
down_revision = "0002_hito2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "contextual_findings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("finding_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("findings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("asset_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("assets.id", ondelete="SET NULL"), nullable=True),
        sa.Column("business_process_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("business_processes.id", ondelete="SET NULL"), nullable=True),
        sa.Column("revenue_dependency", sa.String(10), nullable=True),
        sa.Column("contractual_risk", postgresql.JSON(), nullable=True),
        sa.Column("exposed_data", postgresql.JSON(), nullable=True),
        sa.Column("activated_regulation", postgresql.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("finding_id", name="uq_contextual_finding_per_finding"),
    )


def downgrade() -> None:
    op.drop_table("contextual_findings")
