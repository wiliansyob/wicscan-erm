# WicScan Risk Manager

Plataforma de gestión de riesgos de seguridad en aplicaciones. Correlaciona hallazgos técnicos (SAST/DAST/IA) con impacto de negocio y genera un flujo de riesgo alineado con ISO 31000, en 5 fases: Contextualización, Identificación, Análisis, Evaluación y Tratamiento.

Stack: FastAPI + PostgreSQL + Redis/Celery (backend), Next.js (frontend), microservicios separados para orquestación de escáneres (`scanner-manager`) y proveedores de IA (`ai-gateway`). Todo corre en Docker Compose.

## Requisitos

- Docker y Docker Compose
- `make` (opcional pero recomendado)

## Puesta en marcha (desarrollo)

```bash
git clone https://github.com/wiliansyob/wicscan-erm.git
cd wicscan-erm
make up
```

`make up` copia `.env.example` a `.env` (si no existe) y levanta los contenedores. Al arrancar, el backend ejecuta automáticamente: creación de tablas, migraciones (`alembic upgrade head`), datos iniciales (`seed_auto`) y el catálogo de cuestionarios ISO 31000 (`seed_questionnaire`).

Servicios expuestos:

| Servicio | URL | Credenciales por defecto |
| :--- | :--- | :--- |
| Frontend | http://localhost:3000 | — |
| Backend API Docs | http://localhost:8000/docs | — |
| Scanner Manager | http://localhost:8001/docs | — |
| AI Gateway | http://localhost:8002/docs | — |
| SonarQube | http://localhost:9000 | admin / admin |

SonarQube tarda 1-2 minutos en arrancar (bootstrap de Elasticsearch). `scanner-manager` genera su token de análisis automáticamente contra `admin`/`admin` la primera vez que lo necesita; cambia esa contraseña en la UI de SonarQube si expones el puerto fuera de tu máquina.

### IA (opcional)

- Modelos en la nube (Claude, Gemini, OpenAI): añade la API key desde `/settings` en el frontend, o directamente en `.env`.
- Ollama local (sin coste de API, todo el análisis queda en tu máquina): descomenta el servicio `ollama` en `docker-compose.yml` y luego:
  ```bash
  docker compose up -d ollama
  make ollama-pull
  ```

## Comandos (`Makefile`)

| Comando | Descripción |
| :--- | :--- |
| `make up` | Levanta todos los contenedores en segundo plano |
| `make down` | Detiene y elimina los contenedores |
| `make logs` | Sigue los logs de backend, worker, scanner-manager, ai-gateway |
| `make build` | Reconstruye las imágenes sin caché |
| `make migrate` | Aplica migraciones de base de datos manualmente |
| `make seed` | Carga datos de prueba y usuario administrador |
| `make status` | `docker compose ps` |
| `make health` | Verifica el estado de las APIs y de SonarQube |
| `make clean` | Apaga todo y destruye los volúmenes (irreversible) |
| `make sonar-token` | Genera un token global de análisis para SonarQube |
| `make backend-shell` | Shell bash en el contenedor del backend |
| `make test-backend` | Ejecuta la suite de tests del backend (`pytest`) |
| `make ollama-pull` | Descarga el modelo Llama3.2 en Ollama |

## Despliegue en producción

### 1. Variables de entorno

Copia `.env.example` a `.env` y cambia todos los valores por defecto:

| Variable | Motivo |
| :--- | :--- |
| `SECRET_KEY` | Firma los JWT de sesión. Generar con `openssl rand -hex 32` |
| `POSTGRES_PASSWORD` | Contraseña de la base de datos principal |
| `REDIS_PASSWORD` | Necesaria si Redis queda accesible fuera de la red interna de Docker |
| `SONARQUBE_ADMIN_PASSWORD` | Cambiar también en la UI de SonarQube tras el primer arranque |
| `MOBSF_API_KEY` | Solo si se usa el adaptador MobSF (análisis móvil) |

`.env` ya está en `.gitignore` — nunca lo subas a un repositorio.

### 2. Exposición de servicios

Por defecto el compose publica los puertos de todos los servicios (backend, scanner-manager, ai-gateway, postgres, redis, sonarqube) directamente en el host. En un servidor expuesto a internet:

- Pon un reverse proxy con TLS (Nginx, Caddy o Traefik) delante de `frontend` (3000) y `backend` (8000); expón solo 443/80 al exterior.
- Quita el mapeo `ports:` de `postgres`, `redis`, `scanner-manager`, `ai-gateway` y `sonarqube` en el compose de producción — solo necesitan verse entre sí dentro de la red `wicscan_net`.
- Actualiza `NEXT_PUBLIC_API_URL` / `NEXT_PUBLIC_WS_URL` en el servicio `frontend` para que apunten al dominio público, no a `localhost`.

### 3. Persistencia y backups

Volúmenes con datos: `postgres_data`, `redis_data`, `uploads_data`, `sonarqube_data`, `sonarqube_extensions`, `mobsf_data`. Como mínimo, backup periódico de `postgres_data` (o un `pg_dump` lógico) y de `uploads_data`.

### 4. Recursos

- SonarQube (Elasticsearch embebido) necesita ~2 GB de RAM libres para arrancar de forma estable.
- El worker de Celery escala horizontalmente: `docker compose up -d --scale worker=3`.
- Ollama local necesita GPU o RAM dedicada (bloque comentado en `docker-compose.yml`).

### 5. Checklist antes de publicar

```bash
make build
make up
make health
```

## Arquitectura

- **Frontend**: Next.js 14, TypeScript, TailwindCSS, React Query, Recharts.
- **Backend**: FastAPI, SQLAlchemy async, PostgreSQL, Redis, Celery. Lógica de dominio en `app/modules/` (contexto, identification, escenarios, analisis, tratamiento, admin/catalog, assessment/scoring).
- **Scanner Manager**: microservicio que orquesta y normaliza escaneos de SonarQube.
- **AI Gateway**: microservicio de comunicación estandarizada con proveedores de IA (OpenAI, Anthropic, Gemini, Ollama).
- **Infraestructura**: Docker Compose, volumen local para uploads (evidencias/reportes).

## Fases (ISO 31000)

| Fase | Descripción | Rutas |
| :--- | :--- | :--- |
| 1 — Contextualización | BIA por proceso de negocio | `/contexto/bia` |
| 2 — Identificación | Escaneo de activos y fuentes de código | `/activos`, `/scans`, `/identificacion` |
| 3 — Análisis | Escenarios, probabilidad e impacto | `/escenarios`, `/probabilidad`, `/impacto` |
| 4 — Evaluación | Riesgos de negocio priorizados con IA | `/analisis` |
| 5 — Tratamiento | Planes de tratamiento, ciclos de revisión, reporte | `/tratamiento`, `/reporte` |

## Esquema de base de datos

PostgreSQL. Todas las tablas incluyen `id` (UUID), `created_at`, `updated_at`.

<details>
<summary>Gestión de usuarios y proyectos</summary>

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

</details>

<details>
<summary>Escaneos y hallazgos (Fase 2)</summary>

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

</details>

<details>
<summary>Contextualización (Fase 1)</summary>

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

</details>

<details>
<summary>Escenarios y análisis (Fase 3)</summary>

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

</details>

<details>
<summary>Evaluación de riesgos — AI Gateway (Fase 4)</summary>

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

También existe `risk_finding_links` (muchos-a-muchos entre riesgos y hallazgos).

</details>

<details>
<summary>Monitoreo continuo (Fase 5)</summary>

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

</details>

## Contribución

Issues y pull requests bienvenidos.

## Licencia

MIT — ver [LICENSE](LICENSE).
