from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.auth.routes import router as auth_router
from app.conversations.router import router as conversations_router
from app.core.settings import settings
from app.feedback.router import router as feedback_router
from app.reports.router import router as reports_router
from app.voice.router import router as voice_router

app = FastAPI(title=settings.PROJECT_NAME, version=settings.VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix=settings.API_V1_PREFIX)
app.include_router(conversations_router, prefix=settings.API_V1_PREFIX)
app.include_router(voice_router, prefix=settings.API_V1_PREFIX)
app.include_router(feedback_router, prefix=settings.API_V1_PREFIX)
app.include_router(reports_router, prefix=settings.API_V1_PREFIX)


def _warmup() -> None:
    try:
        from app.voice.stt import get_stt_service
        stt = get_stt_service()
        if hasattr(stt, "warmup"):
            stt.warmup()
    except Exception as e:
        print(f"[startup] STT warmup skipped: {e}")

    try:
        from app.voice.tts import get_tts_service
        tts = get_tts_service()
        if hasattr(tts, "warmup"):
            tts.warmup()
    except Exception as e:
        print(f"[startup] TTS warmup skipped: {e}")


@app.on_event("startup")
def warmup_on_startup() -> None:
    import threading
    threading.Thread(target=_warmup, daemon=True).start()


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"detail": str(exc)})
