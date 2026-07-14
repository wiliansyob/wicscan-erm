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

## ⚙️ Requisitos Previos

- [Docker](https://www.docker.com/) y Docker Compose.
- `make` (opcional, pero fuertemente recomendado).

## 🛠️ Instalación y Uso

1. **Clonar el repositorio:**
   ```bash
   git clone https://github.com/wiliansyob/wicscan-erm.git
   cd wicscan-erm
   ```

2. **Levantar los servicios:**
   ```bash
   make up
   ```
   Equivale a `cp .env.example .env` (solo si `.env` no existe todavía) + `docker compose up -d`. Si prefieres no usar `make`, copia `.env.example` a `.env` manualmente y ejecuta `docker compose up -d`.

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

## 🚀 Despliegue en Producción

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

