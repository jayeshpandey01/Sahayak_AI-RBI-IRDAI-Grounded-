import pytest
from app.models.schemas import JourneyStage
from app.services.fsm_engine import validate_state_transition, FSMTransitionError

def test_fsm_valid_full_lifecycle():
    # 1. INTENT_CAPTURED -> OFFERS_REVIEWED (valid when offer is selected)
    valid, _, _ = validate_state_transition(
        current_stage=JourneyStage.INTENT_CAPTURED,
        target_stage=JourneyStage.OFFERS_REVIEWED,
        has_selected_offer=True
    )
    assert valid is True

    # 2. OFFERS_REVIEWED -> DOCUMENTS_CONFIRMED (valid when docs confirmed)
    valid, _, _ = validate_state_transition(
        current_stage=JourneyStage.OFFERS_REVIEWED,
        target_stage=JourneyStage.DOCUMENTS_CONFIRMED,
        has_selected_offer=True,
        documents_confirmed=True
    )
    assert valid is True

    # 3. DOCUMENTS_CONFIRMED -> READY_FOR_HANDOFF (valid when customer confirms)
    valid, _, human_req = validate_state_transition(
        current_stage=JourneyStage.DOCUMENTS_CONFIRMED,
        target_stage=JourneyStage.READY_FOR_HANDOFF,
        documents_confirmed=True,
        customer_confirmed=True
    )
    assert valid is True
    assert human_req is False

def test_fsm_illegal_skipping_stages():
    # Cannot jump from INTENT_CAPTURED to READY_FOR_HANDOFF
    with pytest.raises(FSMTransitionError) as exc:
        validate_state_transition(
            current_stage=JourneyStage.INTENT_CAPTURED,
            target_stage=JourneyStage.READY_FOR_HANDOFF,
            customer_confirmed=True
        )
    assert exc.value.status_code == 409
    assert "Illegal state transition" in exc.value.message

def test_fsm_missing_offer_guard():
    with pytest.raises(FSMTransitionError) as exc:
        validate_state_transition(
            current_stage=JourneyStage.INTENT_CAPTURED,
            target_stage=JourneyStage.OFFERS_REVIEWED,
            has_selected_offer=False
        )
    assert exc.value.status_code == 400
    assert "selecting a valid lender offer" in exc.value.message

def test_fsm_missing_customer_confirmation_guard():
    with pytest.raises(FSMTransitionError) as exc:
        validate_state_transition(
            current_stage=JourneyStage.DOCUMENTS_CONFIRMED,
            target_stage=JourneyStage.READY_FOR_HANDOFF,
            customer_confirmed=False
        )
    assert exc.value.status_code == 400
    assert "Customer confirmation is strictly required" in exc.value.message

def test_fsm_discrepancy_triggers_human_review():
    valid, _, human_review = validate_state_transition(
        current_stage=JourneyStage.DOCUMENTS_CONFIRMED,
        target_stage=JourneyStage.READY_FOR_HANDOFF,
        customer_confirmed=True,
        unresolved_discrepancies=["Salary slip name differs from PAN name"]
    )
    assert valid is True
    assert human_review is True

def test_fsm_terminal_state():
    with pytest.raises(FSMTransitionError) as exc:
        validate_state_transition(
            current_stage=JourneyStage.READY_FOR_HANDOFF,
            target_stage=JourneyStage.INTENT_CAPTURED
        )
    assert exc.value.status_code == 409
