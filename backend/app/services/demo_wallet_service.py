"""Account-scoped simulated wallet operations. No real cash is represented."""

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.models.db_models import DemoWalletAccountModel, DemoWalletEntryModel, UserModel

DEMO_WALLET_CAP_PAISE = 10_000_000  # ₹100,000
MAX_DEMO_FUND_PAISE = 1_000_000  # ₹10,000 per action


def amount_to_paise(amount_rupees: Decimal) -> int:
    value = amount_rupees * Decimal(100)
    if value != value.to_integral_value():
        raise HTTPException(status_code=422, detail="Amount must be in whole paise.")
    return int(value)


def get_or_create_demo_account(db: Session, user_id: str) -> DemoWalletAccountModel:
    account = db.query(DemoWalletAccountModel).filter_by(user_id=user_id).first()
    if account:
        return account
    account = DemoWalletAccountModel(
        user_id=user_id,
        wallet_code=f"UBK-{uuid4().hex[:12].upper()}",
        balance_paise=0,
    )
    db.add(account)
    db.flush()
    return account


def wallet_account_response(db: Session, user_id: str) -> dict:
    account = get_or_create_demo_account(db, user_id)
    result = {"wallet_code": account.wallet_code, "balance_paise": account.balance_paise}
    db.commit()
    return result


def fund_demo_wallet(db: Session, user: UserModel, amount_rupees: Decimal, idempotency_key: str) -> dict:
    amount_paise = amount_to_paise(amount_rupees)
    if amount_paise > MAX_DEMO_FUND_PAISE:
        raise HTTPException(status_code=422, detail="Demo funds are limited to ₹10,000 per action.")
    existing = db.query(DemoWalletEntryModel).filter_by(
        user_id=user.id, idempotency_key=idempotency_key,
    ).first()
    if existing:
        if existing.amount_paise != amount_paise or existing.entry_type != "DEMO_FUND":
            raise HTTPException(status_code=409, detail="Idempotency key was already used for a different wallet operation.")
        account = db.query(DemoWalletAccountModel).filter_by(user_id=user.id).first()
        return {"transaction_id": existing.transaction_id, "amount_paise": existing.amount_paise,
                "balance_paise": account.balance_paise, "status": "COMPLETED"}

    try:
        account = get_or_create_demo_account(db, user.id)
        updated = db.execute(
            update(DemoWalletAccountModel)
            .where(DemoWalletAccountModel.user_id == user.id,
                   DemoWalletAccountModel.balance_paise <= DEMO_WALLET_CAP_PAISE - amount_paise)
            .values(balance_paise=DemoWalletAccountModel.balance_paise + amount_paise,
                    updated_at=datetime.now(timezone.utc))
        )
        if updated.rowcount != 1:
            raise HTTPException(status_code=409, detail="Demo wallet balance limit reached.")
        transaction_id = f"dtx_{uuid4().hex[:20]}"
        db.add(DemoWalletEntryModel(
            id=f"dwe_{uuid4().hex[:20]}", transaction_id=transaction_id,
            user_id=user.id, idempotency_key=idempotency_key, entry_type="DEMO_FUND",
            amount_paise=amount_paise, description="Demo funds added",
        ))
        db.flush()
        db.refresh(account)
        response = {"transaction_id": transaction_id, "amount_paise": amount_paise,
                    "balance_paise": account.balance_paise, "status": "COMPLETED"}
        db.commit()
        return response
    except Exception:
        db.rollback()
        raise


def send_demo_wallet_money(
    db: Session, sender: UserModel, recipient_wallet_code: str,
    amount_rupees: Decimal, note: str | None, idempotency_key: str,
) -> dict:
    amount_paise = amount_to_paise(amount_rupees)
    if amount_paise <= 0:
        raise HTTPException(status_code=422, detail="Amount must be greater than zero.")

    existing = db.query(DemoWalletEntryModel).filter_by(
        user_id=sender.id, idempotency_key=idempotency_key,
    ).first()
    if existing:
        if (existing.amount_paise != amount_paise or existing.entry_type != "DEBIT"
                or existing.counterparty_user_id is None):
            raise HTTPException(status_code=409, detail="Idempotency key was already used for a different wallet operation.")
        existing_recipient_account = db.query(DemoWalletAccountModel).filter_by(
            user_id=existing.counterparty_user_id,
        ).first()
        if not existing_recipient_account or existing_recipient_account.wallet_code != recipient_wallet_code:
            raise HTTPException(status_code=409, detail="Idempotency key was already used for a different recipient.")
        account = db.query(DemoWalletAccountModel).filter_by(user_id=sender.id).first()
        recipient = db.query(UserModel).filter_by(id=existing.counterparty_user_id).first()
        return {"transaction_id": existing.transaction_id, "amount_paise": existing.amount_paise,
                "balance_paise": account.balance_paise,
                "recipient_name": recipient.full_name if recipient else "Demo user",
                "status": "COMPLETED"}

    recipient_account = db.query(DemoWalletAccountModel).filter_by(
        wallet_code=recipient_wallet_code,
    ).first()
    if not recipient_account:
        raise HTTPException(status_code=404, detail="Demo wallet QR code was not found.")
    if recipient_account.user_id == sender.id:
        raise HTTPException(status_code=422, detail="You cannot send demo funds to your own wallet.")

    try:
        sender_account = get_or_create_demo_account(db, sender.id)
        debit = db.execute(
            update(DemoWalletAccountModel)
            .where(DemoWalletAccountModel.user_id == sender.id,
                   DemoWalletAccountModel.balance_paise >= amount_paise)
            .values(balance_paise=DemoWalletAccountModel.balance_paise - amount_paise,
                    updated_at=datetime.now(timezone.utc))
        )
        if debit.rowcount != 1:
            raise HTTPException(status_code=409, detail="Insufficient demo funds for this send.")

        credit = db.execute(
            update(DemoWalletAccountModel)
            .where(DemoWalletAccountModel.user_id == recipient_account.user_id,
                   DemoWalletAccountModel.balance_paise <= DEMO_WALLET_CAP_PAISE - amount_paise)
            .values(balance_paise=DemoWalletAccountModel.balance_paise + amount_paise,
                    updated_at=datetime.now(timezone.utc))
        )
        if credit.rowcount != 1:
            raise HTTPException(status_code=409, detail="Recipient demo wallet balance limit reached.")

        transaction_id = f"dtx_{uuid4().hex[:20]}"
        recipient = db.query(UserModel).filter_by(id=recipient_account.user_id).first()
        recipient_name = (recipient.full_name if recipient and recipient.full_name else "Demo user")
        note_text = f" · {note.strip()}" if note and note.strip() else ""
        sender_name = sender.full_name or "Demo user"
        db.add_all([
            DemoWalletEntryModel(
                id=f"dwe_{uuid4().hex[:20]}", transaction_id=transaction_id,
                user_id=sender.id, counterparty_user_id=recipient_account.user_id,
                idempotency_key=idempotency_key, entry_type="DEBIT", amount_paise=amount_paise,
                description=f"Sent demo funds to {recipient_name}{note_text}",
            ),
            DemoWalletEntryModel(
                id=f"dwe_{uuid4().hex[:20]}", transaction_id=transaction_id,
                user_id=recipient_account.user_id, counterparty_user_id=sender.id,
                entry_type="CREDIT", amount_paise=amount_paise,
                description=f"Received demo funds from {sender_name}{note_text}",
            ),
        ])
        db.flush()
        db.refresh(sender_account)
        response = {"transaction_id": transaction_id, "amount_paise": amount_paise,
                    "balance_paise": sender_account.balance_paise,
                    "recipient_name": recipient_name, "status": "COMPLETED"}
        db.commit()
        return response
    except Exception:
        db.rollback()
        raise


def list_demo_wallet_entries(db: Session, user_id: str, limit: int = 50) -> list[dict]:
    entries = db.query(DemoWalletEntryModel).filter_by(user_id=user_id).order_by(
        DemoWalletEntryModel.created_at.desc(), DemoWalletEntryModel.id.desc(),
    ).limit(limit).all()
    results = []
    for entry in entries:
        counterparty = None
        if entry.counterparty_user_id:
            counterparty = db.query(UserModel).filter_by(id=entry.counterparty_user_id).first()
        results.append({
            "transaction_id": entry.transaction_id,
            "entry_type": entry.entry_type,
            "amount_paise": entry.amount_paise,
            "description": entry.description,
            "counterparty_name": counterparty.full_name if counterparty else None,
            "created_at": entry.created_at,
        })
    return results
