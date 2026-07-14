from app.models.workspace import Workspace
from app.models.user import User
from app.models.project import Project
from app.models.asset import Asset
from app.models.code_source import CodeSource
from app.models.scan import ScanSession, Scan, RetestComparison
from app.models.scanner import ScannerEngine
from app.models.finding import Finding
from app.models.risk import Risk, RiskTreatment, risk_finding_links

# Module models — imported so Base.metadata is complete when create_tables.py
# calls metadata.create_all() and Alembic resolves cross-module FK references.
from app.modules.admin.catalog.models import *  # noqa: F401,F403
from app.modules.contexto.bia.models import *  # noqa: F401,F403
from app.modules.escenarios.models import *  # noqa: F401,F403
from app.modules.tratamiento.monitoreo.models import *  # noqa: F401,F403

__all__ = [
    "Workspace",
    "User",
    "Project",
    "Asset",
    "CodeSource",
    "ScanSession",
    "Scan",
    "RetestComparison",
    "ScannerEngine",
    "Finding",
    "Risk",
    "RiskTreatment",
    "risk_finding_links",
]
