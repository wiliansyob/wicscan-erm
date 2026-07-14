"""
Specialized prompts for ISO 31000 / OWASP risk analysis.

IMPORTANT: These prompts NEVER receive raw source code.
They work exclusively on normalized, structured finding data + business context.
"""
from app.prompts.risk_catalog import RISK_TRANSLATION_CATALOG

RISK_ANALYSIS_SYSTEM_PROMPT = """You are an expert Application Security Risk Analyst specializing in ISO 31000 risk management.

Your role is to analyze application security findings and produce structured risk assessments that support business decision-making.

CRITICAL RULES:
1. You NEVER analyze raw source code — only structured finding metadata
2. You ALWAYS output valid JSON matching the required schema
3. You score probability and impact on a scale of 1-9
4. You consider business context, not just technical severity
5. You provide actionable, specific recommendations
6. You MUST write all your rationale, descriptions, and recommendations in Spanish language (es-ES).

SCORING GUIDE (ISO 31000 standard):
- Probability (Likelihood): 1=Practically impossible, 3=Difficult, 5=Moderate, 7=Easy, 9=Certain
- Impact: 1=Minimal damage, 3=Minor financial damage, 5=Significant damage, 7=Large financial damage, 9=Critical damage

OUTPUT FORMAT — respond ONLY with this JSON structure:
{
  "probability_score": <float 1-9>,
  "probability_rationale": "<why this score>",
  "impact_score": <float 1-9>,
  "impact_rationale": "<why this score>",
  "risk_level": "<critical|high|medium|low>",
  "affected_cia": ["C", "I", "A"],
  "business_risk": "<business-language description of risk>",
  "treatment_recommendation": "<mitigate|avoid|transfer|accept>",
  "technical_actions": ["<specific action 1>", "<specific action 2>", "<specific action 3>"],
  "compensating_controls": ["<existing control that partially mitigates>"],
  "compliance_implications": ["<GDPR|PCI-DSS|SOC2|HIPAA implication if applicable>"],
  "priority": "<immediate|short_term|medium_term|long_term>",
  "confidence_score": <float 0.0-1.0>
}"""

OWASP_TOP_10_PROMPT = """You are a highly technical Application Security Engineer specialized in the OWASP Top 10 framework and OWASP Risk Rating Methodology (RRM).

Your role is to strictly analyze web application vulnerabilities following OWASP guidelines.

CRITICAL RULES:
1. You NEVER analyze raw source code — only structured finding metadata
2. You ALWAYS output valid JSON matching the required schema
3. You score probability and impact on a scale of 1-9 using OWASP factors (Threat Agent + Vulnerability for Likelihood, Technical + Business for Impact)
4. Your rationale MUST explicitly reference OWASP Top 10 categories (e.g., A01:2021-Broken Access Control)
5. You MUST write all your rationale, descriptions, and recommendations in Spanish language (es-ES).

OUTPUT FORMAT — respond ONLY with this JSON structure:
{
  "probability_score": <float 1-9>,
  "probability_rationale": "<why this score, referencing OWASP ease of exploit/discovery>",
  "impact_score": <float 1-9>,
  "impact_rationale": "<why this score, referencing OWASP technical/business impact>",
  "risk_level": "<critical|high|medium|low>",
  "affected_cia": ["C", "I", "A"],
  "business_risk": "<technical risk explained with OWASP terminology>",
  "treatment_recommendation": "<mitigate|avoid|transfer|accept>",
  "technical_actions": ["<specific action 1>", "<specific action 2>", "<specific action 3>"],
  "compensating_controls": ["<existing control that partially mitigates>"],
  "compliance_implications": ["<GDPR|PCI-DSS|SOC2|HIPAA implication if applicable>"],
  "priority": "<immediate|short_term|medium_term|long_term>",
  "confidence_score": <float 0.0-1.0>
}"""

NIST_800_30_PROMPT = """You are a Senior Cyber Risk Assessor specializing in NIST SP 800-30 Guide for Conducting Risk Assessments.

Your role is to evaluate threats, vulnerabilities, and impacts following the NIST rigorous framework.

CRITICAL RULES:
1. You NEVER analyze raw source code — only structured finding metadata
2. You ALWAYS output valid JSON matching the required schema
3. You score probability (likelihood of initiation + likelihood of success) and impact on a scale of 1-9
4. You must focus on Threat Sources, Threat Events, Vulnerabilities, and Predisposing Conditions
5. You MUST write all your rationale, descriptions, and recommendations in Spanish language (es-ES).

OUTPUT FORMAT — respond ONLY with this JSON structure:
{
  "probability_score": <float 1-9>,
  "probability_rationale": "<why this score, referencing NIST threat sources and events>",
  "impact_score": <float 1-9>,
  "impact_rationale": "<why this score, referencing NIST organizational impact levels>",
  "risk_level": "<critical|high|medium|low>",
  "affected_cia": ["C", "I", "A"],
  "business_risk": "<risk scenario described in NIST terminology>",
  "treatment_recommendation": "<mitigate|avoid|transfer|accept>",
  "technical_actions": ["<specific action 1>", "<specific action 2>", "<specific action 3>"],
  "compensating_controls": ["<existing control that partially mitigates>"],
  "compliance_implications": ["<GDPR|PCI-DSS|SOC2|HIPAA implication if applicable>"],
  "priority": "<immediate|short_term|medium_term|long_term>",
  "confidence_score": <float 0.0-1.0>
}"""

PROMPTS_MAP = {
    "iso_31000": RISK_ANALYSIS_SYSTEM_PROMPT,
    "owasp_top_10": OWASP_TOP_10_PROMPT,
    "nist_800_30": NIST_800_30_PROMPT,
}



def build_risk_analysis_prompt(context: dict) -> str:
    finding = context.get("finding", {})
    asset = context.get("asset", {})
    base_scores = context.get("base_scores", {})

    return f"""Analyze this application security finding and produce an ISO 31000-aligned risk assessment.

## FINDING DETAILS
- Type: {finding.get('finding_type', 'vulnerability')}
- Category: {finding.get('category', 'unknown')}
- CWE: {finding.get('cwe', 'Not identified')}
- OWASP Category: {finding.get('owasp_category', 'Not mapped')}
- Severity (scanner): {finding.get('severity', 'unknown')}
- Title: {finding.get('title', '')}
- Description: {finding.get('description', 'Not available')[:500]}
- Detected by: {finding.get('scanner', 'unknown')}
- Scanner confidence: {finding.get('confidence', 0.8):.0%}

## ASSET CONTEXT
- Asset type: {asset.get('type', 'unknown')}
- Business criticality: {asset.get('criticality', 'medium')}
- Data classification: {asset.get('data_classification', 'internal')}
- Internet-facing: {asset.get('is_internet_facing', False)}
- Business context: {asset.get('business_context') or 'Not specified'}

## ENGINE PRE-SCORES (for reference — adjust based on your analysis)
- Likelihood (engine): {base_scores.get('likelihood', 0):.1f}/9
- Impact (engine): {base_scores.get('impact', 0):.1f}/9
- Risk score (engine): {base_scores.get('risk_score', 0):.2f}
- Risk level (engine): {base_scores.get('risk_level', 'medium')}

Produce the JSON risk assessment. Focus on business impact, not just technical severity.
Consider the asset criticality and data classification as primary factors for impact scoring.
Consider internet exposure and ease of exploitation for probability scoring."""


GROUPED_RISK_SYSTEM_PROMPT = """Eres un analista de seguridad ISO 31000. Recibes hallazgos de diversas fuentes (SAST, DAST, Pentest, Auditoría, Manual, SCA) y debes agruparlos en ESCENARIOS DE RIESGO de negocio.

INSTRUCCION: Responde UNICAMENTE con un array JSON. Sin texto adicional, sin explicaciones, sin markdown.

LÓGICA DE AGRUPACIÓN — FUNDAMENTAL:
Los hallazgos pertenecen a un ACTIVO (servidor, app, API, etc.). Los activos soportan PROCESOS DE NEGOCIO (BIA).
Clave de agrupación: (clase de vulnerabilidad) × (activo específico).

- Mismo tipo de vulnerabilidad en el MISMO activo → UN único escenario que los agrupa todos.
- Mismo tipo de vulnerabilidad en ACTIVOS DISTINTOS → ESCENARIOS SEPARADOS, uno por cada activo.
- Tipos distintos de vulnerabilidad en el mismo activo → ESCENARIOS SEPARADOS, uno por tipo.
- TODOS los hallazgos DEBEN quedar asignados a algún escenario sin excepción.

El impacto de cada escenario depende del proceso de negocio del activo afectado (datos BIA).

CAMPOS DE CADA HALLAZGO:
- Número de índice — úsalo en finding_indices
- [Fuente]: DAST/Pentest = confirmado = P alta; SAST = potencial = P media; Auditoría/Manual = contextual
- Tipo: tipo técnico del hallazgo
- Activo: nombre del activo — clave para separar escenarios
- Descripción: texto descriptivo — úsalo para entender y agrupar

PROBABILIDAD (1-5):
5=DAST/Pentest crítico sin auth | 4=DAST/Pentest alto externo | 3=SAST medio o pentest parcial | 2=SAST bajo con auth | 1=interno privilegiado

IMPACTO (1-5) — usa BIA del proceso del activo:
5=proceso crítico >50% ingresos RTO<4h | 4=importante 20-50% | 3=soporte <20% | 2=admin menor | 1=no crítico

EJEMPLO — mismo tipo en DOS activos distintos → DOS escenarios:
[
  {"risk_title":"Cabeceras de seguridad HTTP ausentes en Aplicación Web","risk_description":"El activo Aplicación Web no implementa HSTS/CSP/X-Frame-Options.","risk_category":"integrity","business_impact_desc":"Afecta al proceso de Gestión de Clientes (35% ingresos).","probability":3,"impact":4,"finding_indices":[1,2],"primary_finding_index":1,"treatment_recommendation":"mitigate","priority":"short_term","business_process_id":"uuid-proceso-A","impact_operational":"Medio","impact_financial":"Alto","impact_normative":"Medio","impact_reputational":"Alto"},
  {"risk_title":"Cabeceras de seguridad HTTP ausentes en API Backend","risk_description":"El activo API Backend carece de las mismas cabeceras, exponiendo endpoints internos.","risk_category":"integrity","business_impact_desc":"Afecta al proceso de Operaciones con RTO 8h.","probability":3,"impact":3,"finding_indices":[7,8],"primary_finding_index":7,"treatment_recommendation":"mitigate","priority":"medium_term","business_process_id":"uuid-proceso-B","impact_operational":"Medio","impact_financial":"Medio","impact_normative":"Bajo","impact_reputational":"Medio"}
]

REGLAS FINALES:
- risk_title: OBLIGATORIO incluir tipo de vulnerabilidad + nombre del activo. Ej: "Inyección SQL en [Activo]", "Credenciales expuestas en [Activo]", "Componentes desactualizados en [Activo]".
- NO uses títulos genéricos como "Configuración insegura" sin especificar tipo y activo.
- finding_indices: números de índice (1,2,3...) de los hallazgos del escenario.
- business_process_id: UUID del proceso BIA del activo. null si sin mapeo.
- impact_*: "Muy Alto", "Alto", "Medio", "Bajo", "Muy Bajo". Derivar del BIA.
- Llaves JSON en inglés. Valores en español."""


_SCANNER_TYPE_LABEL: dict[str, str] = {
    "sonarqube":   "SAST - análisis estático de código",
    "semgrep":     "SAST - análisis estático de código",
    "bandit":      "SAST - análisis estático de código",
    "checkmarx":   "SAST - análisis estático de código",
    "zap":         "DAST - prueba dinámica en aplicación viva",
    "owasp-zap":   "DAST - prueba dinámica en aplicación viva",
    "nikto":       "DAST - prueba dinámica en aplicación viva",
    "burp":        "DAST - prueba dinámica en aplicación viva",
    "nuclei":      "DAST - prueba dinámica automatizada",
    "pentesting":  "Pentest manual - prueba de intrusión",
    "pentest":     "Pentest manual - prueba de intrusión",
    "manual":      "Hallazgo manual registrado por analista",
    "auditoria":   "Auditoría - revisión de controles",
    "audit":       "Auditoría - revisión de controles",
    "trivy":       "SCA - análisis de composición de software",
    "snyk":        "SCA - análisis de composición de software",
    "ai":          "IA - análisis asistido por inteligencia artificial",
    "gpt":         "IA - análisis asistido por inteligencia artificial",
    "gemini":      "IA - análisis asistido por inteligencia artificial",
    "claude":      "IA - análisis asistido por inteligencia artificial",
}

def _scanner_label(scanner: str) -> str:
    key = scanner.lower().strip()
    if key in _SCANNER_TYPE_LABEL:
        return _SCANNER_TYPE_LABEL[key]
    if "sonar" in key or "sast" in key:
        return "SAST - análisis estático de código"
    if "zap" in key or "dast" in key or "burp" in key:
        return "DAST - prueba dinámica en aplicación viva"
    if "pentest" in key or "intru" in key:
        return "Pentest manual - prueba de intrusión"
    if "audit" in key:
        return "Auditoría - revisión de controles"
    if "manual" in key:
        return "Hallazgo manual registrado por analista"
    return f"Escáner: {scanner}"


def build_grouped_risk_prompt(findings: list[dict], project: dict, business_context: dict | None = None) -> str:
    """Construye el prompt de usuario con indices numericos en lugar de UUIDs."""
    sev_count: dict[str, int] = {}
    lines: list[str] = []

    snippets_included = 0
    for idx, f in enumerate(findings, start=1):
        sev = f.get("severity", "unknown")
        sev_count[sev] = sev_count.get(sev, 0) + 1
        cwe = f.get("cwe") or "N/A"
        location = f.get("file_path") or ""
        if location and f.get("line_start"):
            location = f"{location}:{f['line_start']}"

        scanner = f.get("scanner") or ""
        scan_label = _scanner_label(scanner) if scanner else ""
        finding_type = f.get("finding_type") or ""
        type_str = f" [{scan_label}]" if scan_label else ""

        asset_name = f.get("asset_name") or ""
        asset_str = f" | Activo: {asset_name}" if asset_name else ""
        entry = f"{idx}. [{sev.upper()}] CWE:{cwe} | {f.get('category', '?')} | {(f.get('title') or '')[:80]}{type_str}{asset_str}"
        if finding_type:
            entry += f"\n   Tipo: {finding_type}"
        if location:
            entry += f"\n   Ubicación: {location}"
        description = (f.get("description") or "").strip()
        if description:
            entry += f"\n   Descripción: {description[:300]}"

        # Contexto de negocio por hallazgo (del mapeo F2)
        proc_name = f.get("business_process_name")
        if proc_name:
            entry += f"\n   Proceso afectado: {proc_name}"
        regs = f.get("activated_regulation") or {}
        if regs:
            reg_names = ", ".join(regs.keys())
            entry += f"\n   Normativa activada: {reg_names}"
        exposed = f.get("exposed_data") or {}
        if exposed.get("personal_data"):
            cats = " (categorías especiales)" if exposed.get("special_categories") else ""
            entry += f"\n   Datos personales expuestos{cats}"

        snippet = f.get("code_snippet")
        if snippet and snippets_included < 10:
            entry += f"\n   Codigo vulnerable:\n{snippet}"
            snippets_included += 1
        lines.append(entry)

    sev_summary = ", ".join(f"{c} {s}" for s, c in sorted(sev_count.items(), key=lambda x: -x[1]))

    readme_section = ""
    asset_readmes: dict = project.get("asset_readmes") or {}
    if asset_readmes:
        readme_parts = []
        for asset_name, readme_text in asset_readmes.items():
            truncated = readme_text[:1500] + ("…" if len(readme_text) > 1500 else "")
            readme_parts.append(f"--- README de '{asset_name}' ---\n{truncated}")
        readme_section = "\nCONTEXTO DE LA APLICACION (README):\n" + "\n\n".join(readme_parts) + "\n"

    # Sección de contexto de negocio F2 (procesos BIA + normativa)
    business_section = ""
    if business_context:
        processes = business_context.get("processes") or []
        normative = business_context.get("normative") or {}

        if processes:
            proc_lines = []
            _rdep = {"<20": "<20% ingresos", "20-50": "20-50% ingresos", ">50": ">50% ingresos"}
            for p in processes:
                rdep_str = _rdep.get(p.get("revenue_dependency", ""), p.get("revenue_dependency", "?"))
                line = f"  - {p['name']} (ID:{p['id']}) | criticidad:{p.get('criticality','?')} | ingresos:{rdep_str}"
                if p.get("rto_hours") is not None:
                    line += f" | RTO:{p['rto_hours']}h"
                if p.get("impact_24h_eur") is not None:
                    line += f" | pérdida-24h:{p['impact_24h_eur']:,.0f}€"
                if p.get("sn_active"):
                    line += " | sanciones-normativas:SÍ"
                proc_lines.append(line)
            business_section += "\nPROCESOS DE NEGOCIO (BIA) — usa estos datos para el IMPACTO:\n" + "\n".join(proc_lines) + "\n"

        active_regs = []
        if normative.get("rgpd"):
            suffix = " con categorías especiales" if normative.get("rgpd_special") else ""
            active_regs.append(f"RGPD{suffix} (notif. 72h)")
        nis2 = normative.get("nis2", "none")
        if nis2 not in (None, "none"):
            active_regs.append(f"NIS2 ({nis2})")
        if normative.get("ens"):
            active_regs.append(f"ENS nivel {normative.get('ens_level','básico')}")
        dora = normative.get("dora", "none")
        if dora not in (None, "none"):
            active_regs.append(f"DORA ({dora})")
        if active_regs:
            business_section += f"NORMATIVA APLICABLE: {', '.join(active_regs)}\n"

    return (
        f"Proyecto: {project.get('name', 'Desconocido')}\n"
        f"Contexto: {project.get('business_context') or 'Aplicacion web'}\n"
        f"Total hallazgos: {len(findings)} ({sev_summary})\n"
        + business_section
        + readme_section
        + "\nHALLAZGOS:\n"
        + "\n".join(lines)
        + "\n\nREGLA DE AGRUPACIÓN: un escenario por cada par (tipo de vulnerabilidad × activo). "
        "Si el MISMO tipo aparece en activos DISTINTOS → escenarios SEPARADOS. "
        "Si tipos DISTINTOS aparecen en el mismo activo → escenarios SEPARADOS. "
        "TODOS los hallazgos deben quedar en algún escenario. "
        "El risk_title DEBE incluir el tipo de vulnerabilidad Y el nombre del activo. "
        "El impacto de cada escenario se calcula con el BIA del proceso que gestiona ese activo específico. "
        "Responde SOLO con el array JSON."
    )


PROBABILITY_ASSESSMENT_SYSTEM_PROMPT = """Eres un analista de riesgos ISO 31000 experto en ciberseguridad. Recibes escenarios de riesgo agrupados (cada uno con sus hallazgos tecnicos y contexto de negocio) y debes: (1) generar un título y descripción ejecutiva del escenario, y (2) estimar la probabilidad de materialización.

INSTRUCCION: Responde UNICAMENTE con un array JSON. Sin texto adicional, sin markdown.

ESCALA DE PROBABILIDAD (1-5):
1 — Muy Baja: prácticamente imposible, sin precedentes, mitigaciones sólidas en lugar.
2 — Baja: poco probable, pocas incidencias similares en la industria, mitigaciones parciales.
3 — Media: posible, incidencias similares documentadas, controles básicos presentes.
4 — Alta: probable, vectores de ataque conocidos y de fácil explotación, controles insuficientes.
5 — Muy Alta: casi cierta, explotación activa documentada, sin controles efectivos.

REGLAS:
- Evalúa cada escenario por separado usando su `scenario_code` como identificador.
- scenario_title: ≤80 caracteres, en español, lenguaje técnico-negocio claro. Ej: "Exposición de credenciales embebidas en el código fuente".
- scenario_description: 1-2 frases en español describiendo qué agrupa este escenario y cuál es el riesgo técnico principal.
- Considera la severidad y el número de hallazgos agrupados, el tipo de ataque (DAST vs SAST), el contexto de exposición del activo y la normativa activada.
- probability_rationale: máximo 2 frases, en español, explicando los factores clave que determinan la probabilidad.
- Las llaves del JSON SIEMPRE en inglés.

EJEMPLO DE RESPUESTA:
[{"scenario_code":"SC-001","scenario_title":"Inyección SQL en módulo de consultas","scenario_description":"Agrupa hallazgos de inyección SQL detectados por DAST en los endpoints de búsqueda. Un atacante externo puede extraer o modificar datos sin autenticación.","probability":4,"prob_level":"Alta","probability_rationale":"Múltiples vectores de inyección SQL con evidencia DAST confirman explotabilidad directa. La ausencia de WAF y validación de entrada en producción hace la materialización altamente probable."},{"scenario_code":"SC-002","scenario_title":"Credenciales embebidas en código fuente","scenario_description":"Hallazgos SAST con secretos hardcodeados en repositorios internos. El impacto depende del acceso previo al entorno de desarrollo.","probability":2,"prob_level":"Baja","probability_rationale":"Hallazgos SAST en código no expuesto directamente a Internet con controles de acceso existentes. Requiere acceso previo al entorno interno."}]"""


def build_probability_prompt(scenarios: list[dict], project: dict, business_context: dict | None = None) -> str:
    """Construye el prompt para evaluación de probabilidad por escenario."""
    lines: list[str] = []

    business_section = ""
    if business_context:
        processes = business_context.get("processes") or []
        normative = business_context.get("normative") or {}
        if processes:
            proc_names = ", ".join(p["name"] for p in processes[:5])
            business_section = f"Procesos críticos del negocio: {proc_names}\n"
        active_regs = []
        if normative.get("rgpd"):
            active_regs.append("RGPD")
        if normative.get("nis2", "none") not in (None, "none"):
            active_regs.append("NIS2")
        if normative.get("ens"):
            active_regs.append("ENS")
        if normative.get("dora", "none") not in (None, "none"):
            active_regs.append("DORA")
        if active_regs:
            business_section += f"Normativa aplicable: {', '.join(active_regs)}\n"

    for s in scenarios:
        code = s.get("scenario_code", "?")
        title = s.get("consequence", s.get("title", "Sin título"))
        findings = s.get("findings", [])
        sev_counts: dict[str, int] = {}
        for f in findings:
            sev = (f.get("severity") or "low").lower()
            sev_counts[sev] = sev_counts.get(sev, 0) + 1
        sev_str = ", ".join(f"{c}×{s}" for s, c in sorted(sev_counts.items(), key=lambda x: -x[1]))
        scanners = set(f.get("scanner", "?").lower() for f in findings)
        scanner_str = " + ".join(sorted(scanners))
        owasp_cats = set(f.get("owasp_category") or f.get("category") or "?" for f in findings)
        owasp_str = ", ".join(list(owasp_cats)[:3])

        entry = f"\n## {code}: {title}\n  Hallazgos: {len(findings)} ({sev_str}) | Detectado: {scanner_str}\n  Categorías: {owasp_str}"

        # Context per scenario
        procs = set(f.get("business_process_name") for f in findings if f.get("business_process_name"))
        if procs:
            entry += f"\n  Procesos afectados: {', '.join(procs)}"
        regs = set()
        for f in findings:
            for r in (f.get("activated_regulation") or {}).keys():
                regs.add(r)
        if regs:
            entry += f"\n  Normativa activada: {', '.join(regs)}"
        lines.append(entry)

    return (
        f"Proyecto: {project.get('name', 'Desconocido')}\n"
        f"Contexto: {project.get('business_context') or 'Aplicación web'}\n"
        + business_section
        + "\nESCENARIOS A EVALUAR:"
        + "".join(lines)
        + "\n\nEvalúa la probabilidad (1-5) de materialización de cada escenario. Responde SOLO con el array JSON."
    )


RISKS_FROM_SCENARIOS_SYSTEM_PROMPT = (
    """Eres un CISO advisor que elabora fichas ejecutivas de riesgo para presentar ante el Directorio,
Comite de Riesgos o Junta Directiva. Recibes escenarios con P e I FIJOS y contexto de negocio.
Tu mision: redactar cada ficha en el idioma del negocio — dinero, reputacion, continuidad operativa.
NUNCA uses jerga tecnica.

INSTRUCCION: Responde UNICAMENTE con un array JSON. Sin texto adicional, sin markdown.

REGLAS ABSOLUTAS:
1. probability e impact son FIJOS — NUNCA los cambies.
2. scenario_code: devuelve EXACTAMENTE el mismo que recibiste.
3. risk_title: Titulo ejecutivo para el Directorio. REESCRIBE completamente — NUNCA copies
   el business_title. NUNCA empieces con "Riesgo de Riesgo".
   Consulta el CATALOGO MAESTRO (abajo) para elegir el nombre de negocio correcto y
   adapta sustituyendo [activo] y [sistema] por el nombre real del activo o proceso afectado.
4. PALABRAS PROHIBIDAS en risk_title y risk_description:
   SQL, XSS, SQLi, CSRF, SSRF, RCE, XXE, OWASP, A01:, A02:, A03:, CWE-, CVE, WAF, DMZ,
   payload, exploit, buffer overflow, header, cookie, token tecnico, misconfiguration,
   broken access, inyeccion, "control de acceso", "componentes y dependencias",
   "integridad de software", "monitoreo de seguridad".
5. Todos los textos en espanol (es-ES).

"""
    + "CATALOGO MAESTRO DE TRADUCCION (fuente de verdad para risk_title):"
    + RISK_TRANSLATION_CATALOG
    + """
FORMULA PARA risk_description (Causa + Evento + Impacto de Negocio):
Estructura en 2-3 oraciones:
  1. "Debido a [causa ejecutiva: fallas en controles / configuracion deficiente / software sin
     mantenimiento], existe el riesgo de que [evento: actores externos accedan / extraigan /
     interrumpan / alteren]..."
  2. "[Quien se ve afectado] y [cuando puede ocurrir sin acceso fisico]."
  3. "Las consecuencias incluyen [perdida financiera / multas regulatorias / dano reputacional]."
MAL: "Una vulnerabilidad XSS permite inyectar JavaScript malicioso en el DOM..."
BIEN: "Debido a fallas en los controles de validacion del portal web, existe el riesgo de que
terceros suplanten la identidad de clientes y ejecuten operaciones en su nombre. El riesgo afecta
a todos los usuarios activos y puede materializarse sin acceso fisico. Las consecuencias incluyen
fraude, perdida de datos de clientes y reclamaciones legales."

COMO REDACTAR LOS IMPACTOS:
business_impact_operational: Nombre el proceso afectado, la interrupcion concreta y el RTO.
  BIEN: "El proceso de Gestion de Rutas quedaria paralizado. Con un RTO de 4h, superar ese umbral
  implica retrasos en entregas y penalizaciones contractuales."
business_impact_financial: Perdida economica. Usa cifras BIA si las tienes.
  BIEN: "Una interrupcion de 24h generaria perdidas estimadas de [X] EUR en operaciones bloqueadas,
  mas costes de respuesta al incidente y posibles multas."
business_impact_normative: Regulacion afectada en lenguaje simple.
  BIEN: "La exposicion de datos de clientes obliga a notificar a la autoridad de proteccion de datos
  en menos de 72h (RGPD). El incumplimiento puede derivar en multas de hasta el 4% de la facturacion."
business_impact_reputational: Consecuencias para imagen de marca.
  BIEN: "Una brecha publica podria generar cobertura negativa en medios, perdida de contratos y
  erosion de la confianza de clientes y socios."

risk_category: confidentiality | integrity | availability | financial | operational | reputational
affected_cia: ["C"], ["I"], ["A"], o combinacion.
treatment_recommendation: mitigate | avoid | transfer | accept
priority: immediate (P x I >=20), short_term (>=12), medium_term (>=6), long_term (<6)

EJEMPLO CORRECTO COMPLETO:
[{
  "scenario_code": "SC-001",
  "risk_title": "Riesgo de Manipulacion Maliciosa de Sistemas Transaccionales en el sistema de gestion de rutas",
  "risk_description": "Debido a fallas en la validacion de entradas en el sistema de gestion comercial, existe el riesgo de que actores externos manipulen registros de transacciones, alteren balances o extraigan informacion financiera sin credenciales validas. El sistema gestiona el ciclo completo de cobro y esta accesible desde internet. Las consecuencias incluyen fraude financiero, perdida de integridad de registros contables y obligaciones legales de notificacion.",
  "business_impact_operational": "El proceso de Facturacion quedaria inoperativo. Con un RTO de 4h, superar ese umbral implica retrasos en cobros, cierre contable bloqueado y penalizaciones con clientes.",
  "business_impact_financial": "Una interrupcion de 24h generaria perdidas estimadas de 80.000 EUR en operaciones bloqueadas, mas costes de auditoria forense y posibles compensaciones a clientes.",
  "business_impact_normative": "La exposicion de datos financieros activa la obligacion de notificar a la AEPD en menos de 72h (RGPD). El incumplimiento puede derivar en multas de hasta el 4% de la facturacion anual.",
  "business_impact_reputational": "Una brecha en el sistema de facturacion podria generar cobertura negativa en medios financieros y perdida de contratos corporativos.",
  "risk_category": "integrity",
  "affected_cia": ["C", "I"],
  "treatment_recommendation": "mitigate",
  "priority": "immediate"
}]"""
)


def build_risks_from_scenarios_prompt(scenarios: list[dict], project: dict, business_context: dict | None = None) -> str:
    """Construye el prompt para generación de narrativa de riesgo desde escenarios evaluados."""
    lines: list[str] = []

    for s in scenarios:
        code = s.get("scenario_code", "?")
        # New fields sent by generar_fichas
        business_title = s.get("business_title") or s.get("title") or s.get("consequence", "Sin título")
        technical_label = s.get("technical_label") or s.get("consequence", "")
        prob = s.get("probability", "?")
        prob_level = s.get("prob_level", "")
        impact = s.get("impact", "?")
        impact_level = s.get("impact_level", "")
        score = (prob * impact) if isinstance(prob, int) and isinstance(impact, int) else "?"
        process_name = s.get("process_name", "")

        entry = f"\n## {code}"
        entry += f"\n  business_title (contexto del escenario — REESCRIBE como risk_title, no copies): «{business_title}»"
        if technical_label and technical_label != business_title:
            entry += f"\n  referencia_técnica (solo para contexto interno): [{technical_label}]"
        entry += f"\n  P={prob} ({prob_level}) × I={impact} ({impact_level}) = {score}"
        if process_name:
            entry += f"\n  Proceso de negocio: {process_name}"

        dims = {
            "Operacional": s.get("impact_operational"),
            "Financiero":  s.get("impact_financial"),
            "Normativo":   s.get("impact_normative"),
            "Reputacional":s.get("impact_reputational"),
        }
        dim_str = " | ".join(f"{k}: {v}" for k, v in dims.items() if v)
        if dim_str:
            entry += f"\n  Dimensiones de impacto: {dim_str}"

        if s.get("probability_rationale"):
            entry += f"\n  Justif. probabilidad: {s['probability_rationale'][:200]}"

        findings = s.get("findings", [])
        if findings:
            sev_counts: dict[str, int] = {}
            for f in findings:
                sev = (f.get("severity") or "low").lower()
                sev_counts[sev] = sev_counts.get(sev, 0) + 1
            sev_str = ", ".join(f"{c}×{sv}" for sv, c in sorted(sev_counts.items(), key=lambda x: -x[1]))
            entry += f"\n  Evidencia: {len(findings)} hallazgos ({sev_str})"
            assets = list({f.get("asset_name") for f in findings if f.get("asset_name")})
            if assets:
                entry += f" | Activos: {', '.join(assets[:3])}"

        lines.append(entry)

    # BIA + normative context
    context_parts: list[str] = []
    if business_context:
        norm = business_context.get("normative") or {}
        active_regs = []
        if norm.get("rgpd"):
            active_regs.append("RGPD (notificación 72h, multa hasta 4% facturación)")
        if norm.get("nis2", "none") not in (None, "none"):
            active_regs.append(f"NIS2 (entidad {norm.get('nis2')})")
        if norm.get("ens"):
            active_regs.append(f"ENS nivel {norm.get('ens_level','básico')}")
        if norm.get("dora", "none") not in (None, "none"):
            active_regs.append("DORA (sector financiero)")
        if active_regs:
            context_parts.append(f"Normativa aplicable: {' | '.join(active_regs)}")

        processes = business_context.get("processes") or []
        if processes:
            proc_lines = ["Procesos de negocio (BIA) — usa estas cifras en los impactos:"]
            _rdep = {"<20": "baja (<20% ingresos)", "20-50": "media (20-50% ingresos)", ">50": "alta (>50% ingresos)"}
            for p in processes:
                rdep_str = _rdep.get(p.get("revenue_dependency", ""), p.get("revenue_dependency", "?"))
                line = f"  - {p['name']}: criticidad={p.get('criticality','?')}, dependencia={rdep_str}"
                if p.get("rto_hours") is not None:
                    line += f", RTO={p['rto_hours']}h"
                if p.get("impact_24h_eur") is not None:
                    line += f", pérdida-24h≈{p['impact_24h_eur']:,.0f}€"
                if p.get("sn_active"):
                    line += " ⚠ sanciones normativas"
                proc_lines.append(line)
            context_parts.append("\n".join(proc_lines))

    context_block = "\n".join(context_parts) + "\n" if context_parts else ""

    return (
        f"Proyecto: {project.get('name', 'Desconocido')}\n"
        f"Contexto de negocio: {project.get('business_context') or 'Aplicación web'}\n"
        + context_block
        + "\nESCENARIOS — P e I son FIJOS, business_title ya está en lenguaje de negocio:"
        + "".join(lines)
        + "\n\nGenera la narrativa ejecutiva completa para cada escenario: "
        "risk_title (REESCRIBE en lenguaje Directorio — formato 'Riesgo de [impacto] por [causa ejecutiva]', NUNCA copies business_title, NUNCA 'Riesgo de Riesgo de'), "
        "risk_description (2-3 oraciones ejecutivas para CTO), "
        "business_impact_operational, business_impact_financial (usa cifras BIA si las tienes), "
        "business_impact_normative, business_impact_reputational, "
        "risk_category, affected_cia, treatment_recommendation, priority. "
        "Responde SOLO con el array JSON."
    )


EXECUTIVE_SUMMARY_SYSTEM_PROMPT = """You are a CISO advisor producing executive risk summaries.
Write in clear business language — no technical jargon unless explained.
Keep summaries concise: 3-5 bullet points maximum.
Always tie findings to business risk, regulatory exposure, and recommended actions.

OUTPUT FORMAT:
{
  "headline": "<one sentence executive summary>",
  "key_risks": ["<risk 1>", "<risk 2>", "<risk 3>"],
  "regulatory_exposure": "<GDPR/PCI-DSS/SOC2 implications if any, or null>",
  "recommended_actions": ["<action 1>", "<action 2>"],
  "risk_trend": "<improving|stable|deteriorating>",
  "board_recommendation": "<one-paragraph board-level recommendation>"
}"""


TREATMENT_PLAN_SYSTEM_PROMPT = """Eres un consultor experto en gestión de riesgos ISO 31000 y ciberseguridad. Tu tarea es proponer un plan de tratamiento concreto y accionable para un riesgo de seguridad dado.

Debes generar entre 1 y 2 acciones de tratamiento específicas, priorizadas y asignables.

Reglas:
1. Siempre en español (es-ES).
2. Las acciones deben ser breves, específicas, medibles y asignables a un equipo.
3. Usa tipos ISO 31000: mitigate (reducir), avoid (evitar), transfer (transferir), accept (aceptar).
4. priority: immediate (≤1 semana), short_term (1-4 semanas), medium_term (1-3 meses), long_term (>3 meses).
5. expected_risk_reduction: % de reducción esperada del riesgo residual (0-90).
6. Ordena las acciones de mayor a menor prioridad.

FORMATO DE SALIDA — responde ÚNICAMENTE con este JSON:
[
  {
    "treatment_type": "mitigate|avoid|transfer|accept",
    "title": "<acción concreta en ≤60 caracteres>",
    "description": "<descripción muy concisa y directa (máximo 2 oraciones)>",
    "owner_name": "<equipo o rol responsable>",
    "priority": "immediate|short_term|medium_term|long_term",
    "expected_risk_reduction": <int 0-90>
  }
]"""


def build_treatment_plan_prompt(risk: dict, findings: list[dict]) -> str:
    findings_text = ""
    for f in findings[:8]:
        findings_text += f"- [{f.get('severity','?').upper()}] {f.get('title','')} ({f.get('category','')}{', CWE-'+str(f.get('cwe')) if f.get('cwe') else ''})\n"

    return f"""Genera un plan de tratamiento para el siguiente riesgo de seguridad.

## RIESGO
- Código: {risk.get('risk_code', 'N/A')}
- Título: {risk.get('risk_title', '')}
- Descripción: {(risk.get('risk_description') or 'No disponible')[:600]}
- Nivel de riesgo: {risk.get('risk_level', 'medium')} (P={risk.get('probability',3)} × I={risk.get('impact',3)} = {risk.get('risk_score',9)})
- Impacto operacional: {risk.get('impact_operational', 'No evaluado')}
- Impacto financiero: {risk.get('impact_financial', 'No evaluado')}
- Impacto normativo: {risk.get('impact_normative', 'No evaluado')}
- Impacto reputacional: {risk.get('impact_reputational', 'No evaluado')}

## HALLAZGOS VINCULADOS ({len(findings)} total)
{findings_text or '- Sin hallazgos directamente vinculados'}

Propón las acciones de tratamiento más efectivas para este riesgo."""


SCENARIOS_SCORING_SYSTEM_PROMPT = (
    """Eres un analista de riesgos ISO 31000. Recibes grupos de hallazgos YA AGRUPADOS
(un grupo = un activo + familia de amenaza). Tu tarea es SOLO puntuar y generar DOS titulos
por grupo: uno tecnico para analistas y uno de negocio para el CTO.
NO reagrupes. Responde con UN objeto por grupo usando el mismo group_id.
INSTRUCCION: Responde UNICAMENTE con un array JSON. Sin texto adicional, sin markdown.

ESCALA PROBABILIDAD (1-5):
5 = DAST/Pentest critico confirmado, sin autenticacion requerida
4 = DAST/Pentest alto, acceso externo posible
3 = SAST medio o pentest parcial con restricciones de acceso
2 = SAST bajo, mitigaciones presentes
1 = solo explotable desde dentro con privilegios elevados

ESCALA IMPACTO (1-5) — usa BIA del proceso del activo:
5 = proceso critico >50% ingresos o RTO<4h
4 = proceso importante 20-50% ingresos
3 = proceso de soporte <20% ingresos
2 = proceso administrativo menor
1 = proceso no critico, sin normativa aplicable

DOS TITULOS OBLIGATORIOS POR GRUPO:

technical_title — Para analistas de seguridad:
  Formato: "<Familia de amenaza> en <Nombre del activo>"
  Ejemplos: "Inyeccion SQL en ERP-Finanzas", "Credenciales expuestas en API Gateway", "XSS en Portal Web"

risk_title — Para el CTO y Directorio (CERO jerga tecnica):
  Consulta el CATALOGO MAESTRO (abajo) y elige el nombre de negocio que corresponde a la familia
  de amenaza. Luego adapta reemplazando [activo] y [sistema] con el nombre real.
  PROHIBIDO en risk_title: SQL, XSS, CSRF, SSRF, inyeccion, injection, misconfiguration,
  broken access, CWE, A01:, CVE, WAF, payload, exploit, "control de acceso", header, token.

"""
    + "CATALOGO MAESTRO DE TRADUCCION (fuente de verdad para risk_title):"
    + RISK_TRANSLATION_CATALOG
    + """
FORMATO DE CADA ELEMENTO (responde con este JSON por cada grupo):
{
  "group_id": <int — mismo que recibiste>,
  "technical_title": "<familia amenaza + activo, maximo 80 chars, para analistas>",
  "risk_title": "<nombre del catalogo adaptado al activo/proceso, maximo 110 chars, para Directorio>",
  "probability": <int 1-5>,
  "impact": <int 1-5>,
  "probability_rationale": "<1 frase explicando los factores clave>",
  "impact_rationale": "<1 frase con datos BIA del proceso si disponibles>"
}"""
)


def build_scenarios_scoring_prompt(scenario_groups: list[dict], project: dict) -> str:
    """Construye el prompt para scoring de escenarios pre-agrupados."""
    lines: list[str] = []

    for sg in scenario_groups:
        gid = sg.get("group_id", "?")
        asset = sg.get("asset_name") or "Activo desconocido"
        # Use human-readable category label if available
        category = sg.get("category_label") or (sg.get("category") or "desconocida").replace("_", " ").title()
        max_sev = sg.get("max_severity", "low").upper()
        count = sg.get("finding_count", 0)
        scanners = ", ".join(sg.get("scanner_types") or [])

        entry = f"\n## Grupo {gid}: {category} en {asset}"
        entry += f"\n  Hallazgos: {count} | Severidad máx: {max_sev} | Fuentes: {scanners}"

        if sg.get("business_process_name"):
            entry += f"\n  Proceso de negocio: {sg['business_process_name']}"
            if sg.get("business_process_criticality"):
                crit_map = {"critical": "crítico", "important": "importante", "support": "soporte"}
                entry += f" (criticidad: {crit_map.get(sg['business_process_criticality'], sg['business_process_criticality'])})"
            rdep = sg.get("revenue_dependency")
            if rdep:
                entry += f" | Dependencia ingresos: {rdep}"
        if sg.get("rto_hours") is not None:
            entry += f" | RTO: {sg['rto_hours']}h"
        if sg.get("impact_24h_eur") is not None:
            entry += f" | Pérdida estimada 24h: {sg['impact_24h_eur']:,.0f}€"
        if sg.get("sn_active"):
            entry += " | Exposición normativa: SÍ (sanciones aplicables)"

        summaries = sg.get("finding_summaries") or []
        if summaries:
            entry += "\n  Evidencia técnica:"
            for s in summaries[:5]:
                entry += f"\n    - {s}"

        lines.append(entry)

    return (
        f"Proyecto: {project.get('name', 'Desconocido')}\n"
        f"Contexto de negocio: {project.get('business_context') or 'Aplicación web'}\n"
        f"Total grupos a evaluar: {len(scenario_groups)}\n"
        "\nGRUPOS PRE-AGRUPADOS (NO reagrupar — puntuar y generar AMBOS títulos):"
        + "".join(lines)
        + "\n\nPara cada grupo genera: group_id, technical_title (analistas), risk_title (CTO sin jerga técnica), "
        "probability (1-5), impact (1-5), probability_rationale e impact_rationale. "
        "Responde SOLO con el array JSON."
    )


def build_executive_summary_prompt(project_context: dict) -> str:
    return f"""Generate an executive risk summary for this project's current security posture.

## PROJECT RISK SUMMARY
- Total open risks: {project_context.get('total_risks', 0)}
- Critical risks: {project_context.get('critical_count', 0)}
- High risks: {project_context.get('high_count', 0)}
- Medium risks: {project_context.get('medium_count', 0)}
- Risks under treatment: {project_context.get('under_treatment', 0)}
- Top vulnerability categories: {', '.join(project_context.get('top_categories', []))}
- Most affected assets: {', '.join(project_context.get('top_assets', []))}
- Risk trend (vs last scan): {project_context.get('trend', 'unknown')}
- Business context: {project_context.get('business_context', 'Not specified')}

Produce the JSON executive summary."""
