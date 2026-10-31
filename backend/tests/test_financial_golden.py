import pytest
from decimal import Decimal
from app.models.schemas import LenderOffer
from app.services.financial_calculator import (
    calculate_kfs_emi,
    generate_amortization_schedule,
    get_offer_by_id,
    OFFERS_CATALOGUE,
)

# Golden Test Cases for RBI KFS Precision
# Case 1: P = 50,000, R = 12.75%, N = 24 months
# Monthly rate r = 12.75 / 1200 = 0.010625
# (1+r)^24 = 1.010625^24 = 1.288226068...
# EMI = 50000 * 0.010625 * 1.288226068 / (1.288226068 - 1) = 684.3701 / 0.288226 = 2374.42 -> 2374
# Processing fee 1.0%: 50000 * 0.01 = 500
# GST on fee 18%: 500 * 0.18 = 90
# Upfront deduction = 590
# Net disbursed = 49410
# Total repayment = 2374 * 24 = 56976
# Total interest = 56976 - 50000 = 6976

def test_golden_standard_personal_loan():
    offer = LenderOffer(
        offer_id="test-icici",
        lender_id="icici",
        lender_name="ICICI",
        annual_interest_rate_percent=Decimal("12.75"),
        processing_fee_percent=Decimal("1.00"),
        processing_fee_gst_percent=Decimal("18.00"),
        min_amount=Decimal("10000"),
        max_amount=Decimal("1000000"),
        min_tenure_months=6,
        max_tenure_months=48,
        kfs_version="KFS-V1",
        kfs_effective_date="2026-01-01",
    )
    result = calculate_kfs_emi(
        principal=Decimal("50000"),
        tenure_months=24,
        offer=offer,
        maximum_emi=Decimal("2500"),
    )

    assert result.estimated_emi_rupees == Decimal("2371")  # Exact reducing balance computation
    assert result.processing_fee_rupees == Decimal("500")
    assert result.processing_fee_gst_rupees == Decimal("90")
    assert result.total_upfront_deductions_rupees == Decimal("590")
    assert result.net_disbursed_amount_rupees == Decimal("49410")
    assert result.total_repayment_rupees == result.estimated_emi_rupees * 24
    assert result.total_interest_rupees == result.total_repayment_rupees - Decimal("50000")
    assert result.within_user_emi_limit is True
    assert result.kfs_document_hash is not None
    assert len(result.kfs_document_hash) == 64

def test_golden_zero_interest_rate():
    offer = LenderOffer(
        offer_id="test-zero",
        lender_id="zero",
        lender_name="Zero Loan",
        annual_interest_rate_percent=Decimal("0.0"),  # handled gracefully
        processing_fee_percent=Decimal("0.0"),
        processing_fee_gst_percent=Decimal("18.0"),
        min_amount=Decimal("1000"),
        max_amount=Decimal("50000"),
        min_tenure_months=1,
        max_tenure_months=12,
        kfs_version="V1",
        kfs_effective_date="2026-01-01",
    )
    result = calculate_kfs_emi(Decimal("12000"), 12, offer)
    assert result.estimated_emi_rupees == Decimal("1000")
    assert result.total_repayment_rupees == Decimal("12000")
    assert result.total_interest_rupees == Decimal("0")

def test_golden_boundary_validations():
    offer = OFFERS_CATALOGUE[0]
    with pytest.raises(ValueError, match="Principal must be greater than zero"):
        calculate_kfs_emi(Decimal("0"), 12, offer)

    with pytest.raises(ValueError, match="Tenure months must be greater than zero"):
        calculate_kfs_emi(Decimal("10000"), 0, offer)

def test_amortization_schedule_balances():
    offer = OFFERS_CATALOGUE[0]
    schedule = generate_amortization_schedule(Decimal("100000"), 12, offer)
    assert len(schedule) == 12
    assert schedule[0].opening_balance == Decimal("100000")
    assert schedule[-1].closing_balance == Decimal("0")
    # Verify sum of principal components equals principal
    sum_principal = sum(item.principal_component for item in schedule)
    assert sum_principal == Decimal("100000")

def test_get_offer_catalogue():
    assert len(OFFERS_CATALOGUE) >= 3
    offer = get_offer_by_id("offer-hdfc-01")
    assert offer is not None
    assert offer.lender_id == "lender-hdfc"
    assert get_offer_by_id("non-existent-offer") is None

def test_legacy_create_payment_intent_endpoint(client):
    res = client.post(
        "/api/financial/create-payment-intent",
        json={"amount_rupees": 1500.0, "purpose": "Wallet Top-Up"}
    )
    assert res.status_code == 410
    assert "untracked PaymentIntent route is disabled" in res.json()["detail"]

