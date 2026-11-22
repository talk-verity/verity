import base64
import json
from threading import BoundedSemaphore
from uuid import UUID
from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from starlette.concurrency import run_in_threadpool
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.auth.deps import get_current_user
from app.core.settings import settings
from app.models.user import User
from app.voice.service import VoiceService
from database import get_db

router = APIRouter(prefix="/voice", tags=["voice"])
_slots = BoundedSemaphore(settings.VOICE_CONCURRENCY)

def get_voice_service():
    return VoiceService()

async def read_audio(file):
    try:
        data = await file.read(settings.MAX_AUDIO_BYTES + 1)
        if not data or len(data) > settings.MAX_AUDIO_BYTES:
            raise HTTPException(413, f"Audio must be nonempty and at most {settings.MAX_AUDIO_BYTES / 1024 / 1024:g} MB")
        return data
    finally:
        await file.close()

def acquire():
    if not _slots.acquire(blocking=False):
        raise HTTPException(429, "Voice service is busy. Try again shortly.", headers={"Retry-After": "3"})

@router.post("/stt")
async def transcribe(file: UploadFile, current_user: User = Depends(get_current_user),
                     service: VoiceService = Depends(get_voice_service)):
    acquire()
    try:
        data = await read_audio(file)
        text = await run_in_threadpool(service.transcribe, data)
        return {"text": text}
    finally:
        _slots.release()

class SpeechRequest(BaseModel):
    text: str = Field(min_length=1, max_length=8000)

@router.post("/tts")
async def synthesize(body: SpeechRequest, current_user: User = Depends(get_current_user),
                     service: VoiceService = Depends(get_voice_service)):
    acquire()
    try:
        audio = await service.synthesize(body.text)
        return StreamingResponse(iter([audio]), media_type="application/octet-stream")
    finally:
        _slots.release()

@router.post("/converse")
async def converse(file: UploadFile, session_id: str = Form(...), request_id: UUID = Form(...),
                   current_user: User = Depends(get_current_user), db: Session = Depends(get_db),
                   service: VoiceService = Depends(get_voice_service)):
    # Authorization happens before expensive processing and before streaming headers.
    session = await run_in_threadpool(service.conversation.get_session, db, session_id, current_user.id)
    if session.status != "active":
        raise HTTPException(409, "Session is not active")
    user_id = current_user.id
    acquire()
    try:
        audio_data = await read_audio(file)
    except BaseException:
        _slots.release()
        raise

    async def event_stream():
        try:
            async for kind, data in service.converse(db, user_id, session_id, audio_data, request_id=str(request_id)):
                if kind == "audio":
                    data = base64.b64encode(data).decode()
                yield f"event: {kind}\ndata: {json.dumps({'type': kind, 'data': data})}\n\n"
            yield "event: done\ndata: {}\n\n"
        except HTTPException as exc:
            yield f"event: error\ndata: {json.dumps({'message': exc.detail})}\n\n"
        except Exception:
            import logging
            logging.getLogger(__name__).exception("Voice stream failed")
            yield 'event: error\ndata: {"message":"Voice request failed. Please retry."}\n\n'
        finally:
            _slots.release()
    return StreamingResponse(event_stream(), media_type="text/event-stream", headers={
        "Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
