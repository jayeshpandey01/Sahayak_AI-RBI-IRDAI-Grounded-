import re
from decimal import Decimal
from typing import Tuple, Optional
from app.models.schemas import IntentSlotExtraction, LanguageCode

HINDI_NUMBERS = {
    "das hazaar": Decimal("10000"),
    "bees hazaar": Decimal("20000"),
    "pachees hazaar": Decimal("25000"),
    "pachaas hazaar": Decimal("50000"),
    "pachas hazaar": Decimal("50000"),
    "ek lakh": Decimal("100000"),
    "do lakh": Decimal("200000"),
    "panch lakh": Decimal("500000"),
}

TENURE_PATTERNS = [
    (re.compile(r"(\d+)\s*(?:saal|years|year)", re.IGNORECASE), 12),
    (re.compile(r"(\d+)\s*(?:mahine|months|month|mo)", re.IGNORECASE), 1),
]

AMOUNT_PATTERNS = [
    re.compile(r"(?:rs\.?|inr|₹)?\s*(\d{1,3}(?:,\d{3})+|\d+)\s*(?:rupees|rupaiye|rs)?", re.IGNORECASE),
    re.compile(r"(\d+(?:\.\d+)?)\s*(?:lakh|lakhs|lac)", re.IGNORECASE),
]

EMI_LIMIT_PATTERNS = [
    re.compile(r"(?:emi|kisht)\s*(?:under|below|less than|max|maximum)?\s*(?:rs\.?|inr|₹)?\s*(\d{1,3}(?:,\d{3})+|\d+)", re.IGNORECASE),
    re.compile(r"(?:max|maximum)\s*(?:emi)?\s*(?:rs\.?|inr|₹)?\s*(\d+)", re.IGNORECASE),
]

def detect_language(text: str) -> LanguageCode:
    marathi_keywords = ["माझा", "माझी", "मला", "पाहिजे", "सांगा", "कृपया", "आहे", "किती"]
    hindi_keywords = ["mujhe", "chahiye", "saal", "mahine", "kisht", "rupaiye", "kripya", "kaise", "hazaar", "hai", "batao"]
    words = set(re.findall(r"\w+", text.lower()))
    matches = words.intersection(hindi_keywords)
    if any(keyword in text for keyword in marathi_keywords):
        return LanguageCode.MR
    if any("\u0900" <= char <= "\u097F" for char in text):
        return LanguageCode.HI
    if matches:
        return LanguageCode.HINGLISH
    return LanguageCode.EN

def extract_intent_slots(message: str) -> IntentSlotExtraction:
    cleaned = message.strip()
    detected_lang = detect_language(cleaned)
    lower = cleaned.lower()

    # Underwriting query guard check
    underwriting_phrases = [
        "will my loan be approved",
        "will i get approved",
        "approve my loan",
        "loan pass ho jayega",
        "guaranteed approval",
        "credit score kitna chahiye pass hone ke liye",
    ]
    if any(phrase in lower for phrase in underwriting_phrases):
        return IntentSlotExtraction(
            detected_language=detected_lang,
            confidence=0.99,
            route_to_human_queue=True,
            refusal_reason=(
                "Underwriting refusal: Sahayak AI does not make credit approval or rejection decisions. "
                "Only RBI-regulated lender partners determine eligibility."
            )
        )

    # Amount extraction
    amount: Optional[Decimal] = None
    for name, val in HINDI_NUMBERS.items():
        if name in lower:
            amount = val
            break

    if amount is None:
        lakh_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:lakh|lakhs|lac)", lower)
        if lakh_match:
            amount = Decimal(lakh_match.group(1)) * Decimal("100000")
        else:
            amt_match = re.search(r"(?:rs\.?|inr|₹)?\s*(\d{1,3}(?:,\d{2,3})+|\d{4,7})", lower)
            if amt_match:
                cleaned_num = amt_match.group(1).replace(",", "")
                amount = Decimal(cleaned_num)

    # Tenure extraction
    tenure: Optional[int] = None
    for pattern, multiplier in TENURE_PATTERNS:
        match = pattern.search(lower)
        if match:
            tenure = int(match.group(1)) * multiplier
            break

    # Max EMI extraction
    max_emi: Optional[Decimal] = None
    for pattern in EMI_LIMIT_PATTERNS:
        match = pattern.search(lower)
        if match:
            cleaned_emi = match.group(1).replace(",", "")
            max_emi = Decimal(cleaned_emi)
            break

    # Check for ambiguity
    clarification: Optional[str] = None
    if amount is not None and (amount < Decimal("1000") or amount > Decimal("5000000")):
        clarification = f"Requested loan amount ₹{amount:,} is outside RBI personal loan bounds (₹1,000 to ₹50,00,000). Please clarify."
    elif amount is not None and tenure is None:
        clarification = "Got your amount. How many months or years would you prefer for repayment?"

    return IntentSlotExtraction(
        loan_amount=amount,
        tenure_months=tenure,
        max_emi=max_emi,
        purpose="Identified via conversational copilot",
        detected_language=detected_lang,
        confidence=0.94 if amount and tenure else 0.82,
        clarification_required=clarification,
        route_to_human_queue=False,
    )
