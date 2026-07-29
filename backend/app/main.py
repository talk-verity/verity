from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.auth.routes import router as auth_router
from app.conversations.router import router as conversations_router
from app.core.settings import settings
from app.feedback.router import router as feedback_router
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


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"detail": str(exc)})
