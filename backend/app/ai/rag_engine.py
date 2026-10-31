"""Source-grounded RAG retrieval engine with metadata, freshness validation, and multi-collection support.

Conforms to rag_docs.md specifications and .agents/skills/rag-implementation standards.
Provides deterministic, multi-lingual lexical retrieval across Regulatory, Provider, and Assistant collections.
"""

import re
from datetime import date
from typing import Any, Dict, List, Optional, Set

from app.ai.knowledge_base import KNOWLEDGE_SOURCES
from app.ai.official_website_retriever import (
    OFFICIAL_WEBSITE_RECORDS,
    search_official_website_knowledge,
)
from app.models.schemas import GroundedCitation, GroundedRAGResponse

_TOKEN_RE = re.compile(r"[\w\u0900-\u097F]+", re.UNICODE)
_STOPWORDS: Set[str] = {
    "a", "an", "and", "are", "as", "at", "be", "by", "can", "do", "does", "for", "from",
    "how", "i", "if", "in", "is", "it", "me", "my", "no", "not", "of", "on", "or",
    "so", "the", "this", "to", "was", "what", "when", "where", "which", "who", "will",
    "with", "you", "your", "hai", "ho", "ka", "ke", "ki", "kya", "ko", "se", "mein",
    "mujhe", "mera", "meri", "kare", "karna", "batao", "bataiye", "aur",
    "क्या", "मेरा", "मेरी", "है", "हो", "का", "के", "की", "मुझे", "और", "से", "में", "को",
    "करें", "करना", "बताओ", "बताइए", "कि", "यह", "वह",
}


def _source_is_current_and_approved(source: dict) -> bool:
    """Verify document is approved, active, within effective validity window, and jurisdiction matches."""
    try:
        today = date.today()
        if source.get("approved") is not True:
            return False
        if source.get("allowed_use") != "assistant_grounding":
            return False
        if source.get("jurisdiction") != "IN":
            return False
        if source.get("status", "active") != "active":
            return False

        effective_str = source.get("effective_from") or source.get("effective_date")
        if not effective_str or date.fromisoformat(effective_str) > today:
            return False

        review_due_str = source.get("review_due")
        if review_due_str and date.fromisoformat(review_due_str) < today:
            return False

        return True
    except (KeyError, TypeError, ValueError):
        return False


def _tokens(text: str) -> Set[str]:
    return {
        token.casefold()
        for token in _TOKEN_RE.findall(text)
        if len(token) > 1 and token.casefold() not in _STOPWORDS
    }


def query_grounded_rag(
    query: str,
    translated_query: Optional[str] = None,
    collection_type: Optional[str] = None,
) -> Optional[GroundedRAGResponse]:
    """Score reviewed knowledge chunks and emit approved source citations with full metadata."""
    query_lower = query.casefold()
    translated_lower = translated_query.casefold() if translated_query else ""
    query_terms = _tokens(query)
    if translated_query:
        query_terms |= _tokens(translated_query)
    if not query_terms:
        return None

    combined_sources: Dict[str, Dict[str, Any]] = {}
    for s in KNOWLEDGE_SOURCES:
        combined_sources[s["id"]] = s
    for s in OFFICIAL_WEBSITE_RECORDS:
        if s["id"] not in combined_sources:
            combined_sources[s["id"]] = s

    ranked = []
    for source in combined_sources.values():
        if collection_type and source.get("collection_type") != collection_type:
            continue
        if not _source_is_current_and_approved(source):
            continue

        text_terms = _tokens(source["text"])
        aliases = source.get("aliases", [])
        alias_terms = set().union(*(_tokens(alias) for alias in aliases)) if aliases else set()
        matched = query_terms & (text_terms | alias_terms)
        if not matched:
            continue

        # Exact subphrase match against full query strings
        exact_alias_found = any(
            alias.casefold() in query_lower or (translated_lower and alias.casefold() in translated_lower)
            for alias in aliases
            if len(alias) >= 3
        )

        term_overlap = len(matched) / max(1, len(query_terms))
        alias_bonus = 0.35 if exact_alias_found else 0.0

        # Term frequency bonus if matched terms appear prominently in clause title
        clause_terms = _tokens(source.get("clause", ""))
        clause_bonus = 0.15 if (query_terms & clause_terms) else 0.0

        score = term_overlap + alias_bonus + clause_bonus
        ranked.append((score, source))

    ranked.sort(key=lambda item: item[0], reverse=True)
    selected = [(score, source) for score, source in ranked[:3] if score >= 0.12]
    if not selected:
        # Fallback to targeted official website search
        official_matches = search_official_website_knowledge(query)
        if not official_matches and translated_query:
            official_matches = search_official_website_knowledge(translated_query)
        if official_matches:
            selected = [(0.5, rec) for rec in official_matches[:3]]
    if not selected:
        return None

    citations = [
        GroundedCitation(
            citation_id=source["id"],
            document_name=source["document_name"],
            version=source["version"],
            clause=source["clause"],
            snippet=source["text"],
            source_name=source.get("source_name"),
            source_url=source.get("source_url"),
            document_type=source.get("document_type"),
            financial_category=source.get("financial_category"),
            provider_name=source.get("provider_name"),
            effective_from=source.get("effective_from") or source.get("effective_date"),
            status=source.get("status", "active"),
            collection_type=source.get("collection_type"),
        )
        for _, source in selected
    ]

    has_regulatory = any(c.collection_type == "regulatory" for c in citations)
    disclaimer = (
        "Retrieved from official regulatory directions and reviewed Sahayak policies. "
        "This is not individual legal or underwriting advice."
        if has_regulatory
        else "Retrieved from reviewed Sahayak product policy. This is not lender or legal advice."
    )

    avg_score = min(1.0, sum(item[0] for item in selected) / len(selected))
    return GroundedRAGResponse(
        answer=" ".join(citation.snippet for citation in citations),
        citations=citations,
        source_documents=sorted({f"{item.document_name} ({item.version})" for item in citations}),
        confidence=round(avg_score, 3),
        disclaimer=disclaimer,
    )


def get_knowledge_sources(
    collection_type: Optional[str] = None,
    status: str = "active",
) -> List[Dict[str, Any]]:
    """Inspect and filter the in-memory reviewed knowledge sources."""
    results = []
    for source in KNOWLEDGE_SOURCES:
        if collection_type and source.get("collection_type") != collection_type:
            continue
        if status and source.get("status") != status:
            continue
        results.append(source)
    return results


def inspect_source_freshness() -> Dict[str, Any]:
    """Audit corpus freshness, active count, and upcoming review dates."""
    today = date.today()
    summary = {
        "total_sources": len(KNOWLEDGE_SOURCES),
        "active_sources": 0,
        "superseded_sources": 0,
        "expired_sources": 0,
        "due_for_review_soon": 0,
        "collections": {},
    }

    for source in KNOWLEDGE_SOURCES:
        col = source.get("collection_type", "unassigned")
        summary["collections"][col] = summary["collections"].get(col, 0) + 1

        status = source.get("status", "active")
        if status == "superseded":
            summary["superseded_sources"] += 1
            continue
        if status == "expired":
            summary["expired_sources"] += 1
            continue

        try:
            review_due = date.fromisoformat(source["review_due"])
            if review_due < today:
                summary["expired_sources"] += 1
            else:
                summary["active_sources"] += 1
                if (review_due - today).days <= 60:
                    summary["due_for_review_soon"] += 1
        except Exception:
            summary["active_sources"] += 1

    return summary
