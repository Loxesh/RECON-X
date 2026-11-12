
"""Create the approved MongoDB indexes for RECON X."""

import sys
from pathlib import Path

# Ensure the backend directory is importable when this file is
# executed using: python scripts/create_indexes.py
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import settings
from app.core.database import close_mongo_client, create_mongo_client


# Each entry contains:
# (index keys, index options)
INDEX_DEFINITIONS = {
    "organizations": [
        (
            [("slug", 1)],
            {"name": "uq_organizations_slug", "unique": True},
        ),
    ],
    "users": [
        (
            [("org_id", 1), ("email", 1)],
            {"name": "uq_users_org_email", "unique": True},
        ),
        (
            [("org_id", 1), ("external_subject", 1)],
            {
                "name": "uq_users_org_external_subject",
                "unique": True,
                "partialFilterExpression": {
                    "external_subject": {"$type": "string"}
                },
            },
        ),
    ],
    "uploaded_files": [
        (
            [("org_id", 1), ("sha256", 1), ("source_type", 1)],
            {"name": "ix_uploaded_files_org_hash_source"},
        ),
        (
            [("org_id", 1), ("created_at", -1)],
            {"name": "ix_uploaded_files_org_created"},
        ),
    ],
    "ingestion_jobs": [
        (
            [("org_id", 1), ("status", 1)],
            {"name": "ix_ingestion_jobs_org_status"},
        ),
        (
            [("org_id", 1), ("file_id", 1)],
            {"name": "ix_ingestion_jobs_org_file"},
        ),
    ],
    "transactions": [
        (
            [
                ("org_id", 1),
                ("job_id", 1),
                ("source_type", 1),
                ("validity", 1),
            ],
            {"name": "ix_transactions_org_job_source_validity"},
        ),
        (
            [("org_id", 1), ("job_id", 1), ("fingerprint", 1)],
            {"name": "ix_transactions_org_job_fingerprint"},
        ),
        (
            [("org_id", 1), ("job_id", 1), ("txn_ref", 1)],
            {"name": "ix_transactions_org_job_txn_ref"},
        ),
    ],
    "reconciliation_jobs": [
        (
            [("org_id", 1), ("idempotency_key", 1)],
            {
                "name": "uq_reconciliation_jobs_org_idempotency",
                "unique": True,
            },
        ),
        (
            [("org_id", 1), ("status", 1), ("created_at", -1)],
            {"name": "ix_reconciliation_jobs_org_status_created"},
        ),
    ],
    "match_results": [
        (
            [("org_id", 1), ("job_id", 1), ("status", 1)],
            {"name": "ix_match_results_org_job_status"},
        ),
        (
            [("org_id", 1), ("side_a_ids", 1)],
            {"name": "ix_match_results_org_side_a"},
        ),
        (
            [("org_id", 1), ("side_b_ids", 1)],
            {"name": "ix_match_results_org_side_b"},
        ),
    ],
    "exceptions": [
        (
            [("org_id", 1), ("job_id", 1), ("status", 1)],
            {"name": "ix_exceptions_org_job_status"},
        ),
        (
            [("org_id", 1), ("type", 1), ("created_at", -1)],
            {"name": "ix_exceptions_org_type_created"},
        ),
        (
            [("org_id", 1), ("summary", "text")],
            {"name": "tx_exceptions_org_summary"},
        ),
    ],
    "investigations": [
        (
            [("org_id", 1), ("exception_id", 1), ("version", 1)],
            {"name": "ix_investigations_org_exception_version"},
        ),
    ],
    "agent_executions": [
        (
            [("org_id", 1), ("job_id", 1), ("agent_name", 1)],
            {"name": "ix_agent_executions_org_job_agent"},
        ),
    ],
    "workflow_runs": [
        (
            [("org_id", 1), ("job_id", 1)],
            {"name": "uq_workflow_runs_org_job", "unique": True},
        ),
    ],
    "approvals": [
        (
            [("org_id", 1), ("exception_id", 1), ("decided_at", -1)],
            {"name": "ix_approvals_org_exception_decided"},
        ),
    ],
    "audit_events": [
        (
            [("org_id", 1), ("seq", 1)],
            {"name": "uq_audit_events_org_seq", "unique": True},
        ),
        (
            [("org_id", 1), ("event_type", 1), ("ts", -1)],
            {"name": "ix_audit_events_org_type_ts"},
        ),
    ],
    "reports": [
        (
            [("org_id", 1), ("job_id", 1), ("created_at", -1)],
            {"name": "ix_reports_org_job_created"},
        ),
    ],
    "llm_usage": [
        (
            [("org_id", 1), ("job_id", 1)],
            {"name": "ix_llm_usage_org_job"},
        ),
        (
            [("org_id", 1), ("ts", -1)],
            {"name": "ix_llm_usage_org_ts"},
        ),
    ],
}


def create_indexes(database) -> int:
    """Create all declared indexes and return the number processed."""
    created_count = 0

    for collection_name, definitions in INDEX_DEFINITIONS.items():
        collection = database[collection_name]

        for keys, options in definitions:
            index_name = collection.create_index(keys, **options)
            print(f"  {collection_name}: {index_name}")
            created_count += 1

    return created_count


def main() -> None:
    """Connect to MongoDB, create indexes, and close the client."""
    client = create_mongo_client()

    try:
        database = client[settings.mongodb_database]

        print(f"Creating RECON X indexes in: {settings.mongodb_database}")
        print("-" * 60)

        count = create_indexes(database)

        print("-" * 60)
        print(f"Index creation completed. Indexes processed: {count}")

    finally:
        close_mongo_client(client)


if __name__ == "__main__":
    main()
