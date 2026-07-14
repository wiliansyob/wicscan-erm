from fastapi import APIRouter
from app.api.v1 import auth, projects, assets, scans, risks, findings, scanners
from app.api.v1.findings import vuln_export_router
from app.api.v1 import code_sources, scan_sessions, workspaces, treatments
from app.modules.admin.catalog.router import router as catalog_router
from app.modules.contexto.bia.router import router as bia_router
from app.modules.escenarios.router import router as escenarios_router
from app.modules.analisis.router import router as analisis_router
from app.modules.tratamiento.plan.router import router as treatment_plan_router
from app.modules.tratamiento.monitoreo.router import router as monitoring_router

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(projects.router)
api_router.include_router(assets.router)
api_router.include_router(code_sources.router)
api_router.include_router(scan_sessions.router)
api_router.include_router(scans.router)
api_router.include_router(risks.router)
api_router.include_router(findings.router)
api_router.include_router(vuln_export_router)
api_router.include_router(treatments.router)
api_router.include_router(workspaces.router)
api_router.include_router(scanners.router)
# Contexto (F1-F2)
api_router.include_router(catalog_router)
api_router.include_router(bia_router)
# Escenarios (SC-xxx) — F3
api_router.include_router(escenarios_router)
# Análisis — registro de riesgos (RN-xxx)
api_router.include_router(analisis_router)
# Tratamiento + monitoreo
api_router.include_router(treatment_plan_router)
api_router.include_router(monitoring_router)
