import re
from typing import Tuple, Optional
from datetime import datetime, timezone
from app.models.schemas import HumanReviewHandoff

UNDERWRITING_PATTERNS = [
    re.compile(r"will\s+(?:my\s+)?(?:loan\s+)?(?:be\s+)?approved", re.IGNORECASE),
    re.compile(r"guarantee\s+(?:loan\s+)?approval", re.IGNORECASE),
    re.compile(r"guaranteed\s+(?:loan|approval)", re.IGNORECASE),
    re.compile(r"will\s+i\s+be\s+approved", re.IGNORECASE),
    re.compile(r"will\s+(?:my\s+)?loan\s+pass", re.IGNORECASE),
    re.compile(r"why\s+was\s+i\s+rejected", re.IGNORECASE),
    re.compile(r"approve\s+(?:my\s+)?loan", re.IGNORECASE),
    re.compile(r"bypass\s+credit\s+score", re.IGNORECASE),
    re.compile(r"(?:mera|meri)\s+loan\s+(?:approve|pass)\s+(?:ho|hoga|hogi|jayega|jaayega)", re.IGNORECASE),
    re.compile(r"loan\s+(?:pakka|guaranteed|confirm)\s+(?:milega|approve|hoga)", re.IGNORECASE),
    re.compile(r"loan\s+.*(?:approve|approved|pass)\s+.*(?:karega|hoga|milega|jayega|jaayega)", re.IGNORECASE),
    re.compile(r"(?:मेरा|मेरी)\s+लोन\s+(?:मंजूर|पास|अप्रूव)", re.IGNORECASE),
    re.compile(r"(?:मुझे|मेरा)\s+लोन\s+मिलेगा", re.IGNORECASE),
    re.compile(r"क्रेडिट\s+स्कोर\s+बायपास", re.IGNORECASE),
]

def check_underwriting_guardrails(message: str, journey_state: Optional[dict] = None) -> Tuple[bool, Optional[str], Optional[HumanReviewHandoff]]:
    """
    Blocks AI from acting as an underwriter or predicting approval odds.
    Directs the user to official lender verification and routes to the human review queue.
    """
    for pattern in UNDERWRITING_PATTERNS:
        match = pattern.search(message)
        if match:
            matched_phrase = match.group(0)
            handoff = HumanReviewHandoff(
                reason=f"Customer requested credit decisioning / underwriting advice ('{matched_phrase}').",
                escalation_level="L1_UNDERWRITING_SPECIALIST",
                timestamp=datetime.now(timezone.utc),
                unresolved_discrepancies=["Automated decisioning prohibited by RBI Digital Lending Directions."],
                case_summary=journey_state or {},
            )
            explanation = (
                "Sahayak cannot assess your creditworthiness or predict or make a lender's decision. "
                "Only the lender can confirm its decision. You can ask for help from a person for verified guidance."
            )
            return True, explanation, handoff

    return False, None, None
