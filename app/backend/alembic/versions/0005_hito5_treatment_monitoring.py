"""Hito 5 — F4 Priorización, plan y mejora continua

Revision ID: 0005_hito5
Revises: 0004_hito4
Create Date: 2026-06-17

Tables created:
  trigger_events
  review_cycles
  risk_indicators

Columns added to risk_treatments:
  effort, action_priority, verification
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0005_hito5"
down_revision = "0004_hito4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── trigger_events ───────────────────────────────────────────────────
    op.create_table(
        "trigger_events",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "project_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False, index=True,
        ),
        sa.Column("event_type",  sa.String(60),  nullable=False),
        sa.Column("description", sa.Text,        nullable=True),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("created_at",  sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at",  sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("ix_trigger_events_event_type", "trigger_events", ["event_type"])

    # ── review_cycles ────────────────────────────────────────────────────
    op.create_table(
        "review_cycles",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "project_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False, index=True,
        ),
        sa.Column("cycle_type",   sa.String(30), nullable=False),
        sa.Column(
            "triggered_by", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("trigger_events.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("performed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("summary",      postgresql.JSON(),           nullable=True),
        sa.Column("status",       sa.String(30), nullable=False, server_default="pending"),
        sa.Column("created_at",   sa.DateTime(timezone=True),  nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at",   sa.DateTime(timezone=True),  nullable=False,
                  server_default=sa.text("now()")),
    )
    # (ix_review_cycles_project_id auto-created by index=True on Column)

    # ── risk_indicators ──────────────────────────────────────────────────
    op.create_table(
        "risk_indicators",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "project_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False, index=True,
        ),
        sa.Column("period",                sa.String(10),  nullable=False),
        sa.Column("pending_critical_high", sa.Integer(),   nullable=False, server_default="0"),
        sa.Column("actions_on_time_pct",   sa.Float(),     nullable=False, server_default="100"),
        sa.Column("incidents_count",       sa.Integer(),   nullable=False, server_default="0"),
        sa.Column("normative_status",      postgresql.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.UniqueConstraint("project_id", "period", name="uq_indicator_per_project_period"),
    )
    # (ix_risk_indicators_project_id auto-created by index=True on Column)

    # ── ALTER TABLE risk_treatments ──────────────────────────────────────
    op.add_column("risk_treatments", sa.Column("effort",          sa.String(10), nullable=True))
    op.add_column("risk_treatments", sa.Column("action_priority", sa.Integer(),  nullable=True))
    op.add_column("risk_treatments", sa.Column("verification",    sa.Text,       nullable=True))


def downgrade() -> None:
    op.drop_column("risk_treatments", "verification")
    op.drop_column("risk_treatments", "action_priority")
    op.drop_column("risk_treatments", "effort")

    op.drop_table("risk_indicators")
    op.drop_table("review_cycles")
    op.drop_index("ix_trigger_events_event_type", table_name="trigger_events")
    op.drop_table("trigger_events")
