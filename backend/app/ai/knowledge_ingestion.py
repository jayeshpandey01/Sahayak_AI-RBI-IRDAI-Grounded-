"""Document ingestion, validation, and pgvector staging pipeline.

Conforms to rag_docs.md specifications and .agents/skills/rag-implementation standards.
Handles document validation, SHA-256 deduplication hashing, chunking, and pgvector format staging.
"""

import hashlib
import re
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

REQUIRED_METADATA_FIELDS = [
    "id",
    "source_name",
    "source_url",
    "document_type",
    "financial_category",
    "provider_name",
    "jurisdiction",
    "published_at",
    "effective_from",
    "version",
    "status",
    "clause",
    "text",
]

VALID_STATUSES = {"active", "superseded", "expired"}
VALID_COLLECTIONS = {"regulatory", "provider", "assistant_policy", "user_knowledge"}


def compute_sha256(content: str) -> str:
    """Compute deterministic SHA-256 hash of normalized text."""
    normalized = content.strip().encode("utf-8")
    return hashlib.sha256(normalized).hexdigest()


def validate_document_metadata(document: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validate document dictionary against rag_docs.md metadata specifications."""
    errors = []
    for field in REQUIRED_METADATA_FIELDS:
        if field not in document or document[field] is None:
            errors.append(f"Missing required field: '{field}'")
        elif isinstance(document[field], str) and not document[field].strip():
            errors.append(f"Field '{field}' cannot be empty")

    status = document.get("status")
    if status and status not in VALID_STATUSES:
        errors.append(f"Invalid status '{status}'. Must be one of {sorted(VALID_STATUSES)}")

    collection = document.get("collection_type")
    if collection and collection not in VALID_COLLECTIONS:
        errors.append(f"Invalid collection_type '{collection}'. Must be one of {sorted(VALID_COLLECTIONS)}")

    for date_field in ["published_at", "effective_from", "review_due", "last_verified_at"]:
        val = document.get(date_field)
        if val:
            try:
                date.fromisoformat(str(val))
            except ValueError:
                errors.append(f"Field '{date_field}' has invalid ISO-8601 date: '{val}'")

    return (len(errors) == 0, errors)


def chunk_document_by_clauses(
    text: str,
    clause_delimiter: str = r"\n(?=[A-Z0-9\.\#\-\*]+\s+[A-Za-z])",
    max_chunk_chars: int = 600,
) -> List[str]:
    """AST-aware / structural clause chunking without breaking mid-sentence."""
    clauses = re.split(clause_delimiter, text)
    chunks = []
    current_chunk = []
    current_length = 0

    for clause in clauses:
        clause_stripped = clause.strip()
        if not clause_stripped:
            continue
        clause_len = len(clause_stripped)
        if current_length + clause_len <= max_chunk_chars:
            current_chunk.append(clause_stripped)
            current_length += clause_len + 1
        else:
            if current_chunk:
                chunks.append(" ".join(current_chunk))
            current_chunk = [clause_stripped]
            current_length = clause_len

    if current_chunk:
        chunks.append(" ".join(current_chunk))

    return chunks or [text.strip()]


def stage_pgvector_payload(document: Dict[str, Any], embedding: Optional[List[float]] = None) -> Dict[str, Any]:
    """Format document for Supabase pgvector storage table (rag_documents)."""
    text_content = document["text"].strip()
    content_hash = document.get("content_hash") or compute_sha256(text_content)
    
    return {
        "chunk_id": document["id"],
        "collection_type": document.get("collection_type", "regulatory"),
        "source_name": document["source_name"],
        "source_url": document["source_url"],
        "document_name": document.get("document_name", document["source_name"]),
        "document_type": document["document_type"],
        "financial_category": document["financial_category"],
        "provider_name": document["provider_name"],
        "jurisdiction": document.get("jurisdiction", "IN"),
        "published_at": document.get("published_at"),
        "effective_from": document.get("effective_from") or document.get("effective_date"),
        "review_due": document.get("review_due"),
        "last_verified_at": document.get("last_verified_at"),
        "version": document["version"],
        "content_hash": content_hash,
        "status": document.get("status", "active"),
        "clause": document.get("clause", ""),
        "content": text_content,
        "embedding": embedding,
        "metadata": {
            "aliases": document.get("aliases", []),
            "owner": document.get("owner", ""),
            "allowed_use": document.get("allowed_use", "assistant_grounding"),
            "approved": document.get("approved", True),
        },
    }

