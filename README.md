# RECON X

**Intelligent Multi-Agent Financial Reconciliation and Discrepancy Investigation System**

RECON X is a financial reconciliation platform designed to automate transaction matching, identify discrepancies, investigate exceptions using evidence-based AI assistance, and support authorized human review.

## Core Capabilities

- Bank, company ledger and payment gateway file ingestion.
- CSV and XLSX validation and normalization.
- Deterministic financial transaction matching.
- Duplicate and missing transaction detection.
- AI-assisted discrepancy investigation.
- Multi-agent orchestration.
- Human-in-the-Loop review and approval.
- Audit trails and financial reporting.
- Security, governance and cost monitoring.

## Technology Stack

| Component | Technology |
|---|---|
| Frontend | React, Vite, Tailwind CSS |
| Backend | Python, FastAPI |
| Validation | Pydantic |
| Database | MongoDB Atlas |
| Data Processing | Pandas, NumPy, Decimal, openpyxl |
| Background Jobs | Celery, Redis |
| AI | Provider-independent LLM gateway |
| Orchestration | Custom state machine |
| Observability | OpenTelemetry |
| Infrastructure | Docker, GitHub Actions |

## Project Structure

- `backend/` – Backend application and API.
- `frontend/` – React application.
- `docker/` – Container configuration.
- `scripts/` – Development and maintenance scripts.
- `sample_data/` – Synthetic testing datasets.
- `docs/` – Architecture and technical documentation.
- `.github/workflows/` – CI/CD workflows.

## Development Status

Initial repository setup completed.

Implementation follows the approved RECON X Stage 1 Architecture and Stage 2 Implementation Workbook.

## Security

- Never commit environment files containing secrets.
- Use deterministic financial calculations.
- Use Decimal arithmetic for authoritative financial amounts.
- Scope tenant-owned database operations by authenticated organization.
- Require authorized human approval for financial decisions.
- Maintain traceable evidence and audit records.
