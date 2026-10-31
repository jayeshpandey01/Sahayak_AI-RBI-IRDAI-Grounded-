"""Shared atomic rate limits for external chat calls."""

from datetime import datetime, timedelta, timezone
import hashlib
import hmac

from sqlalchemy import case
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.orm import Session

from app.config import settings
from app.models.db_models import AIRateLimitBucketModel


class AIRateLimitExceeded(Exception):
    def __init__(self, retry_after: int):
        self.retry_after = max(1, retry_after)


def _actor_hash(actor: str) -> str:
    # The stable key is necessary for per-user limits; persist only a keyed digest.
    key = settings.AI_RATE_LIMIT_HMAC_KEY or settings.JWT_SECRET
    return hmac.new(key.encode(), actor.encode(), hashlib.sha256).hexdigest()


def _window(now: datetime, seconds: int) -> tuple[datetime, int]:
    epoch = int(now.timestamp())
    start_epoch = epoch - epoch % seconds
    return datetime.fromtimestamp(start_epoch, tz=timezone.utc).replace(tzinfo=None), seconds - (epoch - start_epoch)


def _increment(db: Session, scope: str, start: datetime, actor_hash: str, ceiling: int) -> int:
    model = AIRateLimitBucketModel
    values = {"scope": scope, "bucket_start": start, "actor_hash": actor_hash, "request_count": 1}
    dialect = db.get_bind().dialect.name
    if dialect == "sqlite":
        statement = sqlite_insert(model).values(**values)
    elif dialect == "postgresql":
        statement = postgres_insert(model).values(**values)
    else:
        raise RuntimeError("AI shared rate limits require SQLite or PostgreSQL atomic upsert support.")
    statement = statement.on_conflict_do_update(
        index_elements=["scope", "bucket_start", "actor_hash"],
        set_={
            "request_count": case(
                (model.request_count < ceiling, model.request_count + 1),
                else_=model.request_count,
            )
        },
    ).returning(model.request_count)
    return int(db.execute(statement).scalar_one())


def reserve_chat_request(db: Session, actor: str) -> None:
    """Consume all windows atomically before an external call; failures count against provider caps."""
    now = datetime.now(timezone.utc)
    minute_start, minute_retry = _window(now, 60)
    day_start, day_retry = _window(now, 86400)
    hour_start, hour_retry = _window(now, 3600)
    actor_digest = _actor_hash(actor)
    try:
        with db.begin_nested():
            # Keep this privacy-preserving counter table bounded without a background worker.
            db.query(AIRateLimitBucketModel).filter(
                AIRateLimitBucketModel.bucket_start < now.replace(tzinfo=None) - timedelta(days=2)
            ).delete(synchronize_session=False)
            minute_count = _increment(db, "global_minute", minute_start, "global", settings.OPENROUTER_MINUTE_LIMIT + 1)
            day_count = _increment(db, "global_day", day_start, "global", settings.OPENROUTER_DAILY_LIMIT + 1)
            user_count = _increment(db, "user_hour", hour_start, actor_digest, settings.AI_USER_HOURLY_LIMIT + 1)
            if minute_count > settings.OPENROUTER_MINUTE_LIMIT:
                retry_after = minute_retry
            elif day_count > settings.OPENROUTER_DAILY_LIMIT:
                retry_after = day_retry
            elif user_count > settings.AI_USER_HOURLY_LIMIT:
                retry_after = hour_retry
            else:
                retry_after = None
        # Store denied reservations too, but cap each bucket at limit + 1. This both
        # preserves the provider-call count and prevents repeated 429s growing counters.
        db.commit()
        if retry_after is not None:
            raise AIRateLimitExceeded(retry_after)
    except AIRateLimitExceeded:
        raise
    except Exception:
        db.rollback()
        raise


def reserve_user_ai_request(db: Session, actor: str) -> None:
    """Apply the shared per-user AI cap to speech calls, which do not use OpenRouter."""
    now = datetime.now(timezone.utc)
    hour_start, hour_retry = _window(now, 3600)
    actor_digest = _actor_hash(actor)
    try:
        with db.begin_nested():
            db.query(AIRateLimitBucketModel).filter(
                AIRateLimitBucketModel.bucket_start < now.replace(tzinfo=None) - timedelta(days=2)
            ).delete(synchronize_session=False)
            count = _increment(
                db, "user_hour", hour_start, actor_digest,
                settings.AI_USER_HOURLY_LIMIT + 1,
            )
        db.commit()
        if count > settings.AI_USER_HOURLY_LIMIT:
            raise AIRateLimitExceeded(hour_retry)
    except AIRateLimitExceeded:
        raise
    except Exception:
        db.rollback()
        raise

