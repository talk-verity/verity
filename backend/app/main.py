from app.admin.router import router as admin_router
from fastapi import FastAPI, Request
from contextlib import asynccontextmanager
from starlette.concurrency import run_in_threadpool
import logging
import uuid
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.auth.routes import router as auth_router
from app.conversations.router import router as conversations_router
from app.core.settings import settings
from app.feedback.router import router as feedback_router
from app.reports.router import router as reports_router
from app.voice.router import router as voice_router

@asynccontextmanager
async def lifespan(app):
    if settings.STT_PROVIDER == "parakeet":
        from app.voice.stt import get_stt_service
        await run_in_threadpool(get_stt_service().warmup)
    if settings.TTS_PROVIDER == "kokoro":
        from app.voice.tts import get_tts_service
        await run_in_threadpool(get_tts_service().warmup)
    yield

docs_enabled = settings.DEBUG
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan,
    docs_url="/docs" if docs_enabled else None,
    redoc_url="/redoc" if docs_enabled else None,
    openapi_url="/openapi.json" if docs_enabled else None,
)
from app.core.body_limit import BodyLimitMiddleware
app.add_middleware(BodyLimitMiddleware, max_bytes=settings.MAX_AUDIO_BYTES + 65536)

if "*" in settings.BACKEND_CORS_ORIGINS:
    raise RuntimeError("Wildcard CORS origins are not allowed with credentialed requests")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-Delphi-Referral"],
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
    response.headers.setdefault("Cross-Origin-Resource-Policy", "same-origin")
    if request.url.scheme == "https":
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    return response

app.include_router(admin_router, prefix=settings.API_V1_PREFIX)
app.include_router(auth_router, prefix=settings.API_V1_PREFIX)
app.include_router(conversations_router, prefix=settings.API_V1_PREFIX)
app.include_router(voice_router, prefix=settings.API_V1_PREFIX)
app.include_router(feedback_router, prefix=settings.API_V1_PREFIX)
app.include_router(reports_router, prefix=settings.API_V1_PREFIX)


@app.get("/health")
def health():
    from database import check_db_connection
    db_ready = check_db_connection()
    configured = bool(settings.DEMO_MODE or (settings.GROQ_API_KEY or settings.GEMINI_API_KEY))
    ready = db_ready and configured
    return JSONResponse(status_code=200 if ready else 503, content={
        "status": "ready" if ready else "unavailable", "database": db_ready,
        "conversation_configured": configured, "demo_mode": settings.DEMO_MODE})

@app.get("/live")
def live():
    return {"status": "alive"}


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    request_id = str(uuid.uuid4())
    logging.getLogger(__name__).error("Unhandled request error %s", request_id, exc_info=exc)
    return JSONResponse(status_code=500, content={"detail": "Internal server error", "request_id": request_id})
