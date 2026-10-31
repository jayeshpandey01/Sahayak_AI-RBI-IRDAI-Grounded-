from typing import List

from fastapi import APIRouter, Depends, Header, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.database import get_db
from app.models.db_models import UserModel
from app.models.schemas import (
    DemoWalletAccountResponse,
    DemoWalletEntryResponse,
    DemoWalletFundRequest,
    DemoWalletMutationResponse,
    DemoWalletTransferRequest,
)
from app.services.demo_wallet_service import (
    fund_demo_wallet,
    list_demo_wallet_entries,
    send_demo_wallet_money,
    wallet_account_response,
)

router = APIRouter(prefix="/api/v1/demo-wallet", tags=["Demo Wallet"])


@router.get("/me", response_model=DemoWalletAccountResponse)
def get_my_demo_wallet(
    db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user),
):
    account = wallet_account_response(db, current_user.id)
    account["display_name"] = current_user.full_name or "Demo user"
    return account


@router.post("/funds", response_model=DemoWalletMutationResponse,
             status_code=status.HTTP_201_CREATED)
def add_demo_funds(
    payload: DemoWalletFundRequest,
    x_idempotency_key: str = Header(..., alias="X-Idempotency-Key", min_length=8, max_length=128),
    db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user),
):
    return fund_demo_wallet(db, current_user, payload.amount_rupees, x_idempotency_key)


@router.post("/transfers", response_model=DemoWalletMutationResponse,
             status_code=status.HTTP_201_CREATED)
def send_demo_funds(
    payload: DemoWalletTransferRequest,
    x_idempotency_key: str = Header(..., alias="X-Idempotency-Key", min_length=8, max_length=128),
    db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user),
):
    return send_demo_wallet_money(
        db, current_user, payload.recipient_wallet_code,
        payload.amount_rupees, payload.note, x_idempotency_key,
    )


@router.get("/entries", response_model=List[DemoWalletEntryResponse])
def get_my_demo_wallet_entries(
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user),
):
    return list_demo_wallet_entries(db, current_user.id, limit)
