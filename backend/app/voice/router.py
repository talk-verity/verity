import json

from fastapi import APIRouter, Depends, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.models.user import User
from app.voice.service import VoiceService
from database import get_db

router = APIRouter(prefix="/voice", tags=["voice"])


def get_voice_service() -> VoiceService:
    return VoiceService()


@router.post("/stt")
def transcribe(
    file: UploadFile,
    current_user: User = Depends(get_current_user),
    service: VoiceService = Depends(get_voice_service),
):
    audio_data = file.file.read()
    text = service.transcribe(audio_data)
    return {"text": text}


@router.post("/tts")
async def synthesize(
    text: str,
    current_user: User = Depends(get_current_user),
    service: VoiceService = Depends(get_voice_service),
):
    audio = await service.synthesize(text)
    return StreamingResponse(
        iter([audio]),
        media_type="audio/wav",
        headers={"Content-Disposition": "inline; filename=response.wav"},
    )


@router.post("/converse")
async def converse(
    file: UploadFile,
    session_id: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: VoiceService = Depends(get_voice_service),
):
    audio_data = await file.read()

    sid = session_id or service.get_or_create_session(db, current_user.id)

    async def event_stream():
        async for event_type, data in service.converse(db, current_user.id, sid, audio_data):
            if event_type == "audio":
                import base64
                payload = json.dumps({"type": "audio", "data": base64.b64encode(data).decode()})
                yield f"event: audio\ndata: {payload}\n\n"
            else:
                payload = json.dumps({"type": event_type, "data": data})
                yield f"event: {event_type}\ndata: {payload}\n\n"
        yield "event: done\ndata: {}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
