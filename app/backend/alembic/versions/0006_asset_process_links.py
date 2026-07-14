"""Hito 6 — asset_process_links (peso activo↔proceso para F3)

Revision ID: 0006_asset_process_links
Revises: 4cdda752f344
Create Date: 2026-06-18

Tables created:
  asset_process_links  — N:M con peso entre assets y business_processes
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0006_asset_process_links"
down_revision = "4cdda752f344"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "asset_process_links" in inspector.get_table_names():
        return

    op.create_table(
        "asset_process_links",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "asset_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("assets.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "process_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("business_processes.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        # Fracción de la capacidad del proceso que aporta este activo (0.0–1.0)
        sa.Column("weight", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("asset_id", "process_id", name="uq_asset_process_link"),
    )


def downgrade() -> None:
    op.drop_table("asset_process_links")
