
# RECON X â€“ Project Context

**Last Updated:** 26 November 2026

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

The reconciliation engine uses independent BANK-LEDGER and GATEWAY-LEDGER tracks. Each track maintains its own matching decisions, evidence, ruleset identity and exceptions. A ledger transaction may participate in both tracks because they represent separate source comparisons. A transaction can be consumed only once within its own track.

Supported transaction sources:
- BANK
- LEDGER
- GATEWAY

Supported cross-source pairs:
- BANK-LEDGER
- GATEWAY-LEDGER

The matching cascade is:

1. Exact stable transaction ID or approved reference matching with amount and currency consistency.
2. Deterministic reference/date-window matching with configured amount tolerance.
3. Fuzzy candidate matching; candidate scores are evidence for review, not proof.
4. Explicit aggregate candidate evaluation for permitted one-to-many or many-to-one groups.
5. Duplicate and missing transaction detection.
6. Residual discrepancy classification.

Aggregate matching evaluates explicitly supplied candidate groups. It does not generate every possible group combination and never automatically confirms a financial match.

Matching outcomes include:
- CONFIRMED_AUTO
- SUGGESTED
- AMBIGUOUS
- UNMATCHED

Fuzzy and aggregate outcomes remain suggestions and are not automatic financial confirmations. Equally plausible candidates remain ambiguous; the engine must not silently select one.

Duplicate detection identifies potential duplicates and reference conflicts. It does not delete or merge transactions. Missing detection classifies residual unmatched records by their absent counterpart source.

Discrepancy classification retains evidence for detected differences. Each track maintains independent results. Consolidated reporting counts shared ledger source records only once and must not mix financial decisions across tracks.

Financial comparisons use Python Decimal values. Currency equality and configured date windows are enforced. Matching decisions retain ruleset identity and supporting evidence. AI-generated explanations remain advisory; final financial decisions stay under human control through the approved Human in the Loop process.

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

- `backend/` â€“ FastAPI application and backend modules.
- `frontend/` â€“ React application.
- `docker/` â€“ Local service configuration.
- `scripts/` â€“ Utility scripts.
- `sample_data/` â€“ Development sample data.
- `docs/` â€“ Architecture, operations and project registers.
- `.github/workflows/` â€“ CI workflow configuration.

## 8. Implementation Progress

Total workbook chapters: 52.

Officially completed: 33/52.

- Chapters 1-9 and 11-29: Completed.
- Chapter 10: Deferred.
- Chapter 30: Completed; implementation, documentation, 362 full-suite tests passed, and commit a7288a9 pushed to origin/main.
- Chapter 31: Completed; implementation, documentation and Git milestone pushed as 0f5a18f.
- Chapter 32: Completed; implementation and Git milestone pushed to origin/main.
- Chapter 33: Completed - integration deferred; 15 focused tests passed and commit 8605a0b pushed. Persistence enforcement remains deferred until the investigation workflow exists.
- Chapter 34: Completed; 32 focused tests passed and commit f4c55ad pushed. Full backend suite: 447 passed.
- Chapter 35: Implementation verified; 10 focused tests passed and full backend suite 457 passed. Documentation and Git closure pending.
- Chapters 36-52: Pending implementation.

Chapter 30 verification:
- Audit-chain focused tests: 4 passed.
- Repository, model and permission regression tests: 98 passed.
- Full backend test suite: 362 passed, 1 warning.
- Git milestone: a7288a9 committed and pushed to origin/main.

Earlier chapter focused verification records:
- Chapter 25: 19 focused tests passed.
- Chapter 26: 8 focused tests passed.
- Chapter 27: 15 focused tests passed.
- Chapter 28: 22 focused tests passed.
- Chapter 28 model regression tests: 51 passed.

Chapter 30 is complete. The local and origin/main commit hashes match.

## 9. Chapter 31 - Human Approval Workflow

**Implementation status:** Completed; implementation, documentation and Git milestone pushed as 0f5a18f.

- Review queue and tenant-scoped review detail retrieval implemented.
- Evidence data exposed through the review detail response.
- Approve, modify and reject decisions implemented.
- Decision permission is enforced separately from read permission.
- Auditor access remains read-only.
- Idempotency keys prevent duplicate decisions and detect conflicting retries.
- Exception updates, approval records and audit events are committed transactionally.
- MODIFY stores a proposal without changing protected financial fields or closing the review.
- Terminal decisions update exception status history.
- Focused verification: 22 tests passed.
- No new environment variables introduced.
- Chapter 31 implementation, documentation and Git milestone are complete.

## 10. Current Reconciliation Modules

- `backend/app/reconciliation/schemas.py`
- `backend/app/reconciliation/rules.py`
- `backend/app/reconciliation/exact_match.py`
- `backend/app/reconciliation/fuzzy_match.py`
- `backend/app/reconciliation/aggregate_match.py`
- `backend/app/reconciliation/duplicate_detector.py`
- `backend/app/reconciliation/missing_detector.py`
- `backend/app/reconciliation/discrepancy_detector.py`
- `backend/app/reconciliation/exception_classifier.py`

Related tests:
- `backend/tests/test_reconciliation_rules.py`
- `backend/tests/test_exact_match.py`
- `backend/tests/test_fuzzy_match.py`
- `backend/tests/test_aggregate_match.py`
- `backend/tests/test_duplicate_detector.py`
- `backend/tests/test_missing_detector.py`
- `backend/tests/test_discrepancy_detector.py`
- `backend/tests/test_exception_classifier.py`

## 11. Development and Git Workflow

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

## 12. Important Project Rules

- Preserve the approved architecture and existing functionality.
- Provide complete replacement code for modified files.
- Avoid unnecessary dependencies and unapproved features.
- Do not introduce API endpoints or database persistence unless the workbook requires them.
- Preserve previous project history in documentation.
- Update registers at chapter milestones, not after every small modification.
- Comprehensive testing is planned after all 52 chapters are implemented.

## Chapter 32 ? LLM Gateway and Provider Adapters

**Implementation status:** Completed; commit 08ddcdf pushed to origin/main.

- Chapter 32 of 52 ? Phase 5, Governance and AI foundations.
- Implemented provider-neutral gateway and Gemini, OpenAI-compatible, Mock and local adapters.
- Added timeout, bounded fallback and provider error handling.
- Added usage recording support and LLM configuration.
- Focused tests: 60 passed.
- Full backend suite: 393 passed twice.
- No HTTP endpoint introduced.
- Environment settings recorded in the environment-variable register.
- Official completed count: 33/52. Chapter 32 commit `08ddcdf` is pushed to origin/main.

## Chapter 33 - Prompt Registry and Structured Output

**Implementation status:** Completed - integration deferred; implementation, documentation and Git milestone pushed as 8605a0b.

- Workbook: Stage 2, page 46, Phase 5 - Governance and AI foundations.
- Implemented versioned prompt registration and rendering.
- Implemented strict structured JSON output validation with Pydantic.
- Evidence record references must be members of the supplied evidence IDs.
- Malformed JSON, missing fields, extra fields, invented IDs and overlong output are rejected.
- Focused tests: 15 passed.
- Full backend suite: 408 passed, 1 existing Starlette/httpx deprecation warning.
- No HTTP endpoints or environment variables introduced.
- Output validation does not independently prove natural-language factual truth; Human in the Loop remains mandatory.

## Chapter 34 - Input and Prompt-Injection Guardrails

- Implemented untrusted input validation and serialization.
- Added deterministic prompt-injection inspection for common attack indicators.
- Added evidence-reference validation against supplied evidence IDs.
- Added 32 Chapter 34 tests; 47 focused Chapter 33 and 34 tests passed.
- Full backend suite: 440 passed, 1 existing Starlette/httpx deprecation warning.
- No API endpoints, database collections or environment variables were added.
- Prompt-injection pattern detection is not a guarantee against every attack.
- Human review remains required; these guardrails do not authorize actions.
- Documentation and Git milestone completed in commit f4c55ad.
- Official completed chapter count: 33/52. Chapters 31-34 have completed their implementation and documentation Git milestones.
## Chapter 35 - Agent Base Class and Tool Permission Registry

**Implementation status:** Verified; documentation and Git closure pending.

- Implemented shared agent execution context, typed results and status contracts.
- Added Pydantic input/output validation and execution timeout handling.
- Added deny-by-default tool registry with agent-specific permissions.
- Added tool input/output validation and timeout enforcement.
- Kept agent tool permissions separate from application RBAC.
- Focused tests: 10 passed.
- Full backend suite: 457 passed, 1 existing deprecation warning.
- No new API endpoints, database collections, environment variables or dependencies.
- Official completed count remains 33/52 until Git closure is verified.
