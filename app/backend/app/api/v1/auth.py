from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.config import get_settings
from app.core.exceptions import ConflictError, UnauthorizedError
from app.core.security import create_access_token, hash_password, verify_password
from app.database import get_db
from app.models.workspace import Workspace
from app.models.user import User
from app.models.scanner import ScannerEngine
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none():
        raise ConflictError("Email already registered")

    workspace = Workspace(name=payload.workspace_name)
    db.add(workspace)
    await db.flush()

    user = User(
        workspace_id=workspace.id,
        email=payload.email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
    )
    db.add(user)

    default_scanners = [
        ScannerEngine(workspace_id=workspace.id, name="MobSF", engine_type="mobsf", url="http://mobsf:8000", is_active=True),
        ScannerEngine(workspace_id=workspace.id, name="SonarQube", engine_type="sonarqube", url="http://sonarqube:9000", is_active=True),
        ScannerEngine(workspace_id=workspace.id, name="OWASP ZAP", engine_type="zap", url="http://zap:8080", is_active=True),
        ScannerEngine(workspace_id=workspace.id, name="Scanner IA", engine_type="ai_review", url="http://ai-gateway:8002", is_active=True),
    ]
    db.add_all(default_scanners)

    await db.flush()

    token = create_access_token(user.id, {"workspace_id": str(workspace.id)})
    return TokenResponse(
        access_token=token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(payload.password, user.password_hash):
        raise UnauthorizedError("Invalid credentials")
    if not user.is_active:
        raise UnauthorizedError("Account is disabled")

    user.last_login = datetime.now(timezone.utc)
    token = create_access_token(user.id, {"workspace_id": str(user.workspace_id)})
    return TokenResponse(
        access_token=token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser):
    return user
