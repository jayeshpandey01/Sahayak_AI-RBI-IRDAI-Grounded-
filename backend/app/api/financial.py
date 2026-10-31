from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_admin_user
from app.database import get_db
from app.models.db_models import UserModel
from app.models.schemas import (
    AmortizationItem, EMICalculationRequest, EMICalculationResponse,
    LenderOffer, LoanProductUpsert, LoanRateHistoryResponse,
)
from app.services.financial_calculator import (
    calculate_kfs_emi, generate_amortization_schedule, get_offer_by_id,
)
from app.services.loan_catalogue_service import (
    list_loan_products, list_rate_history, upsert_loan_product,
)

router = APIRouter(prefix="/api/financial", tags=["Financial Services"])


@router.post("/create-payment-intent", status_code=410)
def create_payment_intent_endpoint():
    raise HTTPException(status_code=410, detail="Legacy untracked PaymentIntent route is disabled. Use an authenticated payment-order flow.")


@router.get("/offers", response_model=List[LenderOffer])
def list_offers(
    loan_amount: Optional[Decimal] = Query(None, ge=1000),
    tenure_months: Optional[int] = Query(None, ge=1, le=360),
    monthly_income: Optional[Decimal] = Query(None, gt=0),
    employment_type: Optional[str] = Query(None, min_length=1, max_length=64),
    location: Optional[str] = Query(None, min_length=1, max_length=128),
    loan_type: Optional[str] = Query(None, min_length=2, max_length=32),
    db: Session = Depends(get_db),
):
    """Return active database catalogue products matching provided criteria."""
    return list_loan_products(
        db, loan_amount=loan_amount, tenure_months=tenure_months,
        monthly_income=monthly_income, employment_type=employment_type,
        location=location, loan_type=loan_type,
    )


@router.post("/admin/offers", response_model=LenderOffer, status_code=201)
def create_or_update_offer(
    payload: LoanProductUpsert,
    db: Session = Depends(get_db),
    _admin: UserModel = Depends(get_admin_user),
):
    """Create or update sourced catalogue terms. Restricted to administrators."""
    return upsert_loan_product(db, payload)


@router.get("/admin/offers/{offer_id}/rate-history", response_model=List[LoanRateHistoryResponse])
def get_offer_rate_history(
    offer_id: str,
    db: Session = Depends(get_db),
    _admin: UserModel = Depends(get_admin_user),
):
    return list_rate_history(db, offer_id)


@router.post("/calculate", response_model=EMICalculationResponse)
@router.post("/emi", response_model=EMICalculationResponse)
def calculate_emi_endpoint(payload: EMICalculationRequest, db: Session = Depends(get_db)):
    offer = get_offer_by_id(payload.offer_id, db)
    if not offer:
        raise HTTPException(status_code=404, detail="Active loan product not found")
    effective_tenure = payload.tenure_months or payload.preferred_tenure_months or 24
    if payload.loan_amount < offer.min_amount or payload.loan_amount > offer.max_amount:
        raise HTTPException(
            status_code=400,
            detail=f"Loan amount ₹{payload.loan_amount:,} is outside lender limits (₹{offer.min_amount:,} - ₹{offer.max_amount:,})",
        )
    if effective_tenure < offer.min_tenure_months or effective_tenure > offer.max_tenure_months:
        raise HTTPException(
            status_code=400,
            detail=f"Tenure {effective_tenure} months is outside lender limits ({offer.min_tenure_months} - {offer.max_tenure_months} mos)",
        )
    return calculate_kfs_emi(payload.loan_amount, effective_tenure, offer, payload.maximum_emi)


@router.get("/offers/{offer_id}/amortization", response_model=List[AmortizationItem])
def get_amortization_table(
    offer_id: str,
    principal: Decimal = Query(..., ge=1000),
    tenure_months: int = Query(..., ge=1, le=360),
    db: Session = Depends(get_db),
):
    offer = get_offer_by_id(offer_id, db)
    if not offer:
        raise HTTPException(status_code=404, detail="Active loan product not found")
    if principal < offer.min_amount or principal > offer.max_amount:
        raise HTTPException(status_code=400, detail="Principal is outside product limits")
    if tenure_months < offer.min_tenure_months or tenure_months > offer.max_tenure_months:
        raise HTTPException(status_code=400, detail="Tenure is outside product limits")
    return generate_amortization_schedule(principal, tenure_months, offer)
