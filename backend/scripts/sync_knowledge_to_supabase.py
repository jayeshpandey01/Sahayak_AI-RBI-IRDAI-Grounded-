#!/usr/bin/env python3
"""Sync validated financial knowledge corpus to Supabase pgvector table.

Usage:
    python3 backend/scripts/sync_knowledge_to_supabase.py [--dry-run]
"""

import argparse
import json
import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.ai.knowledge_base import KNOWLEDGE_SOURCES
from app.ai.knowledge_ingestion import stage_pgvector_payload, validate_document_metadata
from app.config import settings


def sync_knowledge(dry_run: bool = False):
    print("==================================================")
    print(" Sahayak AI Knowledge Sync -> Supabase pgvector")
    print("==================================================")
    print(f"Total knowledge sources to process: {len(KNOWLEDGE_SOURCES)}")

    valid_records = []
    for doc in KNOWLEDGE_SOURCES:
        valid, errors = validate_document_metadata(doc)
        if not valid:
            print(f"❌ Document '{doc.get('id')}' validation failed: {errors}")
            continue
        payload = stage_pgvector_payload(doc)
        valid_records.append(payload)

    print(f"✅ Successfully validated {len(valid_records)} / {len(KNOWLEDGE_SOURCES)} records.")

    collections = {}
    for r in valid_records:
        col = r["collection_type"]
        collections[col] = collections.get(col, 0) + 1

    print("\nBreakdown by Collection:")
    for col, count in collections.items():
        print(f"  • {col}: {count} records")

    if dry_run or not settings.SUPABASE_URL or not settings.SUPABASE_SECRET_KEY:
        print("\n[INFO] Dry-run or Supabase credentials not set.")
        print("Staged payloads are ready for insertion into table 'rag_documents'.")
        output_path = BACKEND_DIR / "scripts" / "staged_knowledge_export.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(valid_records, f, indent=2, ensure_ascii=False)
        print(f"Saved staged JSON export to: {output_path}")
        return

    try:
        from supabase import create_client
        supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_SECRET_KEY)
        for record in valid_records:
            # Upsert into rag_documents on chunk_id
            supabase.table("rag_documents").upsert(record, on_conflict="chunk_id").execute()
        print(f"🚀 Successfully synced {len(valid_records)} records to Supabase table 'rag_documents'!")
    except Exception as exc:
        print(f"⚠️ Error syncing to Supabase: {exc}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sync knowledge base to Supabase")
    parser.add_argument("--dry-run", action="store_true", help="Validate and export JSON only")
    args = parser.parse_args()
    sync_knowledge(dry_run=args.dry_run)

