"""Authenticated recurring expense schedules and manually recorded payments."""

from calendar import monthrange
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from uuid import uuid4
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.database import get_db
from app.models.db_models import BillPaymentRecordModel, RecurringBillModel, UserModel
from app.models.schemas import (
    BillPaymentCreate,
    BillPaymentResponse,
    RecurringBillCreate,
    RecurringBillResponse,
    RecurringBillUpdate,
)

INDIA_TZ = ZoneInfo("Asia/Kolkata")

router = APIRouter(prefix="/api/bills", tags=["Recurring Expense Schedule"])


def _to_bill_response(bill: RecurringBillModel, today: date | None = None) -> RecurringBillResponse:
    today = today or datetime.now(INDIA_TZ).date()
    due_date = date.fromisoformat(bill.next_due_date)
    days_until_due = (due_date - today).days
    if not bill.is_active:
        due_status = "PAUSED"
    elif days_until_due < 0:
        due_status = "OVERDUE"
    elif days_until_due == 0:
        due_status = "DUE_TODAY"
    elif days_until_due <= bill.reminder_days_before:
        due_status = "DUE_SOON"
    else:
        due_status = "UPCOMING"
    amount = (Decimal(bill.expected_amount_paise) / Decimal("100")
              if bill.expected_amount_paise is not None else None)
    return RecurringBillResponse(
        id=bill.id, name=bill.name, category=bill.category, payee=bill.payee,
        expected_amount_rupees=amount, frequency=bill.frequency,
        next_due_date=due_date, reminder_days_before=bill.reminder_days_before,
        is_active=bill.is_active, notes=bill.notes, due_status=due_status,
        days_until_due=days_until_due, created_at=bill.created_at,
        updated_at=bill.updated_at,
    )


def _to_payment_response(payment: BillPaymentRecordModel, bill_name: str) -> BillPaymentResponse:
    return BillPaymentResponse(
        id=payment.id, bill_id=payment.bill_id, bill_name=bill_name,
        due_date=date.fromisoformat(payment.due_date),
        amount_rupees=(Decimal(payment.amount_paise) / Decimal("100")),
        paid_at=payment.paid_at, note=payment.note,
    )


def _next_due_date(due_date: date, frequency: str, schedule_day: int, schedule_month: int | None) -> date:
    if frequency == "WEEKLY":
        from datetime import timedelta
        return due_date + timedelta(days=7)
    if frequency == "YEARLY":
        year, month = due_date.year + 1, schedule_month or due_date.month
        return date(year, month, min(schedule_day, monthrange(year, month)[1]))
    months_to_add = 3 if frequency == "QUARTERLY" else 1
    month_index = due_date.year * 12 + due_date.month - 1 + months_to_add
    year, month_zero = divmod(month_index, 12)
    month = month_zero + 1
    return date(year, month, min(schedule_day, monthrange(year, month)[1]))


@router.get("", response_model=list[RecurringBillResponse])
def list_bills(
    include_inactive: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    query = db.query(RecurringBillModel).filter(RecurringBillModel.user_id == current_user.id)
    if not include_inactive:
        query = query.filter(RecurringBillModel.is_active.is_(True))
    rows = query.order_by(RecurringBillModel.next_due_date.asc(), RecurringBillModel.created_at.desc()).all()
    return [_to_bill_response(row) for row in rows]


@router.post("", response_model=RecurringBillResponse, status_code=status.HTTP_201_CREATED)
def create_bill(
    payload: RecurringBillCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    now = datetime.now(timezone.utc)
    expected_paise = None
    if payload.expected_amount_rupees is not None:
        expected_paise = int((payload.expected_amount_rupees * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    bill = RecurringBillModel(
        id=f"bill_{uuid4().hex}", user_id=current_user.id,
        name=payload.name, category=payload.category.value,
        payee=payload.payee, expected_amount_paise=expected_paise,
        frequency=payload.frequency.value, next_due_date=payload.next_due_date.isoformat(),
        schedule_day=payload.next_due_date.day, schedule_month=payload.next_due_date.month,
        reminder_days_before=payload.reminder_days_before, is_active=True,
        notes=payload.notes, created_at=now, updated_at=now,
    )
    db.add(bill)
    db.commit()
    db.refresh(bill)
    return _to_bill_response(bill)


@router.get("/payments/history", response_model=list[BillPaymentResponse])
def list_bill_payment_history(
    limit: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    rows = db.query(BillPaymentRecordModel, RecurringBillModel.name).join(
        RecurringBillModel, RecurringBillModel.id == BillPaymentRecordModel.bill_id,
    ).filter(
        BillPaymentRecordModel.user_id == current_user.id,
        RecurringBillModel.user_id == current_user.id,
    ).order_by(BillPaymentRecordModel.paid_at.desc()).limit(limit).all()
    return [_to_payment_response(payment, name) for payment, name in rows]


@router.patch("/{bill_id}", response_model=RecurringBillResponse)
def update_bill(
    bill_id: str,
    payload: RecurringBillUpdate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    bill = db.query(RecurringBillModel).filter(
        RecurringBillModel.id == bill_id,
        RecurringBillModel.user_id == current_user.id,
    ).first()
    if not bill:
        raise HTTPException(status_code=404, detail="Bill schedule not found.")
    values = payload.model_dump(exclude_unset=True)
    if "name" in values and values["name"] is not None:
        values["name"] = values["name"].strip()
        if not values["name"]:
            raise HTTPException(status_code=422, detail="Bill name cannot be blank.")
    for key in ("category", "frequency", "next_due_date", "reminder_days_before", "is_active"):
        if key in values and values[key] is None:
            values.pop(key)
    if "category" in values and values["category"] is not None:
        values["category"] = values["category"].value
    if "frequency" in values and values["frequency"] is not None:
        values["frequency"] = values["frequency"].value
    if "next_due_date" in values and values["next_due_date"] is not None:
        next_due_date = values["next_due_date"]
        values["next_due_date"] = next_due_date.isoformat()
        values["schedule_day"] = next_due_date.day
        values["schedule_month"] = next_due_date.month
    if "expected_amount_rupees" in values:
        amount = values.pop("expected_amount_rupees")
        values["expected_amount_paise"] = (
            int((amount * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
            if amount is not None else None
        )
    for key, value in values.items():
        setattr(bill, key, value)
    bill.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(bill)
    return _to_bill_response(bill)


@router.post("/{bill_id}/payments", response_model=BillPaymentResponse, status_code=status.HTTP_201_CREATED)
def record_bill_payment(
    bill_id: str,
    payload: BillPaymentCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    bill = db.query(RecurringBillModel).filter(
        RecurringBillModel.id == bill_id,
        RecurringBillModel.user_id == current_user.id,
        RecurringBillModel.is_active.is_(True),
    ).first()
    if not bill:
        raise HTTPException(status_code=404, detail="Active bill schedule not found.")
    due_date = date.fromisoformat(bill.next_due_date)
    existing = db.query(BillPaymentRecordModel).filter(
        BillPaymentRecordModel.bill_id == bill.id,
        BillPaymentRecordModel.user_id == current_user.id,
        BillPaymentRecordModel.due_date == bill.next_due_date,
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="This bill occurrence is already marked paid.")
    amount_paise = bill.expected_amount_paise
    if payload.amount_rupees is not None:
        amount_paise = int((payload.amount_rupees * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    if amount_paise is None:
        raise HTTPException(status_code=422, detail="Enter the amount paid for this variable bill.")

    now = datetime.now(timezone.utc)
    payment = BillPaymentRecordModel(
        id=f"billpay_{uuid4().hex}", bill_id=bill.id, user_id=current_user.id,
        due_date=bill.next_due_date, amount_paise=amount_paise,
        paid_at=now, note=payload.note, created_at=now,
    )
    db.add(payment)
    bill.next_due_date = _next_due_date(
        due_date, bill.frequency, bill.schedule_day, bill.schedule_month,
    ).isoformat()
    bill.updated_at = now
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="This bill occurrence is already marked paid.") from None
    db.refresh(payment)
    return _to_payment_response(payment, bill.name)
