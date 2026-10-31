import logging
from typing import Optional
from supabase import create_client, Client
from app.config import settings

logger = logging.getLogger("sahayak.supabase")

_supabase_client: Optional[Client] = None

def get_supabase_client() -> Optional[Client]:
    """
    Returns a configured singleton Supabase client instance.
    Prefers SUPABASE_SECRET_KEY for server operations, or falls back to PUBLISHABLE_KEY.
    """
    global _supabase_client
    if _supabase_client is not None:
        return _supabase_client

    url = settings.SUPABASE_URL
    key = settings.SUPABASE_SECRET_KEY or settings.SUPABASE_PUBLISHABLE_KEY

    if not url or not key:
        logger.warning("Supabase URL or Key is not configured in backend environment.")
        return None

    try:
        _supabase_client = create_client(url, key)
        logger.info(f"Supabase client initialized for project: {url}")
        return _supabase_client
    except Exception as exc:
        logger.error(f"Failed to initialize Supabase client: {str(exc)}")
        return None

def sync_payment_order_to_supabase(order_dict: dict) -> bool:
    """
    Safely mirrors or upserts payment order records into Supabase cloud datastore.
    Operates fail-safe: failures are logged without blocking local operations.
    """
    client = get_supabase_client()
    if not client:
        return False
    try:
        # Convert non-serializable objects (datetime, Decimal)
        payload = {}
        for k, v in order_dict.items():
            if hasattr(v, "isoformat"):
                payload[k] = v.isoformat()
            elif hasattr(v, "__float__"):
                payload[k] = float(v)
            else:
                payload[k] = v
        client.table("payment_orders").upsert(payload).execute()
        logger.info(f"Mirrored payment order {order_dict.get('id')} to Supabase.")
        return True
    except Exception as exc:
        logger.warning(f"Supabase payment order sync skipped/failed: {exc}")
        return False

def sync_audit_log_to_supabase(audit_dict: dict) -> bool:
    """
    Safely appends payment audit log entries into Supabase cloud datastore.
    """
    client = get_supabase_client()
    if not client:
        return False
    try:
        payload = {}
        for k, v in audit_dict.items():
            if hasattr(v, "isoformat"):
                payload[k] = v.isoformat()
            elif hasattr(v, "__float__"):
                payload[k] = float(v)
            else:
                payload[k] = v
        client.table("payment_audit_logs").insert(payload).execute()
        logger.info(f"Mirrored audit log {audit_dict.get('id')} to Supabase.")
        return True
    except Exception as exc:
        logger.warning(f"Supabase audit log sync skipped/failed: {exc}")
        return False


