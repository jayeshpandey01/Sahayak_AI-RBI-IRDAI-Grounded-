import base64
import logging
import re
from decimal import Decimal
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.ai.guardrails import check_underwriting_guardrails
from app.ai.intent_parser import extract_intent_slots
from app.ai.provider_clients import (
    generate_grounded_answer,
    sanitize_provider_text,
    synthesize_speech,
    translate_query_to_english,
)
from app.ai.rag_engine import query_grounded_rag
from app.ai.rate_limits import AIRateLimitExceeded, reserve_chat_request
from app.api.dependencies import get_optional_current_user
from app.api.journeys import verify_journey_ownership
from app.ai.provider_clients import providers_enabled
from app.config import settings
from app.database import get_db
from app.models.db_models import (
    JourneyModel, UserModel, PaymentOrderModel, WalletLedgerEntryModel,
    PaymentAIConsentAuditModel,
)
from app.services.credit_score_service import build_payment_behaviour_estimate
from app.services.profile_loan_advice import build_loan_profile_reply, is_loan_profile_question
from app.models.schemas import (
    ChatInputRequest,
    ChatResponse,
    GroundedCitation,
    GroundedRAGResponse,
    LanguageCode,
)

router = APIRouter(prefix="/api/chat", tags=["AI Copilot & Guardrails"])
logger = logging.getLogger("sahayak.ai")
_NUMBERS = re.compile(r"\d+(?:[,.]\d+)*")
_SCORE_QUESTION = re.compile(
    r"\b(cibil|civil|credit\s*score|score\s*(?:mera|my|please|batao|tell)|mera\s+score|my\s+score|"
    r"what(?:'s| is)\s+(?:my\s+)?(?:credit\s+)?score|give\s+me\s+(?:my\s+)?(?:credit\s+)?score|"
    r"tell\s+me\s+(?:my\s+)?(?:credit\s+)?score)\b|"
    r"(क्रेडिट\s*स्कोर|सिबिल|सिविल\s*स्कोर|स्कोअर|माझा\s+स्कोर)", re.IGNORECASE,
)
def _score_question_reply(estimate: dict, language: LanguageCode) -> str:
    if language == LanguageCode.MR:
        if estimate["score"] is None:
            return "तुमचा अधिकृत CIBIL स्कोअर मला उपलब्ध नाही. या अॅपमध्ये सध्या कर्जाच्या हप्त्यांचा पडताळलेला इतिहास नाही. वॉलेट टॉप-अपवरून CIBIL स्कोअर ठरत नाही. हा क्रेडिट ब्युरो स्कोअर किंवा कर्ज मंजुरीचा अंदाज नाही."
        return (f"तुमचा Sahayak डेमो पेमेंट-वर्तन निर्देशांक {estimate['score']}/900 आहे. "
                f"तो फक्त {estimate['repayment_count']} कृत्रिम हप्ता नोंदींवर आधारित आहे; हा अधिकृत CIBIL स्कोअर किंवा कर्ज मंजुरीचा अंदाज नाही.")
    if language == LanguageCode.HI:
        if estimate["score"] is None:
            return "मुझे आपका आधिकारिक CIBIL स्कोर उपलब्ध नहीं है। इस ऐप में अभी सत्यापित ऋण किस्तों का इतिहास नहीं है; वॉलेट टॉप-अप CIBIL स्कोर नहीं बताता। यह कोई क्रेडिट-ब्यूरो स्कोर या ऋण स्वीकृति का अनुमान नहीं है।"
        return (f"आपका Sahayak डेमो भुगतान-व्यवहार संकेतक {estimate['score']}/900 है, "
                f"जो केवल {estimate['repayment_count']} सिंथेटिक किस्त रिकॉर्ड पर आधारित है। यह आधिकारिक CIBIL स्कोर नहीं है और ऋण स्वीकृति नहीं बताता।")
    if language == LanguageCode.HINGLISH:
        if estimate["score"] is None:
            return "Mujhe aapka official CIBIL score available nahi hai. App mein abhi verified loan EMI history nahi hai; wallet top-ups CIBIL score nahi batate. Yeh bureau score ya loan approval prediction nahi hai."
        return (f"Aapka Sahayak demo payment-behaviour indicator {estimate['score']}/900 hai, "
                f"jo sirf {estimate['repayment_count']} synthetic EMI records par based hai. Yeh official CIBIL score nahi hai aur loan approval nahi batata.")
    if estimate["score"] is None:
        return "I can’t access your official CIBIL score. This app currently has no verified loan-repayment history; wallet top-ups do not establish a credit score. This is not a bureau score or a loan-approval prediction."
    return (f"Your Sahayak demo payment-behaviour indicator is {estimate['score']}/900, "
            f"based only on {estimate['repayment_count']} synthetic repayment records. "
            "It is not an official CIBIL score and does not predict loan approval.")


def _localized_fallback(language: LanguageCode, consent_required: bool = False) -> str:
    if consent_required:
        return {
            LanguageCode.EN: "To get an AI-generated explanation, first allow this chat message to be processed by our configured AI provider. Your chat is not saved by Sahayak.",
            LanguageCode.HI: "AI से जवाब पाने के लिए पहले इस चैट संदेश को हमारे चुने हुए AI प्रदाता से प्रोसेस करने की अनुमति दें। Sahayak आपकी चैट सेव नहीं करता।",
            LanguageCode.MR: "AI कडून स्पष्टीकरण मिळवण्यासाठी हा चॅट संदेश आमच्या AI सेवा प्रदात्याकडे प्रक्रिया करण्याची परवानगी द्या. Sahayak तुमचा चॅट जतन करत नाही.",
            LanguageCode.HINGLISH: "AI explanation ke liye pehle is chat message ko hamare selected AI provider se process karne ki permission dein. Sahayak chat save nahi karta.",
        }[language]
    return {
        LanguageCode.EN: "I don't have a reliable approved source for that answer right now. I can help you find the relevant step or connect you with a person.",
        LanguageCode.HI: "इस जवाब के लिए मेरे पास अभी भरोसेमंद, स्वीकृत जानकारी नहीं है। मैं सही चरण ढूँढने या किसी व्यक्ति से जोड़ने में मदद कर सकता हूँ।",
        LanguageCode.MR: "या प्रश्नासाठी माझ्याकडे सध्या विश्वसनीय आणि मंजूर माहिती नाही. योग्य पायरी शोधण्यात किंवा मदतीसाठी व्यक्तीशी जोडण्यात मी मदत करू शकतो.",
        LanguageCode.HINGLISH: "Is jawab ke liye mere paas abhi reliable approved source nahi hai. Main relevant step dhoondhne ya kisi person se connect karne mein help kar sakta hoon.",
    }[language]


def _localized_provider_unavailable(language: LanguageCode) -> str:
    return {
        LanguageCode.EN: "Sahayak's AI service is temporarily unavailable. I can't give a grounded answer right now; please try again later or ask a person for help.",
        LanguageCode.HI: "Sahayak की AI सेवा अभी उपलब्ध नहीं है। मैं इस समय स्रोत-आधारित जवाब नहीं दे सकता। कृपया बाद में फिर कोशिश करें या किसी व्यक्ति से सहायता लें।",
        LanguageCode.MR: "Sahayak ची AI सेवा सध्या उपलब्ध नाही. मी आत्ता स्रोतांवर आधारित उत्तर देऊ शकत नाही. कृपया नंतर पुन्हा प्रयत्न करा किंवा व्यक्तीची मदत घ्या.",
        LanguageCode.HINGLISH: "Sahayak ki AI service abhi available nahi hai. Main abhi source-based jawab nahi de sakta. Baad mein try karein ya kisi person se help lein.",
    }[language]


def _localized_handoff(language: LanguageCode) -> str:
    return {
        LanguageCode.EN: "I can't predict or make a lender's decision. Please contact the lender or ask our support team for verified guidance.",
        LanguageCode.HI: "इस अनुरोध के लिए किसी व्यक्ति की सहायता चाहिए। मैं आपकी ओर से वित्तीय निर्णय नहीं ले सकता।",
        LanguageCode.MR: "या विनंतीसाठी व्यक्तीची मदत आवश्यक आहे. मी तुमच्या वतीने आर्थिक निर्णय घेऊ शकत नाही.",
        LanguageCode.HINGLISH: "Is request ke liye kisi person ki help chahiye. Main aapke liye financial decision nahi le sakta.",
    }[language]


def _payment_status_reply(summary: dict, language: LanguageCode) -> str:
    amount = f"₹{summary['amount_paise'] // 100}.{summary['amount_paise'] % 100:02d}"
    provider = "Stripe" if summary.get("provider") == "stripe" else "payment provider"
    payment_status = summary["status"]
    if payment_status == "SUCCEEDED" and summary["wallet_credit_recorded"]:
        return {
            LanguageCode.EN: f"{provider} confirms this payment, and the wallet ledger records {amount} as credited.",
            LanguageCode.HI: f"{provider} ने इस भुगतान की पुष्टि की है और वॉलेट लेज़र में {amount} जमा दर्ज है।",
            LanguageCode.MR: f"{provider} ने या पेमेंटची पुष्टी केली आहे आणि वॉलेट लेजरमध्ये {amount} जमा नोंदवले आहे.",
            LanguageCode.HINGLISH: f"{provider} ne payment confirm kiya hai, aur wallet ledger mein {amount} credit dikh raha hai.",
        }[language]
    if payment_status == "SUCCEEDED":
        return {
            LanguageCode.EN: f"{provider} reports success, but the wallet ledger has no matching credit. Contact support before retrying.",
            LanguageCode.HI: f"{provider} ने भुगतान सफल बताया है, लेकिन वॉलेट लेज़र में जमा दर्ज नहीं है। दोबारा भुगतान करने से पहले सहायता से संपर्क करें।",
            LanguageCode.MR: f"{provider} ने पेमेंट यशस्वी असल्याचे सांगितले आहे, पण वॉलेट लेजरमध्ये जमा नोंद नाही. पुन्हा प्रयत्न करण्यापूर्वी मदतीशी संपर्क साधा.",
            LanguageCode.HINGLISH: f"{provider} payment successful bata raha hai, lekin wallet ledger mein credit nahi hai. Retry se pehle support se baat karein.",
        }[language]
    if payment_status in ("CREATED", "REQUIRES_ACTION", "PROCESSING"):
        return {
            LanguageCode.EN: f"This payment is still being confirmed. The wallet is credited only after {provider} verifies success.",
            LanguageCode.HI: f"इस भुगतान की पुष्टि अभी हो रही है। {provider} की सफलता की पुष्टि के बाद ही वॉलेट में राशि जमा होगी।",
            LanguageCode.MR: f"या पेमेंटची पुष्टी सुरू आहे. {provider} यशाची पुष्टी केल्यानंतरच वॉलेटमध्ये रक्कम जमा होईल.",
            LanguageCode.HINGLISH: f"Payment abhi confirm ho raha hai. {provider} success verify hone ke baad hi wallet credit hoga.",
        }[language]
    if payment_status == "RECONCILIATION_REQUIRED":
        return {
            LanguageCode.EN: "This payment needs support review. The wallet has not been credited.",
            LanguageCode.HI: "इस भुगतान की सहायता टीम से जाँच ज़रूरी है। वॉलेट में राशि जमा नहीं हुई है।",
            LanguageCode.MR: "या पेमेंटची मदत पथकाकडून तपासणी आवश्यक आहे. वॉलेटमध्ये रक्कम जमा झालेली नाही.",
            LanguageCode.HINGLISH: "Is payment ko support review chahiye. Wallet credit nahi hua hai.",
        }[language]
    return {
        LanguageCode.EN: f"{provider} did not confirm this payment, so no wallet credit was posted.",
        LanguageCode.HI: f"{provider} ने इस भुगतान की पुष्टि नहीं की, इसलिए वॉलेट में राशि जमा नहीं हुई।",
        LanguageCode.MR: f"{provider} ने या पेमेंटची पुष्टी केली नाही, त्यामुळे वॉलेटमध्ये रक्कम जमा झाली नाही.",
        LanguageCode.HINGLISH: f"{provider} ne payment confirm nahi kiya, isliye wallet credit nahi hua.",
    }[language]


def _validated_citations(rag_info: GroundedRAGResponse, citation_ids: list[str]) -> list[GroundedCitation]:
    allowed = {item.citation_id: item for item in rag_info.citations}
    if not citation_ids or any(item not in allowed for item in citation_ids):
        return []
    return [allowed[item] for item in dict.fromkeys(citation_ids)]


def _normalize_num(s: str) -> str:
    cleaned = s.replace(",", "")
    if cleaned.isdigit():
        return str(int(cleaned))
    try:
        f = float(cleaned)
        return str(int(f)) if f.is_integer() else str(f)
    except ValueError:
        return cleaned


def _contains_untrusted_number(answer: str, cited: list[GroundedCitation]) -> bool:
    allowed = set()
    for item in cited:
        for text in (
            item.snippet,
            item.clause,
            item.version,
            item.document_name,
            getattr(item, "effective_from", None) or "",
        ):
            allowed.update(_normalize_num(number) for number in _NUMBERS.findall(text))
    generated = {_normalize_num(number) for number in _NUMBERS.findall(answer)}
    return not generated.issubset(allowed)


@router.post("", response_model=ChatResponse)
async def handle_chat_message(
    payload: ChatInputRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[UserModel] = Depends(get_optional_current_user),
):
    journey = None
    if payload.journey_id:
        journey = db.query(JourneyModel).filter(JourneyModel.id == payload.journey_id).first()
        if not journey:
            raise HTTPException(status_code=404, detail="Journey not found")
        verify_journey_ownership(journey, current_user)

    if _SCORE_QUESTION.search(payload.message):
        if not current_user:
            raise HTTPException(status_code=401, detail="Sign in to view your payment-behaviour summary.")
        estimate = build_payment_behaviour_estimate(db, current_user.id)
        return ChatResponse(
            reply=_score_question_reply(estimate, payload.language),
            language=payload.language,
            payment_context=estimate,
        )

    # A product catalogue comparison is not a credit decision. Handle this safe,
    # deterministic request before the underwriting-prediction guardrail.
    if is_loan_profile_question(payload.message):
        if not current_user:
            raise HTTPException(status_code=401, detail="Sign in to compare catalogue options with your loan journey.")
        return ChatResponse(
            reply=build_loan_profile_reply(db, current_user.id, payload.message, payload.language, journey),
            language=payload.language,
            slot_updates=extract_intent_slots(payload.message),
        )

    payment_summary = None
    payment_citation = None
    if payload.include_payment_context:
        if not current_user:
            raise HTTPException(status_code=401, detail="Sign in to include payment context.")
        if not payload.payment_order_id:
            raise HTTPException(status_code=422, detail="payment_order_id is required with payment context.")
        payment_order = db.query(PaymentOrderModel).filter(
            PaymentOrderModel.id == payload.payment_order_id,
            PaymentOrderModel.user_id == current_user.id,
        ).first()
        if not payment_order:
            raise HTTPException(status_code=404, detail="Payment order not found.")
        credited = db.query(WalletLedgerEntryModel.id).filter(
            WalletLedgerEntryModel.payment_order_id == payment_order.id,
            WalletLedgerEntryModel.user_id == current_user.id,
        ).first() is not None
        payment_summary = {
            "order_id": payment_order.id, "amount_paise": payment_order.amount_paise,
            "currency": payment_order.currency.upper(), "provider": payment_order.provider,
            "status": payment_order.status,
            "wallet_credit_recorded": credited, "last_updated": payment_order.updated_at.isoformat(),
        }
        if payload.allow_external_processing and settings.AI_PAYMENT_CONTEXT_ENABLED and providers_enabled():
            consent = db.query(PaymentAIConsentAuditModel).filter(
                PaymentAIConsentAuditModel.user_id == current_user.id,
                PaymentAIConsentAuditModel.scope == "ai_payment_context_processing",
            ).order_by(PaymentAIConsentAuditModel.created_at.desc()).first()
            if not consent or not consent.is_granted:
                raise HTTPException(status_code=403, detail="Record separate payment-context AI consent before enabling external AI processing.")
            amount_rupees = f"{payment_order.amount_paise // 100}.{payment_order.amount_paise % 100:02d}"
            payment_citation = GroundedCitation(
                citation_id="verified_payment_order", document_name="Verified payment status",
                source_name="Sahayak verified payment record", version="server-verified",
                clause="Payment order status and wallet credit ledger",
                snippet=(f"Provider {payment_order.provider}; amount INR {amount_rupees}; status {payment_order.status}; "
                         f"wallet credit recorded: {str(credited).lower()}; updated {payment_order.updated_at.isoformat()}"),
                document_type="user_payment_record",
            )

    # Deterministic decision checks run before any provider call.
    is_blocked, refusal_text, handoff = check_underwriting_guardrails(payload.message)
    if is_blocked:
        if journey and handoff:
            journey.human_review_required = True
            journey.human_review_reason = "User requested an underwriting decision."
            db.commit()
        localized_refusal = {
            LanguageCode.EN: refusal_text or _localized_fallback(payload.language),
            LanguageCode.HI: "Sahayak आपकी ऋण पात्रता का आकलन या ऋणदाता का निर्णय नहीं कर सकता। निर्णय की पुष्टि केवल ऋणदाता कर सकता है। सही जानकारी के लिए आप किसी व्यक्ति से सहायता माँग सकते हैं।",
            LanguageCode.MR: "Sahayak तुमची कर्ज पात्रता ठरवू शकत नाही किंवा कर्जदात्याचा निर्णय सांगू शकत नाही. निर्णयाची पुष्टी फक्त कर्जदाता करू शकतो. अचूक माहितीसाठी व्यक्तीची मदत घ्या.",
            LanguageCode.HINGLISH: "Sahayak aapki loan eligibility assess ya lender ka decision predict nahi kar sakta. Decision sirf lender confirm kar sakta hai. Verified guidance ke liye aap kisi person se help maang sakte hain.",
        }[payload.language]
        return ChatResponse(reply=localized_refusal, language=payload.language, human_handoff=handoff)

    slot_result = extract_intent_slots(payload.message)
    if slot_result.route_to_human_queue:
        if journey:
            journey.human_review_required = True
            journey.human_review_reason = "User request requires human review."
            db.commit()
        return ChatResponse(reply=_localized_handoff(payload.language), language=payload.language, slot_updates=slot_result)

    if payment_summary and (not payment_citation or not payload.allow_external_processing or not providers_enabled()):
        return ChatResponse(
            reply=_payment_status_reply(payment_summary, payload.language),
            language=payload.language,
            slot_updates=slot_result,
            payment_context=payment_summary,
        )

    # Payment records enter model context only through the verified citation above,
    # after ownership, explicit request, purpose-specific consent and feature gates pass.
    retrieval_query = sanitize_provider_text(payload.message)
    external_requested = payload.allow_external_processing and providers_enabled()
    if external_requested:
        client_host = request.client.host if request.client else "anonymous"
        actor = f"user:{current_user.id}" if current_user else f"ip:{client_host}"
        try:
            reserve_chat_request(db, actor)
        except AIRateLimitExceeded as exc:
            raise HTTPException(
                status_code=429,
                detail="AI request limit reached. Please try again later.",
                headers={"Retry-After": str(exc.retry_after)},
            ) from None
        except Exception:
            logger.exception("ai_quota_unavailable")
            return ChatResponse(
                reply=_localized_provider_unavailable(payload.language),
                language=payload.language,
                slot_updates=slot_result,
            )

    translated_query = None
    if external_requested:
        try:
            translated_query = await translate_query_to_english(retrieval_query, payload.language)
        except (httpx.HTTPError, ValueError, KeyError):
            logger.info("ai_translation_unavailable")
            return ChatResponse(
                reply=_localized_provider_unavailable(payload.language),
                language=payload.language,
                slot_updates=slot_result,
            )

    rag_info = query_grounded_rag(retrieval_query, translated_query)
    if not rag_info and payment_citation:
        rag_info = GroundedRAGResponse(
            answer="Verified payment status context.", citations=[payment_citation],
            source_documents=[payment_citation.document_name], confidence=1.0,
            disclaimer="Payment status is read from Sahayak's verified order and ledger records.",
        )
    elif rag_info and payment_citation:
        rag_info.citations.append(payment_citation)
        rag_info.source_documents.append(payment_citation.document_name)
    if not rag_info:
        return ChatResponse(reply=_localized_fallback(payload.language), language=payload.language, slot_updates=slot_result)

    if not payload.allow_external_processing:
        return ChatResponse(
            reply=_localized_fallback(payload.language, consent_required=True),
            language=payload.language,
            slot_updates=slot_result,
            payment_context=payment_summary,
        )

    if not providers_enabled():
        return ChatResponse(
            reply=_localized_provider_unavailable(payload.language),
            language=payload.language,
            slot_updates=slot_result,
            payment_context=payment_summary,
        )

    turns = [{"role": turn.role, "content": turn.content} for turn in payload.conversation]
    try:
        result = await generate_grounded_answer(
            question=payload.message,
            language=payload.language,
            citations=[citation.model_dump() for citation in rag_info.citations],
            conversation=turns,
        )
    except (httpx.HTTPError, KeyError, ValueError, IndexError, TypeError):
        logger.info("ai_provider_unavailable")
        result = None

    if result is None:
        return ChatResponse(reply=_localized_provider_unavailable(payload.language), language=payload.language, slot_updates=slot_result, payment_context=payment_summary)
    if result.uncertainty:
        return ChatResponse(reply=_localized_fallback(payload.language), language=payload.language, slot_updates=slot_result, payment_context=payment_summary)

    citations = _validated_citations(rag_info, result.citation_ids)
    if not citations or _contains_untrusted_number(result.answer, citations):
        logger.info("ai_output_rejected")
        return ChatResponse(reply=_localized_provider_unavailable(payload.language), language=payload.language, slot_updates=slot_result, payment_context=payment_summary)

    safe_rag = GroundedRAGResponse(
        answer=result.answer,
        citations=citations,
        source_documents=sorted({f"{item.document_name} ({item.version})" for item in citations}),
        confidence=rag_info.confidence,
        disclaimer=rag_info.disclaimer,
    )
    audio_b64 = None
    if payload.include_audio and external_requested:
        try:
            synth_bytes = await synthesize_speech(result.answer, payload.language)
            audio_b64 = base64.b64encode(synth_bytes).decode("ascii")
        except Exception:
            pass

    return ChatResponse(
        reply=result.answer,
        language=payload.language,
        slot_updates=slot_result,
        rag_info=safe_rag,
        payment_context=payment_summary,
        audio_base64=audio_b64,
    )
