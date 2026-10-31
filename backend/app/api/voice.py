import base64
import json
import logging
from pathlib import Path
from typing import Optional

import httpx
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.ai.provider_clients import providers_enabled, synthesize_speech, transcribe_audio
from app.ai.rate_limits import AIRateLimitExceeded, reserve_user_ai_request
from app.api.dependencies import get_optional_current_user
from app.api.journeys import verify_journey_ownership
from app.database import get_db
from app.models.db_models import JourneyModel, UserModel
from app.models.schemas import (
    ConversationTurn,
    LanguageCode,
    VoiceChatResponse,
    VoiceSynthesisResponse,
    VoiceTranscriptionResponse,
)
from app.services.voice_agent_service import (
    ALLOWED_AUDIO_TYPES,
    detect_audio_signature,
    matches_audio_signature,
    process_voice_chat,
)

router = APIRouter(prefix="/api/chat/voice", tags=["AI Voice"])
logger = logging.getLogger("sahayak.ai.voice")
MAX_AUDIO_BYTES = 10 * 1024 * 1024


def _matches_audio_signature(audio: bytes, content_type: str) -> bool:
    return matches_audio_signature(audio, content_type)


def _reserve_voice_quota(db: Session, request: Request, user: Optional[UserModel]) -> None:
    host = request.client.host if request.client else "anonymous"
    actor = f"user:{user.id}" if user else f"ip:{host}"
    try:
        reserve_user_ai_request(db, actor)
    except AIRateLimitExceeded as exc:
        raise HTTPException(
            status_code=429,
            detail="AI request limit reached. Please try again later.",
            headers={"Retry-After": str(exc.retry_after)},
        ) from None
    except Exception:
        logger.info("ai_voice_quota_unavailable")
        raise HTTPException(status_code=503, detail="Voice services are temporarily unavailable.") from None


@router.post("/transcribe", response_model=VoiceTranscriptionResponse)
async def transcribe_voice(
    request: Request,
    db: Session = Depends(get_db),
    file: UploadFile = File(...),
    language: LanguageCode = Form(...),
    allow_external_processing: bool = Form(True),
    current_user: Optional[UserModel] = Depends(get_optional_current_user),
):
    if not allow_external_processing:
        raise HTTPException(status_code=403, detail="External AI processing consent is required for transcription.")
    if not providers_enabled():
        raise HTTPException(status_code=503, detail="Voice services are not enabled.")

    raw_ct = file.content_type or ""
    norm_ct = raw_ct.split(";")[0].strip().lower()

    try:
        audio = await file.read(MAX_AUDIO_BYTES + 1)
    finally:
        await file.close()

    if not audio:
        raise HTTPException(status_code=422, detail="Audio content is empty.")
    if len(audio) > MAX_AUDIO_BYTES:
        raise HTTPException(status_code=413, detail="Audio must be at most 10 MB.")
    detected_type = detect_audio_signature(audio)
    effective_content_type = detected_type or (norm_ct if norm_ct in ALLOWED_AUDIO_TYPES else "audio/webm")
    if not detected_type and norm_ct not in ALLOWED_AUDIO_TYPES:
        raise HTTPException(status_code=415, detail="Unsupported audio format.")
    if not detected_type and not _matches_audio_signature(audio, norm_ct):
        raise HTTPException(status_code=415, detail="Audio content does not match its declared format.")

    _reserve_voice_quota(db, request, current_user)

    try:
        extension = {
            "audio/wav": "wav", "audio/x-wav": "wav", "audio/mpeg": "mp3",
            "audio/mp4": "m4a", "audio/x-m4a": "m4a", "audio/aac": "aac",
            "audio/ogg": "ogg", "audio/webm": "webm", "audio/flac": "flac",
        }.get(effective_content_type, "wav")
        transcript = await transcribe_audio(audio, f"voice-input.{extension}", effective_content_type, language)
    except httpx.HTTPStatusError as exc:
        logger.info("sarvam_transcription_provider_error status=%s", exc.response.status_code)
        raise HTTPException(status_code=502, detail="Speech recognition is temporarily unavailable.") from None
    except (httpx.HTTPError, RuntimeError, ValueError):
        logger.info("sarvam_transcription_unavailable")
        raise HTTPException(status_code=502, detail="Speech recognition is temporarily unavailable.") from None
    finally:
        del audio

    return {"transcript": transcript, "language": language.value, "requires_user_review": True}


@router.post("/speak", response_model=VoiceSynthesisResponse)
async def synthesize_voice(
    request: Request,
    db: Session = Depends(get_db),
    text: str = Form(..., max_length=2500),
    language: LanguageCode = Form(...),
    allow_external_processing: bool = Form(True),
    current_user: Optional[UserModel] = Depends(get_optional_current_user),
):
    if not allow_external_processing:
        raise HTTPException(status_code=403, detail="External AI processing consent is required for speech synthesis.")
    if not providers_enabled():
        raise HTTPException(status_code=503, detail="Voice services are not enabled.")
    if not text.strip():
        raise HTTPException(status_code=422, detail="Text is required.")

    _reserve_voice_quota(db, request, current_user)

    try:
        audio = await synthesize_speech(text.strip(), language)
    except httpx.HTTPStatusError as exc:
        logger.info("sarvam_speech_provider_error status=%s", exc.response.status_code)
        raise HTTPException(status_code=502, detail="Speech playback is temporarily unavailable.") from None
    except (httpx.HTTPError, RuntimeError, ValueError):
        logger.info("sarvam_speech_unavailable")
        raise HTTPException(status_code=502, detail="Speech playback is temporarily unavailable.") from None

    encoded = base64.b64encode(audio).decode("ascii")
    del audio
    return {"audio_base64": encoded, "content_type": "audio/mpeg", "language": language.value}


# -----------------------------------------------------------------------------
# UNIFIED E2E VOICE-TO-VOICE ENDPOINT
# -----------------------------------------------------------------------------

@router.post("/e2e", response_model=VoiceChatResponse)
@router.post("/voice-chat", response_model=VoiceChatResponse)
async def voice_chat_e2e(
    request: Request,
    db: Session = Depends(get_db),
    file: UploadFile = File(...),
    language: LanguageCode = Form(LanguageCode.EN),
    allow_external_processing: bool = Form(True),
    journey_id: Optional[str] = Form(None),
    conversation: Optional[str] = Form(None),
    client_transcript: Optional[str] = Form(None),
    current_user: Optional[UserModel] = Depends(get_optional_current_user),
):
    """End-to-End Voice-to-Voice: Audio In -> STT -> Grounded RAG -> LLM -> TTS -> Audio Out."""
    raw_ct = file.content_type or ""
    norm_ct = raw_ct.split(";")[0].strip().lower()

    try:
        audio = await file.read(MAX_AUDIO_BYTES + 1)
    finally:
        await file.close()

    if not audio:
        raise HTTPException(status_code=422, detail="Audio content is empty.")
    if len(audio) > MAX_AUDIO_BYTES:
        raise HTTPException(status_code=413, detail="Audio must be at most 10 MB.")
    detected_type = detect_audio_signature(audio)
    effective_content_type = detected_type or (norm_ct if norm_ct in ALLOWED_AUDIO_TYPES else "audio/webm")
    if not detected_type and norm_ct not in ALLOWED_AUDIO_TYPES:
        raise HTTPException(status_code=415, detail="Unsupported audio format.")
    if not detected_type and not matches_audio_signature(audio, norm_ct):
        raise HTTPException(status_code=415, detail="Audio content does not match its declared format.")

    journey = None
    if journey_id:
        journey = db.query(JourneyModel).filter(JourneyModel.id == journey_id).first()
        if not journey:
            raise HTTPException(status_code=404, detail="Journey not found")
        verify_journey_ownership(journey, current_user)

    conversation_turns: List[ConversationTurn] = []
    if conversation:
        try:
            raw_turns = json.loads(conversation)
            if isinstance(raw_turns, list):
                conversation_turns = [ConversationTurn(**t) for t in raw_turns]
        except Exception:
            pass

    client_ip = request.client.host if request.client else "anonymous"

    return await process_voice_chat(
        audio_bytes=audio,
        content_type=effective_content_type,
        language=language,
        allow_external_processing=allow_external_processing,
        db=db,
        journey=journey,
        current_user=current_user,
        conversation=conversation_turns,
        client_ip=client_ip,
        client_transcript=client_transcript,
    )


# -----------------------------------------------------------------------------
# INTERACTIVE BROWSER DEMO UI
# -----------------------------------------------------------------------------

@router.get("/demo", response_class=HTMLResponse)
async def voice_demo_page():
    """Serves the interactive dual-modal Chat + Voice demo application."""
    html_path = Path(__file__).resolve().parent.parent / "static" / "voice_demo.html"
    if html_path.exists():
        return HTMLResponse(content=html_path.read_text(encoding="utf-8"))
    return HTMLResponse("<h3>Voice Demo HTML template not found</h3>", status_code=404)


# -----------------------------------------------------------------------------
# REAL-TIME BIDIRECTIONAL WEBSOCKET STREAM
# -----------------------------------------------------------------------------

@router.websocket("/ws")
async def voice_websocket_stream(
    websocket: WebSocket,
    db: Session = Depends(get_db),
):
    """Bidirectional WebSocket for low-latency streaming of Voice-to-Voice and Chat."""
    await websocket.accept()
    language = LanguageCode.EN
    allow_external = True
    journey_id = None
    conversation_turns: List[ConversationTurn] = []

    try:
        while True:
            raw_msg = await websocket.receive_text()
            try:
                data = json.loads(raw_msg)
            except Exception:
                await websocket.send_json({"event": "error", "message": "Invalid JSON frame"})
                continue

            msg_type = data.get("type", "")

            # 1. Config / Session Initialization
            if msg_type == "init":
                lang_val = data.get("language", "en")
                try:
                    language = LanguageCode(lang_val)
                except ValueError:
                    language = LanguageCode.EN
                allow_external = bool(data.get("allow_external_processing", True))
                journey_id = data.get("journey_id")
                await websocket.send_json({"event": "ready", "language": language.value})
                continue

            # 2. Text Chat Turn over WebSocket
            if msg_type == "text":
                user_text = data.get("message", "").strip()
                if not user_text:
                    continue
                await websocket.send_json({"event": "processing", "type": "text"})
                
                from app.services.voice_agent_service import process_text_chat
                resp = await process_text_chat(
                    message=user_text,
                    language=language,
                    allow_external_processing=allow_external,
                    db=db,
                    conversation=conversation_turns,
                    include_audio=bool(data.get("include_audio", True)),
                )
                conversation_turns.append(ConversationTurn(role="user", content=user_text[:2000]))
                conversation_turns.append(ConversationTurn(role="assistant", content=resp.reply_text[:2000]))

                await websocket.send_json({
                    "event": "completed",
                    "transcript": user_text,
                    "reply_text": resp.reply_text,
                    "audio_base64": resp.audio_base64,
                    "rag_info": resp.rag_info.model_dump() if resp.rag_info else None,
                    "timings": resp.timings.model_dump(),
                })
                continue

            # 3. Audio Turn over WebSocket
            if msg_type == "audio":
                audio_b64 = data.get("data", "")
                content_type = data.get("content_type", "audio/webm")
                try:
                    audio_bytes = base64.b64decode(audio_b64)
                except Exception:
                    await websocket.send_json({"event": "error", "message": "Corrupted audio payload"})
                    continue

                await websocket.send_json({"event": "stt_started"})
                resp = await process_voice_chat(
                    audio_bytes=audio_bytes,
                    content_type=content_type,
                    language=language,
                    allow_external_processing=allow_external,
                    db=db,
                    conversation=conversation_turns,
                )
                if resp.transcript:
                    conversation_turns.append(ConversationTurn(role="user", content=resp.transcript[:2000]))
                    conversation_turns.append(ConversationTurn(role="assistant", content=resp.reply_text[:2000]))

                await websocket.send_json({
                    "event": "completed",
                    "transcript": resp.transcript,
                    "reply_text": resp.reply_text,
                    "audio_base64": resp.audio_base64,
                    "rag_info": resp.rag_info.model_dump() if resp.rag_info else None,
                    "timings": resp.timings.model_dump(),
                })
                continue

    except WebSocketDisconnect:
        logger.info("websocket_voice_client_disconnected")
    except Exception as exc:
        logger.warning("websocket_voice_stream_error: %s", exc)
        try:
            await websocket.close()
        except Exception:
            pass
