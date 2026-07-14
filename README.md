# WicScan Risk Manager

WicScan Risk Manager es una plataforma para el análisis, gestión y evaluación de riesgos de seguridad en aplicaciones y repositorios de código. Su enfoque principal es **llevar los hallazgos técnicos (vulnerabilidades) a riesgos de negocio**, para que las organizaciones puedan entender el impacto real de las brechas de seguridad. Utiliza inteligencia artificial (modelos locales como Ollama/Llama3.2 o APIs de terceros como Anthropic y Gemini) junto con herramientas de análisis estático y dinámico de código para generar reportes detallados y matrices de riesgo alineadas con **ISO 31000**.

## 🚀 Características Principales

- **Gestión de Proyectos y Activos**: Organiza repositorios, aplicaciones y fuentes de código por proyecto.
- **Fase 1 — Contextualización**: **Análisis de Impacto en el Negocio (BIA)** por proceso, con criticidad, dependencia de ingresos y cálculo de RTO/RPO/MTPD.
- **Fase 2 — Identificación**: Análisis multi-escáner automático con **SonarQube** (SAST), **OWASP ZAP** (DAST) y **AI Review** (revisión asistida por IA).
- **Fase 3 — Análisis**: Consolidación inteligente de hallazgos en escenarios de riesgo, evaluación de **probabilidad e impacto** (operacional, financiero, normativo, reputacional) con apoyo de IA.
- **Fase 4 — Evaluación**: El *AI Gateway* traduce escenarios en riesgos de negocio priorizados, puntuados y clasificados por severidad.
- **Fase 5 — Tratamiento**: Planes de tratamiento (mitigar / evitar / transferir / aceptar), ciclos de revisión, eventos desencadenantes, indicadores de riesgo por período y reporte final.
- **Catálogo de Cuestionarios (Admin)**: Gestión versionada de definiciones de cuestionarios con inmutabilidad de versiones publicadas (copy-on-publish).
- **Soporte Multi-Modelo**: Modelos locales (`Ollama`) para privacidad del código, o modelos en la nube (`Claude`, `Gemini`, `OpenAI`).
- **Monitoreo de Servicios**: Dashboard en tiempo real del estado de los microservicios y gestión de escáneres conectados.

## 🗂️ Proceso ISO 31000 — Fases

```
Fase 1            Fase 2            Fase 3          Fase 4         Fase 5
Contextualización → Identificación → Análisis      → Evaluación  → Tratamiento
(BIA)                (SAST/DAST/IA)   (Escenarios)    (Riesgos IA)  (Plan/Reporte)
```

| Fase | Descripción | Rutas Frontend |
| :--- | :--- | :--- |
| **Fase 1** | Análisis de Impacto en el Negocio (BIA) por proceso | `/contexto/bia` |
| **Fase 2** | Escaneo de activos y fuentes de código | `/activos`, `/scans`, `/identificacion` |
| **Fase 3** | Consolidación en escenarios, probabilidad e impacto | `/escenarios`, `/probabilidad`, `/impacto` |
| **Fase 4** | Evaluación de riesgos de negocio con apoyo de IA | `/analisis` |
| **Fase 5** | Planes de tratamiento, ciclos de revisión y reporte | `/tratamiento`, `/reporte` |

## 🏗️ Arquitectura Técnica

- **Frontend**: Next.js 14, React, TypeScript, TailwindCSS, Radix UI, React Query, Recharts.
- **Backend**: FastAPI (Python), SQLAlchemy async, PostgreSQL, Redis, Celery. La lógica de dominio se organiza en `app/modules/` (contexto, identification, escenarios, analisis, tratamiento, admin/catalog, assessment/scoring).
- **Scanner Manager**: Microservicio que orquesta y normaliza los escaneos de SonarQube.
- **AI Gateway**: Microservicio dedicado a la comunicación estandarizada con proveedores de IA (OpenAI, Anthropic, Gemini, Ollama).
- **Infraestructura**: Docker Compose, volumen local para uploads (evidencias/reportes).

## 🗄️ Esquema de Base de Datos

La aplicación utiliza PostgreSQL. Todas las tablas incluyen `id` (UUID), `created_at` y `updated_at`. La lógica relacional se maneja vía SQLAlchemy.

### Gestión de Usuarios y Proyectos

#### `workspaces`
| Columna | Tipo | Descripción |
| :--- | :--- | :--- |
| `name` | String | Nombre del espacio de trabajo |
| `description` | Text | Descripción opcional |
| `ai_config` | JSON | Configuración global de IA |

#### `users`
| Columna | Tipo | Descripción |
| :--- | :--- | :--- |
| `workspace_id` | UUID | Referencia al workspace |
| `email` | String | Correo electrónico único |
| `password_hash` | String | Hash de contraseña |
| `full_name` | String | Nombre completo |
| `is_active` | Boolean | Estado del usuario |
| `last_login` | DateTime | Fecha del último acceso |

#### `projects`
| Columna | Tipo | Descripción |
| :--- | :--- | :--- |
| `workspace_id` | UUID | Referencia al workspace |
| `name` | String | Nombre del proyecto |
| `description` | Text | Descripción opcional |
| `risk_appetite` | String | Apetito de riesgo (low/medium/high) |
| `business_context` | Text | Contexto de negocio |
| `status` | String | Estado (active/archived) |
| `scanner_config` | JSON | Configuración de escáneres |
| `ai_provider_config` | JSON | Configuración del proveedor IA |

#### `assets`
| Columna | Tipo | Descripción |
| :--- | :--- | :--- |
| `project_id` | UUID | Referencia al proyecto |
| `name` | String | Nombre del activo |
| `asset_type` | String | api, webapp, repository, database, etc. |
| `criticality` | String | critical, high, medium, low |
| `technical_owner` | String | Responsable técnico |
| `business_owner` | String | Responsable de negocio |
| `url` | String | URL del activo |
| `tags` | JSON | Etiquetas adicionales |
| `readme_content` | Text | Documentación del activo |

#### `code_sources`
| Columna | Tipo | Descripción |
| :--- | :--- | :--- |
| `project_id` | UUID | Referencia al proyecto |
| `asset_id` | UUID | (Opcional) Activo asociado |
| `source_type` | String | github, zip |
| `github_url` | String | URL del repositorio |
| `github_branch` | String | Rama (ej. main) |
| `status` | String | pending, cloning, ready, error |
| `snapshot_hash` | String | Hash de integridad |

### Escaneos y Hallazgos (Fase 2 — Identificación)

#### `scan_sessions`
| Columna | Tipo | Descripción |
| :--- | :--- | :--- |
| `project_id` | UUID | Referencia al proyecto |
| `code_source_id` | UUID | Fuente de código |
| `status` | String | pending, running, completed, failed, cancelled |
| `is_retest` | Boolean | ¿Es re-escaneo? |
| `total_findings_count` | Integer | Total de hallazgos |
| `new_findings_count` | Integer | Nuevos hallazgos |
| `resolved_findings_count` | Integer | Hallazgos resueltos |

#### `scans`
| Columna | Tipo | Descripción |
| :--- | :--- | :--- |
| `session_id` | UUID | Referencia a la sesión |
| `scanner_type` | String | sonarqube, zap, ai_review |
| `status` | String | Estado del escaneo |
| `findings_count` | Integer | Número de hallazgos |
| `raw_output` | JSON | Salida cruda del escáner |

#### `findings`
| Columna | Tipo | Descripción |
| :--- | :--- | :--- |
| `scan_id` | UUID | Referencia al escaneo |
| `asset_id` | UUID | Activo afectado |
| `scanner` | String | Herramienta detectora |
| `finding_type` | String | vulnerability, code_smell, bug |
| `severity` | String | critical, high, medium, low, info |
| `cwe` | String | CWE correspondiente |
| `owasp_category` | String | Categoría OWASP |
| `cvss_score` | Float | Puntuación CVSS |
| `file_path` | String | Archivo afectado |
| `status` | String | open, confirmed, false_positive, resolved |
| `fingerprint` | String | Huella para deduplicación |

#### `retest_comparisons`
| Columna | Tipo | Descripción |
| :--- | :--- | :--- |
| `project_id` | UUID | Referencia al proyecto |
| `baseline_session_id` | UUID | Sesión base |
| `retest_session_id` | UUID | Sesión de retest |
| `new_count` | Integer | Hallazgos nuevos |
| `resolved_count` | Integer | Hallazgos resueltos |
| `regression_count` | Integer | Regresiones detectadas |

### Fase 1 — Contextualización

#### `questionnaire_definitions` (Catálogo Admin)
| Columna | Tipo | Descripción |
| :--- | :--- | :--- |
| `version` | Integer | Versión publicada (null si es borrador) |
| `status` | String | draft, published, archived |
| `published_at` | DateTime | Fecha de publicación |
| `notes` | Text | Notas de la versión |

#### `question_definitions`
| Columna | Tipo | Descripción |
| :--- | :--- | :--- |
| `definition_id` | UUID | Referencia al cuestionario |
| `block` | String | Bloque (A, B, C, D) |
| `question_id` | String | ID de la pregunta (A1, B2a…) |
| `type` | String | single_choice, multi_choice, range, free_text |
| `options` | JSON | Opciones de respuesta |
| `feeds` | JSON | Campos normativos/BIA que alimenta |

#### `question_dependencies`
| Columna | Tipo | Descripción |
| :--- | :--- | :--- |
| `definition_id` | UUID | Cuestionario padre |
| `parent_question_id` | String | Pregunta condicional |
| `trigger_value` | String | Valor que activa la dependencia |
| `child_question_id` | String | Pregunta hija habilitada |
| `effect` | JSON | Efecto declarativo sobre el perfil normativo |

#### `definition_change_log`
Registro de auditoría inmutable de toda acción sobre definiciones (create, update, publish, clone, etc.).

#### `cuestionarios`
| Columna | Tipo | Descripción |
| :--- | :--- | :--- |
| `project_id` | UUID | Proyecto al que pertenece |
| `definition_id` | UUID | Versión del cuestionario usada (inmutable) |
| `status` | String | in_progress, completed |
| `completed_at` | DateTime | Fecha de completado |

#### `respuestas_cuestionario`
| Columna | Tipo | Descripción |
| :--- | :--- | :--- |
| `questionnaire_id` | UUID | Cuestionario al que pertenece |
| `block` | String | Bloque de la pregunta |
| `question_id` | String | ID de la pregunta respondida |
| `value` | JSON | Respuesta (string, lista o número) |

#### `procesos_negocio` (BIA)
| Columna | Tipo | Descripción |
| :--- | :--- | :--- |
| `project_id` | UUID | Referencia al proyecto |
| `name` | String | Nombre del proceso |
| `criticality` | String | critical, important, support |
| `revenue_dependency` | String | Porcentaje de dependencia de ingresos |
| `manual_alternative` | String | Capacidad de operación manual |
| `contractual_commitment` | JSON | Compromisos contractuales |

#### `estimaciones_bia`
| Columna | Tipo | Descripción |
| :--- | :--- | :--- |
| `process_id` | UUID | Proceso de negocio |
| `impact_2h` / `_8h` / `_24h` | Float | Impacto por ventana temporal |
| `mtpd_hours` | Float | Máximo tiempo de interrupción tolerable |
| `rto_hours` | Float | Objetivo de tiempo de recuperación |
| `rpo_hours` | Float | Objetivo de punto de recuperación |
| `breakdown` | JSON | Desglose del cálculo |

#### `activo_proceso_links`
Relación muchos-a-muchos entre activos y procesos de negocio, con peso de dependencia.

### Fase 3 — Escenarios y Análisis

#### `escenarios`
| Columna | Tipo | Descripción |
| :--- | :--- | :--- |
| `project_id` | UUID | Referencia al proyecto |
| `scenario_code` | String | Código del escenario (ej. E-001) |
| `title` | String | Título del escenario |
| `consequence` | String | Consecuencia principal |
| `asset_id` | UUID | Activo afectado |
| `business_process_id` | UUID | Proceso de negocio afectado |
| `probability` | Integer | Nivel de probabilidad (1–5) |
| `impact` | Integer | Nivel de impacto compuesto (1–5) |
| `impact_operational` / `_financial` / `_normative` / `_reputational` | String | Impactos desglosados |
| `status` | String | pending, assessed, approved |

#### `escenario_hallazgos`
Relación muchos-a-muchos entre escenarios y hallazgos técnicos.

### Fase 4 — Evaluación de Riesgos (AI Gateway)

#### `risk_engine_runs`
| Columna | Tipo | Descripción |
| :--- | :--- | :--- |
| `project_id` | UUID | Referencia al proyecto |
| `ai_provider` | String | openai, anthropic, gemini, ollama |
| `model_used` | String | Modelo específico |
| `status` | String | Estado del análisis |
| `findings_input_count` | Integer | Hallazgos evaluados |
| `risks_generated_count` | Integer | Riesgos generados |
| `tokens_used` | Integer | Tokens consumidos |
| `cost_usd` | Float | Costo estimado |

#### `risks`
| Columna | Tipo | Descripción |
| :--- | :--- | :--- |
| `project_id` | UUID | Referencia al proyecto |
| `risk_code` | String | Código (R-001, etc.) |
| `risk_title` | String | Título del riesgo de negocio |
| `probability` | Integer | Probabilidad (1–5) |
| `impact` | Integer | Impacto (1–5) |
| `risk_score` | Float | Puntuación total |
| `risk_level` | String | critical, high, medium, low |
| `affected_cia` | JSON | Impacto CIA |
| `methodology` | String | iso_31000 |
| `status` | String | open, in_progress, mitigated, accepted |
| `residual_score` | Float | Puntaje residual post-tratamiento |

#### `risk_treatments`
| Columna | Tipo | Descripción |
| :--- | :--- | :--- |
| `risk_id` | UUID | Referencia al riesgo |
| `treatment_type` | String | mitigate, avoid, transfer, accept |
| `owner_name` | String | Responsable |
| `due_date` | DateTime | Fecha límite |
| `priority` | String | immediate, short_term, medium_term, long_term |
| `status` | String | planned, in_progress, completed, cancelled |
| `expected_risk_reduction` | Float | Reducción esperada |

*También existe `risk_finding_links` (muchos-a-muchos entre riesgos y hallazgos).*

### Fase 5 — Monitoreo Continuo

#### `trigger_events`
| Columna | Tipo | Descripción |
| :--- | :--- | :--- |
| `project_id` | UUID | Referencia al proyecto |
| `event_type` | String | new_critical_vuln, new_system, incident, regulatory_change, etc. |
| `description` | Text | Descripción del evento |
| `detected_at` | DateTime | Fecha de detección |

#### `review_cycles`
| Columna | Tipo | Descripción |
| :--- | :--- | :--- |
| `project_id` | UUID | Referencia al proyecto |
| `cycle_type` | String | annual, biennial, triggered |
| `triggered_by` | UUID | Evento desencadenante (opcional) |
| `status` | String | pending, in_progress, completed |
| `summary` | JSON | Resumen del ciclo |

#### `risk_indicators`
| Columna | Tipo | Descripción |
| :--- | :--- | :--- |
| `project_id` | UUID | Referencia al proyecto |
| `period` | String | Período (ej. 2026-Q3) |
| `pending_critical_high` | Integer | Riesgos críticos/altos pendientes |
| `actions_on_time_pct` | Float | % de acciones a tiempo |
| `incidents_count` | Integer | Incidentes en el período |
| `normative_status` | JSON | Estado normativo por regulación |

## ⚙️ Requisitos Previos

- [Docker](https://www.docker.com/) y Docker Compose.
- `make` (opcional, pero fuertemente recomendado).

## 🛠️ Instalación y Uso

1. **Clonar el repositorio:**
   ```bash
   git clone https://github.com/tu-usuario/wscan.git
   cd wscan
   ```

2. **Levantar los servicios:**
   Se copia automáticamente `.env.example` a `.env` si no existe y se construyen los contenedores.
   ```bash
   make up
   ```

   Al arrancar, el backend ejecuta automáticamente:
   - Creación de tablas (`create_tables`)
   - Migraciones (`alembic upgrade head`)
   - Datos iniciales (`seed_auto`)
   - Catálogo de cuestionarios (`seed_questionnaire` — carga el cuestionario ISO 31000 v1 con 17 preguntas, bloques A–D)

3. **Configurar la IA (Opcional):**
   Para usar modelos en la nube (Claude, Gemini, OpenAI), añade tu API key desde `/settings` en el frontend o directamente en `.env`.

   Para usar Ollama en local (privacidad total del código, sin coste de API), descomenta el servicio `ollama` en `docker-compose.yml`, levanta de nuevo los contenedores y descarga el modelo por defecto:
   ```bash
   docker compose up -d ollama
   make ollama-pull
   ```

4. **Acceso a los servicios:**
   | Servicio | URL | Credenciales por defecto |
   | :--- | :--- | :--- |
   | Frontend | http://localhost:3000 | — |
   | Backend API Docs | http://localhost:8000/docs | — |
   | Scanner Manager | http://localhost:8001/docs | — |
   | AI Gateway | http://localhost:8002/docs | — |
   | SonarQube | http://localhost:9000 | admin / admin |

   > SonarQube tarda 1-2 minutos en arrancar la primera vez (bootstrap de Elasticsearch). `scanner-manager` genera su token de análisis automáticamente contra `admin`/`admin` la primera vez que lo necesita — cambia esa contraseña en la UI de SonarQube si expones el puerto fuera de tu máquina.

## 📖 Comandos Útiles (`Makefile`)

| Comando | Descripción |
| :--- | :--- |
| `make up` | Levanta todos los contenedores en segundo plano |
| `make down` | Detiene y elimina los contenedores |
| `make logs` | Sigue (tail) los logs de los microservicios principales |
| `make build` | Reconstruye las imágenes de Docker sin caché |
| `make migrate` | Aplica migraciones de base de datos manualmente |
| `make seed` | Carga datos de prueba y usuario administrador |
| `make status` | Muestra el estado de los contenedores (`docker compose ps`) |
| `make health` | Verifica el estado de salud de todas las APIs y SonarQube |
| `make clean` | Apaga todo y destruye los volúmenes. **¡Úsalo con precaución!** |
| `make sonar-token` | Genera un token global de análisis para SonarQube |
| `make backend-shell` | Abre una shell bash en el contenedor del backend |
| `make test-backend` | Ejecuta la suite de tests del backend (`pytest`) |
| `make ollama-pull` | Descarga el modelo Llama3.2 en Ollama |

## 🚀 Despliegue en Producción

WicScan se despliega como un stack de contenedores Docker Compose. Para una instalación expuesta a internet u otros usuarios (no solo `localhost`), ten en cuenta lo siguiente:

### 1. Variables de entorno

Copia `.env.example` a `.env` y cambia **todos** los valores por defecto antes de desplegar:

| Variable | Por qué cambiarla |
| :--- | :--- |
| `SECRET_KEY` | Firma los JWT de sesión. Genera una aleatoria: `openssl rand -hex 32` |
| `POSTGRES_PASSWORD` | Contraseña de la base de datos principal |
| `REDIS_PASSWORD` | Si Redis queda accesible fuera de la red interna de Docker |
| `SONARQUBE_ADMIN_PASSWORD` | Cámbiala en la UI de SonarQube tras el primer arranque y refléjalo aquí |
| `MOBSF_API_KEY` | Solo si usas el adaptador MobSF (análisis móvil) |

Nunca subas tu `.env` real a un repositorio (ya está en `.gitignore`).

### 2. Exposición de servicios

Por defecto, `docker-compose.yml` publica los puertos de **todos** los servicios (backend, scanner-manager, ai-gateway, postgres, redis, sonarqube...) directamente en el host. En un servidor de producción:

- Coloca un **reverse proxy con TLS** (Nginx, Caddy o Traefik) delante del `frontend` (3000) y el `backend` (8000), y expón solo esos dos puertos (443/80) al exterior.
- Restringe o elimina el mapeo de puertos (`ports:`) de `postgres`, `redis`, `scanner-manager`, `ai-gateway` y `sonarqube` en el compose de producción — solo necesitan ser alcanzables entre sí dentro de la red `wicscan_net`, no desde fuera del host.
- Actualiza `NEXT_PUBLIC_API_URL` / `NEXT_PUBLIC_WS_URL` en el servicio `frontend` para que apunten al dominio público, no a `localhost`.

### 3. Persistencia y backups

Todos los datos viven en volúmenes con nombre (`postgres_data`, `redis_data`, `uploads_data`, `sonarqube_data`, `sonarqube_extensions`, `mobsf_data`). Como mínimo, programa un backup periódico de `postgres_data` (o mejor, de un `pg_dump` lógico) y de `uploads_data`.

### 4. Recursos y escalado

- SonarQube (Elasticsearch embebido) necesita al menos ~2 GB de RAM disponibles para arrancar de forma estable.
- El `worker` de Celery se puede escalar horizontalmente: `docker compose up -d --scale worker=3`.
- Si usas Ollama local, resérvale GPU o RAM dedicada (ver bloque comentado del servicio `ollama` en `docker-compose.yml`).

### 5. Checklist rápido antes de publicar

```bash
make build      # imágenes limpias, sin caché
make up          # levanta el stack
make health       # verifica que todos los servicios respondan
```

## 🤝 Contribución

¡Las contribuciones son bienvenidas! Por favor, abre un *issue* o envía un *pull request* con tus sugerencias o mejoras.

## 📝 Licencia

Este proyecto está bajo la Licencia MIT - mira el archivo [LICENSE](LICENSE) para más detalles.
