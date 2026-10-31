"""Safe, transparent demo payment-behaviour indicator (not a credit-bureau score)."""
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.db_models import DemoRepaymentModel


def build_payment_behaviour_estimate(db: Session, user_id: str) -> dict[str, Any]:
    """Summarize explicit simulated repayment records owned by this user.

    Wallet top-ups and general payments are deliberately excluded: they do not
    establish credit repayment behavior or a CIBIL score.
    """
    rows = db.query(DemoRepaymentModel).filter(
        DemoRepaymentModel.user_id == user_id,
        DemoRepaymentModel.source == "simulation",
    ).order_by(DemoRepaymentModel.due_at.desc()).limit(36).all()
    counted = [row for row in rows if row.status in {"PAID_ON_TIME", "PAID_LATE", "MISSED"}]
    if not counted:
        return {
            "score_type": "sahayak_demo_payment_behaviour",
            "is_official_credit_score": False,
            "status": "INSUFFICIENT_DATA",
            "score": None,
            "range": None,
            "repayment_count": 0,
            "on_time_count": 0,
            "late_count": 0,
            "missed_count": 0,
            "basis": "No simulated repayment records are available. Wallet top-ups and ordinary payments are not credit repayment history.",
            "disclaimer": "This is not a CIBIL or other bureau score and cannot assess creditworthiness or predict loan approval.",
            "calculated_at": datetime.now(timezone.utc).isoformat(),
        }

    on_time = sum(row.status == "PAID_ON_TIME" for row in counted)
    late = sum(row.status == "PAID_LATE" for row in counted)
    missed = sum(row.status == "MISSED" for row in counted)
    # A bounded demonstration indicator based only on explicit mock repayment
    # events. It is intentionally labeled and never shown as a bureau score.
    score = round(300 + 600 * (on_time + 0.25 * late) / len(counted))
    return {
        "score_type": "sahayak_demo_payment_behaviour",
        "is_official_credit_score": False,
        "status": "ESTIMATE_AVAILABLE",
        "score": score,
        "range": {"min": 300, "max": 900},
        "repayment_count": len(counted),
        "on_time_count": on_time,
        "late_count": late,
        "missed_count": missed,
        "basis": "Synthetic repayment records only; no lender or credit-bureau data was queried.",
        "disclaimer": "This is not a CIBIL or other bureau score and cannot assess creditworthiness or predict loan approval.",
        "calculated_at": datetime.now(timezone.utc).isoformat(),
    }
