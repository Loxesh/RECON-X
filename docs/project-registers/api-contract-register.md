
# RECON X - API Contract Register

**Last Updated:** 19 November 2026

## Implemented Endpoints

| Method | Endpoint | Purpose | Status |
|---|---|---|---|
| GET | /api/v1/health | Check backend API liveness | Implemented |
| GET | /api/v1/ready | Check application and MongoDB readiness | Implemented |
| POST | /api/v1/auth/login | Authenticate a user and issue an access token | Implemented |
| GET | /api/v1/auth/me | Retrieve the authenticated user's information | Implemented |
| POST | /api/v1/uploads | Validate, privately store and register a financial source file | Implemented |

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
- **Purpose:** Validates an uploaded financial source file, stores the original in private local storage and registers its metadata in MongoDB.
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
- Stores the original file in a private local development storage directory.
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
| 500 | Private storage or metadata registration failure |

### Storage Notes

- Chapter 17 uses a provider-independent storage interface with a private local development implementation.
- The local private upload directory is excluded from Git.
- Original files are not exposed through public URLs.
- MinIO and S3-compatible provider integration is addressed in Chapter 18.

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
| upload.py | UploadPeriodSchema, UploadMetadataSchema, UploadedFileResponse, UploadInitiationResponse | Upload metadata and upload response contracts |
| job.py | JobPeriodSchema, ReconciliationFileSelection, ReconciliationJobCreateRequest, ReconciliationJobResponse, ReconciliationJobListItem | Reconciliation job request and response contracts |
| transaction.py | TransactionResponse, TransactionListFilters, TransactionAmountSummary | Transaction retrieval, filtering and summary contracts |
| exception.py | ExceptionResponse, ExceptionListFilters, ExceptionAssignmentRequest, ExceptionStatusUpdateRequest | Exception review and assignment contracts |
| investigation.py | InvestigationResponse, InvestigationRequest, InvestigationListFilters | Investigation request and response contracts |
| report.py | ReportResponse, ReportGenerationRequest, ReportListFilters, ReportSignoffSchema | Report generation, retrieval and sign-off contracts |

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

- Upload status retrieval
- Reconciliation jobs
- Transactions and matches
- Exceptions
- Investigations
- Human review
- Reports
- Administration

## Notes

- The health endpoint checks API liveness independently of database readiness.
- The readiness endpoint reports MongoDB connectivity.
- Authentication and current-user endpoints are implemented.
- JWT authentication and role-based access control infrastructure are available.
- Tenant context is derived from the authenticated user.
- The secure financial file upload endpoint is implemented and tested.
- The upload endpoint uses private local storage; MinIO/S3 integration is not yet implemented.
- Schema definitions do not mean their corresponding HTTP endpoints are already available.
- Reconciliation, investigation, reporting and frontend API integration will be implemented in their designated workbook chapters.
