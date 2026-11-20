
# RECON X - File Inventory

**Last Updated:** 20 November 2026

## Root Structure

| Path | Purpose |
|---|---|
| README.md | Project overview and setup information |
| .gitignore | Excludes secrets, environments, private uploads and generated files |
| backend/ | FastAPI backend |
| frontend/ | React + Vite frontend |
| docker/ | Local container configuration for S3-compatible storage |
| scripts/ | Project utility scripts |
| sample_data/ | Sample input data |
| docs/ | Project documentation and registers |
| .github/workflows/ | CI workflow directory |

## Docker Configuration

| File | Purpose |
|---|---|
| docker/docker-compose.yml | Local SILO S3-compatible object storage service configuration |

## Backend Files

| File | Purpose |
|---|---|
| backend/.env.example | Safe local environment configuration template |
| backend/pyproject.toml | Python project configuration and dependencies |
| backend/app/__init__.py | Backend application package |
| backend/app/main.py | FastAPI application, lifespan management, middleware, routers and health endpoints |

## Core Configuration and Infrastructure

| File | Purpose |
|---|---|
| backend/app/core/__init__.py | Core configuration package |
| backend/app/core/config.py | Central Pydantic Settings configuration loader |
| backend/app/core/database.py | MongoDB client creation, ping and shutdown utilities |
| backend/app/core/security.py | Password hashing, password verification and JWT token utilities |
| backend/app/core/permissions.py | Role-based access control and permission definitions |
| backend/app/core/exceptions.py | Centralized API exception handlers and error responses |
| backend/app/core/middleware.py | Request ID handling, request context and HTTP request logging |

## Observability

| File | Purpose |
|---|---|
| backend/app/observability/__init__.py | Observability package |
| backend/app/observability/health.py | MongoDB health and readiness status helper |

## MongoDB Document Models

| File | Purpose |
|---|---|
| backend/app/models/__init__.py | MongoDB document models package |
| backend/app/models/base.py | Shared document fields, ObjectId validation and tenant document base |
| backend/app/models/enums.py | Shared model enumerations |
| backend/app/models/bson.py | Decimal128 conversion and BSON serialization helpers |
| backend/app/models/organization.py | Organization document and configuration models |
| backend/app/models/user.py | Tenant-owned user document model |
| backend/app/models/uploaded_file.py | Uploaded financial file and file period models |
| backend/app/models/ingestion_job.py | File ingestion job and ingestion result models |
| backend/app/models/transaction.py | Normalized financial transaction document model |
| backend/app/models/reconciliation_job.py | Reconciliation job, period and file reference models |
| backend/app/models/match_result.py | Deterministic transaction match result model |
| backend/app/models/exception.py | Reconciliation exception and status history models |
| backend/app/models/investigation.py | Exception investigation and validation models |
| backend/app/models/agent_execution.py | Agent execution tracking model |
| backend/app/models/workflow_run.py | Workflow execution and step tracking models |
| backend/app/models/approval.py | Human approval decision document model |
| backend/app/models/audit_event.py | Audit event, actor and resource models |
| backend/app/models/report.py | Generated reconciliation report and signoff models |
| backend/app/models/llm_usage.py | LLM usage and estimated cost tracking model |

## API Schemas

| File | Purpose |
|---|---|
| backend/app/schemas/__init__.py | API schemas package |
| backend/app/schemas/common.py | Shared API response and pagination schemas |
| backend/app/schemas/auth.py | Authentication request, token and current-user response schemas |
| backend/app/schemas/upload.py | Upload metadata and upload response schemas |
| backend/app/schemas/job.py | Reconciliation job request, response and period schemas |
| backend/app/schemas/transaction.py | Transaction response, filters and amount summary schemas |
| backend/app/schemas/exception.py | Exception response, filters, assignment and status update schemas |
| backend/app/schemas/investigation.py | Investigation request, response and validation schemas |
| backend/app/schemas/report.py | Report generation request, response and signoff schemas |

## API Routing and Dependencies

| File | Purpose |
|---|---|
| backend/app/api/v1/router.py | Central versioned API router |
| backend/app/api/v1/routers/auth.py | Login and authenticated current-user endpoints |
| backend/app/api/v1/routers/uploads.py | Authenticated financial file upload endpoint |
| backend/app/api/deps/auth_deps.py | Current-user authentication and permission dependency functions |
| backend/app/api/deps/tenant_deps.py | Trusted organization context from authenticated user identity |

## Services

| File | Purpose |
|---|---|
| backend/app/services/auth_service.py | User authentication, organization validation and active-user retrieval |

## Repositories

| File | Purpose |
|---|---|
| backend/app/repositories/__init__.py | Repository package |
| backend/app/repositories/base.py | Base tenant-scoped MongoDB repository and CRUD operations |
| backend/app/repositories/tenant_collections.py | Tenant-scoped repositories for organization-owned collections |
| backend/app/repositories/organization.py | Organization repository |
| backend/app/repositories/audit_event.py | Append-only audit event repository interface |

## Ingestion

File	Purpose
backend/app/ingestion/__init__.py	Ingestion package
backend/app/ingestion/file_validator.py	File extension, MIME type, size, CSV and XLSX validation
backend/app/ingestion/csv_xlsx_parser.py	CSV and multi-sheet XLSX parsing with source-row and sheet information preservation
backend/app/ingestion/header_mapper.py	Maps bank, ledger and gateway column aliases into canonical transaction fields
backend/app/ingestion/validators.py	Validates mapped transaction rows and preserves row-level validation issues
backend/app/ingestion/normalizer.py      Normalizes dates, Decimal amounts, currencies, directions, references and descriptions
backend/app/ingestion/provenance.py      Preserves source file and row provenance and generates deterministic SHA-256 fingerprints

## Integrations

| File | Purpose |
|---|---|
| backend/app/integrations/__init__.py | External integration package |
| backend/app/integrations/object_storage.py | Provider-independent storage interface with private local and boto3-based S3-compatible implementations |

## Sample Development Data

| File | Purpose |
|---|---|
| backend/sample_bank_statement.csv | Synthetic bank statement used for parser and ingestion testing |

## Backend Scripts

| File | Purpose |
|---|---|
| backend/scripts/create_indexes.py | Creates MongoDB indexes for RECON X collections |
| backend/scripts/create_dev_admin.py | Interactive setup of a development organisation and administrator account |

## Backend Tests

| File | Purpose |
|---|---|
| backend/tests/test_health.py | API health and database readiness tests |
| backend/tests/test_models.py | Collection model, tenant ownership and financial precision tests |
| backend/tests/test_repository_base.py | Base repository tenant isolation and CRUD tests |
| backend/tests/test_collection_repositories.py | Collection repository behaviour tests |
| backend/tests/test_auth.py | Password hashing, JWT and authentication endpoint tests |
| backend/tests/test_permissions.py | Role-based access control and tenant-context tests |
| backend/tests/test_api_infrastructure.py | API error handling, request middleware and infrastructure tests |
| backend/tests/test_file_validator.py | Financial file format, MIME type, size and content validation tests |
| backend/tests/test_object_storage.py | Local and mocked S3-compatible storage operation tests |
| backend/tests/test_uploads.py | Authenticated upload API, metadata, storage and permission tests |
| backend/tests/test_csv_xlsx_parser.py | CSV and XLSX parser behaviour, encoding, multi-sheet and malformed input tests |
File	Purpose
backend/tests/test_header_mapping.py	Header mapping, source-specific aliases, ambiguous headers and row validation tests
| backend/tests/test_normalizer.py | Date, timezone, Decimal amount, currency, direction and reference normalization tests |
| backend/tests/test_provenance.py | Source provenance, raw-row hashing and transaction fingerprint tests |

## Local Development Files

| File | Purpose | Git Status |
|---|---|---|
| backend/.env | Local application and MongoDB Atlas configuration | Ignored |
| backend/.env.example | Shareable configuration template | Trackable |
| backend/private_uploads/ | Private local development storage for original uploaded files | Ignored |

## Frontend Files

| File | Purpose |
|---|---|
| frontend/package.json | Frontend dependencies and scripts |
| frontend/package-lock.json | Locked frontend dependency versions |
| frontend/index.html | Application HTML entry point |
| frontend/vite.config.js | Vite, React and Tailwind plugin configuration |
| frontend/eslint.config.js | ESLint configuration |
| frontend/src/main.jsx | React entry point |
| frontend/src/App.jsx | Initial RECON X dashboard shell |
| frontend/src/App.css | Reusable component styles |
| frontend/src/index.css | Global styles and design tokens |
| frontend/public/favicon.svg | Favicon asset |
| frontend/public/icons.svg | Icon asset |
| frontend/src/assets/ | Frontend assets |

## Operations Documentation

| File | Purpose |
|---|---|
| docs/operations/mongodb-atlas.md | MongoDB Atlas development setup and connection verification |
| docs/operations/mongodb-collection-schemas.md | Field definitions and sample documents for all 15 MongoDB collections |

## Project Registers

| File | Purpose |
|---|---|
| docs/project-registers/api-contract-register.md | Implemented and planned API endpoints |
| docs/project-registers/environment-variables-register.md | Environment variable tracking |
| docs/project-registers/file-inventory.md | Project file inventory |
| docs/project-registers/chapter-completion-record.md | Workbook chapter progress |

## Notes

- Python virtual environments, node_modules and frontend dist output are excluded from Git.
- Local `.env` files must never be committed.
- `.env.example` must contain safe placeholders only.
- Private local uploaded files are stored under `backend/private_uploads/` and excluded from Git.
- The frontend uses JavaScript and JSX, not TypeScript.
- MongoDB Atlas is used as the development database.
- PyMongo is the approved synchronous MongoDB driver.
- The FastAPI application manages one MongoDB client through its lifespan.
- Document models are defined for all 15 RECON X collections.
- API request and response schemas are maintained separately from MongoDB document models.
- Financial values use Python Decimal and MongoDB Decimal128.
- Tenant-owned document models require an organization ID.
- Tenant-scoped repositories enforce organization-level data isolation.
- JWT authentication and role-based access control are implemented.
- Tenant identity is obtained from the authenticated user context, not directly from client input.
- API request IDs, centralized exception handling and request logging are implemented.
- MongoDB indexes are defined and created through the backend index creation script.
- Secure financial file validation, SHA-256 hashing, private object storage and upload metadata registration are implemented.
- The local S3-compatible storage service uses SILO; it is not the official MinIO server image.
- The development sample bank statement contains synthetic data only.
- The development administrator setup script prompts for credentials and hashes passwords using Argon2.
- S3-compatible storage integration is implemented using the local SILO service and boto3 adapter.
- CSV/XLSX parsing, header mapping, row validation, financial normalization and source provenance are implemented as ingestion components.
- Financial amounts are normalized using Decimal; original source rows and provenance are preserved.
- Naive transaction dates require an explicitly supplied source timezone; no local timezone is silently assumed.
- Reconciliation workflows, AI agents and frontend API integration remain in their designated implementation chapters.
- Additional modules will be recorded as implementation progresses.
