
# RECON X - API Contract Register

**Last Updated:** 26 November 2026

## Implemented Endpoints

| Method | Endpoint | Purpose | Status |
|---|---|---|---|
| GET | /api/v1/health | Check backend API liveness | Implemented |
| GET | /api/v1/ready | Check application and MongoDB readiness | Implemented |
| POST | /api/v1/auth/login | Authenticate a user and issue an access token | Implemented |
| GET | /api/v1/auth/me | Retrieve the authenticated user's information | Implemented |
| POST | /api/v1/uploads | Validate, privately store and register a financial source file and enqueue ingestion | Implemented |
| GET | /api/v1/uploads/{file_id}/status | Retrieve tenant-scoped ingestion job status and row counts | Implemented |
| GET | /api/v1/reviews | Retrieve the tenant-scoped human review queue | Implemented |
| GET | /api/v1/reviews/{exception_id} | Retrieve review detail and evidence data | Implemented |
| POST | /api/v1/reviews/{exception_id}/decision | Submit an idempotent human approval decision | Implemented |

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

The endpoint returns HTTP 503 when MongoDB is unavailable. The API uses the centralized error response structure.

## 3. Authentication Endpoint

- **Method:** POST
- **Path:** `/api/v1/auth/login`
- **Purpose:** Authenticates an active user within an organization and issues a JWT access token.
- **Authentication:** Not required for this endpoint.

### Behaviour

- Validates the supplied login credentials.
- Checks the organization and user status.
- Verifies the stored password hash.
- Issues a signed JWT access token for successful authentication.
- Uses configured JWT issuer, audience and expiration settings.

## 4. Current User Endpoint

- **Method:** GET
- **Path:** `/api/v1/auth/me`
- **Purpose:** Returns the authenticated user's information.
- **Authentication:** Requires a valid JWT access token.

### Behaviour

- Verifies the access token.
- Retrieves the active user from MongoDB.
- Validates the user's organization context.
- Returns the authenticated user's information.
- Rejects missing, invalid or expired access tokens.

## 5. Secure Financial File Upload Endpoint

- **Method:** POST
- **Path:** `/api/v1/uploads`
- **Expected HTTP Status:** 201 when the upload is successfully stored and registered.
- **Purpose:** Validates an uploaded financial source file, stores the original in private object storage and registers its metadata in MongoDB.
- **Authentication:** Requires a valid JWT access token.
- **Permission:** `uploads:create`.
- **Content Type:** `multipart/form-data`.

### Multipart Fields

| Field | Required | Description |
|---|---|---|
| file | Yes | Financial source file |
| source_type | Yes | Source classification: BANK, LEDGER or GATEWAY |
| period_start_date | No | Start date of the financial period |
| period_end_date | No | End date of the financial period |

Both period dates must be supplied together. The end date cannot be earlier than the start date.

### Behaviour

- Accepts the configured allowlisted CSV and XLSX file formats.
- Checks file extension, MIME type, content and file size.
- Rejects empty, malformed, unsupported and oversized files.
- Calculates the SHA-256 checksum of the original file.
- Generates a tenant-scoped storage key using the organization ID, year, month and file ID.
- Stores the original file through the configured private object storage adapter.
- Registers upload metadata using the tenant-scoped UploadedFileRepository.
- Derives organization identity from the authenticated user, not from client input.
- Sets the initial scan status to `PENDING`.
- Attempts to remove the stored file if metadata registration fails.
- Does not expose internal storage keys or bucket names in the API response.

### Response Fields

The successful response uses `UploadedFileResponse` and includes:

- `id`
- `original_filename`
- `source_type`
- `content_type`
- `size_bytes`
- `sha256`
- `scan_status`
- `created_at`

### Error Behaviour

| HTTP Status | Condition |
|---|---|
| 400 | Invalid, unsupported or oversized file |
| 401 | Missing or invalid authentication |
| 403 | Authenticated user lacks upload permission or valid organization context |
| 422 | Invalid multipart metadata or incomplete period dates |
| 503 | MongoDB database unavailable |
| 409 | Idempotency key reused with different request data or duplicate file fingerprint |
| 500 | Private storage or metadata registration failure |

### Idempotency and Background Ingestion

- Upload requests require the `Idempotency-Key` HTTP header.
- Repeating the same request with the same key returns the existing upload and ingestion job without creating another job or enqueueing duplicate work.
- Reusing the same key with different request data returns HTTP 409 Conflict.
- Uploading the same file fingerprint for the same organization and source type with a different key returns HTTP 409 Conflict.
- The file fingerprint uses the original file SHA-256 and source type within the authenticated organization.
- A newly registered upload creates an ingestion job and dispatches the background Celery task.
- The worker processes parsing, header mapping, row validation and canonical normalization, then records job status and row counts.
- Queue dispatch failure is reported to the client; the registered job remains observable for recovery.

### Ingestion Status Endpoint

- **Method:** GET
- **Path:** `/api/v1/uploads/{file_id}/status`
- **Authentication:** Requires a valid JWT access token.
- **Tenant isolation:** File and job lookup are scoped to the authenticated organization.
- **Response information:** Job status, total/valid/invalid row counts, error summary and attempt count.
- The endpoint does not expose another organization's upload or ingestion job.

### Storage Notes

- Chapter 17 introduced the provider-independent storage interface and private upload implementation.
- Chapter 18 extended the adapter with S3-compatible storage operations.
- Local development uses SILO, a MinIO-derived S3-compatible server.
- The backend communicates with S3-compatible storage through the storage adapter and boto3.
- The development bucket is `recon-x-private-dev`.
- The bucket is configured for private access.
- Supported adapter operations include put, get, delete and head.
- Presigned download URL generation is supported by the storage adapter.
- The local private upload directory and storage credentials are excluded from Git.
- Original files are not exposed through public URLs.

## 6. MongoDB Health Behaviour

- A single synchronous PyMongo client is created during FastAPI startup.
- MongoDB connectivity is checked using the administrative ping command.
- The connection status is stored in application state.
- The MongoDB client is closed during application shutdown.
- Database credentials and connection strings are never returned by health endpoints.
- Readiness currently reflects the connectivity check performed at startup.

## 7. API Schema Contracts

**Status:** Schema definitions implemented; corresponding business API endpoints are not yet implemented unless listed in the implemented endpoints section.

The following Pydantic API schemas are available under `backend/app/schemas/`.

| Schema module | Main contracts | Purpose |
|---|---|---|
| common.py | ApiResponse, PaginationParams, PaginationMetadata, PaginatedResponse | Standard API responses and pagination |
| auth.py | LoginRequest, TokenResponse, CurrentUserResponse | Authentication and current-user response contracts |
| upload.py | UploadPeriodSchema, UploadMetadataSchema, UploadedFileResponse, UploadInitiationResponse, IngestionJobStatusResponse | Upload metadata, ingestion initiation and job status response contracts |
| job.py | JobPeriodSchema, ReconciliationFileSelection, ReconciliationJobCreateRequest, ReconciliationJobResponse, ReconciliationJobListItem | Reconciliation job request and response contracts |
| transaction.py | TransactionResponse, TransactionListFilters, TransactionAmountSummary | Transaction retrieval, filtering and summary contracts |
| exception.py | ExceptionResponse, ExceptionListFilters, ExceptionAssignmentRequest, ExceptionStatusUpdateRequest | Exception review and assignment contracts |
| investigation.py | InvestigationResponse, InvestigationRequest, InvestigationListFilters | Investigation request and response contracts |
| report.py | ReportResponse, ReportGenerationRequest, ReportListFilters, ReportSignoffSchema | Report generation, retrieval and sign-off contracts |
| review.py | ReviewDecisionRequest, ReviewQueueItem, ReviewDetailResponse, ReviewDecisionResponse | Human review queue, evidence detail and decision contracts |

## 8. API Contract Rules

- All API routes must follow the `/api/v1` versioning convention.
- Request and response schemas are separate from MongoDB document models.
- API monetary values must be represented as decimal strings.
- MongoDB ObjectIds are represented as strings in API contracts.
- Private storage keys and internal secrets must not be exposed through public API responses.
- Tenant identity must come from trusted authentication context, not an untrusted request-body `org_id`.
- Protected endpoints must use the appropriate authentication and permission dependencies.
- Tenant-owned database operations must be scoped to the authenticated organization.
- Centralized exception handlers provide consistent API error responses.
- Request IDs are attached to requests and returned through response headers.
- Human approval remains a separate controlled workflow; an LLM cannot approve financial actions.

## 9. Planned API Groups

These API groups remain planned for subsequent implementation chapters:

- Reconciliation jobs
- Transactions and matches
- Exceptions
- Investigations
- Reports
- Administration

## Notes

- The health endpoint checks API liveness independently of database readiness.
- The readiness endpoint reports MongoDB connectivity.
- Authentication and current-user endpoints are implemented.
- JWT authentication and role-based access control infrastructure are available.
- Tenant context is derived from the authenticated user.
- The secure financial file upload endpoint, idempotency handling, background ingestion dispatch and tenant-scoped upload status endpoint are implemented and automated tests are passing.
- S3-compatible storage operations have been tested against the local SILO server.
- CSV and XLSX parsing, header mapping, row validation and canonical normalization are executed by the background ingestion task; parsing components do not introduce separate HTTP endpoints.
- Schema definitions do not mean their corresponding HTTP endpoints are already available.
- Reconciliation, investigation, reporting and frontend API integration will be implemented in their designated workbook chapters.

## Chapter 23 � Matching Contracts

- Defined internal matching input and output schemas.
- Defined matching outcomes, rule identifiers and evidence structures.
- Matching results carry the ruleset version and SHA-256 ruleset fingerprint.
- No reconciliation API endpoint is introduced in this chapter. API endpoints will be added in their designated workbook chapters.

## Chapter 28 - Discrepancy Detection

- Discrepancy detection and exception classification are internal reconciliation modules.
- No HTTP endpoint or externally exposed API contract was introduced.
- Existing exception document and response schema contracts were preserved.

## 10. Human Review API

### Review Queue

- **Method:** GET
- **Path:** `/api/v1/reviews`
- **Authentication:** Requires a valid JWT access token.
- **Permission:** `reviews:read`
- **Purpose:** Retrieves the authenticated organisation's pending review items.
- **Tenant isolation:** Results are scoped to the authenticated organisation.
- **Pagination:** Supports `skip` and `limit`.

### Review Detail and Evidence

- **Method:** GET
- **Path:** `/api/v1/reviews/{exception_id}`
- **Authentication:** Requires a valid JWT access token.
- **Permission:** `reviews:read`
- **Purpose:** Retrieves review details, transaction references, risk information and evidence.
- **Tenant isolation:** An exception belonging to another organisation is not exposed.

### Submit a Review Decision

- **Method:** POST
- **Path:** `/api/v1/reviews/{exception_id}/decision`
- **Authentication:** Requires a valid JWT access token.
- **Permission:** `reviews:decide`
- **Required Header:** `Idempotency-Key`
- **Request Schema:** `ReviewDecisionRequest`
- **Response Schema:** `ReviewDecisionResponse`

#### Request Fields

| Field | Required | Description |
|---|---|---|
| decision | Yes | APPROVE, MODIFY or REJECT |
| comment | No | Reviewer comment, maximum 4000 characters |
| after | Conditional | Non-empty proposal required for MODIFY |

#### Decision Behaviour

- **APPROVE:** Sets exception status to `APPROVED` and clears `review_required`.
- **REJECT:** Sets exception status to `REJECTED` and clears `review_required`.
- **MODIFY:** Stores the proposed changes in the approval record; exception remains `OPEN` and `review_required`.
- Modification proposals do not directly overwrite protected financial fields.
- Terminal status transitions append to `status_history`.
- Approval persistence, exception updates and audit append execute in one MongoDB transaction.
- Identical idempotent retries replay the original decision.
- Reusing an idempotency key with a different request returns HTTP 409.
- Invalid state transitions and simultaneous conflicting decisions are rejected.

#### Permission and Error Behaviour

- `org_admin` and `finance_analyst` are authorised decision roles.
- `auditor` is read-only and cannot submit decisions.
- HTTP 401: Missing or invalid authentication.
- HTTP 403: Missing decision permission.
- HTTP 404: Review item not found within the tenant.
- HTTP 409: Conflicting idempotency key or unavailable review state.
- HTTP 422: Invalid decision payload.
- HTTP 503: Transaction or audit persistence failure.

## Chapter 32 ? LLM Gateway Contract

- No HTTP endpoint introduced by Chapter 32.
- The LLM gateway is an internal application service.
- Provider adapters: Gemini, OpenAI-compatible, Mock and local.
- Provider credentials and endpoints are configured server-side.
- Secrets must not be exposed through API responses or logs.

## Chapter 33 - Prompt Registry and Structured Output

- No HTTP endpoints introduced.
- Prompt registry and output validation are internal application components.
- Structured output is validated against strict Pydantic schemas before it can be accepted.
- Evidence record IDs must belong to the evidence supplied for the request.
- Invalid JSON, missing or unexpected fields, unsupported evidence IDs and overlong outputs are rejected.
- No public API contract or response schema was added by this chapter.
- Human review remains separate; validated LLM output does not authorise or approve financial decisions.

## Chapter 34 - Input and Prompt-Injection Guardrails

- No new API endpoints or external API contracts were introduced.
- Input validation, prompt-injection inspection and evidence-reference validation are internal guardrail components.
- These components do not execute tools or authorize actions.
