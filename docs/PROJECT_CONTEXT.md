# RECON X – Project Context

**Last Updated:** 24 November 2026

## 1. Project Overview

RECON X is an intelligent, multi-agent financial reconciliation and discrepancy investigation system.

It compares:
- Bank statements
- Company accounting ledger exports
- Payment gateway settlement reports

The system ingests financial files, normalizes transactions, performs deterministic matching, identifies discrepancies, investigates exceptions, provides evidence-backed explanations and generates reconciliation reports.

Final financial decisions remain under human control through the approved Human in the Loop architecture.

## 2. Technology Stack

### Backend
- Python 3.12
- FastAPI
- Pydantic
- PyMongo
- MongoDB Atlas
- Celery and Redis
- SILO S3-compatible object storage
- OpenTelemetry observability

### Frontend
- React
- Vite
- JavaScript and JSX
- Tailwind CSS

### Reconciliation
- Python Decimal for financial calculations
- RapidFuzz for fuzzy reference similarity
- Immutable, versioned matching rulesets
- SHA-256 fingerprints for ruleset and transaction integrity checks

## 3. Architecture Principles

1. Deterministic financial calculations and matching.
2. Tenant isolation and trusted organization context.
3. Authentication and role-based access control.
4. Evidence-backed reconciliation outcomes.
5. Immutable ruleset snapshots and fingerprints.
6. Centralized validation and error handling.
7. Auditability and observability.
8. Human approval for decisions requiring review.
9. Secure handling of financial data and credentials.
10. Modular backend and frontend architecture.

## 4. Reconciliation Architecture

The reconciliation engine uses configurable matching passes:

1. Duplicate detection
2. Exact matching
3. Reference matching
4. Tolerance matching
5. Fuzzy matching
6. Aggregate matching
7. Residual handling

Supported transaction sources:
- BANK
- LEDGER
- GATEWAY

Supported cross-source pairs:
- BANK–LEDGER
- GATEWAY–LEDGER

Matching outcomes include:
- CONFIRMED_AUTO
- SUGGESTED
- AMBIGUOUS
- UNMATCHED

Fuzzy and aggregate matching produce suggestions, not automatic financial confirmations.

Financial comparisons use Decimal values. Currency equality and configured date windows are enforced.

## 5. AI and Agent Governance

The approved architecture includes specialised agents coordinated through a separate state-machine orchestrator.

Agents communicate through the orchestrator rather than directly with one another.

LLMs may assist with explanations, investigations, communications and narrative summaries.

LLMs must not:
- Perform authoritative financial calculations.
- Make deterministic matching decisions.
- Execute arbitrary tools.
- Lower rule-based risk.
- Approve financial decisions.

Validation, permissions, evidence checks and human review remain mandatory safeguards.

## 6. Security Requirements

- Derive tenant identity from authenticated user context.
- Enforce role-based permissions.
- Validate all external inputs.
- Protect secrets and environment files.
- Keep uploaded financial files private.
- Preserve audit evidence.
- Validate agent inputs and outputs.
- Enforce allowed tools and state transitions.
- Never allow an LLM to bypass deterministic controls.

## 7. Repository Structure

- `backend/` – FastAPI application and backend modules.
- `frontend/` – React application.
- `docker/` – Local service configuration.
- `scripts/` – Utility scripts.
- `sample_data/` – Development sample data.
- `docs/` – Architecture, operations and project registers.
- `.github/workflows/` – CI workflow configuration.

## 8. Implementation Progress

Total workbook chapters: 52.

Officially completed: 24/52.

- Chapters 1–24: Completed.
- Chapter 10: Deferred.
- Chapter 25: Implementation and focused verification passed; documentation/Git closure pending.
- Chapter 26: Implementation and focused verification passed; documentation/Git closure pending.
- Remaining chapters: Pending implementation.

Chapter 25 focused tests: 19 passed.

Chapter 26 focused tests: 8 passed.

The full backend suite was not rerun after Chapter 26.

## 9. Current Reconciliation Modules

- `backend/app/reconciliation/schemas.py`
- `backend/app/reconciliation/rules.py`
- `backend/app/reconciliation/exact_match.py`
- `backend/app/reconciliation/fuzzy_match.py`
- `backend/app/reconciliation/aggregate_match.py`

Related tests:
- `backend/tests/test_reconciliation_rules.py`
- `backend/tests/test_exact_match.py`
- `backend/tests/test_fuzzy_match.py`
- `backend/tests/test_aggregate_match.py`

## 10. Development and Git Workflow

Work chapter by chapter according to the approved workbook and ADRs.

For each chapter:
1. Inspect existing code and dependencies.
2. Implement the complete approved functionality.
3. Perform focused verification.
4. Update project documentation after the chapter implementation is verified.
5. Review changes and sensitive files.
6. Run `git diff --check`.
7. Stage only intended files.
8. Commit and push at the approved chapter milestone.
9. Verify the resulting Git state.

Never commit secrets or force-push without approval.

Do not mark a chapter complete until implementation, verification, documentation and Git checkpoint requirements are satisfied.

## 11. Important Project Rules

- Preserve the approved architecture and existing functionality.
- Provide complete replacement code for modified files.
- Avoid unnecessary dependencies and unapproved features.
- Do not introduce API endpoints or database persistence unless the workbook requires them.
- Preserve previous project history in documentation.
- Update registers at chapter milestones, not after every small modification.
- Comprehensive testing is planned after all 52 chapters are implemented.
