"""Hito 1 — versioned catalog, questionnaire engine, normative profile

Revision ID: 0001_hito1
Revises:
Create Date: 2026-06-17

Tables created:
  questionnaire_definitions
  question_definitions
  question_dependencies
  definition_change_log
  context_questionnaires
  questionnaire_answers
  normative_profiles

Seed: v1 questionnaire definition (published) with blocks A–D.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "0001_hito1"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ─── questionnaire_definitions ───────────────────────────────────────────
    op.create_table(
        "questionnaire_definitions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("version", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # ─── question_definitions ────────────────────────────────────────────────
    op.create_table(
        "question_definitions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("definition_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("questionnaire_definitions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("block", sa.String(2), nullable=False),
        sa.Column("question_id", sa.String(20), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("options", postgresql.JSON(), nullable=True),
        sa.Column("order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("feeds", postgresql.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("definition_id", "question_id", name="uq_question_in_definition"),
    )

    # ─── question_dependencies ───────────────────────────────────────────────
    op.create_table(
        "question_dependencies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("definition_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("questionnaire_definitions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("parent_question_id", sa.String(20), nullable=False),
        sa.Column("trigger_value", sa.String(100), nullable=False),
        sa.Column("child_question_id", sa.String(20), nullable=True),
        sa.Column("effect", postgresql.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # ─── definition_change_log ───────────────────────────────────────────────
    op.create_table(
        "definition_change_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("definition_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("questionnaire_definitions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(30), nullable=False),
        sa.Column("diff", postgresql.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # ─── context_questionnaires ──────────────────────────────────────────────
    op.create_table(
        "context_questionnaires",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("definition_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("questionnaire_definitions.id"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="in_progress"),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # ─── questionnaire_answers ───────────────────────────────────────────────
    op.create_table(
        "questionnaire_answers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("questionnaire_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("context_questionnaires.id", ondelete="CASCADE"), nullable=False),
        sa.Column("block", sa.String(2), nullable=False),
        sa.Column("question_id", sa.String(20), nullable=False),
        sa.Column("value", postgresql.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("questionnaire_id", "question_id", name="uq_answer_per_question"),
    )

    # ─── normative_profiles ──────────────────────────────────────────────────
    op.create_table(
        "normative_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("rgpd_applies", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("rgpd_special_categories", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("nis2_status", sa.String(20), nullable=True, server_default="none"),
        sa.Column("ens_applies", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("ens_level", sa.String(10), nullable=True),
        sa.Column("dora_status", sa.String(20), nullable=True, server_default="none"),
        sa.Column("rationale", postgresql.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("project_id", name="uq_normative_profile_per_project"),
    )

    # ─── Seed: v1 published questionnaire definition ─────────────────────────
    _seed_v1_questionnaire()


def _seed_v1_questionnaire() -> None:
    """Insert the v1 questionnaire definition with questions A1-A7, B1-B2b_det, C1-C2, D1-D_fin."""
    bind = op.get_bind()
    now = datetime.now(timezone.utc)
    defn_id = uuid.UUID("00000000-0001-0001-0001-000000000001")

    # Insert definition (already published)
    bind.execute(
        sa.text("""
            INSERT INTO questionnaire_definitions (id, version, status, published_at, notes, created_at, updated_at)
            VALUES (:id, :version, :status, :published_at, :notes, :now, :now)
        """),
        {
            "id": str(defn_id),
            "version": 1,
            "status": "published",
            "published_at": now.isoformat(),
            "notes": "Cuestionario v1 ISO 31000 — bloques A (RGPD/NIS2/ENS/DORA), B (activos), C (amenazas), D (impacto)",
            "now": now.isoformat(),
        },
    )

    # ── Block A: normativo ────────────────────────────────────────────────────
    questions = [
        # id, block, question_id, text, type, options, order, feeds
        (
            "A", "A1",
            "¿La organización trata datos de carácter personal (clientes, empleados, proveedores)?",
            "single_choice",
            ["yes", "no"],
            1,
            ["rgpd_applies"],
        ),
        (
            "A", "A2",
            "¿Se tratan categorías especiales de datos (salud, biometría, origen racial, opiniones políticas, etc.)?",
            "single_choice",
            ["yes", "no"],
            2,
            ["rgpd_special_categories"],
        ),
        (
            "A", "A3",
            "¿La organización opera en un sector regulado por NIS2 (energía, transporte, banca, infraestructura digital…)?",
            "single_choice",
            ["none", "important", "essential"],
            3,
            ["nis2_status"],
        ),
        (
            "A", "A4",
            "¿La organización es proveedor directo de una entidad esencial o importante según NIS2?",
            "single_choice",
            ["yes", "no"],
            4,
            ["nis2_status"],
        ),
        (
            "A", "A5",
            "¿La organización presta servicios TIC a entidades financieras reguladas por DORA?",
            "single_choice",
            ["none", "contractual", "latent"],
            5,
            ["dora_status"],
        ),
        (
            "A", "A6",
            "¿Los sistemas de la organización tratan o almacenan información del sector público (Administración)?",
            "single_choice",
            ["yes", "no"],
            6,
            ["ens_applies"],
        ),
        (
            "A", "A7",
            "¿Cuál es el nivel de categoría ENS requerido para sus sistemas?",
            "single_choice",
            ["basic", "medium", "high"],
            7,
            ["ens_level"],
        ),
    ]

    # ── Block B: activos ──────────────────────────────────────────────────────
    questions += [
        (
            "B", "B1",
            "¿Cuántos empleados tiene la organización?",
            "single_choice",
            ["1-10", "11-50", "51-250", "251+"],
            1,
            ["org_size"],
        ),
        (
            "B", "B2a",
            "¿Cuáles son los tipos de activos TIC principales? (selección múltiple)",
            "multi_choice",
            ["servidores_propios", "cloud_publica", "cloud_hibrida", "saas_terceros", "ot_scada", "dispositivos_moviles"],
            2,
            ["asset_types"],
        ),
        (
            "B", "B2b",
            "¿La organización dispone de infraestructura en la nube pública?",
            "single_choice",
            ["yes", "no"],
            3,
            ["cloud_exposure"],
        ),
        (
            "B", "B2b_det",
            "¿Qué proveedor(es) cloud utiliza principalmente?",
            "multi_choice",
            ["aws", "azure", "gcp", "otros"],
            4,
            ["cloud_providers"],
        ),
    ]

    # ── Block C: amenazas ─────────────────────────────────────────────────────
    questions += [
        (
            "C", "C1",
            "¿Ha sufrido la organización algún incidente de seguridad en los últimos 12 meses?",
            "single_choice",
            ["yes", "no", "unknown"],
            1,
            ["incident_history"],
        ),
        (
            "C", "C2",
            "¿Cuáles son las principales amenazas percibidas? (selección múltiple)",
            "multi_choice",
            ["ransomware", "phishing", "insider", "ddos", "supply_chain", "apt", "accidental"],
            2,
            ["threat_landscape"],
        ),
    ]

    # ── Block D: impacto ──────────────────────────────────────────────────────
    questions += [
        (
            "D", "D1",
            "¿Cuál sería el impacto estimado de una interrupción total de sistemas durante 24h?",
            "single_choice",
            ["bajo", "medio", "alto", "critico"],
            1,
            ["business_impact"],
        ),
        (
            "D", "D_fin",
            "¿Cuál es el volumen aproximado de facturación anual?",
            "single_choice",
            ["menos_1M", "1M_10M", "10M_50M", "mas_50M"],
            2,
            ["revenue_band"],
        ),
        (
            "D", "D_sal",
            "¿Cuántas personas dependen operativamente de los sistemas TIC?",
            "single_choice",
            ["1-10", "11-50", "51-250", "251+"],
            3,
            ["operational_dependency"],
        ),
        (
            "D", "D_pub",
            "¿La organización presta servicios directamente al público en general?",
            "single_choice",
            ["yes", "no"],
            4,
            ["public_exposure"],
        ),
    ]

    for block, qid, text, qtype, options, order, feeds in questions:
        bind.execute(
            sa.text("""
                INSERT INTO question_definitions
                  (id, definition_id, block, question_id, text, type, options, "order", feeds, created_at, updated_at)
                VALUES
                  (:id, :did, :block, :qid, :text, :type, :options, :order, :feeds, :now, :now)
            """),
            {
                "id": str(uuid.uuid4()),
                "did": str(defn_id),
                "block": block,
                "qid": qid,
                "text": text,
                "type": qtype,
                "options": __import__("json").dumps(options),
                "order": order,
                "feeds": __import__("json").dumps(feeds),
                "now": now.isoformat(),
            },
        )

    # ── Dependencies ─────────────────────────────────────────────────────────
    deps = [
        # A2 shown only when A1=yes
        ("A1", "yes", "A2", None),
        # A4 shown only when A3=none (not a direct NIS2 entity — check supply chain)
        ("A3", "none", "A4", None),
        # A7 shown only when A6=yes
        ("A6", "yes", "A7", None),
        # B2b_det (cloud providers detail) shown only when B2b=yes
        ("B2b", "yes", "B2b_det", None),
    ]

    for parent_qid, trigger_val, child_qid, effect in deps:
        bind.execute(
            sa.text("""
                INSERT INTO question_dependencies
                  (id, definition_id, parent_question_id, trigger_value, child_question_id, effect, created_at, updated_at)
                VALUES
                  (:id, :did, :parent, :trigger, :child, :effect, :now, :now)
            """),
            {
                "id": str(uuid.uuid4()),
                "did": str(defn_id),
                "parent": parent_qid,
                "trigger": trigger_val,
                "child": child_qid,
                "effect": __import__("json").dumps(effect),
                "now": now.isoformat(),
            },
        )


def downgrade() -> None:
    op.drop_table("normative_profiles")
    op.drop_table("questionnaire_answers")
    op.drop_table("context_questionnaires")
    op.drop_table("definition_change_log")
    op.drop_table("question_dependencies")
    op.drop_table("question_definitions")
    op.drop_table("questionnaire_definitions")
