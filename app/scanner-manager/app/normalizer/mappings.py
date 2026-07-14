"""
Mapping tables for scanner-specific values → canonical values.
"""

# SonarQube severity → canonical severity
SONARQUBE_SEVERITY_MAP: dict[str, str] = {
    "BLOCKER": "critical",
    "CRITICAL": "high",
    "MAJOR": "medium",
    "MINOR": "low",
    "INFO": "info",
}

# SonarQube type → canonical finding_type
SONARQUBE_TYPE_MAP: dict[str, str] = {
    "VULNERABILITY": "vulnerability",
    "BUG": "bug",
    "CODE_SMELL": "code_smell",
    "SECURITY_HOTSPOT": "security_hotspot",
}

# SonarQube effort → canonical effort
SONARQUBE_EFFORT_MAP: dict[str, str] = {
    "5min": "low",
    "10min": "low",
    "15min": "low",
    "30min": "low",
    "1h": "medium",
    "2h": "medium",
    "3h": "medium",
    "4h": "high",
    "1d": "high",
    "2d": "high",
    "3d": "high",
}

# CWE → canonical category
CWE_CATEGORY_MAP: dict[str, str] = {
    "CWE-89":  "sql_injection",
    "CWE-79":  "xss",
    "CWE-78":  "command_injection",
    "CWE-22":  "path_traversal",
    "CWE-611": "xxe",
    "CWE-918": "ssrf",
    "CWE-287": "broken_auth",
    "CWE-798": "hardcoded_credentials",
    "CWE-330": "insecure_random",
    "CWE-327": "weak_crypto",
    "CWE-352": "csrf",
    "CWE-502": "insecure_deserialization",
    "CWE-200": "sensitive_data",
    "CWE-312": "sensitive_data",
    "CWE-319": "sensitive_data",
    "CWE-601": "open_redirect",
    "CWE-284": "broken_access_control",
    "CWE-285": "broken_access_control",
    "CWE-434": "file_upload",
    "CWE-476": "null_dereference",
    "CWE-190": "integer_overflow",
    "CWE-416": "use_after_free",
    "CWE-125": "out_of_bounds_read",
    "CWE-400": "resource_exhaustion",
}

# SonarQube rule → CWE
SONARQUBE_RULE_CWE_MAP: dict[str, str] = {
    "java:S2077": "CWE-89",
    "java:S3649": "CWE-89",
    "python:S3649": "CWE-89",
    "python:S2076": "CWE-78",
    "python:S2083": "CWE-22",
    "java:S5131": "CWE-79",
    "java:S2631": "CWE-79",
    "python:S5131": "CWE-79",
    "java:S6349": "CWE-918",
    "python:S5144": "CWE-918",
    "java:S6288": "CWE-287",
    "python:S2245": "CWE-330",
    "java:S2278": "CWE-327",
    "java:S4426": "CWE-327",
    "python:S4790": "CWE-327",
    "java:S2068": "CWE-798",
    "python:S2068": "CWE-798",
    "java:S1481": "CWE-200",
}

# SonarQube rule → OWASP category
SONARQUBE_RULE_OWASP_MAP: dict[str, str] = {
    "java:S2077":  "A03:2021",
    "python:S3649": "A03:2021",
    "java:S5131":  "A03:2021",
    "python:S5131": "A03:2021",
    "java:S6288":  "A07:2021",
    "java:S2278":  "A02:2021",
    "java:S4426":  "A02:2021",
    "java:S2068":  "A07:2021",
    "python:S2068": "A07:2021",
    "java:S6349":  "A10:2021",
    "python:S5144": "A10:2021",
}


# ─────────────────────────────────────────────────────────────────────────────
# Taxonomía CWE → Escenario de riesgo de negocio (ISO 31000)
#
# Agrupa CWEs relacionados bajo una clave común para que la IA (y el engine)
# puedan consolidar hallazgos del mismo tipo en UN SOLO escenario de riesgo.
# ─────────────────────────────────────────────────────────────────────────────

# CWE → clave de agrupación
CWE_GROUPING_KEY: dict[str, str] = {
    # Inyección
    "CWE-89":  "inyeccion",   # SQL Injection
    "CWE-78":  "inyeccion",   # OS Command Injection
    "CWE-88":  "inyeccion",   # Argument Injection
    "CWE-94":  "inyeccion",   # Code Injection
    "CWE-77":  "inyeccion",   # Command Injection genérico
    # XSS
    "CWE-79":  "xss",         # Cross-site Scripting
    "CWE-80":  "xss",         # Basic XSS
    "CWE-83":  "xss",         # XSS in Attributes
    # Exposición de datos / credenciales
    "CWE-798": "exposicion_datos",  # Hardcoded Credentials
    "CWE-200": "exposicion_datos",  # Information Disclosure
    "CWE-312": "exposicion_datos",  # Cleartext Storage of Sensitive Info
    "CWE-319": "exposicion_datos",  # Cleartext Transmission
    "CWE-311": "exposicion_datos",  # Missing Encryption
    # Autenticación / control de acceso
    "CWE-287": "control_acceso",    # Improper Authentication
    "CWE-330": "control_acceso",    # Insecure Randomness
    "CWE-284": "control_acceso",    # Improper Access Control
    "CWE-285": "control_acceso",    # Improper Authorization
    "CWE-306": "control_acceso",    # Missing Authentication
    "CWE-307": "control_acceso",    # Brute Force sin protección
    # Criptografía débil / deserialización
    "CWE-327": "cripto_debil",      # Use of Broken Algorithm
    "CWE-326": "cripto_debil",      # Inadequate Encryption Strength
    "CWE-328": "cripto_debil",      # Weak Hash
    "CWE-502": "cripto_debil",      # Insecure Deserialization
    # Path traversal / XXE / SSRF
    "CWE-22":  "acceso_recursos",   # Path Traversal
    "CWE-23":  "acceso_recursos",   # Relative Path Traversal
    "CWE-611": "acceso_recursos",   # XXE
    "CWE-918": "acceso_recursos",   # SSRF
    # Configuración insegura
    "CWE-16":  "mala_configuracion",  # Configuration
    "CWE-732": "mala_configuracion",  # Incorrect Permission Assignment
    "CWE-434": "mala_configuracion",  # Unrestricted File Upload
    # Agotamiento de recursos / DoS
    "CWE-400": "disponibilidad",      # Resource Exhaustion
    "CWE-770": "disponibilidad",      # Allocation Without Limits
}


# Clave de agrupación → escenario de riesgo de negocio
CWE_BUSINESS_SCENARIO: dict[str, dict] = {
    "inyeccion": {
        "titulo": "Ejecución de comandos no autorizados en base de datos o sistema",
        "categoria": "confidentiality",
        "impacto_base": 5,
        "compliance": ["GDPR", "PCI-DSS"],
        "tratamiento": "mitigate",
        "prioridad": "immediate",
    },
    "xss": {
        "titulo": "Secuestro de sesión de usuario y robo de credenciales",
        "categoria": "integrity",
        "impacto_base": 4,
        "compliance": ["GDPR"],
        "tratamiento": "mitigate",
        "prioridad": "short_term",
    },
    "exposicion_datos": {
        "titulo": "Exposición de información sensible y credenciales de acceso",
        "categoria": "confidentiality",
        "impacto_base": 5,
        "compliance": ["GDPR", "HIPAA", "SOC2"],
        "tratamiento": "mitigate",
        "prioridad": "immediate",
    },
    "control_acceso": {
        "titulo": "Autenticación deficiente y escalación de privilegios no autorizada",
        "categoria": "integrity",
        "impacto_base": 4,
        "compliance": ["SOC2", "PCI-DSS", "ISO27001"],
        "tratamiento": "mitigate",
        "prioridad": "short_term",
    },
    "cripto_debil": {
        "titulo": "Compromiso de integridad de datos por criptografía débil o deserialización insegura",
        "categoria": "confidentiality",
        "impacto_base": 4,
        "compliance": ["PCI-DSS", "FIPS", "ISO27001"],
        "tratamiento": "mitigate",
        "prioridad": "medium_term",
    },
    "acceso_recursos": {
        "titulo": "Acceso no autorizado a archivos internos y exfiltración de red",
        "categoria": "confidentiality",
        "impacto_base": 4,
        "compliance": ["GDPR"],
        "tratamiento": "mitigate",
        "prioridad": "short_term",
    },
    "mala_configuracion": {
        "titulo": "Configuración insegura que amplía la superficie de ataque",
        "categoria": "operational",
        "impacto_base": 3,
        "compliance": ["SOC2", "CIS"],
        "tratamiento": "mitigate",
        "prioridad": "medium_term",
    },
    "disponibilidad": {
        "titulo": "Agotamiento de recursos y riesgo de interrupción del servicio",
        "categoria": "availability",
        "impacto_base": 3,
        "compliance": ["SOC2"],
        "tratamiento": "mitigate",
        "prioridad": "medium_term",
    },
}


def get_grouping_key(cwe: str | None) -> str | None:
    """Devuelve la clave de agrupación para un CWE, o None si no está mapeado."""
    if not cwe:
        return None
    normalized = cwe.strip().upper()
    if not normalized.startswith("CWE-"):
        normalized = f"CWE-{normalized}"
    return CWE_GROUPING_KEY.get(normalized)


def get_business_scenario(cwe: str | None) -> dict | None:
    """Devuelve el escenario de negocio para un CWE dado."""
    key = get_grouping_key(cwe)
    return CWE_BUSINESS_SCENARIO.get(key) if key else None


def normalize_effort(raw_effort: str | None) -> str | None:
    if not raw_effort:
        return None
    # Try exact match first
    if raw_effort in SONARQUBE_EFFORT_MAP:
        return SONARQUBE_EFFORT_MAP[raw_effort]
    # Parse numeric effort in minutes
    try:
        raw_lower = raw_effort.lower()
        if "min" in raw_lower:
            mins = int(raw_lower.replace("min", ""))
            if mins <= 30:
                return "low"
            if mins <= 180:
                return "medium"
            return "high"
        if "h" in raw_lower and "d" not in raw_lower:
            hours = float(raw_lower.replace("h", ""))
            return "low" if hours <= 1 else ("medium" if hours <= 3 else "high")
        if "d" in raw_lower:
            return "high"
    except (ValueError, AttributeError):
        pass
    return None
