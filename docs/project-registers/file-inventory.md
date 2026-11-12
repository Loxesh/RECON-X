# RECON X - File Inventory

**Last Updated:** 12 November 2026

## Root Structure

| Path | Purpose |
|---|---|
| README.md | Project overview and setup information |
| .gitignore | Excludes secrets, environments and generated files |
| backend/ | FastAPI backend |
| frontend/ | React + Vite frontend |
| docker/ | Container configuration |
| scripts/ | Project utility scripts |
| sample_data/ | Sample input data |
| docs/ | Project documentation and registers |
| .github/workflows/ | CI workflow directory |

## Backend Files

| File | Purpose |
|---|---|
| backend/.env.example | Safe local environment configuration template |
| backend/pyproject.toml | Python project configuration and dependencies |
| backend/app/__init__.py | Backend application package |
| backend/app/main.py | FastAPI application, lifespan management and health endpoints |
| backend/app/core/__init__.py | Core configuration package |
| backend/app/core/config.py | Central Pydantic Settings configuration loader |
| backend/app/core/database.py | MongoDB client creation, ping and shutdown utilities |
| backend/app/observability/__init__.py | Observability package |
| backend/app/observability/health.py | MongoDB readiness status helper |
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
| backend/tests/test_health.py | API health and database readiness tests |
| backend/tests/test_models.py | Collection model, tenant ownership and financial precision tests |

## Local Development Files

| File | Purpose | Git Status |
|---|---|---|
| backend/.env | Local application and MongoDB Atlas configuration | Ignored |
| backend/.env.example | Shareable configuration template | Trackable |

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
- The frontend uses JavaScript and JSX, not TypeScript.
- MongoDB Atlas is used as the development database.
- PyMongo is the approved synchronous MongoDB driver.
- The FastAPI application manages one MongoDB client through its lifespan.
- Document models are defined for all 15 RECON X collections.
- Financial values use Python Decimal and MongoDB Decimal128.
- Tenant-owned document models require an organization ID.
- Database collections, indexes and tenant-scoped repositories will be implemented in subsequent chapters.
- Additional modules will be recorded as implementation progresses.