from typing import Set, Tuple, Optional, List
from app.models.schemas import JourneyStage

ALLOWED_FORWARD_TRANSITIONS: dict[JourneyStage, Set[JourneyStage]] = {
    JourneyStage.INTENT_CAPTURED: {JourneyStage.OFFERS_REVIEWED},
    JourneyStage.OFFERS_REVIEWED: {JourneyStage.DOCUMENTS_CONFIRMED, JourneyStage.INTENT_CAPTURED},
    JourneyStage.DOCUMENTS_CONFIRMED: {JourneyStage.READY_FOR_HANDOFF, JourneyStage.INTENT_CAPTURED},
    JourneyStage.READY_FOR_HANDOFF: set(),
}

class FSMTransitionError(Exception):
    def __init__(self, message: str, status_code: int = 409):
        super().__init__(message)
        self.message = message
        self.status_code = status_code

def validate_state_transition(
    current_stage: JourneyStage,
    target_stage: JourneyStage,
    has_selected_offer: bool = False,
    documents_confirmed: bool = False,
    customer_confirmed: bool = False,
    unresolved_discrepancies: Optional[List[str]] = None,
) -> Tuple[bool, Optional[str], bool]:
    """
    Validates explicit stage transitions.
    Returns: (is_valid, error_reason, human_review_required)
    """
    if target_stage not in ALLOWED_FORWARD_TRANSITIONS.get(current_stage, set()):
        raise FSMTransitionError(
            f"Illegal state transition from {current_stage.value} to {target_stage.value}. "
            f"Allowed next stages: {[s.value for s in ALLOWED_FORWARD_TRANSITIONS.get(current_stage, set())]}",
            status_code=409
        )

    # Specific Stage Guards
    if target_stage == JourneyStage.OFFERS_REVIEWED:
        if not has_selected_offer:
            raise FSMTransitionError("Cannot progress to OFFERS_REVIEWED without selecting a valid lender offer", status_code=400)

    if target_stage == JourneyStage.DOCUMENTS_CONFIRMED:
        if not documents_confirmed:
            raise FSMTransitionError("Cannot progress to DOCUMENTS_CONFIRMED before completing and confirming OCR extraction", status_code=400)

    if target_stage == JourneyStage.READY_FOR_HANDOFF:
        if not customer_confirmed:
            raise FSMTransitionError("Customer confirmation is strictly required prior to READY_FOR_HANDOFF", status_code=400)

    human_review_required = False
    if unresolved_discrepancies and len(unresolved_discrepancies) > 0:
        human_review_required = True

    return True, None, human_review_required
