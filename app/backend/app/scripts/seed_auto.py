"""Auto-seed: creates default user only if the users table is empty."""
import asyncio
from sqlalchemy import select, func
from app.database import AsyncSessionLocal
from app.models.workspace import Workspace
from app.models.user import User
from app.models.project import Project
from app.models.asset import Asset
from app.models.scanner import ScannerEngine
from app.core.security import hash_password

DEFAULT_SCANNERS = [
    {"name": "SonarQube",   "engine_type": "sonarqube",  "category": "sast", "url": "http://sonarqube:9000"},
    {"name": "OWASP ZAP",   "engine_type": "zap",        "category": "dast", "url": "http://zap:8080"},
    {"name": "Scanner IA",  "engine_type": "AI_REVIEW",  "category": "ia",   "url": "http://ai-gateway:8002"},
    {"name": "Nuclei",      "engine_type": "nuclei",     "category": "dast", "url": "http://nuclei:9100"},
    {"name": "OpenVAS",     "engine_type": "openvas",    "category": "vuln", "url": "http://openvas-api:9200"},
    {"name": "Semgrep",     "engine_type": "semgrep",    "category": "sast", "url": "local"},
    {"name": "MobSF",       "engine_type": "mobsf",      "category": "sast", "url": "http://wicscan_mobsf:8000"},
]


async def _seed_scanners(db, workspace_id) -> None:
    for s in DEFAULT_SCANNERS:
        exists = (await db.execute(
            select(func.count(ScannerEngine.id)).where(
                ScannerEngine.workspace_id == workspace_id,
                func.lower(ScannerEngine.engine_type) == s["engine_type"].lower(),
            )
        )).scalar() or 0
        if not exists:
            db.add(ScannerEngine(
                workspace_id=workspace_id,
                name=s["name"],
                engine_type=s["engine_type"],
                category=s["category"],
                url=s["url"],
                is_active=True,
            ))
            print(f"  Scanner seeded: {s['name']}")
    await db.commit()


async def main() -> None:
    async with AsyncSessionLocal() as db:
        count = (await db.execute(select(func.count(User.id)))).scalar() or 0
        if count > 0:
            # Existing install — only ensure default scanners exist
            workspace = (await db.execute(select(Workspace).limit(1))).scalar_one_or_none()
            if workspace:
                await _seed_scanners(db, workspace.id)
            print(f"Seed skipped — {count} user(s) already exist.")
            return

        workspace = Workspace(name="Demo Workspace", description="Local development workspace")
        db.add(workspace)
        await db.flush()

        user = User(
            workspace_id=workspace.id,
            email="ciso@wicscan.local",
            password_hash=hash_password("wicscan123"),
            full_name="CISO Admin",
            is_active=True,
        )
        db.add(user)
        await db.flush()

        project = Project(
            workspace_id=workspace.id,
            name="Demo Project",
            description="Proyecto de demostración",
            risk_appetite="medium",
        )
        db.add(project)
        await db.flush()

        asset = Asset(
            project_id=project.id,
            name="Demo Application",
            asset_type="webapp",
            criticality="medium",
            is_active=True,
        )
        db.add(asset)
        await db.flush()

        await _seed_scanners(db, workspace.id)
        print(f"Auto-seed complete: {user.email} / wicscan123")


if __name__ == "__main__":
    asyncio.run(main())
