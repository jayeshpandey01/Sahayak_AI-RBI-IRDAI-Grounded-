import hashlib
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional
from app.models.schemas import LenderOffer, EMICalculationResponse, AmortizationItem

# Standard RBI KFS Rounding Precision
RUPEE_PRECISION = Decimal("1")
PERCENT_PRECISION = Decimal("0.01")

OFFERS_CATALOGUE: List[LenderOffer] = [
    LenderOffer(
        offer_id="offer-hdfc-01",
        lender_id="lender-hdfc",
        lender_name="HDFC Bank (Synthetic Partner)",
        annual_interest_rate_percent=Decimal("11.50"),
        processing_fee_percent=Decimal("1.25"),
        processing_fee_gst_percent=Decimal("18.00"),
        min_amount=Decimal("25000"),
        max_amount=Decimal("2000000"),
        min_tenure_months=12,
        max_tenure_months=60,
        kfs_version="KFS-HDFC-2026.1",
        kfs_effective_date="2026-01-01",
        disclaimer="Indicative offer under RBI Digital Lending Guidelines 2025. Subject to formal verification.",
    ),
    LenderOffer(
        offer_id="offer-icici-02",
        lender_id="lender-icici",
        lender_name="ICICI Bank (Synthetic Partner)",
        annual_interest_rate_percent=Decimal("12.75"),
        processing_fee_percent=Decimal("1.00"),
        processing_fee_gst_percent=Decimal("18.00"),
        min_amount=Decimal("10000"),
        max_amount=Decimal("1500000"),
        min_tenure_months=6,
        max_tenure_months=48,
        kfs_version="KFS-ICICI-2026.2",
        kfs_effective_date="2026-02-15",
        disclaimer="Pre-approved indicative terms. No upfront advance fee required.",
    ),
    LenderOffer(
        offer_id="offer-bajaj-03",
        lender_id="lender-bajaj",
        lender_name="Bajaj Finance (Synthetic Partner)",
        annual_interest_rate_percent=Decimal("14.00"),
        processing_fee_percent=Decimal("1.50"),
        processing_fee_gst_percent=Decimal("18.00"),
        min_amount=Decimal("10000"),
        max_amount=Decimal("1000000"),
        min_tenure_months=6,
        max_tenure_months=36,
        kfs_version="KFS-BAJAJ-2026.1",
        kfs_effective_date="2026-01-10",
        disclaimer="Flexible tenure personal loan with zero pre-payment charges after 6 months.",
    ),
]

def get_offer_by_id(offer_id: str, db=None) -> Optional[LenderOffer]:
    if db is not None:
        from app.services.loan_catalogue_service import get_loan_offer
        return get_loan_offer(db, offer_id)
    for offer in OFFERS_CATALOGUE:
        if offer.offer_id == offer_id:
            return offer
    return None

def calculate_kfs_emi(
    principal: Decimal,
    tenure_months: int,
    offer: LenderOffer,
    maximum_emi: Optional[Decimal] = None
) -> EMICalculationResponse:
    """
    Computes deterministic EMI, Total Repayment, Upfront Deductions, and Annual Percentage Rate (APR)
    strictly using Python Decimal arithmetic matching RBI Key Fact Statement (KFS) standards.
    """
    if principal <= Decimal("0"):
        raise ValueError("Principal must be greater than zero")
    if tenure_months <= 0:
        raise ValueError("Tenure months must be greater than zero")

    monthly_rate = (offer.annual_interest_rate_percent / Decimal("1200"))
    
    if monthly_rate == Decimal("0"):
        raw_emi = principal / Decimal(tenure_months)
    else:
        # Standard reducing balance EMI formula: P * r * (1+r)^n / ((1+r)^n - 1)
        factor = (Decimal("1") + monthly_rate) ** tenure_months
        raw_emi = principal * monthly_rate * factor / (factor - Decimal("1"))

    # RBI Standard: Round EMI to nearest integer rupee
    emi = raw_emi.quantize(RUPEE_PRECISION, rounding=ROUND_HALF_UP)
    total_repayment = (emi * Decimal(tenure_months)).quantize(RUPEE_PRECISION, rounding=ROUND_HALF_UP)
    total_interest = total_repayment - principal

    # Processing Fee + 18% GST calculation
    base_processing_fee = (principal * offer.processing_fee_percent / Decimal("100")).quantize(
        RUPEE_PRECISION, rounding=ROUND_HALF_UP
    )
    gst_fee = (base_processing_fee * offer.processing_fee_gst_percent / Decimal("100")).quantize(
        RUPEE_PRECISION, rounding=ROUND_HALF_UP
    )
    total_upfront_deductions = base_processing_fee + gst_fee
    net_disbursed = principal - total_upfront_deductions

    # Annual Percentage Rate (APR) including total finance charges (Interest + All upfront fees)
    # Annualized over tenure as mandated in RBI KFS 2025:
    total_cost_of_credit = total_interest + total_upfront_deductions
    apr = ((total_cost_of_credit / principal) * (Decimal("12") / Decimal(tenure_months)) * Decimal("100")).quantize(
        PERCENT_PRECISION, rounding=ROUND_HALF_UP
    )

    # Cryptographic digest of KFS terms to ensure unalterable state
    kfs_data = f"{offer.offer_id}:{offer.kfs_version}:{principal}:{tenure_months}:{emi}:{apr}"
    kfs_hash = hashlib.sha256(kfs_data.encode("utf-8")).hexdigest()

    is_within_limit = None
    if maximum_emi is not None:
        is_within_limit = emi <= maximum_emi

    assumptions = [
        f"Interest calculation mode: Reducing balance at {offer.annual_interest_rate_percent}% p.a.",
        f"Processing fee: {offer.processing_fee_percent}% plus {offer.processing_fee_gst_percent}% GST",
        "EMI rounded to nearest whole rupee per RBI Key Fact Statement guidelines",
        f"KFS Version: {offer.kfs_version} (Effective {offer.kfs_effective_date})",
        "No hidden charges, pre-closure or advance EMI deductions without customer consent",
    ]

    return EMICalculationResponse(
        offer_id=offer.offer_id,
        lender_name=offer.lender_name,
        principal_rupees=principal,
        tenure_months=tenure_months,
        annual_interest_rate_percent=offer.annual_interest_rate_percent,
        monthly_interest_rate=monthly_rate.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP),
        estimated_emi_rupees=emi,
        total_interest_rupees=total_interest,
        processing_fee_rupees=base_processing_fee,
        illustrative_processing_fee_rupees=base_processing_fee,
        processing_fee_gst_rupees=gst_fee,
        total_upfront_deductions_rupees=total_upfront_deductions,
        net_disbursed_amount_rupees=net_disbursed,
        total_repayment_rupees=total_repayment,
        annual_percentage_rate_apr=apr,
        within_user_emi_limit=is_within_limit,
        kfs_document_hash=kfs_hash,
        assumptions=assumptions,
    )

def generate_amortization_schedule(
    principal: Decimal,
    tenure_months: int,
    offer: LenderOffer
) -> List[AmortizationItem]:
    """Generates month-by-month principal and interest amortization breakdown."""
    monthly_rate = offer.annual_interest_rate_percent / Decimal("1200")
    if monthly_rate == Decimal("0"):
        emi = (principal / Decimal(tenure_months)).quantize(RUPEE_PRECISION, rounding=ROUND_HALF_UP)
    else:
        factor = (Decimal("1") + monthly_rate) ** tenure_months
        emi = (principal * monthly_rate * factor / (factor - Decimal("1"))).quantize(
            RUPEE_PRECISION, rounding=ROUND_HALF_UP
        )

    schedule: List[AmortizationItem] = []
    opening = principal

    for m in range(1, tenure_months + 1):
        interest_comp = (opening * monthly_rate).quantize(RUPEE_PRECISION, rounding=ROUND_HALF_UP)
        principal_comp = emi - interest_comp
        closing = opening - principal_comp
        if m == tenure_months or closing < Decimal("0"):
            principal_comp = opening
            closing = Decimal("0")
            emi = principal_comp + interest_comp

        schedule.append(
            AmortizationItem(
                month=m,
                opening_balance=opening,
                emi=emi,
                principal_component=principal_comp,
                interest_component=interest_comp,
                closing_balance=closing,
            )
        )
        opening = closing

    return schedule
