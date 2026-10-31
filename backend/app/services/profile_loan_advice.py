"""Owner-scoped DB context for conversational loan product questions."""

import re
from decimal import Decimal
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.ai.intent_parser import extract_intent_slots
from app.models.db_models import DemoRepaymentModel, JourneyModel, UserLoanModel
from app.models.schemas import LanguageCode
from app.services.loan_catalogue_service import list_loan_products


LOAN_PROFILE_QUESTION = re.compile(
    r"(?:which|what)\s+(?:loan|loans|loan options|products).{0,80}(?:can\s+i|get|take|eligible|available|profile)|"
    r"(?:loan|loans|loan options).{0,80}(?:my\s+profile|profile\s+me|according\s+to\s+my\s+profile)|"
    r"(?:मेरी|मेरे)\s+प्रोफाइल\s+(?:में|के\s+लिए).{0,80}लोन|"
    r"प्रोफाइल\s+के\s+अनुसार.{0,80}लोन|"
    r"(?:कौन\s+कौन|कौन-कौन|कौन)\s+(?:सा|से|सी)\s+लोन.{0,80}(?:ले|मिल|सकता|सकती)|"
    r"प्रोफाइल\s+(?:में|के\s+अनुसार).{0,60}कौन\s+कौन\s+से\s+लोन|"
    r"(?:कौन|कौन-कौन)\s+से\s+लोन.{0,80}(?:मेरी|मेरे)\s+प्रोफाइल|"
    r"(?:according\s+to|based\s+on|using|from)\s+(?:the\s+)?(?:db|database|my\s+profile|my\s+records?).{0,120}(?:loan|borrow|take|home)|"
    r"(?:should|would|can)\s+i.{0,60}(?:take|apply\s+for|afford).{0,35}(?:a\s+)?(?:home|housing)\s+loan|"
    r"(?:home|housing)\s+loan.{0,70}(?:according\s+to\s+my|based\s+on\s+my|from\s+my\s+profile)",
    re.IGNORECASE,
)
HOME_LOAN_QUESTION = re.compile(
    r"\b(?:home|housing)\s+loan\b|\bloan\s+for\s+(?:a\s+)?home\b|घर\s+का\s+लोन|गृह\s+कर्ज",
    re.IGNORECASE,
)


def is_loan_profile_question(message: str) -> bool:
    return bool(LOAN_PROFILE_QUESTION.search(message))


def build_loan_profile_reply(
    db: Session,
    user_id: str,
    message: str,
    language: LanguageCode,
    journey: Optional[JourneyModel] = None,
) -> str:
    """Summarize only this user's stored loan facts and catalogue matches."""
    slots = extract_intent_slots(message)
    amount = slots.loan_amount or (Decimal(str(journey.loan_amount)) if journey else None)
    tenure = slots.tenure_months or (journey.preferred_tenure_months if journey else None)
    home_loan_question = bool(HOME_LOAN_QUESTION.search(message))
    requested_loan_type = "home" if home_loan_question else None
    offers = list_loan_products(
        db, loan_amount=amount, tenure_months=tenure, loan_type=requested_loan_type,
    )

    # All personal evidence is filtered by the authenticated user ID. Payment
    # top-ups are excluded; they do not demonstrate loan repayment ability.
    user_loans = db.query(UserLoanModel).filter(UserLoanModel.user_id == user_id).all()
    repayment_counts = dict(
        db.query(DemoRepaymentModel.status, func.count(DemoRepaymentModel.id))
        .filter(DemoRepaymentModel.user_id == user_id, DemoRepaymentModel.source == "simulation")
        .group_by(DemoRepaymentModel.status)
        .all()
    )
    active_loans = [loan for loan in user_loans if loan.status.upper() in {"ACTIVE", "OVERDUE", "RESTRUCTURED"}]
    active_emi = sum((Decimal(str(loan.emi_amount)) for loan in active_loans), Decimal("0"))
    active_outstanding = sum((Decimal(str(loan.outstanding_principal)) for loan in active_loans), Decimal("0"))

    profile_context_hi = (
        f"आपके DB में {len(user_loans)} दर्ज loan account हैं; {len(active_loans)} सक्रिय/बकाया, "
        f"कुल दर्ज EMI ₹{active_emi:,.0f}/माह और outstanding ₹{active_outstanding:,.0f} है। "
        if user_loans else "आपके DB में अभी कोई loan account दर्ज नहीं है। "
    )
    profile_context_en = (
        f"Your DB has {len(user_loans)} recorded loan accounts; {len(active_loans)} active/overdue, "
        f"with recorded EMIs of ₹{active_emi:,.0f}/month and ₹{active_outstanding:,.0f} outstanding. "
        if user_loans else "Your DB currently has no recorded loan accounts. "
    )
    if repayment_counts:
        repayment_total = sum(repayment_counts.values())
        on_time = repayment_counts.get("PAID_ON_TIME", 0)
        late = repayment_counts.get("PAID_LATE", 0)
        missed = repayment_counts.get("MISSED", 0)
        profile_context_hi += (f"DB में {repayment_total} simulated EMI entries हैं: {on_time} समय पर, "
                              f"{late} देर से, {missed} छूटी हुई; यह bureau history नहीं है। ")
        profile_context_en += (f"The DB has {repayment_total} simulated EMI entries: {on_time} on time, "
                               f"{late} late, {missed} missed; this is not bureau history. ")

    if amount is not None:
        criteria = f"₹{amount:,.0f}"
        if tenure:
            criteria += f" / {tenure} months"
    else:
        criteria = "your current profile records"

    if home_loan_question:
        loan_lines = []
        for loan in user_loans[:5]:
            demo = " (simulated demo record)" if "simulated demo data only" in (loan.notes or "").lower() else ""
            loan_lines.append(
                f"{loan.loan_type.replace('_', ' ').title()} at {loan.lender_name}: {loan.status.lower()}, "
                f"EMI ₹{Decimal(str(loan.emi_amount)):,.0f}/month, "
                f"outstanding ₹{Decimal(str(loan.outstanding_principal)):,.0f}{demo}"
            )
        if language == LanguageCode.HI:
            current_debts = ("आपके DB के दर्ज मौजूदा loan:\n" + "\n".join(f"• {line}" for line in loan_lines)
                             if loan_lines else "आपके DB में कोई मौजूदा loan account दर्ज नहीं है।")
            catalogue_note = ("मौजूदा catalogue में कोई home-loan product दर्ज नहीं है। " if not offers
                              else "Catalogue में home-loan entries हैं, पर वे पात्रता की पुष्टि नहीं करतीं। ")
            return (f"मैंने आपके account के DB records देखे। {current_debts}\n{profile_context_hi}{catalogue_note}"
                    "DB में मासिक take-home आय, जरूरी घरेलू खर्च, बचत/down payment, घर की कीमत या मांगी गई loan राशि दर्ज नहीं है। "
                    "इसलिए इन records से अभी ‘home loan लेना चाहिए या नहीं’ का भरोसेमंद yes/no जवाब नहीं निकलेगा। "
                    "ये जानकारी दें, तो मैं दर्ज EMI के साथ अनुमानित affordability और hypothetical EMI समझा सकता हूँ; अंतिम निर्णय lender का होगा।")
        if language == LanguageCode.MR:
            current_debts = ("तुमच्या DB मधील नोंदवलेली कर्जे:\n" + "\n".join(f"• {line}" for line in loan_lines)
                             if loan_lines else "तुमच्या DB मध्ये सध्या loan account नोंदलेले नाही.")
            catalogue_note = ("सध्याच्या catalogue मध्ये home-loan product नोंदलेले नाही. " if not offers
                              else "Catalogue मधील home-loan entries पात्रता सिद्ध करत नाहीत. ")
            return (f"मी तुमच्या account चे DB records पाहिले. {current_debts}\n"
                    f"नोंदवलेली सक्रिय EMI ₹{active_emi:,.0f}/महिना आणि बाकी ₹{active_outstanding:,.0f} आहे. {catalogue_note}"
                    "मासिक हातात येणारे उत्पन्न, घरखर्च, बचत/down payment, घराची किंमत किंवा अपेक्षित loan रक्कम DB मध्ये नाही. "
                    "म्हणून सध्याच्या records वरून home loan घ्यावा की नाही हे ठाम सांगता येत नाही. ही माहिती दिल्यास नोंदवलेल्या EMI सहित "
                    "अंदाजे affordability आणि hypothetical EMI समजावता येईल; अंतिम निर्णय lender चा असेल.")
        current_debts = ("Your DB records list these existing loans:\n" + "\n".join(f"• {line}" for line in loan_lines)
                         if loan_lines else "Your DB currently has no existing loan accounts recorded.")
        catalogue_note = ("The current catalogue has no home-loan products, so I can't compare an offer yet. " if not offers
                          else "The catalogue has home-loan entries, but they do not confirm eligibility. ")
        return (f"I checked the records linked to your account. {current_debts}\n{profile_context_en}{catalogue_note}"
                "Your DB does not contain monthly take-home income, essential household expenses, savings/down payment, property price, "
                "or requested loan amount. So the records alone are not enough for a reliable yes/no on whether you should take a home loan. "
                "Share those figures and I can estimate affordability alongside your recorded EMIs and explain a hypothetical EMI; "
                "only a lender can confirm eligibility or approval.")

    if language == LanguageCode.HI:
        if not offers:
            return (profile_context_hi + f"{criteria} से मेल खाने वाला कोई सक्रिय catalogue विकल्प नहीं मिला। "
                    "इस प्रोफाइल में आय, नौकरी का प्रकार, उम्र या शहर दर्ज नहीं है। राशि, मासिक take-home आय, नौकरी का प्रकार, उम्र और शहर बताएं; "
                    "मैं catalogue criteria छाँट सकता हूँ। यह पात्रता या मंज़ूरी तय नहीं करता।")
        lines = [f"• {o.lender_name} — ₹{o.min_amount:,.0f}–₹{o.max_amount:,.0f}, {o.min_tenure_months}–{o.max_tenure_months} माह, "
                 f"दर {o.annual_interest_rate_percent}% ({o.source_type})" for o in offers[:5]]
        return (profile_context_hi + f"{criteria} के लिए catalogue में ये विकल्प मिले:\n" + "\n".join(lines)
                + (" ये synthetic demo विकल्प हैं, वास्तविक lender offers नहीं।" if all(o.source_type == "synthetic" for o in offers)
                   else " सूची catalogue में दर्ज स्रोतों पर आधारित है।")
                + " यह lender eligibility check या loan approval नहीं है।")

    if language == LanguageCode.MR:
        if not offers:
            return (f"या प्रोफाइलमध्ये {len(user_loans)} नोंदवलेली loan accounts आहेत; सक्रिय EMI ₹{active_emi:,.0f}/महिना. "
                    f"{criteria} साठी सक्रिय catalogue पर्याय सापडला नाही. मासिक उत्पन्न, नोकरीचा प्रकार, वय आणि शहर सांगा; "
                    "मी catalogue निकष तपासू शकतो. यावरून पात्रता किंवा मंजुरी ठरत नाही.")
        lines = [f"• {o.lender_name} — ₹{o.min_amount:,.0f}–₹{o.max_amount:,.0f}, {o.min_tenure_months}–{o.max_tenure_months} महिने, "
                 f"दर {o.annual_interest_rate_percent}% ({o.source_type})" for o in offers[:5]]
        return (profile_context_en + f"{criteria} साठी catalogue पर्याय:\n" + "\n".join(lines)
                + " हा lender eligibility check किंवा कर्जमंजुरीचा निर्णय नाही.")

    if not offers:
        return (profile_context_en + f"No active catalogue option matches {criteria}. Your account profile does not store income, "
                "employment type, age, or location. Share the requested amount, monthly take-home income, employment type, age, and city "
                "and I can filter catalogue terms. This does not determine eligibility or approval.")
    lines = [f"• {o.lender_name} — ₹{o.min_amount:,.0f}–₹{o.max_amount:,.0f}, {o.min_tenure_months}–{o.max_tenure_months} months, "
             f"{o.annual_interest_rate_percent}% rate ({o.source_type})" for o in offers[:5]]
    return (profile_context_en + f"Based on {criteria}, these catalogue options match:\n" + "\n".join(lines)
            + (" These are synthetic demo examples, not real lender offers." if all(o.source_type == "synthetic" for o in offers)
               else " This list uses sources recorded in the catalogue.")
            + " This is not a lender eligibility check or approval.")
