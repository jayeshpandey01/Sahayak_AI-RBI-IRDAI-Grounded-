import logging
from datetime import datetime, date, timezone, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional, Tuple, Dict, Any
from uuid import uuid4
from sqlalchemy.orm import Session

from app.models.db_models import UserLoanModel
from app.models.schemas import (
    UserLoanCreate,
    UserLoanUpdate,
    UserLoanResponse,
    LoanAuditRequest,
    LoanAuditReport,
    PrepaymentSimulationRequest,
    PrepaymentSimulationResult,
    RefinanceOpportunity,
    EMICalendarItem,
    LenderType,
    LoanType,
    LoanStatus,
)
from app.services.financial_calculator import OFFERS_CATALOGUE, RUPEE_PRECISION
from app.services.loan_catalogue_service import list_loan_products

logger = logging.getLogger("sahayak.loan_audit")


def compute_monthly_emi(principal: Decimal, annual_rate_percent: Decimal, tenure_months: int) -> Decimal:
    """
    Standard reducing balance EMI calculation: P * r * (1+r)^n / ((1+r)^n - 1)
    Strictly using Decimal arithmetic matching RBI Key Fact Statement (KFS) rules.
    """
    if principal <= Decimal("0") or tenure_months <= 0:
        return Decimal("0.00")
    if annual_rate_percent <= Decimal("0"):
        return (principal / Decimal(tenure_months)).quantize(RUPEE_PRECISION, rounding=ROUND_HALF_UP)

    monthly_rate = annual_rate_percent / Decimal("1200")
    factor = (Decimal("1") + monthly_rate) ** tenure_months
    emi = principal * monthly_rate * factor / (factor - Decimal("1"))
    return emi.quantize(RUPEE_PRECISION, rounding=ROUND_HALF_UP)


def calculate_next_due_date(due_day: int) -> str:
    """Calculates the upcoming due date string (YYYY-MM-DD) based on the specified day of month."""
    today = date.today()
    target_day = max(1, min(due_day, 28))  # safe day for all months
    try:
        candidate = date(today.year, today.month, target_day)
    except ValueError:
        candidate = date(today.year, today.month, 28)

    if candidate <= today:
        # Move to next month
        if today.month == 12:
            candidate = date(today.year + 1, 1, target_day)
        else:
            candidate = date(today.year, today.month + 1, target_day)

    return candidate.isoformat()


def seed_default_user_loans(db: Session, user_id: str) -> List[UserLoanModel]:
    """
    Seeds a realistic multi-platform loan portfolio for the user:
    - 1 Tier-1 Bank Personal Loan (HDFC Bank @ 12.5% p.a.)
    - 1 NBFC Consumer Durable EMI (Bajaj Finserv @ 17.5% p.a.)
    - 1 Fintech Digital Credit Line (KreditBee @ 24.0% p.a.)
    Demonstrating cross-platform loan aggregation and interest rate disparities.
    """
    existing = db.query(UserLoanModel).filter(UserLoanModel.user_id == user_id).all()
    if existing:
        return existing

    now = datetime.now(timezone.utc)
    demo_loans = [
        UserLoanModel(
            id=f"loan-hdfc-{uuid4().hex[:8]}",
            user_id=user_id,
            lender_name="HDFC Bank",
            lender_type="BANK",
            loan_type="PERSONAL",
            account_number="PL-HDFC-8492",
            original_principal=Decimal("300000.00"),
            outstanding_principal=Decimal("195000.00"),
            interest_rate_percent=Decimal("12.50"),
            tenure_months=36,
            remaining_tenure_months=22,
            emi_amount=Decimal("10037.00"),
            emi_due_day=5,
            next_due_date=calculate_next_due_date(5),
            status="ACTIVE",
            disbursement_date="2025-01-10",
            processing_fee_paid=Decimal("3500.00"),
            prepayment_penalty_percent=Decimal("0.00"),
            notes="SIMULATED DEMO DATA ONLY — not a real HDFC Bank loan or account. Example personal loan for a home-renovation scenario.",
            created_at=now,
            updated_at=now,
        ),
        UserLoanModel(
            id=f"loan-bajaj-{uuid4().hex[:8]}",
            user_id=user_id,
            lender_name="Bajaj Finserv",
            lender_type="NBFC",
            loan_type="CONSUMER_DURABLE",
            account_number="CD-BAJAJ-4102",
            original_principal=Decimal("65000.00"),
            outstanding_principal=Decimal("38000.00"),
            interest_rate_percent=Decimal("17.50"),
            tenure_months=18,
            remaining_tenure_months=10,
            emi_amount=Decimal("4132.00"),
            emi_due_day=10,
            next_due_date=calculate_next_due_date(10),
            status="ACTIVE",
            disbursement_date="2025-08-15",
            processing_fee_paid=Decimal("1180.00"),
            prepayment_penalty_percent=Decimal("0.00"),
            notes="SIMULATED DEMO DATA ONLY — not a real Bajaj Finserv loan or account. Example consumer-durable EMI scenario.",
            created_at=now,
            updated_at=now,
        ),
        UserLoanModel(
            id=f"loan-kreditbee-{uuid4().hex[:8]}",
            user_id=user_id,
            lender_name="KreditBee",
            lender_type="FINTECH",
            loan_type="CREDIT_LINE",
            account_number="KB-CRD-9031",
            original_principal=Decimal("50000.00"),
            outstanding_principal=Decimal("29500.00"),
            interest_rate_percent=Decimal("24.00"),
            tenure_months=12,
            remaining_tenure_months=7,
            emi_amount=Decimal("4728.00"),
            emi_due_day=20,
            next_due_date=calculate_next_due_date(20),
            status="ACTIVE",
            disbursement_date="2025-11-20",
            processing_fee_paid=Decimal("1500.00"),
            prepayment_penalty_percent=Decimal("0.00"),
            notes="SIMULATED DEMO DATA ONLY — not a real KreditBee loan or account. Example digital credit-line scenario.",
            created_at=now,
            updated_at=now,
        ),
    ]

    for loan in demo_loans:
        db.add(loan)
    db.commit()

    return demo_loans


def create_user_loan(db: Session, user_id: str, payload: UserLoanCreate) -> UserLoanModel:
    """Creates a new user loan record with deterministic EMI and next due date calculation."""
    loan_id = f"loan-{uuid4().hex[:10]}"
    now = datetime.now(timezone.utc)

    outstanding = payload.outstanding_principal if payload.outstanding_principal is not None else payload.original_principal
    remaining_tenure = payload.remaining_tenure_months if payload.remaining_tenure_months is not None else payload.tenure_months
    due_day = payload.emi_due_day or 5

    # Auto-calculate EMI if omitted
    if payload.emi_amount and payload.emi_amount > 0:
        emi = payload.emi_amount
    else:
        emi = compute_monthly_emi(payload.original_principal, payload.interest_rate_percent, payload.tenure_months)

    next_due = payload.next_due_date or calculate_next_due_date(due_day)
    account_no = payload.account_number or f"LN-{payload.lender_name[:4].upper()}-{uuid4().hex[:4].upper()}"

    loan = UserLoanModel(
        id=loan_id,
        user_id=user_id,
        lender_name=payload.lender_name,
        lender_type=payload.lender_type.value,
        loan_type=payload.loan_type.value,
        account_number=account_no,
        original_principal=payload.original_principal,
        outstanding_principal=outstanding,
        interest_rate_percent=payload.interest_rate_percent,
        tenure_months=payload.tenure_months,
        remaining_tenure_months=remaining_tenure,
        emi_amount=emi,
        emi_due_day=due_day,
        next_due_date=next_due,
        status=payload.status.value,
        disbursement_date=payload.disbursement_date,
        processing_fee_paid=payload.processing_fee_paid or Decimal("0.00"),
        prepayment_penalty_percent=payload.prepayment_penalty_percent or Decimal("0.00"),
        notes=payload.notes,
        created_at=now,
        updated_at=now,
    )
    db.add(loan)
    db.commit()
    db.refresh(loan)
    return loan


def update_user_loan(db: Session, user_id: str, loan_id: str, payload: UserLoanUpdate) -> Optional[UserLoanModel]:
    """Updates an existing loan owned by the user."""
    loan = db.query(UserLoanModel).filter(UserLoanModel.id == loan_id, UserLoanModel.user_id == user_id).first()
    if not loan:
        return None

    update_data = payload.model_dump(exclude_unset=True)
    for field, val in update_data.items():
        if val is not None:
            if hasattr(val, "value"):
                setattr(loan, field, val.value)
            else:
                setattr(loan, field, val)

    loan.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(loan)
    return loan


def delete_user_loan(db: Session, user_id: str, loan_id: str) -> bool:
    """Deletes a loan owned by the user."""
    loan = db.query(UserLoanModel).filter(UserLoanModel.id == loan_id, UserLoanModel.user_id == user_id).first()
    if not loan:
        return False
    db.delete(loan)
    db.commit()
    return True


def simulate_prepayment_amortization(
    outstanding_principal: Decimal,
    annual_rate_percent: Decimal,
    current_emi: Decimal,
    remaining_months: int,
    extra_monthly: Decimal = Decimal("0.00"),
    lump_sum: Decimal = Decimal("0.00"),
) -> Tuple[int, Decimal]:
    """
    Simulates month-by-month reducing balance amortization under prepayment conditions:
    Returns (new_remaining_months, total_interest_paid).
    """
    if outstanding_principal <= Decimal("0"):
        return 0, Decimal("0.00")

    balance = max(Decimal("0.00"), outstanding_principal - lump_sum)
    if balance == Decimal("0.00"):
        return 0, Decimal("0.00")

    monthly_rate = annual_rate_percent / Decimal("1200")
    effective_emi = current_emi + extra_monthly
    total_interest = Decimal("0.00")
    months = 0
    max_months = remaining_months + 120  # Safeguard bound

    while balance > Decimal("0.00") and months < max_months:
        months += 1
        month_interest = (balance * monthly_rate).quantize(RUPEE_PRECISION, rounding=ROUND_HALF_UP)
        total_interest += month_interest

        principal_paid = effective_emi - month_interest
        if principal_paid <= Decimal("0"):
            # EMI does not even cover monthly interest: tenure would explode
            return remaining_months, (outstanding_principal * monthly_rate * Decimal(remaining_months)).quantize(RUPEE_PRECISION)

        if principal_paid >= balance:
            # Paid off
            balance = Decimal("0.00")
            break
        else:
            balance -= principal_paid

    return months, total_interest.quantize(RUPEE_PRECISION, rounding=ROUND_HALF_UP)


def run_prepayment_simulation(
    loans: List[UserLoanModel],
    target_loan_id: Optional[str] = None,
    extra_monthly: Decimal = Decimal("0.00"),
    lump_sum: Decimal = Decimal("0.00"),
) -> Optional[PrepaymentSimulationResult]:
    """
    Simulates either extra monthly payment or one-time lump-sum prepayment on the designated
    or highest-interest loan (Avalanche strategy).
    """
    active_loans = [l for l in loans if l.status == "ACTIVE" and l.outstanding_principal > 0]
    if not active_loans:
        return None

    target = None
    if target_loan_id:
        target = next((l for l in active_loans if l.id == target_loan_id), None)
    if not target:
        # Default to highest interest rate loan (Debt Avalanche)
        target = max(active_loans, key=lambda l: l.interest_rate_percent)

    is_monthly = extra_monthly > 0
    sim_mode = "EXTRA_MONTHLY" if is_monthly else "LUMP_SUM"
    prep_amount = extra_monthly if is_monthly else lump_sum

    if prep_amount <= 0:
        # Default illustrative prepayment of ₹1,000/mo to give user immediate value
        sim_mode = "EXTRA_MONTHLY"
        extra_monthly = Decimal("1000.00")
        prep_amount = extra_monthly

    # Baseline remaining interest without extra payment
    base_months, base_interest = simulate_prepayment_amortization(
        target.outstanding_principal,
        target.interest_rate_percent,
        target.emi_amount,
        target.remaining_tenure_months,
        extra_monthly=Decimal("0.00"),
        lump_sum=Decimal("0.00"),
    )

    # Simulated with prepayment
    new_months, new_interest = simulate_prepayment_amortization(
        target.outstanding_principal,
        target.interest_rate_percent,
        target.emi_amount,
        target.remaining_tenure_months,
        extra_monthly=extra_monthly,
        lump_sum=lump_sum,
    )

    months_saved = max(0, base_months - new_months)
    interest_saved = max(Decimal("0.00"), base_interest - new_interest)

    if sim_mode == "EXTRA_MONTHLY":
        advice = (
            f"Adding ₹{prep_amount:,.0f}/month to your {target.lender_name} loan "
            f"({target.interest_rate_percent}% p.a.) closes the loan {months_saved} months early "
            f"and saves you ₹{interest_saved:,.0f} in interest!"
        )
    else:
        advice = (
            f"Prepaying a lump-sum of ₹{prep_amount:,.0f} towards your {target.lender_name} loan "
            f"reduces your tenure by {months_saved} months, saving ₹{interest_saved:,.0f} in future interest."
        )

    return PrepaymentSimulationResult(
        target_loan_id=target.id,
        lender_name=target.lender_name,
        simulation_mode=sim_mode,
        prepayment_amount=prep_amount,
        original_tenure_remaining_months=target.remaining_tenure_months,
        new_tenure_remaining_months=new_months,
        months_saved=months_saved,
        original_remaining_interest=base_interest,
        new_remaining_interest=new_interest,
        interest_saved_rupees=interest_saved,
        advice=advice,
    )


def compute_refinancing_opportunities(
    loans: List[UserLoanModel], offers=None,
) -> List[RefinanceOpportunity]:
    """
    Scans all user loans for interest rate leakage by comparing against current verified catalogue offers.
    Identifies high-interest loans (e.g. >= 15%) that would benefit from balance transfer.
    """
    offers = offers if offers is not None else OFFERS_CATALOGUE
    if not offers:
        return []
    best_offer = min(offers, key=lambda offer: offer.annual_interest_rate_percent)
    best_rate = best_offer.annual_interest_rate_percent
    opportunities: List[RefinanceOpportunity] = []
    active_loans = [l for l in loans if l.status == "ACTIVE" and l.outstanding_principal > 0]

    for loan in active_loans:
        # Check if loan rate is higher than best market catalogue rate by at least 2.5%
        rate_diff = loan.interest_rate_percent - best_rate
        if rate_diff >= Decimal("2.50"):
            # Calculate new EMI at lower rate
            new_emi = compute_monthly_emi(loan.outstanding_principal, best_rate, loan.remaining_tenure_months)
            monthly_saving = max(Decimal("0.00"), loan.emi_amount - new_emi)

            # Processing fee for balance transfer (approx 1% + 18% GST)
            processing_fee = (loan.outstanding_principal * Decimal("0.01") * Decimal("1.18")).quantize(RUPEE_PRECISION, rounding=ROUND_HALF_UP)
            lifetime_gross_saving = monthly_saving * Decimal(loan.remaining_tenure_months)
            net_benefit = lifetime_gross_saving - processing_fee

            is_worthwhile = net_benefit > Decimal("1000.00")
            recommendation = (
                f"Your {loan.lender_name} loan carries {loan.interest_rate_percent}% p.a. interest. "
                f"Refinancing or transferring balance to {best_offer.lender_name} at {best_rate}% p.a. "
                f"could save you ₹{monthly_saving:,.0f}/month and approx ₹{net_benefit:,.0f} net over the remaining tenure."
            )

            opportunities.append(RefinanceOpportunity(
                loan_id=loan.id,
                lender_name=loan.lender_name,
                loan_type=loan.loan_type,
                outstanding_principal=loan.outstanding_principal,
                current_interest_rate=loan.interest_rate_percent,
                catalogue_offer_lender=best_offer.lender_name,
                catalogue_offer_rate=best_rate,
                monthly_saving_rupees=monthly_saving,
                lifetime_saving_rupees=lifetime_gross_saving,
                processing_fee_estimate=processing_fee,
                net_benefit_rupees=net_benefit,
                is_worthwhile=is_worthwhile,
                recommendation=recommendation,
            ))

    return opportunities


def generate_loan_audit_report(
    db: Session,
    user_id: str,
    audit_req: Optional[LoanAuditRequest] = None,
) -> LoanAuditReport:
    """
    Executes a comprehensive, multi-platform Loan & EMI Audit:
    1. Aggregates multi-platform debt liabilities (Bank + NBFC + Fintech).
    2. Computes Fixed Obligation to Income Ratio (FOIR / DTI) with risk classification.
    3. Calculates interest leakage and high-cost loan exposure.
    4. Evaluates refinancing and balance transfer opportunities against the loan catalogue.
    5. Runs prepayment impact simulation (Avalanche / Snowball).
    6. Constructs a consolidated monthly EMI calendar with days-to-due countdown.
    7. Provides grounded, actionable AI insights and RBI compliance disclosures.
    """
    loans = db.query(UserLoanModel).filter(UserLoanModel.user_id == user_id).all()

    monthly_income = audit_req.monthly_income if audit_req and audit_req.monthly_income else Decimal("50000.00")
    extra_prep = audit_req.extra_monthly_prepayment if audit_req and audit_req.extra_monthly_prepayment else Decimal("0.00")
    lump_prep = audit_req.lump_sum_prepayment if audit_req and audit_req.lump_sum_prepayment else Decimal("0.00")
    target_loan = audit_req.target_loan_id if audit_req else None

    active_loans = [l for l in loans if l.status == "ACTIVE"]

    total_borrowed = sum((l.original_principal for l in loans), Decimal("0.00"))
    total_outstanding = sum((l.outstanding_principal for l in active_loans), Decimal("0.00"))
    total_monthly_emi = sum((l.emi_amount for l in active_loans), Decimal("0.00"))

    # Compute total remaining interest across all active loans
    total_remaining_interest = Decimal("0.00")
    weighted_rate_sum = Decimal("0.00")

    for l in active_loans:
        future_payments = l.emi_amount * Decimal(l.remaining_tenure_months)
        rem_interest = max(Decimal("0.00"), future_payments - l.outstanding_principal)
        total_remaining_interest += rem_interest
        weighted_rate_sum += l.outstanding_principal * l.interest_rate_percent

    weighted_avg_rate = (
        (weighted_rate_sum / total_outstanding).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if total_outstanding > 0 else Decimal("0.00")
    )

    # FOIR / DTI calculation
    foir_percent = (
        (total_monthly_emi / monthly_income * Decimal("100")).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
        if monthly_income > 0 else Decimal("0.0")
    )

    if foir_percent < Decimal("35.0"):
        foir_risk = "SAFE"
        foir_advice = "Your debt-to-income ratio is healthy (<35%). You have adequate disposable income for savings and emergencies."
    elif foir_percent <= Decimal("50.0"):
        foir_risk = "MODERATE"
        foir_advice = "Moderate debt load (35%-50%). Recommended: Avoid taking new loans; focus extra savings on high-interest EMI reduction."
    elif foir_percent <= Decimal("65.0"):
        foir_risk = "HIGH_RISK"
        foir_advice = "High debt burden (>50%). Lenders classify you as over-leveraged. Immediate balance transfer or debt consolidation is advised."
    else:
        foir_risk = "CRITICAL"
        foir_advice = "Critical debt stress (>65% of monthly income committed to EMIs). High probability of cashflow distress and default risk."

    catalogue_offers = list_loan_products(db)
    benchmark_offer = min(catalogue_offers, key=lambda offer: offer.annual_interest_rate_percent) if catalogue_offers else None
    benchmark_rate = benchmark_offer.annual_interest_rate_percent if benchmark_offer else Decimal("0")

    # Identify high interest loans (> 15% p.a.)
    high_interest_loans = [l for l in active_loans if l.interest_rate_percent >= Decimal("15.00")]
    high_interest_count = len(high_interest_loans)

    # Calculate monthly interest leakage (excess interest paid over catalogue benchmark)
    monthly_leakage = Decimal("0.00")
    if benchmark_offer:
        for l in high_interest_loans:
            diff_rate = l.interest_rate_percent - benchmark_rate
            monthly_diff = (l.outstanding_principal * (diff_rate / Decimal("1200"))).quantize(RUPEE_PRECISION, rounding=ROUND_HALF_UP)
            monthly_leakage += max(Decimal("0.00"), monthly_diff)

    # Refinancing opportunities
    refinancing_opps = compute_refinancing_opportunities(loans, catalogue_offers)

    # Prepayment simulation
    prepayment_sim = run_prepayment_simulation(
        loans=loans,
        target_loan_id=target_loan,
        extra_monthly=extra_prep,
        lump_sum=lump_prep,
    )

    # Consolidated EMI calendar
    today = date.today()
    calendar_items: List[EMICalendarItem] = []
    for l in sorted(active_loans, key=lambda x: x.emi_due_day):
        try:
            due_dt = date.fromisoformat(l.next_due_date)
            days_left = (due_dt - today).days
        except Exception:
            days_left = 5
            due_dt = today + timedelta(days=5)

        calendar_items.append(EMICalendarItem(
            loan_id=l.id,
            lender_name=l.lender_name,
            loan_type=l.loan_type,
            account_number=l.account_number,
            emi_amount=l.emi_amount,
            due_day=l.emi_due_day,
            next_due_date=l.next_due_date,
            days_until_due=max(0, days_left),
            status=l.status,
        ))

    # Actionable AI insights and advice
    ai_insights = [
        f"You have {len(active_loans)} active loans across {len(set(l.lender_name for l in active_loans))} platforms with total monthly EMI of ₹{total_monthly_emi:,.0f}.",
        f"Your Debt-to-Income (FOIR) is {foir_percent}% on ₹{monthly_income:,.0f} income, placing you in the '{foir_risk}' financial category.",
    ]
    if high_interest_count > 0:
        ai_insights.append(
            f"Alert: {high_interest_count} of your loans charge high interest (up to {max(l.interest_rate_percent for l in high_interest_loans)}% p.a.), creating ₹{monthly_leakage:,.0f}/month of interest leakage."
        )
    if refinancing_opps:
        best_opp = max(refinancing_opps, key=lambda o: o.net_benefit_rupees)
        ai_insights.append(
            f"Opportunity: Refinancing your {best_opp.lender_name} loan ({best_opp.current_interest_rate}%) could save you ₹{best_opp.net_benefit_rupees:,.0f} in net interest."
        )

    # Structured Action Plan
    action_plan = [
        "1. Prioritize paying off highest-interest loans first (Debt Avalanche strategy).",
        "2. Keep EMI due dates synchronized after your monthly salary credit date to avoid bounce charges.",
        "3. Consider consolidating high-cost digital credit lines into a single lower-rate bank personal loan.",
    ]
    if prepayment_sim and prepayment_sim.months_saved > 0:
        action_plan.append(f"4. {prepayment_sim.advice}")

    rbi_guideline_notes = [
        "Under RBI Master Directions on Digital Lending, floating-rate personal loans to individuals carry ZERO prepayment or foreclosure charges.",
        "Ensure all lender agreements provide a verified Key Fact Statement (KFS) detailing total Annual Percentage Rate (APR).",
        "Never pay upfront security deposits or advance verification fees to unverified lenders.",
    ]

    return LoanAuditReport(
        total_loans_count=len(loans),
        active_loans_count=len(active_loans),
        total_borrowed_principal=total_borrowed,
        total_outstanding_principal=total_outstanding,
        total_monthly_emi=total_monthly_emi,
        total_remaining_interest=total_remaining_interest,
        weighted_average_interest_rate=weighted_avg_rate,
        monthly_income=monthly_income,
        foir_percent=foir_percent,
        foir_risk_level=foir_risk,
        foir_advice=foir_advice,
        high_interest_loans_count=high_interest_count,
        total_monthly_interest_leakage=monthly_leakage,
        refinancing_opportunities=refinancing_opps,
        prepayment_simulation=prepayment_sim,
        emi_calendar=calendar_items,
        ai_insights=ai_insights,
        action_plan=action_plan,
        rbi_guideline_notes=rbi_guideline_notes,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )

