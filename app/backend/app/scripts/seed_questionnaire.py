"""
Seed the TFM questionnaire (ISO 31000 context — F2).

Creates and publishes v1 with the 4 blocks (A–D) if no published definition
exists yet. Safe to re-run: skips if a published definition is already present.

Question IDs match the rule engine in modules/context/normative/rules.py:
  A1–A7  → derive the NormativeProfile fields
  C1/C2  → feed derive_exposed_data() in mapping/service.py
  D_pub  → feeds public_exposure in derive_exposed_data()
"""
import asyncio

from sqlalchemy import func, select

from app.database import AsyncSessionLocal
from app.modules.admin.catalog.models import (
    QuestionDefinition,
    QuestionDependency,
    QuestionnaireDefinition,
)


# ─── Question catalogue (Block A–D) ──────────────────────────────────────────

QUESTIONS: list[dict] = [
    # ── Block A: Normativa y perfil de la organización (A1–A7) ───────────────
    {
        "block": "A", "question_id": "A1", "order": 10,
        "text": "¿La organización trata datos personales de ciudadanos de la UE o del EEE?",
        "type": "single_choice",
        "options": ["Sí", "No"],
        "feeds": ["rgpd_applies"],
    },
    {
        "block": "A", "question_id": "A2", "order": 20,
        "text": (
            "¿Los datos que trata incluyen categorías especiales según el art. 9 RGPD "
            "(datos de salud, biométricos, genéticos, religiosos o políticos)?"
        ),
        "type": "single_choice",
        "options": ["Sí", "No"],
        "feeds": ["rgpd_special_categories"],
    },
    {
        "block": "A", "question_id": "A3", "order": 30,
        "text": (
            "Seleccione la clasificación NIS2 (Directiva EU 2022/2555) que corresponde "
            "a la organización según sus Anexos I y II:"
        ),
        "type": "single_choice",
        "options": ["Operador esencial", "Entidad importante", "No aplica"],
        "feeds": ["nis2_status"],
    },
    {
        "block": "A", "question_id": "A4", "order": 40,
        "text": (
            "¿La organización actúa como proveedor directo de un operador esencial "
            "o entidad importante bajo NIS2?"
        ),
        "type": "single_choice",
        "options": ["Sí", "No"],
        "feeds": ["nis2_status"],
    },
    {
        "block": "A", "question_id": "A5", "order": 50,
        "text": (
            "Indique la exposición de la organización al Reglamento DORA (EU 2022/2554 "
            "— Digital Operational Resilience Act):"
        ),
        "type": "single_choice",
        "options": [
            "Entidad financiera regulada",
            "Proveedor TIC de entidad financiera",
            "No aplica",
        ],
        "feeds": ["dora_status"],
    },
    {
        "block": "A", "question_id": "A6", "order": 60,
        "text": (
            "¿Los sistemas de información de la organización están sujetos al Esquema "
            "Nacional de Seguridad — ENS (RD 311/2022)?"
        ),
        "type": "single_choice",
        "options": ["Sí", "No"],
        "feeds": ["ens_applies"],
    },
    {
        "block": "A", "question_id": "A7", "order": 70,
        "text": "Indique el nivel ENS aplicable a los sistemas afectados:",
        "type": "single_choice",
        "options": ["Básico", "Medio", "Alto"],
        "feeds": ["ens_level"],
    },
    # ── Block B: Perfil de la organización ───────────────────────────────────
    {
        "block": "B", "question_id": "B1", "order": 10,
        "text": "¿Cuántos empleados tiene la organización?",
        "type": "single_choice",
        "options": ["Menos de 50", "50 a 249", "250 a 999", "1.000 o más"],
        "feeds": None,
    },
    {
        "block": "B", "question_id": "B2", "order": 20,
        "text": "¿Cuál es la facturación anual aproximada de la organización?",
        "type": "single_choice",
        "options": ["Menos de 2 M€", "2 a 10 M€", "10 a 50 M€", "Más de 50 M€"],
        "feeds": None,
    },
    {
        "block": "B", "question_id": "B3", "order": 30,
        "text": "¿Los procesos de negocio críticos dependen de sistemas TIC para su continuidad?",
        "type": "single_choice",
        "options": ["Sí, totalmente", "Sí, parcialmente", "No"],
        "feeds": None,
    },
    {
        "block": "B", "question_id": "B4", "order": 40,
        "text": "¿Con qué frecuencia se realizan auditorías o revisiones de seguridad?",
        "type": "single_choice",
        "options": ["Nunca", "Ocasionalmente", "Anualmente", "Continuamente"],
        "feeds": None,
    },
    # ── Block C: Datos y tratamiento (C1/C2 usados por mapping service) ──────
    {
        "block": "C", "question_id": "C1", "order": 10,
        "text": (
            "¿Ha sufrido la organización incidentes de ciberseguridad en los últimos 24 meses "
            "que hayan requerido notificación a autoridades competentes?"
        ),
        "type": "single_choice",
        "options": ["Sí, con notificación regulatoria", "Sí, sin notificación", "No"],
        "feeds": ["incident_history"],
    },
    {
        "block": "C", "question_id": "C2", "order": 20,
        "text": "¿Cuáles son las principales amenazas que percibe la organización sobre sus activos TIC? (puede seleccionar varias)",
        "type": "multi_choice",
        "options": [
            "Ransomware",
            "Phishing / ingeniería social",
            "Insider threat",
            "APT / espionaje industrial",
            "DDoS",
            "Vulnerabilidades de software no parcheadas",
            "Ataques a la cadena de suministro",
        ],
        "feeds": ["threat_landscape"],
    },
    {
        "block": "C", "question_id": "C3", "order": 30,
        "text": "¿Qué tipos de datos personales gestiona la organización? (puede seleccionar varios)",
        "type": "multi_choice",
        "options": [
            "Identificativos (nombre, DNI, pasaporte)",
            "Datos de contacto (email, teléfono)",
            "Datos económicos o financieros",
            "Datos sanitarios",
            "Datos biométricos",
            "Datos de menores",
            "Datos de geolocalización",
        ],
        "feeds": None,
    },
    # ── Block D: Sector específico (D_pub usado por mapping service) ──────────
    {
        "block": "D", "question_id": "D1", "order": 10,
        "text": "¿En qué sector opera principalmente la organización?",
        "type": "single_choice",
        "options": [
            "Energía",
            "Transporte y logística",
            "Banca y finanzas",
            "Infraestructura digital",
            "Salud",
            "Administración pública",
            "Industria / manufactura",
            "Servicios profesionales",
            "Otro",
        ],
        "feeds": None,
    },
    {
        "block": "D", "question_id": "D2", "order": 20,
        "text": "¿Dispone la organización de un Sistema de Gestión de Seguridad de la Información (SGSI)?",
        "type": "single_choice",
        "options": [
            "Sí, ISO 27001 certificado",
            "Sí, ISO 27001 en implantación",
            "Sí, ENS certificado",
            "Sistema propio documentado",
            "No",
        ],
        "feeds": None,
    },
    {
        "block": "D", "question_id": "D_pub", "order": 30,
        "text": "¿Los sistemas y servicios de la organización tienen exposición pública a Internet?",
        "type": "single_choice",
        "options": ["yes", "no"],
        "feeds": ["public_exposure"],
    },
    {
        "block": "D", "question_id": "D3", "order": 40,
        "text": "Valore el nivel de madurez en ciberseguridad de la organización (1 = inicial, 5 = optimizado):",
        "type": "range",
        "options": None,
        "feeds": None,
    },
]

# Visible only when parent answer matches trigger_value
DEPENDENCIES: list[dict] = [
    # A2 only shown if processing personal data (A1=Sí)
    {
        "parent_question_id": "A1",
        "trigger_value": "Sí",
        "child_question_id": "A2",
        "effect": None,
    },
    # A4 only shown if NOT already a NIS2 entity (A3=No aplica)
    {
        "parent_question_id": "A3",
        "trigger_value": "No aplica",
        "child_question_id": "A4",
        "effect": None,
    },
    # A7 only shown if ENS applies (A6=Sí)
    {
        "parent_question_id": "A6",
        "trigger_value": "Sí",
        "child_question_id": "A7",
        "effect": None,
    },
]


# ─── Seed entry point ─────────────────────────────────────────────────────────


async def main() -> None:
    async with AsyncSessionLocal() as db:
        # Skip if a published definition already exists
        existing = (
            await db.execute(
                select(func.count(QuestionnaireDefinition.id)).where(
                    QuestionnaireDefinition.status == "published"
                )
            )
        ).scalar() or 0

        if existing > 0:
            print(f"Seed questionnaire skipped — {existing} published definition(s) already exist.")
            return

        # Create draft
        defn = QuestionnaireDefinition(
            status="draft",
            notes="TFM ISO 31000 — v1 inicial (seed automático)",
        )
        db.add(defn)
        await db.flush()

        # Add questions
        for q in QUESTIONS:
            db.add(
                QuestionDefinition(
                    definition_id=defn.id,
                    block=q["block"],
                    question_id=q["question_id"],
                    text=q["text"],
                    type=q["type"],
                    options=q["options"],
                    order=q["order"],
                    feeds=q["feeds"],
                )
            )

        # Add dependencies
        for dep in DEPENDENCIES:
            db.add(
                QuestionDependency(
                    definition_id=defn.id,
                    parent_question_id=dep["parent_question_id"],
                    trigger_value=dep["trigger_value"],
                    child_question_id=dep["child_question_id"],
                    effect=dep["effect"],
                )
            )

        await db.flush()

        # Publish directly (bypasses validate since we trust the seed data)
        from datetime import datetime, timezone
        from sqlalchemy import func as sqlfunc

        max_v = (
            await db.execute(
                select(sqlfunc.max(QuestionnaireDefinition.version)).where(
                    QuestionnaireDefinition.status == "published"
                )
            )
        ).scalar() or 0

        defn.status = "published"
        defn.version = max_v + 1
        defn.published_at = datetime.now(timezone.utc)

        await db.commit()
        print(
            f"Seed questionnaire complete: v{defn.version} published "
            f"({len(QUESTIONS)} questions, {len(DEPENDENCIES)} dependencies)."
        )


if __name__ == "__main__":
    asyncio.run(main())
