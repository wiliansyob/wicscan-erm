import time
import uuid
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from app.api.v1.router import api_router
from app.config import get_settings
from app.database import engine, get_db
from app.worker.celery_app import celery_app
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

settings = get_settings()
log = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("wicscan_startup", version=settings.APP_VERSION, env=settings.ENVIRONMENT)
    yield
    await engine.dispose()
    log.info("wicscan_shutdown")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
    default_response_class=ORJSONResponse,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> Response:
    """Catch unhandled exceptions and return 500 WITH CORS headers.
    Without this, Starlette's ServerErrorMiddleware sends the 500 before
    CORSMiddleware can add the header, causing browser CORS failures."""
    origin = request.headers.get("origin", "")
    cors_headers: dict[str, str] = {}
    if origin in settings.CORS_ORIGINS:
        cors_headers = {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
        }
    log.error("unhandled_exception", path=str(request.url.path), error=repr(exc)[:200])
    return ORJSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
        headers=cors_headers,
    )


@app.middleware("http")
async def request_logger(request: Request, call_next) -> Response:
    correlation_id = str(uuid.uuid4())
    request.state.correlation_id = correlation_id
    t0 = time.monotonic()

    response = await call_next(request)

    duration_ms = int((time.monotonic() - t0) * 1000)
    log.info(
        "http_request",
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        duration_ms=duration_ms,
        correlation_id=correlation_id,
    )
    response.headers["X-Correlation-ID"] = correlation_id
    return response


app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/health", tags=["ops"])
async def health(db: AsyncSession = Depends(get_db)):
    status = {
        "status": "ok", 
        "version": settings.APP_VERSION, 
        "postgres": "checking", 
        "redis_celery": "checking",
        "installed_scanners": ["sonarqube", "zap"] # Solo reportamos los que realmente están instalados
    }
    
    # Check Postgres
    try:
        await db.execute(text("SELECT 1"))
        status["postgres"] = "ok"
    except Exception as e:
        status["postgres"] = "error"
        status["status"] = "error"
        
    # Check Redis/Celery Broker
    try:
        with celery_app.connection_for_read() as conn:
            conn.default_channel.client.ping()
        status["redis_celery"] = "ok"
    except Exception as e:
        try:
            # Fallback simple ping if the above fails
            celery_app.control.ping(timeout=1.0)
            status["redis_celery"] = "ok"
        except Exception:
            status["redis_celery"] = "error"
            status["status"] = "error"
            
    return status
