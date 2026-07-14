"""Hito 7 — business_process_id en risks (vincula riesgo ↔ proceso BIA)

Revision ID: 0007_add_business_process_to_risks
Revises: 0006_asset_process_links
Create Date: 2026-06-18
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0007_bp_to_risks"
down_revision = "0006_asset_process_links"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = [c["name"] for c in inspector.get_columns("risks")]
    if "business_process_id" in columns:
        return

    op.add_column(
        "risks",
        sa.Column(
            "business_process_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("business_processes.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_risks_business_process_id", "risks", ["business_process_id"])


def downgrade() -> None:
    op.drop_index("ix_risks_business_process_id", table_name="risks")
    op.drop_column("risks", "business_process_id")
