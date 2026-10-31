import logging
from typing import List, Optional
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.api.dependencies import get_current_user
from app.models.db_models import UserModel, UserLoanModel
from app.models.schemas import (
    UserLoanCreate,
    UserLoanUpdate,
    UserLoanResponse,
    LoanAuditRequest,
    LoanAuditReport,
    PrepaymentSimulationRequest,
    PrepaymentSimulationResult,
    RefinanceOpportunity,
)
from app.services.loan_audit_service import (
    create_user_loan,
    update_user_loan,
    delete_user_loan,
    seed_default_user_loans,
    generate_loan_audit_report,
    run_prepayment_simulation,
    compute_refinancing_opportunities,
)
from app.services.loan_catalogue_service import list_loan_products

logger = logging.getLogger("sahayak.loan_api")

router = APIRouter(prefix="/api/loans", tags=["Multi-Platform Loans & EMI Audit"])

@router.get("", response_model=List[UserLoanResponse])
@router.get("/", response_model=List[UserLoanResponse])
def list_user_loans(
    status_filter: Optional[str] = Query(None, description="Filter by status: ACTIVE, OVERDUE, CLOSED"),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """
    Returns all loans taken by the user across multiple banking, NBFC, and fintech platforms.
    Returns only the authenticated user's loan records. Demo data is added only
    through the explicit seed endpoint.
    """
    user_id = current_user.id
    query = db.query(UserLoanModel).filter(UserLoanModel.user_id == user_id)

    if status_filter:
        query = query.filter(UserLoanModel.status == status_filter.upper())

    loans = query.order_by(UserLoanModel.created_at.desc()).all()
    return loans


@router.post("", response_model=UserLoanResponse, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=UserLoanResponse, status_code=status.HTTP_201_CREATED)
def add_user_loan(
    payload: UserLoanCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """
    Adds a new loan from any lender or platform (Bank, NBFC, or Fintech app).
    Computes deterministic EMI and next due date if omitted.
    """
    user_id = current_user.id
    loan = create_user_loan(db, user_id, payload)
    return loan


@router.post("/seed-demo", response_model=List[UserLoanResponse])
def seed_demo_loans_endpoint(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """Adds the sample portfolio only when the signed-in user has no loans."""
    user_id = current_user.id
    loans = seed_default_user_loans(db, user_id)
    return loans


@router.post("/audit", response_model=LoanAuditReport)
def run_loan_audit_endpoint(
    payload: Optional[LoanAuditRequest] = None,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """
    Executes a comprehensive, multi-platform Loan & EMI Audit:
    - Debt-to-income (FOIR) calculation & risk scoring
    - Multi-platform liability breakdown & interest leakage detection
    - Refinancing & balance transfer opportunities
    - Prepayment impact simulation
    - Consolidated EMI calendar
    - RBI KFS compliance disclosures
    """
    user_id = current_user.id
    report = generate_loan_audit_report(db, user_id, payload)
    return report


@router.post("/simulate-prepayment", response_model=PrepaymentSimulationResult)
def simulate_prepayment_endpoint(
    payload: PrepaymentSimulationRequest,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """
    Simulates extra monthly payments or one-time lump-sum prepayment:
    calculates exact tenure reduction (months saved) and total interest saved.
    """
    user_id = current_user.id
    loans = db.query(UserLoanModel).filter(UserLoanModel.user_id == user_id).all()

    result = run_prepayment_simulation(
        loans=loans,
        target_loan_id=payload.target_loan_id,
        extra_monthly=payload.extra_monthly_prepayment or Decimal("0.00"),
        lump_sum=payload.lump_sum_prepayment or Decimal("0.00"),
    )
    if not result:
        raise HTTPException(status_code=400, detail="No active loans available for prepayment simulation.")
    return result


@router.get("/refinance-opportunities", response_model=List[RefinanceOpportunity])
def get_refinance_opportunities_endpoint(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """Evaluates user's high-interest loans against current market catalogue offers for refinancing."""
    user_id = current_user.id
    loans = db.query(UserLoanModel).filter(UserLoanModel.user_id == user_id).all()

    return compute_refinancing_opportunities(loans, list_loan_products(db))


@router.get("/{loan_id}", response_model=UserLoanResponse)
def get_user_loan(
    loan_id: str,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """Fetches details of a specific user loan."""
    user_id = current_user.id
    loan = db.query(UserLoanModel).filter(UserLoanModel.id == loan_id, UserLoanModel.user_id == user_id).first()
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found or unauthorized.")
    return loan


@router.put("/{loan_id}", response_model=UserLoanResponse)
def update_user_loan_endpoint(
    loan_id: str,
    payload: UserLoanUpdate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """Updates loan balance, interest rate, tenure, or status."""
    user_id = current_user.id
    loan = update_user_loan(db, user_id, loan_id, payload)
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found or unauthorized.")
    return loan


@router.delete("/{loan_id}", status_code=status.HTTP_200_OK)
def delete_user_loan_endpoint(
    loan_id: str,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """Deletes a loan record."""
    user_id = current_user.id
    deleted = delete_user_loan(db, user_id, loan_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Loan not found or unauthorized.")
    return {"success": True, "message": f"Loan {loan_id} successfully deleted."}

