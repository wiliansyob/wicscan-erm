"""
Catálogo Maestro de Traducción de Riesgos
De Vulnerabilidades Técnicas a Riesgos de Negocio para Directorio / Junta Directiva

Fuente de verdad única para transformar hallazgos técnicos de seguridad en
lenguaje estratégico apto para la toma de decisiones ejecutiva.
"""

# ─────────────────────────────────────────────────────────────────────────────
# LOOKUP RÁPIDO: Familia técnica → Nombre del Riesgo de Negocio
# Usado en score-scenarios para generar risk_title sin jerga técnica
# ─────────────────────────────────────────────────────────────────────────────
FAMILY_TO_BUSINESS_RISK: dict[str, str] = {
    # Aplicaciones Web
    "injection":             "Riesgo de Manipulación Maliciosa de Sistemas Transaccionales",
    "xss":                   "Riesgo de Fraude Digital y Suplantación de Identidad hacia Clientes",
    "csrf":                  "Riesgo de Ejecución No Autorizada de Transacciones en Nombre del Cliente",
    "broken_auth":           "Riesgo de Acceso Ilegítimo a Cuentas y Sistemas Críticos",
    "data_exposure":         "Riesgo de Fuga Masiva de Información Confidencial y Personal",
    "access_control":        "Riesgo de Escalada de Privilegios y Acceso No Autorizado a Información",
    "misconfiguration":      "Riesgo de Exposición Involuntaria de la Arquitectura Interna de Sistemas",
    "vulnerable_components": "Riesgo de Compromiso por Vulnerabilidades Heredadas en la Cadena de Software",
    "ssrf":                  "Riesgo de Acceso Encubierto a Sistemas Internos desde el Exterior",
    "cryptography":          "Riesgo de Exposición y Robo de Datos Sensibles por Debilidades en Cifrado",
    "credentials":           "Riesgo de Acceso No Autorizado a Sistemas Críticos por Credenciales Expuestas",
    "insecure_design":       "Riesgo de Deficiencias Estructurales en Aplicaciones que Exponen el Negocio",
    "logging":               "Riesgo de Incapacidad de Detección y Respuesta Tardía ante Ataques Silenciosos",
    "integrity_failures":    "Riesgo de Sabotaje de la Cadena de Suministro Digital e Infraestructura Crítica",
    # Infraestructura
    "patch_management":      "Riesgo de Explotación de Fallos de Seguridad Conocidos en Plataformas Operativas",
    "eol_systems":           "Riesgo Operativo Crítico por Obsolescencia Tecnológica de Plataformas Core",
    "excessive_privileges":  "Riesgo de Daño Catastrófico por Abuso de Cuentas con Máximos Privilegios",
    "audit_logging":         "Riesgo de Incapacidad para Detectar Fraude e Incumplimiento de Trazabilidad",
    "backup_recovery":       "Riesgo de Pérdida Definitiva de Capacidad de Recuperación ante Desastres",
    # Red y perímetro
    "network_segmentation":  "Riesgo de Propagación Irrestricta de Incidentes en la Red Corporativa",
    "remote_access":         "Riesgo de Acceso Remoto No Controlado a Sistemas de Administración Críticos",
    "dos_ddos":              "Riesgo de Interrupción Deliberada y Prolongada de los Canales Digitales",
    "dns":                   "Riesgo de Redirección Fraudulenta del Tráfico hacia Sitios Maliciosos",
    # Identidad y accesos
    "mfa_missing":           "Riesgo de Usurpación de Identidad Digital de Empleados y Directivos",
    "orphan_accounts":       "Riesgo de Acceso Activo a Sistemas por Personal No Vinculado a la Organización",
    "least_privilege":       "Riesgo de Daño Interno Amplificado por Exceso de Privilegios",
    "pam":                   "Riesgo de Acción No Trazable con Máximo Impacto por Cuentas de Control Total",
    # Nube
    "cloud_misconfiguration":"Riesgo de Exposición Pública No Intencional de Activos Digitales Corporativos",
    "cloud_iam":             "Riesgo de Compromiso Total del Entorno Digital ante Brecha de una Sola Identidad",
    # Terceros y cadena de suministro
    "third_party_access":    "Riesgo de Compromiso de Sistemas Corporativos a través de Terceros de Confianza",
    "supply_chain":          "Riesgo de Infiltración Encubierta mediante Canales de Actualización de Software",
    "shadow_it":             "Riesgo Operativo y Legal por Tecnología No Gestionada en el Ecosistema Corporativo",
}

# ─────────────────────────────────────────────────────────────────────────────
# CATÁLOGO COMPLETO para risk_description e impactos (formato para IA)
# ─────────────────────────────────────────────────────────────────────────────
RISK_TRANSLATION_CATALOG = """
=== CATÁLOGO MAESTRO: VULNERABILIDAD TÉCNICA → RIESGO DE NEGOCIO ===

REGLA DE ORO: Si el nombre del riesgo contiene el nombre de una marca (Microsoft, Cisco),
un protocolo (SQL, HTTP, XSS), o un acrónimo técnico (CVE, WAF, DMZ), NO está listo para
el Directorio. Debe enfocarse en el impacto financiero, operativo o reputacional.

GLOSARIO DE SUSTITUCIÓN (nunca uses la columna izquierda en presentaciones ejecutivas):
  SQL Injection / SQLi      → "manipulación maliciosa de consultas a sistemas de información"
  XSS (Cross-Site Scripting)→ "inserción de código fraudulento en canales digitales"
  CVE                       → "vulnerabilidad de seguridad documentada públicamente"
  WAF                       → "capa de protección perimetral de aplicaciones digitales"
  MFA                       → "verificación de identidad en múltiples pasos"
  Zero-Day                  → "vulnerabilidad sin corrección disponible del fabricante"
  IDOR                      → "acceso no autorizado a registros de otros usuarios"
  RDP                       → "protocolo de administración remota de servidores"
  OWASP                     → "marco internacional de referencia para seguridad de aplicaciones"
  SIEM                      → "plataforma de monitoreo y correlación de eventos de seguridad"
  Patch Tuesday             → "ciclo periódico de actualizaciones de seguridad de fabricantes"

--- DIMENSIÓN 1: Aplicaciones (Web, Móviles, APIs) ---

Inyección de código en BD (SQL/Command Injection)
  → NOMBRE: "Riesgo de Manipulación Maliciosa de Sistemas Transaccionales"
  → IMPACTO: Un agente externo puede extraer, alterar o destruir la totalidad de la información
    almacenada en los sistemas de negocio (clientes, transacciones, contratos), con consecuencias
    directas de pérdida financiera, fraude y sanciones regulatorias por exposición de datos.

Secuencias de comandos entre sitios (XSS)
  → NOMBRE: "Riesgo de Fraude Digital y Suplantación de Identidad hacia Clientes"
  → IMPACTO: Los clientes pueden ser engañados mediante páginas manipuladas que parecen legítimas,
    permitiendo el robo de credenciales, sesiones activas y datos financieros, con daño reputacional
    y reclamaciones legales.

Falsificación de peticiones (CSRF)
  → NOMBRE: "Riesgo de Ejecución No Autorizada de Transacciones en Nombre del Cliente"
  → IMPACTO: Un tercero puede forzar operaciones (transferencias, aprobaciones) usando la sesión
    activa de un usuario legítimo, generando fraude operativo y erosión de confianza del cliente.

Autenticación rota o deficiente
  → NOMBRE: "Riesgo de Acceso Ilegítimo a Cuentas y Sistemas Críticos"
  → IMPACTO: La debilidad en los mecanismos de identidad permite que actores no autorizados accedan
    a sistemas, información privilegiada o paneles de administración, con riesgo de fraude y
    violación normativa.

Exposición de datos sensibles / Fallas criptográficas
  → NOMBRE: "Riesgo de Fuga Masiva de Información Confidencial y Personal"
  → IMPACTO: La ausencia de protección sobre datos sensibles en tránsito o en reposo expone a la
    organización a brechas que activan obligaciones de notificación regulatoria, multas sustanciales
    y daño permanente a la reputación.

Control de acceso roto (Broken Access Control / IDOR)
  → NOMBRE: "Riesgo de Escalada de Privilegios y Acceso No Autorizado a Información de Terceros"
  → IMPACTO: Cualquier usuario podría visualizar o manipular información de otros clientes, empleados
    o directivos, generando violaciones de privacidad, responsabilidad legal y riesgo de extorsión.

Configuración de seguridad incorrecta
  → NOMBRE: "Riesgo de Exposición Involuntaria de la Arquitectura Interna de Sistemas"
  → IMPACTO: La configuración inadecuada entrega a actores maliciosos información para mapear la
    infraestructura y planificar ataques dirigidos de mayor envergadura.

Componentes vulnerables y desactualizados
  → NOMBRE: "Riesgo de Compromiso por Vulnerabilidades Heredadas en la Cadena de Software"
  → IMPACTO: El uso de componentes con defectos conocidos permite ataques sin técnicas sofisticadas,
    comprometiendo aplicaciones críticas con riesgo de interrupción de servicios y robo de datos.

Falsificación de peticiones del servidor (SSRF)
  → NOMBRE: "Riesgo de Acceso Encubierto a Sistemas Internos desde el Exterior"
  → IMPACTO: Un atacante usa los propios servidores como puente para acceder a sistemas internos
    protegidos, eludiendo todos los controles perimetrales establecidos.

Credenciales y secretos expuestos en código
  → NOMBRE: "Riesgo de Acceso No Autorizado a Sistemas Críticos por Exposición de Credenciales"
  → IMPACTO: Las claves de acceso embebidas en código permiten a actores malintencionados acceder
    directamente a todos los sistemas de producción, bases de datos y recursos en la nube.

Fallos de integridad de software / Deserialización insegura
  → NOMBRE: "Riesgo de Sabotaje de la Cadena de Suministro Digital e Infraestructura Crítica"
  → IMPACTO: Las actualizaciones legítimas de proveedores de confianza pueden ser manipuladas para
    distribuir código malicioso, comprometiendo simultáneamente múltiples sistemas de la organización.

Registro y monitoreo insuficiente
  → NOMBRE: "Riesgo de Incapacidad de Detección y Respuesta Tardía ante Ataques Silenciosos"
  → IMPACTO: Sin registros de actividad adecuados, la organización es incapaz de detectar accesos
    fraudulentos, reconstruir incidentes, cumplir con auditorías regulatorias o cuantificar brechas.

--- DIMENSIÓN 2: Infraestructura y Servidores ---

Parches de seguridad no aplicados / Sistemas sin soporte (EOL)
  → NOMBRE: "Riesgo de Explotación de Fallos Conocidos en Plataformas Operativas" /
             "Riesgo Operativo Crítico por Obsolescencia Tecnológica de Plataformas Core"
  → IMPACTO: Los sistemas sin actualizaciones son vulnerables a técnicas de ataque ampliamente
    documentadas y disponibles, incrementando exponencialmente la probabilidad de incidente severo.

Privilegios administrativos excesivos
  → NOMBRE: "Riesgo de Daño Catastrófico por Abuso o Compromiso de Cuentas con Máximos Privilegios"
  → IMPACTO: El compromiso de una sola cuenta con privilegios globales permite cifrar todos los
    sistemas, exfiltrar la totalidad de la información o borrar evidencia de actividad fraudulenta.

Respaldos no cifrados o sin verificación
  → NOMBRE: "Riesgo de Pérdida Definitiva de Capacidad de Recuperación ante Desastres"
  → IMPACTO: Si los respaldos son comprometidos junto con los sistemas de producción, la organización
    pierde toda capacidad de recuperación autónoma, quedando expuesta a pago de rescates o cierre.

--- DIMENSIÓN 3: Red y Perímetro ---

Ausencia de segmentación de red
  → NOMBRE: "Riesgo de Propagación Irrestricta de Incidentes en la Red Corporativa"
  → IMPACTO: Un único dispositivo comprometido puede comprometer la totalidad de los sistemas críticos
    sin encontrar barreras de contención.

Exposición de interfaces de administración remota
  → NOMBRE: "Riesgo de Acceso Remoto No Controlado a Sistemas de Administración Críticos"
  → IMPACTO: La exposición de herramientas de administración al exterior convierte la organización en
    objetivo de ataques automatizados masivos que otorgan control total de la infraestructura.

Ataques de denegación de servicio (DDoS)
  → NOMBRE: "Riesgo de Interrupción Deliberada y Prolongada de los Canales Digitales de Negocio"
  → IMPACTO: Servicios digitales (atención a clientes, comercio, banca) pueden quedar inaccesibles
    durante horas o días, con impacto directo en ingresos y penalizaciones contractuales.

--- DIMENSIÓN 4: Nube / Cloud ---

Configuración incorrecta de servicios en la nube
  → NOMBRE: "Riesgo de Exposición Pública No Intencional de Activos Digitales Corporativos"
  → IMPACTO: Un recurso mal configurado puede quedar accesible sin autenticación desde Internet,
    exponiendo bases de datos de clientes y sistemas operativos a cualquier actor externo.

Permisos excesivos en la nube (IAM mal configurado)
  → NOMBRE: "Riesgo de Compromiso Total del Entorno Digital ante Brecha de una Sola Identidad"
  → IMPACTO: En un modelo sin restricciones, el compromiso de cualquier cuenta de usuario otorga
    acceso irrestricto a todos los activos digitales de la organización.

--- DIMENSIÓN 5: Identidad y Accesos ---

Ausencia de verificación multifactor (MFA)
  → NOMBRE: "Riesgo de Usurpación de Identidad Digital de Empleados y Directivos"
  → IMPACTO: Una contraseña comprometida mediante ingeniería social o comprada en mercados ilegales
    otorga acceso total al sistema, incluyendo aplicaciones financieras y paneles ejecutivos.

Cuentas de exempleados o terceros activas
  → NOMBRE: "Riesgo de Acceso Activo a Sistemas Corporativos por Personal No Vinculado"
  → IMPACTO: Identidades de personas sin relación laboral permanecen activas como vías de acceso
    no supervisadas, explotables tanto por el exempleado como por terceros con sus credenciales.

Cuentas privilegiadas sin control (PAM)
  → NOMBRE: "Riesgo de Acción No Trazable con Máximo Impacto por Cuentas de Control Total"
  → IMPACTO: Sin gestión de cuentas privilegiadas, su compromiso puede resultar en destrucción,
    cifrado o exfiltración de la totalidad de los activos digitales sin dejar rastro auditable.

--- DIMENSIÓN 6: Datos y Almacenamiento ---

Bases de datos sin cifrado en reposo o expuestas directamente
  → NOMBRE: "Riesgo de Ataque Directo a los Repositorios Centrales de Información del Negocio"
  → IMPACTO: Los sistemas de almacenamiento expuestos facilitan ataques directos de extracción,
    manipulación o destrucción de la totalidad de la información corporativa.

Retención indefinida de datos personales
  → NOMBRE: "Riesgo de Incumplimiento de Obligaciones Legales de Protección de Datos Personales"
  → IMPACTO: El almacenamiento de datos personales más allá de los plazos normativos expone a
    sanciones administrativas y constituye un agravante en caso de brecha, multiplicando el impacto.

--- DIMENSIÓN 7: Cadena de Suministro y Terceros ---

Accesos de proveedores sin supervisión
  → NOMBRE: "Riesgo de Compromiso de Sistemas Corporativos a través de Terceros de Confianza"
  → IMPACTO: Un incidente de seguridad en el proveedor se convierte automáticamente en un incidente
    de la organización, afectando a toda la cadena de clientes y procesos.

Actualización de software comprometida (Supply Chain Attack)
  → NOMBRE: "Riesgo de Infiltración Encubierta mediante Canales de Actualización de Software"
  → IMPACTO: Código malicioso distribuido a través de actualizaciones legítimas compromete
    simultáneamente a múltiples organizaciones sin levantar alertas de seguridad.

--- DIMENSIÓN 8: Nuevas Tecnologías (IA, IoT, Contenedores) ---

Dispositivos IoT con contraseñas de fábrica o sin actualizar
  → NOMBRE: "Riesgo de Compromiso de la Red Corporativa a través de Dispositivos Físicos Conectados"
  → IMPACTO: Los dispositivos conectados son el punto de entrada más vulnerable de las redes
    corporativas, permitiendo establecer presencia permanente y oculta dentro de la infraestructura.

Modelos de IA con acceso a datos confidenciales
  → NOMBRE: "Riesgo de Divulgación No Controlada de Información Confidencial mediante IA"
  → IMPACTO: Los modelos de IA pueden revelar información confidencial a usuarios no autorizados a
    través de consultas aparentemente inocentes, constituyendo un canal de fuga de difícil detección.
"""
