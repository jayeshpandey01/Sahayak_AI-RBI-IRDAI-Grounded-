#!/usr/bin/env python3
"""Idempotently seed an authenticated user's local demo portfolio.

This writes only isolated demo-wallet entries and explicitly simulated loan rows.
It never creates Stripe orders, Stripe wallet credits, or real repayments.
"""

import argparse
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.models.db_models import (
    DemoWalletAccountModel,
    DemoWalletEntryModel,
    UserLoanModel,
    UserModel,
)
from app.services.demo_wallet_service import (
    DEMO_WALLET_CAP_PAISE,
    MAX_DEMO_FUND_PAISE,
    fund_demo_wallet,
    get_or_create_demo_account,
    send_demo_wallet_money,
)
from app.services.loan_audit_service import seed_default_user_loans

TARGET_BALANCE_PAISE = 10_000_000  # ₹100,000
TARGET_ACTIVITY_COUNT = 100
SEED_PREFIX = "demo-portfolio-v1"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("email", help="Exact email address for the local demo account")
    args = parser.parse_args()

    if settings.ENVIRONMENT.lower() == "production":
        raise SystemExit("Refusing to seed a production database.")
    if not settings.SYNC_DATABASE_URL.startswith("sqlite:"):
        raise SystemExit("Refusing to seed a non-SQLite database; this script is for local demo data only.")

    database_url = make_url(settings.SYNC_DATABASE_URL)
    if database_url.database and database_url.database != ":memory:":
        database_path = Path(database_url.database)
        if not database_path.is_absolute():
            database_url = database_url.set(
                database=str((BACKEND_DIR / database_path).resolve()),
            )

    engine = create_engine(
        database_url,
        connect_args={"check_same_thread": False},
    )
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = Session()
    try:
        user = db.query(UserModel).filter(UserModel.email == args.email.strip().lower()).first()
        if not user:
            raise SystemExit("No account with that email exists in the configured local database.")

        account = get_or_create_demo_account(db, user.id)
        if account.balance_paise > DEMO_WALLET_CAP_PAISE:
            raise SystemExit("Current demo wallet balance is above its configured cap; refusing to seed.")

        # Add only enough explicitly simulated demo funds to reach the requested target.
        fund_index = 0
        while account.balance_paise < TARGET_BALANCE_PAISE:
            amount_paise = min(
                MAX_DEMO_FUND_PAISE,
                TARGET_BALANCE_PAISE - account.balance_paise,
            )
            fund_demo_wallet(
                db,
                user,
                Decimal(amount_paise) / Decimal(100),
                f"{SEED_PREFIX}:{user.id}:fund:{fund_index}",
            )
            db.refresh(account)
            fund_index += 1

        # Seed exactly three sample loans if this user has no loan records.
        loans = db.query(UserLoanModel).filter(UserLoanModel.user_id == user.id).all()
        if not loans:
            loans = seed_default_user_loans(db, user.id)
        for loan in loans:
            if loan.notes and not loan.notes.startswith("SIMULATED DEMO DATA ONLY"):
                # Preserve user-entered note content while ensuring seed results
                # cannot be mistaken for lender-confirmed accounts.
                loan.notes = f"SIMULATED DEMO DATA ONLY — {loan.notes}"
        db.commit()

        # Replace the initial standalone mock rows (if this script version was
        # run already) with proper paired demo-wallet transfers.
        db.query(DemoWalletEntryModel).filter(
            DemoWalletEntryModel.user_id == user.id,
            DemoWalletEntryModel.idempotency_key.like(
                f"{SEED_PREFIX}:{user.id}:activity:%"
            ),
        ).delete(synchronize_session=False)
        db.commit()

        # Reuse/add disabled synthetic contacts so every demo transfer has a
        # matching debit and credit on two isolated demo-wallet accounts.
        counterparties = []
        for index in range(1, 6):
            contact_id = f"demo_contact_{user.id[-8:]}_{index}"
            contact = db.query(UserModel).filter_by(id=contact_id).first()
            if not contact:
                contact = UserModel(
                    id=contact_id,
                    email=f"{contact_id}@sahayak.invalid",
                    password_hash=None,
                    full_name=f"Demo contact {index}",
                    auth_provider="demo",
                    role="borrower",
                    is_active=False,
                    is_verified=False,
                )
                db.add(contact)
                db.flush()
            counterparties.append((contact, get_or_create_demo_account(db, contact.id)))
        db.commit()

        # Put the demo seed funds before the synthetic activity in the history.
        now = datetime.now(timezone.utc)
        fund_rows = db.query(DemoWalletEntryModel).filter(
            DemoWalletEntryModel.user_id == user.id,
            DemoWalletEntryModel.idempotency_key.like(f"{SEED_PREFIX}:{user.id}:fund:%"),
        ).order_by(DemoWalletEntryModel.created_at.asc()).all()
        for index, entry in enumerate(fund_rows):
            entry.created_at = now - timedelta(days=190, minutes=len(fund_rows) - index)
        db.commit()

        current_count = db.query(DemoWalletEntryModel).filter_by(user_id=user.id).count()
        pair = 0
        while current_count < TARGET_ACTIVITY_COUNT:
            contact, contact_account = counterparties[pair % len(counterparties)]
            amount_paise = 35_000 + (pair * 13_700) % 265_000  # ₹350–₹3,000
            amount_rupees = Decimal(amount_paise) / Decimal(100)
            outbound_key = f"{SEED_PREFIX}:{user.id}:out:{pair}"
            inbound_key = f"{SEED_PREFIX}:{contact.id}:in:{pair}"
            sent = send_demo_wallet_money(
                db, user, contact_account.wallet_code, amount_rupees,
                "SIMULATED DEMO TRANSACTION", outbound_key,
            )
            received = send_demo_wallet_money(
                db, contact, account.wallet_code, amount_rupees,
                "SIMULATED DEMO TRANSACTION", inbound_key,
            )
            credit_at = now - timedelta(days=min(179, pair * 4), minutes=25)
            debit_at = now - timedelta(days=min(179, pair * 4), minutes=10)
            for transaction_id, timestamp in (
                (sent["transaction_id"], credit_at),
                (received["transaction_id"], debit_at),
            ):
                db.query(DemoWalletEntryModel).filter(
                    DemoWalletEntryModel.transaction_id == transaction_id,
                ).update({"created_at": timestamp}, synchronize_session=False)
            db.commit()
            current_count = db.query(DemoWalletEntryModel).filter_by(user_id=user.id).count()
            pair += 1

        db.refresh(account)
        final_entry_count = db.query(DemoWalletEntryModel).filter_by(user_id=user.id).count()
        final_loan_count = db.query(UserLoanModel).filter(UserLoanModel.user_id == user.id).count()
        print("Demo portfolio seed complete (all values are simulated).")
        print(f"demo_wallet_balance_rupees: {account.balance_paise / 100:.2f}")
        print(f"demo_wallet_history_entries: {final_entry_count}")
        print(f"simulated_loan_records: {final_loan_count}")
        print("stripe_payment_orders_created: 0")
        print("stripe_wallet_credits_created: 0")
        print("real_repayments_created: 0")
    finally:
        db.close()
        engine.dispose()


if __name__ == "__main__":
    main()
