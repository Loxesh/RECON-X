# RECON X - API Contract Register

**Last Updated:** 12 November 2026

## Implemented Endpoints

| Method | Endpoint | Purpose | Status |
|---|---|---|---|
| GET | /api/v1/health | Check backend API liveness | Implemented |
| GET | /api/v1/ready | Check application and MongoDB readiness | Implemented |

## 1. API Health Endpoint

- **Method:** GET
- **Path:** `/api/v1/health`
- **Expected HTTP Status:** 200
- **Purpose:** Confirms that the API process is running.

### Expected Response

```json
{
  "status": "healthy",
  "service": "recon-x-api",
  "api_version": "v1"
}
```

## 2. Application Readiness Endpoint

- **Method:** GET
- **Path:** `/api/v1/ready`
- **Expected HTTP Status:** 200 when MongoDB is reachable; 503 when unavailable.
- **Purpose:** Reports whether the application can access MongoDB.

### Successful Response

```json
{
  "status": "ready",
  "service": "recon-x-api",
  "database": "connected"
}
```

### Unavailable Database Response

```json
{
  "detail": {
    "status": "not_ready",
    "database": "unavailable"
  }
}
```

## MongoDB Health Behaviour

- A single synchronous PyMongo client is created during FastAPI startup.
- MongoDB connectivity is checked using the administrative ping command.
- The connection status is stored in application state.
- The MongoDB client is closed during application shutdown.
- Database credentials and connection strings are never returned by health endpoints.
- Readiness currently reflects the connectivity check performed at startup.

## 3. API Schema Contracts

**Status:** Schema definitions implemented; corresponding business API endpoints are not yet implemented.

The following Pydantic API schemas are available under `backend/app/schemas/`.

| Schema module | Main contracts | Purpose |
|---|---|---|
| common.py | ApiResponse, PaginationParams, PaginationMetadata, PaginatedResponse | Standard API responses and pagination |
| upload.py | UploadPeriodSchema, UploadMetadataSchema, UploadedFileResponse, UploadInitiationResponse | Upload metadata and upload response contracts |
| job.py | JobPeriodSchema, ReconciliationFileSelection, ReconciliationJobCreateRequest, ReconciliationJobResponse, ReconciliationJobListItem | Reconciliation job request and response contracts |
| transaction.py | TransactionResponse, TransactionListFilters, TransactionAmountSummary | Transaction retrieval, filtering and summary contracts |
| exception.py | ExceptionResponse, ExceptionListFilters, ExceptionAssignmentRequest, ExceptionStatusUpdateRequest | Exception review and assignment contracts |
| investigation.py | InvestigationResponse, InvestigationRequest, InvestigationListFilters | Investigation request and response contracts |
| report.py | ReportResponse, ReportGenerationRequest, ReportListFilters, ReportSignoffSchema | Report generation, retrieval and sign-off contracts |

### API Contract Rules

- All future API routes must follow the `/api/v1` versioning convention.
- Request and response schemas are separate from MongoDB document models.
- API monetary values must be represented as decimal strings.
- MongoDB ObjectIds are represented as strings in API contracts.
- Private storage keys and internal secrets must not be exposed through public API responses.
- Tenant identity must come from trusted authentication context, not an untrusted request-body `org_id`.
- Human approval remains a separate controlled workflow; an LLM cannot approve financial actions.

## Planned API Groups

These are planned, not yet implemented:

- Authentication
- Uploads
- Reconciliation jobs
- Transactions and matches
- Exceptions
- Human review
- Reports
- Administration

## Notes

- The health endpoint checks API liveness independently of database readiness.
- The readiness endpoint reports MongoDB connectivity.
- Schema definitions do not mean their corresponding HTTP endpoints are already available.
- API endpoint implementation and frontend integration will be completed in their designated workbook chapters.
