"""Database-backed loan catalogue with explicitly synthetic development seed data."""

import json
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.db_models import LoanProductModel, LoanRateHistoryModel
from app.models.schemas import LenderOffer, LoanProductUpsert


def _to_offer(product: LoanProductModel, missing: list[str] | None = None) -> LenderOffer:
    try:
        employment_types = json.loads(product.employment_types_json or "[]")
    except (TypeError, ValueError):
        employment_types = []
    try:
        locations = json.loads(product.locations_json or "[]")
    except (TypeError, ValueError):
        locations = []
    return LenderOffer(
        offer_id=product.offer_id, lender_id=product.lender_id,
        lender_name=product.lender_name,
        annual_interest_rate_percent=product.annual_interest_rate_percent,
        processing_fee_percent=product.processing_fee_percent,
        processing_fee_gst_percent=product.processing_fee_gst_percent,
        min_amount=product.min_amount, max_amount=product.max_amount,
        min_tenure_months=product.min_tenure_months,
        max_tenure_months=product.max_tenure_months,
        kfs_version=product.kfs_version, kfs_effective_date=product.kfs_effective_date,
        disclaimer=product.disclaimer, product_name=product.product_name,
        loan_type=product.loan_type, min_monthly_income=product.min_monthly_income,
        min_age=product.min_age, max_age=product.max_age,
        employment_types=employment_types, locations=locations,
        source_name=product.source_name, source_url=product.source_url,
        source_type=product.source_type, last_verified_at=product.last_verified_at,
        status=product.status, eligibility_data_missing=bool(missing),
        missing_criteria=missing or [],
    )


def seed_demo_catalogue_if_empty(db: Session) -> None:
    if db.query(LoanProductModel.offer_id).first():
        return
    # Import lazily to keep the calculator independent of database initialization.
    from app.services.financial_calculator import OFFERS_CATALOGUE

    now = datetime.now(timezone.utc)
    for offer in OFFERS_CATALOGUE:
        product = LoanProductModel(
            offer_id=offer.offer_id, lender_id=offer.lender_id,
            lender_name=offer.lender_name, product_name="Personal Loan",
            loan_type="personal", min_amount=offer.min_amount,
            max_amount=offer.max_amount,
            annual_interest_rate_percent=offer.annual_interest_rate_percent,
            processing_fee_percent=offer.processing_fee_percent,
            processing_fee_gst_percent=offer.processing_fee_gst_percent,
            min_tenure_months=offer.min_tenure_months,
            max_tenure_months=offer.max_tenure_months,
            employment_types_json="[]", locations_json="[]",
            kfs_version=offer.kfs_version, kfs_effective_date=offer.kfs_effective_date,
            source_name="Synthetic demo catalogue", source_type="synthetic",
            status="active",
            disclaimer="Synthetic demo terms for calculation only; not a lender offer or approval.",
            created_at=now, updated_at=now,
        )
        db.add(product)
        db.flush()
        db.add(LoanRateHistoryModel(
            id=f"lrh_{uuid4().hex}", offer_id=offer.offer_id,
            annual_interest_rate_percent=offer.annual_interest_rate_percent,
            processing_fee_percent=offer.processing_fee_percent,
            valid_from=now, source_name="Synthetic demo catalogue",
            created_at=now,
        ))
    db.commit()


def list_loan_products(
    db: Session, *, loan_amount: Decimal | None = None,
    tenure_months: int | None = None, monthly_income: Decimal | None = None,
    employment_type: str | None = None, location: str | None = None,
    loan_type: str | None = None,
) -> list[LenderOffer]:
    seed_demo_catalogue_if_empty(db)
    products = db.query(LoanProductModel).filter_by(status="active").order_by(
        LoanProductModel.annual_interest_rate_percent.asc(), LoanProductModel.lender_name.asc()
    ).all()
    offers = []
    for product in products:
        if loan_type is not None and (product.loan_type or "").lower() != loan_type.lower():
            continue
        if loan_amount is not None and not (product.min_amount <= loan_amount <= product.max_amount):
            continue
        if tenure_months is not None and not (product.min_tenure_months <= tenure_months <= product.max_tenure_months):
            continue
        if product.min_monthly_income is not None and monthly_income is not None and monthly_income < product.min_monthly_income:
            continue
        employment_types = json.loads(product.employment_types_json or "[]")
        locations = json.loads(product.locations_json or "[]")
        if employment_type and employment_types and employment_type.lower() not in employment_types:
            continue
        if location and locations and location.lower() not in locations:
            continue
        missing = []
        if product.min_monthly_income is not None and monthly_income is None:
            missing.append("monthly_income")
        if employment_types and employment_type is None:
            missing.append("employment_type")
        if locations and location is None:
            missing.append("location")
        offers.append(_to_offer(product, missing))
    return offers


def get_loan_offer(db: Session, offer_id: str) -> LenderOffer | None:
    seed_demo_catalogue_if_empty(db)
    product = db.query(LoanProductModel).filter_by(offer_id=offer_id, status="active").first()
    return _to_offer(product) if product else None


def upsert_loan_product(db: Session, payload: LoanProductUpsert) -> LenderOffer:
    now = datetime.now(timezone.utc)
    product = db.query(LoanProductModel).filter_by(offer_id=payload.offer_id).first()
    was_new = product is None
    if was_new:
        product = LoanProductModel(offer_id=payload.offer_id, created_at=now)
        db.add(product)
    old_rate = product.annual_interest_rate_percent if not was_new else None
    old_fee = product.processing_fee_percent if not was_new else None
    values = payload.model_dump(exclude={"employment_types", "locations"})
    for key, value in values.items():
        setattr(product, key, value)
    product.employment_types_json = json.dumps(payload.employment_types)
    product.locations_json = json.dumps(payload.locations)
    product.updated_at = now
    db.flush()
    if was_new or old_rate != payload.annual_interest_rate_percent or old_fee != payload.processing_fee_percent:
        previous = db.query(LoanRateHistoryModel).filter_by(offer_id=payload.offer_id, valid_until=None).first()
        if previous:
            previous.valid_until = now
        db.add(LoanRateHistoryModel(
            id=f"lrh_{uuid4().hex}", offer_id=payload.offer_id,
            annual_interest_rate_percent=payload.annual_interest_rate_percent,
            processing_fee_percent=payload.processing_fee_percent, valid_from=now,
            source_name=payload.source_name, source_url=payload.source_url, created_at=now,
        ))
    db.commit()
    db.refresh(product)
    return _to_offer(product)


def list_rate_history(db: Session, offer_id: str) -> list[LoanRateHistoryModel]:
    return db.query(LoanRateHistoryModel).filter_by(offer_id=offer_id).order_by(
        LoanRateHistoryModel.valid_from.desc()
    ).all()
