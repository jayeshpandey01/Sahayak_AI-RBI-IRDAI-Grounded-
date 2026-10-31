"""End-to-End Voice-to-Voice and Dual-Modal Voice Agent Orchestrator.

Conforms to rag_docs.md specifications, .agents/skills/rag-implementation,
and .agents/skills/clean-code standards.
Connects Sarvam AI STT & TTS with Sahayak AI's source-grounded RAG pipeline (RBI, IRDAI, NPCI).
"""

import base64
import logging
import time
from typing import Any, Dict, List, Optional, Tuple

import httpx
from sqlalchemy.orm import Session

from app.ai.guardrails import check_underwriting_guardrails
from app.ai.intent_parser import extract_intent_slots
from app.ai.provider_clients import (
    generate_grounded_answer,
    providers_enabled,
    sanitize_provider_text,
    synthesize_speech,
    transcribe_audio,
    translate_query_to_english,
)
from app.ai.rag_engine import query_grounded_rag
from app.ai.rate_limits import reserve_chat_request
from app.api.chat import _contains_untrusted_number, _localized_fallback, _validated_citations
from app.models.db_models import JourneyModel, UserModel
from app.models.schemas import (
    ConversationTurn,
    GroundedCitation,
    GroundedRAGResponse,
    LanguageCode,
    VoiceChatResponse,
    VoiceChatTimingBreakdown,
)
from app.services.profile_loan_advice import build_loan_profile_reply, is_loan_profile_question

logger = logging.getLogger("sahayak.ai.voice_agent")

ALLOWED_AUDIO_TYPES = {
    "audio/wav", "audio/x-wav", "audio/mpeg", "audio/mp4", "audio/x-m4a",
    "audio/aac", "audio/ogg", "audio/webm", "audio/flac",
    "video/webm", "video/mp4", "application/octet-stream",
}


def normalize_content_type(content_type: Optional[str]) -> str:
    """Normalize MIME type by stripping parameters like ;codecs=opus."""
    if not content_type:
        return ""
    return content_type.split(";")[0].strip().lower()


def detect_audio_signature(audio: bytes) -> Optional[str]:
    """Detect actual audio format from magic bytes."""
    if audio.startswith(b"RIFF") and len(audio) > 12 and audio[8:12] == b"WAVE":
        return "audio/wav"
    if audio.startswith(b"ID3") or (len(audio) > 1 and audio[0] == 0xFF and audio[1] & 0xE0 == 0xE0):
        return "audio/mpeg"
    if (len(audio) > 12 and audio[4:8] == b"ftyp") or (len(audio) > 1 and audio[0] == 0xFF and audio[1] & 0xF6 == 0xF0):
        return "audio/mp4"
    if audio.startswith(b"OggS"):
        return "audio/ogg"
    if audio.startswith(bytes.fromhex("1a45dfa3")):
        return "audio/webm"
    if audio.startswith(b"fLaC"):
        return "audio/flac"
    return None


def matches_audio_signature(audio: bytes, content_type: str) -> bool:
    """Validate magic bytes to prevent MIME spoofing before processing."""
    norm_ct = normalize_content_type(content_type)
    detected = detect_audio_signature(audio)
    if detected is not None:
        if norm_ct == detected or norm_ct in ALLOWED_AUDIO_TYPES:
            return True
    return False


async def process_voice_chat(
    audio_bytes: bytes,
    content_type: str,
    language: LanguageCode,
    allow_external_processing: bool,
    db: Session,
    journey: Optional[JourneyModel] = None,
    current_user: Optional[UserModel] = None,
    conversation: Optional[List[ConversationTurn]] = None,
    client_ip: str = "anonymous",
    client_transcript: Optional[str] = None,
) -> VoiceChatResponse:
    """Full Voice-to-Voice pipeline: STT -> Guardrails -> RAG -> LLM -> TTS -> Response."""
    start_total = time.perf_counter()
    timings = VoiceChatTimingBreakdown()
    conversation_turns = conversation or []

    # Auto-detect audio signature if client-declared MIME is generic or mismatched
    detected_type = detect_audio_signature(audio_bytes)
    if detected_type:
        content_type = detected_type

    # 1. Speech-to-Text (STT) Stage
    t0 = time.perf_counter()
    transcript = ""
    # Use client-recognized transcript if provided (from real-time speech recognition)
    if client_transcript and client_transcript.strip():
        transcript = client_transcript.strip()
    else:
        extension = {
            "audio/wav": "wav", "audio/x-wav": "wav", "audio/mpeg": "mp3",
            "audio/mp4": "m4a", "audio/x-m4a": "m4a", "audio/aac": "aac",
            "audio/ogg": "ogg", "audio/webm": "webm", "audio/flac": "flac",
        }.get(content_type, "wav")

        try:
            transcript = await transcribe_audio(
                audio=audio_bytes,
                filename=f"voice-query.{extension}",
                content_type=content_type,
                language=language,
            )
        except Exception as exc:
            logger.warning("stt_transcription_failed: %s", exc)
            transcript = ""
    timings.stt_ms = int((time.perf_counter() - t0) * 1000)

    if not transcript or not transcript.strip():
        fallback_msg = _localized_fallback(language)
        audio_b64 = None
        if allow_external_processing and providers_enabled():
            try:
                t_tts = time.perf_counter()
                synth = await synthesize_speech(fallback_msg, language)
                audio_b64 = base64.b64encode(synth).decode("ascii")
                timings.tts_ms = int((time.perf_counter() - t_tts) * 1000)
            except Exception:
                pass
        timings.total_ms = int((time.perf_counter() - start_total) * 1000)
        return VoiceChatResponse(
            transcript="",
            reply_text=fallback_msg,
            audio_base64=audio_b64,
            content_type="audio/mpeg",
            language=language,
            timings=timings,
            requires_user_review=True,
        )

    # Profile questions use the same owner-scoped DB answer as text chat.
    if is_loan_profile_question(transcript):
        if current_user:
            profile_reply = build_loan_profile_reply(db, current_user.id, transcript, language, journey)
        else:
            profile_reply = {
                LanguageCode.EN: "Please sign in so I can answer from the loan records saved to your account.",
                LanguageCode.HI: "आपके खाते में सेव loan records के आधार पर जवाब देने के लिए कृपया sign in करें।",
                LanguageCode.MR: "तुमच्या खात्यातील loan records वरून उत्तर देण्यासाठी कृपया sign in करा.",
                LanguageCode.HINGLISH: "Aapke account ke saved loan records se jawab dene ke liye please sign in karein.",
            }[language]
        audio_b64 = None
        if allow_external_processing and providers_enabled():
            try:
                t_tts = time.perf_counter()
                audio_b64 = base64.b64encode(await synthesize_speech(profile_reply, language)).decode("ascii")
                timings.tts_ms = int((time.perf_counter() - t_tts) * 1000)
            except Exception:
                pass
        timings.total_ms = int((time.perf_counter() - start_total) * 1000)
        return VoiceChatResponse(
            transcript=transcript, reply_text=profile_reply, audio_base64=audio_b64,
            content_type="audio/mpeg", language=language, timings=timings,
            requires_user_review=False,
        )

    # 2. Guardrails & Intent Check
    is_blocked, refusal_text, handoff = check_underwriting_guardrails(transcript)
    if is_blocked:
        if journey and handoff:
            journey.human_review_required = True
            journey.human_review_reason = "User requested an underwriting decision via voice."
            db.commit()

        localized_refusal = {
            LanguageCode.EN: refusal_text or _localized_fallback(language),
            LanguageCode.HI: "Sahayak आपकी ऋण पात्रता का आकलन या ऋणदाता का निर्णय नहीं कर सकता। निर्णय की पुष्टि केवल ऋणदाता कर सकता है।",
            LanguageCode.MR: "Sahayak तुमची कर्ज पात्रता ठरवू शकत नाही किंवा कर्जदात्याचा निर्णय सांगू शकत नाही. निर्णयाची पुष्टी फक्त कर्जदाता करू शकतो.",
            LanguageCode.HINGLISH: "Sahayak aapki loan eligibility assess ya lender ka decision predict nahi kar sakta. Decision sirf lender confirm kar sakta hai.",
        }.get(language, refusal_text or _localized_fallback(language))

        # Generate voice audio for the refusal response if external processing enabled
        audio_b64 = None
        if allow_external_processing and providers_enabled():
            t_tts = time.perf_counter()
            try:
                refusal_audio = await synthesize_speech(localized_refusal, language)
                audio_b64 = base64.b64encode(refusal_audio).decode("ascii")
            except Exception:
                pass
            timings.tts_ms = int((time.perf_counter() - t_tts) * 1000)

        timings.total_ms = int((time.perf_counter() - start_total) * 1000)
        return VoiceChatResponse(
            transcript=transcript,
            reply_text=localized_refusal,
            audio_base64=audio_b64,
            language=language,
            timings=timings,
            human_handoff=handoff,
            requires_user_review=True,
        )

    slot_result = extract_intent_slots(transcript)

    # 3. Grounded RAG Retrieval Stage
    t_rag = time.perf_counter()
    retrieval_query = sanitize_provider_text(transcript)
    translated_query = None

    if allow_external_processing and providers_enabled():
        actor = f"user:{current_user.id}" if current_user else f"ip:{client_ip}"
        try:
            reserve_chat_request(db, actor)
        except Exception:
            pass

        try:
            translated_query = await translate_query_to_english(retrieval_query, language)
        except Exception:
            pass

    rag_info = query_grounded_rag(retrieval_query, translated_query)
    timings.rag_ms = int((time.perf_counter() - t_rag) * 1000)

    if not rag_info:
        fallback_msg = _localized_fallback(language)
        audio_b64 = None
        if allow_external_processing and providers_enabled():
            try:
                t_tts = time.perf_counter()
                synth = await synthesize_speech(fallback_msg, language)
                audio_b64 = base64.b64encode(synth).decode("ascii")
                timings.tts_ms = int((time.perf_counter() - t_tts) * 1000)
            except Exception:
                pass
        timings.total_ms = int((time.perf_counter() - start_total) * 1000)
        return VoiceChatResponse(
            transcript=transcript,
            reply_text=fallback_msg,
            audio_base64=audio_b64,
            content_type="audio/mpeg",
            language=language,
            slot_updates=slot_result,
            timings=timings,
            requires_user_review=True,
        )

    # 4. LLM Grounded Answer Generation Stage
    t_llm = time.perf_counter()
    reply_text = rag_info.answer
    safe_rag = rag_info

    if allow_external_processing and providers_enabled():
        turns = [{"role": turn.role, "content": turn.content} for turn in conversation_turns[-6:]]
        try:
            result = await generate_grounded_answer(
                question=transcript,
                language=language,
                citations=[c.model_dump() for c in rag_info.citations],
                conversation=turns,
            )
            if result and not result.uncertainty:
                valid_cites = _validated_citations(rag_info, result.citation_ids)
                if valid_cites and not _contains_untrusted_number(result.answer, valid_cites):
                    reply_text = result.answer
                    safe_rag = GroundedRAGResponse(
                        answer=result.answer,
                        citations=valid_cites,
                        source_documents=sorted({f"{item.document_name} ({item.version})" for item in valid_cites}),
                        confidence=rag_info.confidence,
                        disclaimer=rag_info.disclaimer,
                    )
        except Exception as exc:
            logger.warning("llm_grounded_generation_failed: %s", exc)
    timings.llm_ms = int((time.perf_counter() - t_llm) * 1000)

    # 5. Text-to-Speech (TTS) Voice Synthesis Stage
    t_tts = time.perf_counter()
    audio_base64 = None
    if allow_external_processing and providers_enabled():
        try:
            synth_bytes = await synthesize_speech(reply_text, language)
            audio_base64 = base64.b64encode(synth_bytes).decode("ascii")
        except Exception as exc:
            logger.warning("tts_synthesis_failed: %s", exc)
    timings.tts_ms = int((time.perf_counter() - t_tts) * 1000)

    timings.total_ms = int((time.perf_counter() - start_total) * 1000)
    return VoiceChatResponse(
        transcript=transcript,
        reply_text=reply_text,
        audio_base64=audio_base64,
        content_type="audio/mpeg",
        language=language,
        rag_info=safe_rag,
        timings=timings,
        slot_updates=slot_result,
        requires_user_review=False,
    )


async def process_text_chat(
    message: str,
    language: LanguageCode,
    allow_external_processing: bool,
    db: Session,
    journey: Optional[JourneyModel] = None,
    current_user: Optional[UserModel] = None,
    conversation: Optional[List[ConversationTurn]] = None,
    include_audio: bool = False,
    client_ip: str = "anonymous",
) -> VoiceChatResponse:
    """Dual-modal text chat pipeline with optional TTS voice generation."""
    start_total = time.perf_counter()
    timings = VoiceChatTimingBreakdown()
    conversation_turns = conversation or []

    if is_loan_profile_question(message):
        if current_user:
            profile_reply = build_loan_profile_reply(db, current_user.id, message, language, journey)
        else:
            profile_reply = {
                LanguageCode.EN: "Please sign in so I can answer from the loan records saved to your account.",
                LanguageCode.HI: "आपके खाते में सेव loan records के आधार पर जवाब देने के लिए कृपया sign in करें।",
                LanguageCode.MR: "तुमच्या खात्यातील loan records वरून उत्तर देण्यासाठी कृपया sign in करा.",
                LanguageCode.HINGLISH: "Aapke account ke saved loan records se jawab dene ke liye please sign in karein.",
            }[language]
        audio_b64 = None
        if include_audio and allow_external_processing and providers_enabled():
            try:
                t_tts = time.perf_counter()
                audio_b64 = base64.b64encode(await synthesize_speech(profile_reply, language)).decode("ascii")
                timings.tts_ms = int((time.perf_counter() - t_tts) * 1000)
            except Exception:
                pass
        timings.total_ms = int((time.perf_counter() - start_total) * 1000)
        return VoiceChatResponse(
            transcript=message, reply_text=profile_reply, audio_base64=audio_b64,
            content_type="audio/mpeg", language=language, timings=timings,
        )

    # 1. Guardrails Check
    is_blocked, refusal_text, handoff = check_underwriting_guardrails(message)
    if is_blocked:
        if journey and handoff:
            journey.human_review_required = True
            journey.human_review_reason = "User requested underwriting advice."
            db.commit()
        localized_refusal = {
            LanguageCode.EN: refusal_text or _localized_fallback(language),
            LanguageCode.HI: "Sahayak आपकी ऋण पात्रता का आकलन या ऋणदाता का निर्णय नहीं कर सकता। निर्णय की पुष्टि केवल ऋणदाता कर सकता है।",
            LanguageCode.MR: "Sahayak तुमची कर्ज पात्रता ठरवू शकत नाही किंवा कर्जदात्याचा निर्णय सांगू शकत नाही. निर्णयाची पुष्टी फक्त कर्जदाता करू शकतो.",
            LanguageCode.HINGLISH: "Sahayak aapki loan eligibility assess ya lender ka decision predict nahi kar sakta. Decision sirf lender confirm kar sakta hai.",
        }.get(language, refusal_text or _localized_fallback(language))

        audio_b64 = None
        if include_audio and allow_external_processing and providers_enabled():
            try:
                audio_bytes = await synthesize_speech(localized_refusal, language)
                audio_b64 = base64.b64encode(audio_bytes).decode("ascii")
            except Exception:
                pass

        timings.total_ms = int((time.perf_counter() - start_total) * 1000)
        return VoiceChatResponse(
            transcript=message,
            reply_text=localized_refusal,
            audio_base64=audio_b64,
            language=language,
            timings=timings,
            human_handoff=handoff,
        )

    slot_result = extract_intent_slots(message)

    # 2. Grounded RAG Retrieval
    t_rag = time.perf_counter()
    retrieval_query = sanitize_provider_text(message)
    translated_query = None

    if allow_external_processing and providers_enabled():
        actor = f"user:{current_user.id}" if current_user else f"ip:{client_ip}"
        try:
            reserve_chat_request(db, actor)
        except Exception:
            pass

        try:
            translated_query = await translate_query_to_english(retrieval_query, language)
        except Exception:
            pass

    rag_info = query_grounded_rag(retrieval_query, translated_query)
    timings.rag_ms = int((time.perf_counter() - t_rag) * 1000)

    if not rag_info:
        fallback_msg = _localized_fallback(language)
        audio_b64 = None
        if include_audio and allow_external_processing and providers_enabled():
            try:
                t_tts = time.perf_counter()
                synth = await synthesize_speech(fallback_msg, language)
                audio_b64 = base64.b64encode(synth).decode("ascii")
                timings.tts_ms = int((time.perf_counter() - t_tts) * 1000)
            except Exception:
                pass
        timings.total_ms = int((time.perf_counter() - start_total) * 1000)
        return VoiceChatResponse(
            transcript=message,
            reply_text=fallback_msg,
            audio_base64=audio_b64,
            content_type="audio/mpeg",
            language=language,
            slot_updates=slot_result,
            timings=timings,
        )

    # 3. LLM Grounded Answer Generation
    t_llm = time.perf_counter()
    reply_text = rag_info.answer
    safe_rag = rag_info

    if allow_external_processing and providers_enabled():
        turns = [{"role": turn.role, "content": turn.content} for turn in conversation_turns[-6:]]
        try:
            result = await generate_grounded_answer(
                question=message,
                language=language,
                citations=[c.model_dump() for c in rag_info.citations],
                conversation=turns,
            )
            if result and not result.uncertainty:
                valid_cites = _validated_citations(rag_info, result.citation_ids)
                if valid_cites and not _contains_untrusted_number(result.answer, valid_cites):
                    reply_text = result.answer
                    safe_rag = GroundedRAGResponse(
                        answer=result.answer,
                        citations=valid_cites,
                        source_documents=sorted({f"{item.document_name} ({item.version})" for item in valid_cites}),
                        confidence=rag_info.confidence,
                        disclaimer=rag_info.disclaimer,
                    )
        except Exception as exc:
            logger.warning("llm_text_generation_failed: %s", exc)
    timings.llm_ms = int((time.perf_counter() - t_llm) * 1000)

    # 4. Optional TTS Voice Synthesis
    audio_b64 = None
    if include_audio and allow_external_processing and providers_enabled():
        t_tts = time.perf_counter()
        try:
            synth_bytes = await synthesize_speech(reply_text, language)
            audio_b64 = base64.b64encode(synth_bytes).decode("ascii")
        except Exception as exc:
            logger.warning("tts_synthesis_failed: %s", exc)
        timings.tts_ms = int((time.perf_counter() - t_tts) * 1000)

    timings.total_ms = int((time.perf_counter() - start_total) * 1000)
    return VoiceChatResponse(
        transcript=message,
        reply_text=reply_text,
        audio_base64=audio_b64,
        content_type="audio/mpeg",
        language=language,
        rag_info=safe_rag,
        timings=timings,
        slot_updates=slot_result,
    )

