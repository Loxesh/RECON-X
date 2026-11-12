# RECON X – MongoDB Collection Schema Reference

**Purpose:** Document the 15 MongoDB collections, their model fields, tenant ownership and representative sample documents.

**Database:** `RECON_X_DEV`
**Schema version:** 1
**Source:** RECON X approved Stage 1 architecture and implemented Pydantic document models.

---

## 1. Shared document fields

All collections except `organizations` inherit tenant ownership through `TenantDocument`.

| Field | Type | Description |
|---|---|---|
| `_id` | ObjectId | MongoDB document identifier |
| `created_at` | datetime | UTC creation timestamp |
| `updated_at` | datetime | UTC last-update timestamp |
| `schema_version` | integer | Document schema version; default 1 |
| `org_id` | string | Organisation identifier; required for tenant-owned collections |

`organizations` inherits `DocumentBase` and therefore does not contain `org_id`. Its `_id` identifies the organisation.

**Financial data:** Monetary values use Python `Decimal` and MongoDB BSON `Decimal128`. Never use floating-point values for financial amounts.

The examples below use MongoDB Extended JSON notation for ObjectIds and Decimal128 values. Timestamps are illustrative.

---

## 2. Collection: organizations

**Model:** `OrganizationDocument`
**Tenant-owned:** No
**Purpose:** Stores organisation details, matching rules, risk policy and budget settings.

| Field | Type |
|---|---|
| name | string |
| slug | string |
| status | string |
| settings.matching_rules | object |
| settings.risk_policy | object |
| settings.retention_days | integer |
| settings.budget | object |
| settings.maker_checker | boolean |
| settings.base_currency | string |

**Sample document**

```json
{
  "_id": {"$oid": "672000000000000000000001"},
  "name": "Acme Finance",
  "slug": "acme-finance",
  "status": "ACTIVE",
  "settings": {
    "matching_rules": {
      "date_tolerance_days": 3,
      "amount_tolerance": {"$numberDecimal": "0.00"},
      "reference_matching": true
    },
    "risk_policy": {
      "high_risk_threshold": 70,
      "medium_risk_threshold": 40
    },
    "retention_days": 365,
    "budget": {
      "monthly_usd": {"$numberDecimal": "100.00"},
      "per_job_usd": {"$numberDecimal": "10.00"},
      "alert_pct": 80
    },
    "maker_checker": true,
    "base_currency": "INR"
  },
  "created_at": "2026-11-12T10:00:00Z",
  "updated_at": "2026-11-12T10:00:00Z",
  "schema_version": 1
}
```

---

## 3. Collection: users

**Model:** `UserDocument`
**Tenant-owned:** Yes
**Purpose:** Stores organisation users and authentication-related information.

| Field | Type |
|---|---|
| org_id | string |
| email | EmailStr |
| password_hash | string or null |
| roles | array of strings |
| status | string |
| external_subject | string or null |
| last_login | datetime or null |

**Sample document**

```json
{
  "_id": {"$oid": "672000000000000000000002"},
  "org_id": "672000000000000000000001",
  "email": "reviewer@example.com",
  "password_hash": null,
  "roles": ["REVIEWER"],
  "status": "ACTIVE",
  "external_subject": null,
  "last_login": null,
  "created_at": "2026-11-12T10:00:00Z",
  "updated_at": "2026-11-12T10:00:00Z",
  "schema_version": 1
}
```

---

## 4. Collection: uploaded_files

**Model:** `UploadedFileDocument`
**Tenant-owned:** Yes
**Purpose:** Stores uploaded financial file metadata and private storage references.

| Field | Type |
|---|---|
| org_id | string |
| source_type | SourceType |
| original_filename | string |
| content_type | string |
| size_bytes | integer |
| sha256 | string |
| storage_bucket | string |
| storage_key | string |
| scan_status | string |
| uploaded_by | string |
| period | object or null |

**Sample document**

```json
{
  "_id": {"$oid": "672000000000000000000003"},
  "org_id": "672000000000000000000001",
  "source_type": "BANK",
  "original_filename": "bank_statement.csv",
  "content_type": "text/csv",
  "size_bytes": 20480,
  "sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "storage_bucket": "reconx-private",
  "storage_key": "organisations/acme/uploads/file-001.csv",
  "scan_status": "PENDING",
  "uploaded_by": "USER001",
  "period": {
    "start_date": "2026-11-01",
    "end_date": "2026-11-30"
  },
  "created_at": "2026-11-12T10:00:00Z",
  "updated_at": "2026-11-12T10:00:00Z",
  "schema_version": 1
}
```

---

## 5. Collection: ingestion_jobs

**Model:** `IngestionJobDocument`
**Tenant-owned:** Yes
**Purpose:** Tracks file ingestion, row counts, mapping and validation errors.

| Field | Type |
|---|---|
| org_id | string |
| file_id | string |
| status | string |
| counts | object: total, valid, invalid |
| mapping | object |
| errors_summary | array of error objects |
| started_at | datetime or null |
| finished_at | datetime or null |

**Sample document**

```json
{
  "_id": {"$oid": "672000000000000000000004"},
  "org_id": "672000000000000000000001",
  "file_id": "FILE001",
  "status": "COMPLETED",
  "counts": {
    "total": 100,
    "valid": 98,
    "invalid": 2
  },
  "mapping": {
    "date": "Transaction Date",
    "amount": "Amount",
    "reference": "Reference"
  },
  "errors_summary": [
    {
      "row_number": 12,
      "error_code": "INVALID_AMOUNT",
      "message": "Amount is not a valid decimal value."
    }
  ],
  "started_at": "2026-11-12T10:00:00Z",
  "finished_at": "2026-11-12T10:01:00Z",
  "created_at": "2026-11-12T10:00:00Z",
  "updated_at": "2026-11-12T10:01:00Z",
  "schema_version": 1
}
```

---

## 6. Collection: transactions

**Model:** `TransactionDocument`
**Tenant-owned:** Yes
**Purpose:** Stores normalised financial transactions extracted from uploaded files.

| Field | Type |
|---|---|
| org_id | string |
| job_id | string |
| file_id | string |
| source_type | SourceType |
| source_row | integer |
| txn_ref | string or null |
| reference_norm | string or null |
| txn_date | datetime |
| amount | Decimal128 |
| currency | string |
| direction | TransactionDirection |
| description_raw | string or null |
| description_norm | string or null |
| fingerprint | string |
| validity | TransactionValidity |
| validation_errors | array |
| raw_row | object |
| match_status | TransactionMatchStatus |
| flags | array of strings |

**Sample document**

```json
{
  "_id": {"$oid": "672000000000000000000005"},
  "org_id": "672000000000000000000001",
  "job_id": "JOB001",
  "file_id": "FILE001",
  "source_type": "BANK",
  "source_row": 2,
  "txn_ref": "BANK12345",
  "reference_norm": "BANK12345",
  "txn_date": "2026-11-12T09:30:00Z",
  "amount": {"$numberDecimal": "7500.50"},
  "currency": "INR",
  "direction": "CREDIT",
  "description_raw": "Customer payment",
  "description_norm": "CUSTOMER PAYMENT",
  "fingerprint": "txn-fingerprint-001",
  "validity": "VALID",
  "validation_errors": [],
  "raw_row": {
    "Reference": "BANK12345",
    "Amount": "7500.50"
  },
  "match_status": "UNMATCHED",
  "flags": [],
  "created_at": "2026-11-12T10:00:00Z",
  "updated_at": "2026-11-12T10:00:00Z",
  "schema_version": 1
}
```

---

## 7. Collection: reconciliation_jobs

**Model:** `ReconciliationJobDocument`
**Tenant-owned:** Yes
**Purpose:** Stores reconciliation job configuration, selected files, rules and results statistics.

| Field | Type |
|---|---|
| org_id | string |
| name | string |
| period | object: start_date, end_date |
| status | string |
| idempotency_key | string |
| file_ids | object: bank, ledger, gateway |
| rules_snapshot | object |
| stats | object |
| workflow_run_id | string or null |
| created_by | string |
| completed_at | datetime or null |

**Sample document**

```json
{
  "_id": {"$oid": "672000000000000000000006"},
  "org_id": "672000000000000000000001",
  "name": "November Bank Reconciliation",
  "period": {
    "start_date": "2026-11-01T00:00:00Z",
    "end_date": "2026-11-30T23:59:59Z"
  },
  "status": "PENDING",
  "idempotency_key": "ACME-NOV-2026-001",
  "file_ids": {
    "bank": "FILE001",
    "ledger": "FILE002",
    "gateway": null
  },
  "rules_snapshot": {},
  "stats": {},
  "workflow_run_id": null,
  "created_by": "USER001",
  "completed_at": null,
  "created_at": "2026-11-12T10:00:00Z",
  "updated_at": "2026-11-12T10:00:00Z",
  "schema_version": 1
}
```

---

## 8. Collection: match_results

**Model:** `MatchResultDocument`
**Tenant-owned:** Yes
**Purpose:** Stores deterministic transaction matching results and supporting evidence.

| Field | Type |
|---|---|
| org_id | string |
| job_id | string |
| relationship | object: side_a, side_b |
| match_type | MatchType |
| status | string |
| origin | MatchOrigin |
| rule_id | string or null |
| side_a_ids | array of strings |
| side_b_ids | array of strings |
| amount_a | Decimal128 |
| amount_b | Decimal128 |
| difference | Decimal128 |
| score | integer (0–100) |
| confidence | ConfidenceLabel |
| evidence | object |
| confirmed_by | string or null |

**Sample document**

```json
{
  "_id": {"$oid": "672000000000000000000007"},
  "org_id": "672000000000000000000001",
  "job_id": "JOB001",
  "relationship": {
    "side_a": "BANK",
    "side_b": "LEDGER"
  },
  "match_type": "EXACT",
  "status": "PROPOSED",
  "origin": "DETERMINISTIC_DECISION",
  "rule_id": "RULE001",
  "side_a_ids": ["TXN001"],
  "side_b_ids": ["TXN002"],
  "amount_a": {"$numberDecimal": "7500.50"},
  "amount_b": {"$numberDecimal": "7500.50"},
  "difference": {"$numberDecimal": "0.00"},
  "score": 100,
  "confidence": "HIGH",
  "evidence": {
    "reference_match": true,
    "amount_match": true
  },
  "confirmed_by": null,
  "created_at": "2026-11-12T10:00:00Z",
  "updated_at": "2026-11-12T10:00:00Z",
  "schema_version": 1
}
```

---

## 9. Collection: exceptions

**Model:** `ExceptionDocument`
**Tenant-owned:** Yes
**Purpose:** Tracks unmatched transactions, discrepancies and items requiring human review.

| Field | Type |
|---|---|
| org_id | string |
| job_id | string |
| type | string |
| severity | string |
| summary | string |
| primary_txn_ids | array of strings |
| related_match_ids | array of strings |
| status | string |
| review_required | boolean |
| risk | object |
| evidence | object |
| investigation_id | string or null |
| status_history | array of status-change objects |
| assigned_to | string or null |

**Sample document**

```json
{
  "_id": {"$oid": "672000000000000000000008"},
  "org_id": "672000000000000000000001",
  "job_id": "JOB001",
  "type": "AMOUNT_MISMATCH",
  "severity": "HIGH",
  "summary": "Bank and ledger transaction amounts differ.",
  "primary_txn_ids": ["TXN001", "TXN002"],
  "related_match_ids": ["MATCH001"],
  "status": "OPEN",
  "review_required": true,
  "risk": {
    "score": 85,
    "level": "HIGH"
  },
  "evidence": {
    "bank_amount": "7500.50",
    "ledger_amount": "7000.50"
  },
  "investigation_id": null,
  "status_history": [],
  "assigned_to": null,
  "created_at": "2026-11-12T10:00:00Z",
  "updated_at": "2026-11-12T10:00:00Z",
  "schema_version": 1
}
```

---

## 10. Collection: investigations

**Model:** `InvestigationDocument`
**Tenant-owned:** Yes
**Purpose:** Stores investigation findings, cited records, explanations and recommended actions.

| Field | Type |
|---|---|
| org_id | string |
| exception_id | string |
| version | integer |
| findings | object |
| cited_record_ids | array of strings |
| explanation_text | string |
| recommended_actions | array of strings |
| confidence_label | ConfidenceLabel |
| generated_by | object: agent, llm_usage_id |
| validation | object: status, issues |

**Sample document**

```json
{
  "_id": {"$oid": "672000000000000000000009"},
  "org_id": "672000000000000000000001",
  "exception_id": "EXC001",
  "version": 1,
  "findings": {
    "bank_amount": "7500.50",
    "ledger_amount": "7000.50",
    "difference": "500.00"
  },
  "cited_record_ids": ["TXN001", "TXN002"],
  "explanation_text": "The bank and ledger amounts differ by INR 500.00.",
  "recommended_actions": [
    "Review the source transactions.",
    "Verify the ledger entry."
  ],
  "confidence_label": "HIGH",
  "generated_by": {
    "agent": "investigation_agent",
    "llm_usage_id": null
  },
  "validation": {
    "status": "PENDING",
    "issues": []
  },
  "created_at": "2026-11-12T10:00:00Z",
  "updated_at": "2026-11-12T10:00:00Z",
  "schema_version": 1
}
```

---

## 11. Collection: agent_executions

**Model:** `AgentExecutionDocument`
**Tenant-owned:** Yes
**Purpose:** Records individual agent execution attempts and redacted outputs.

| Field | Type |
|---|---|
| org_id | string |
| job_id | string |
| workflow_run_id | string |
| agent_name | string |
| step | string |
| attempt | integer |
| status | string |
| input_hash | string |
| output_summary_redacted | string or null |
| duration_ms | integer or null |
| error_code | string or null |

**Sample document**

```json
{
  "_id": {"$oid": "672000000000000000000010"},
  "org_id": "672000000000000000000001",
  "job_id": "JOB001",
  "workflow_run_id": "WF001",
  "agent_name": "reconciliation_agent",
  "step": "MATCH_TRANSACTIONS",
  "attempt": 1,
  "status": "COMPLETED",
  "input_hash": "input-hash-001",
  "output_summary_redacted": "Processed 100 transactions.",
  "duration_ms": 1250,
  "error_code": null,
  "created_at": "2026-11-12T10:00:00Z",
  "updated_at": "2026-11-12T10:00:00Z",
  "schema_version": 1
}
```

---

## 12. Collection: workflow_runs

**Model:** `WorkflowRunDocument`
**Tenant-owned:** Yes
**Purpose:** Stores orchestration state, execution plan, step checkpoints and errors.

| Field | Type |
|---|---|
| org_id | string |
| job_id | string |
| state | string |
| plan | array of strings |
| steps | array of step objects |
| correlation_id | string |
| error | object or null |

**Sample document**

```json
{
  "_id": {"$oid": "672000000000000000000011"},
  "org_id": "672000000000000000000001",
  "job_id": "JOB001",
  "state": "RUNNING",
  "plan": ["INGEST", "NORMALIZE", "MATCH", "REVIEW", "REPORT"],
  "steps": [
    {
      "name": "INGEST",
      "status": "COMPLETED",
      "attempts": 1,
      "checkpoint": {
        "processed_files": 2
      }
    },
    {
      "name": "MATCH",
      "status": "PENDING",
      "attempts": 0,
      "checkpoint": {}
    }
  ],
  "correlation_id": "CORR-JOB001",
  "error": null,
  "created_at": "2026-11-12T10:00:00Z",
  "updated_at": "2026-11-12T10:00:00Z",
  "schema_version": 1
}
```

---

## 13. Collection: approvals

**Model:** `ApprovalDocument`
**Tenant-owned:** Yes
**Purpose:** Records human decisions and maker-checker approval evidence.

| Field | Type |
|---|---|
| org_id | string |
| job_id | string |
| exception_id | string |
| decision | ApprovalDecision |
| reviewer_id | string |
| reviewer_role | string |
| comment | string or null |
| before | object |
| after | object |
| decided_at | datetime |
| policy_snapshot | object |

**Sample document**

```json
{
  "_id": {"$oid": "672000000000000000000012"},
  "org_id": "672000000000000000000001",
  "job_id": "JOB001",
  "exception_id": "EXC001",
  "decision": "approve",
  "reviewer_id": "USER002",
  "reviewer_role": "APPROVER",
  "comment": "Reviewed the supporting evidence.",
  "before": {
    "status": "OPEN"
  },
  "after": {
    "status": "APPROVED"
  },
  "decided_at": "2026-11-12T11:00:00Z",
  "policy_snapshot": {
    "maker_checker": true
  },
  "created_at": "2026-11-12T11:00:00Z",
  "updated_at": "2026-11-12T11:00:00Z",
  "schema_version": 1
}
```

---

## 14. Collection: audit_events

**Model:** `AuditEventDocument`
**Tenant-owned:** Yes
**Purpose:** Stores append-only audit evidence with hash-chain fields.

| Field | Type |
|---|---|
| org_id | string |
| seq | integer |
| ts | datetime |
| event_type | string |
| actor | object: actor_id, actor_type, name |
| resource | object: resource_type, resource_id |
| action | string |
| outcome | AuditOutcome |
| details | object |
| correlation_id | string |
| prev_hash | string or null |
| hash | string |

**Sample document**

```json
{
  "_id": {"$oid": "672000000000000000000013"},
  "org_id": "672000000000000000000001",
  "seq": 1,
  "ts": "2026-11-12T11:00:00Z",
  "event_type": "EXCEPTION_REVIEWED",
  "actor": {
    "actor_id": "USER002",
    "actor_type": "USER",
    "name": "Finance Reviewer"
  },
  "resource": {
    "resource_type": "EXCEPTION",
    "resource_id": "EXC001"
  },
  "action": "REVIEW",
  "outcome": "SUCCESS",
  "details": {
    "decision": "APPROVED"
  },
  "correlation_id": "CORR-JOB001",
  "prev_hash": null,
  "hash": "audit-hash-001",
  "created_at": "2026-11-12T11:00:00Z",
  "updated_at": "2026-11-12T11:00:00Z",
  "schema_version": 1
}
```

**Integrity rule:** Audit events are append-only. Application repositories must not expose update or delete operations for this collection.

---

## 15. Collection: reports

**Model:** `ReportDocument`
**Tenant-owned:** Yes
**Purpose:** Stores generated reconciliation report metadata, private storage references and human sign-off.

| Field | Type |
|---|---|
| org_id | string |
| job_id | string |
| format | string |
| storage_key | string |
| sha256 | string |
| figures_snapshot | object |
| narrative | string |
| generated_by | string |
| signoff | object: status, signed_by, signed_at, comment |

**Sample document**

```json
{
  "_id": {"$oid": "672000000000000000000014"},
  "org_id": "672000000000000000000001",
  "job_id": "JOB001",
  "format": "PDF",
  "storage_key": "organisations/acme/reports/report-001.pdf",
  "sha256": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
  "figures_snapshot": {
    "total_transactions": 100,
    "matched_transactions": 90,
    "unmatched_transactions": 10
  },
  "narrative": "Monthly reconciliation report.",
  "generated_by": "report_agent",
  "signoff": {
    "status": "PENDING",
    "signed_by": null,
    "signed_at": null,
    "comment": null
  },
  "created_at": "2026-11-12T11:00:00Z",
  "updated_at": "2026-11-12T11:00:00Z",
  "schema_version": 1
}
```

---

## 16. Collection: llm_usage

**Model:** `LLMUsageDocument`
**Tenant-owned:** Yes
**Purpose:** Records model usage, token counts, estimated cost, latency and correlation details.

| Field | Type |
|---|---|
| org_id | string |
| job_id | string |
| agent_name | string |
| task | string |
| provider | string |
| model | string |
| tier | string |
| input_tokens | integer |
| output_tokens | integer |
| cached | boolean |
| est_cost | Decimal128 |
| currency | string |
| price_version | string |
| latency_ms | integer |
| status | string |
| correlation_id | string |
| ts | datetime |

**Sample document**

```json
{
  "_id": {"$oid": "672000000000000000000015"},
  "org_id": "672000000000000000000001",
  "job_id": "JOB001",
  "agent_name": "investigation_agent",
  "task": "GENERATE_EXPLANATION",
  "provider": "ollama",
  "model": "llama3.2:3b",
  "tier": "LOCAL",
  "input_tokens": 1200,
  "output_tokens": 300,
  "cached": false,
  "est_cost": {"$numberDecimal": "0.00"},
  "currency": "USD",
  "price_version": "local-v1",
  "latency_ms": 1800,
  "status": "SUCCESS",
  "correlation_id": "CORR-JOB001",
  "ts": "2026-11-12T11:00:00Z",
  "created_at": "2026-11-12T11:00:00Z",
  "updated_at": "2026-11-12T11:00:00Z",
  "schema_version": 1
}
```

---

## 17. Important implementation and security rules

1. Every tenant-owned document must contain `org_id`.
2. Tenant repositories must derive `org_id` from trusted authenticated application context, never directly from an untrusted client request.
3. Every tenant-owned read and write must include tenant scope.
4. Organisation records are the exception: their `_id` identifies the organisation.
5. Monetary values must use `Decimal` in Python and `Decimal128` in MongoDB.
6. API monetary values must be represented as decimal strings, not floating-point JSON numbers.
7. Uploaded originals must remain immutable and use private storage keys.
8. File metadata must retain SHA-256, MIME type, size and scan status.
9. Audit events must be append-only and preserve hash-chain evidence.
10. LLM-generated content must not independently match transactions, calculate financial amounts, execute arbitrary tools or approve financial actions.
11. Investigation explanations must retain cited record IDs and validation information.
12. LLM estimated cost is an application estimate, not actual provider billing.

---

## 18. Collection inventory

| No. | Collection | Model | Tenant-owned |
|---:|---|---|---|
| 1 | organizations | OrganizationDocument | No |
| 2 | users | UserDocument | Yes |
| 3 | uploaded_files | UploadedFileDocument | Yes |
| 4 | ingestion_jobs | IngestionJobDocument | Yes |
| 5 | transactions | TransactionDocument | Yes |
| 6 | reconciliation_jobs | ReconciliationJobDocument | Yes |
| 7 | match_results | MatchResultDocument | Yes |
| 8 | exceptions | ExceptionDocument | Yes |
| 9 | investigations | InvestigationDocument | Yes |
| 10 | agent_executions | AgentExecutionDocument | Yes |
| 11 | workflow_runs | WorkflowRunDocument | Yes |
| 12 | approvals | ApprovalDocument | Yes |
| 13 | audit_events | AuditEventDocument | Yes |
| 14 | reports | ReportDocument | Yes |
| 15 | llm_usage | LLMUsageDocument | Yes |

**Document status:** Initial schema reference prepared from the implemented document models. Sample documents are illustrative and are not production seed data. Index definitions and operational repository behaviour are documented separately.
