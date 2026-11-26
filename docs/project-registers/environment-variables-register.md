
# RECON X - Environment Variables Register

**Last Updated:** 26 November 2026

## Current Status

The backend uses Pydantic Settings to load configuration from `backend/.env`. The local `.env` file is excluded from Git, while `.env.example` contains safe placeholders.

MongoDB Atlas connectivity is integrated into the FastAPI application through synchronous PyMongo.

Authentication, JWT configuration, request middleware, private S3-compatible object storage and Redis-backed Celery worker configuration are implemented.

## Implemented Variables

| Variable | Scope | Purpose | Secret? | Status |
|---|---|---|---|---|
| APP_NAME | Backend | Application display name | No | Implemented |
| APP_VERSION | Backend | Application version | No | Implemented |
| API_V1_PREFIX | Backend | Versioned API route prefix | No | Implemented |
| ENVIRONMENT | Backend | Runtime environment | No | Implemented |
| DEBUG | Backend | FastAPI debug configuration | No | Implemented |
| SECRET_KEY | Backend | Application security placeholder | Yes | Placeholder only |
| LOG_LEVEL | Backend | Application logging level | No | Implemented |
| CORS_ORIGINS | Backend | Permitted frontend origins | No | Implemented |
| MONGODB_URI | Backend | MongoDB Atlas connection URI | Yes | Configured and application connection verified |
| MONGODB_DATABASE | Backend | Application database name | No | Configured: RECON_X_DEV |
| MONGODB_SERVER_SELECTION_TIMEOUT_MS | Backend | MongoDB server selection timeout | No | Implemented default: 5000 |
| MONGODB_CONNECT_TIMEOUT_MS | Backend | MongoDB connection timeout | No | Implemented default: 5000 |
| MONGODB_SOCKET_TIMEOUT_MS | Backend | MongoDB socket timeout | No | Implemented default: 10000 |
| MONGODB_MAX_POOL_SIZE | Backend | Maximum MongoDB connection pool size | No | Implemented default: 20 |
| MAX_UPLOAD_BYTES | Backend | Maximum permitted upload size | No | Implemented default: 10 MB |
| PRIVATE_UPLOAD_STORAGE_PATH | Backend | Private local filesystem storage directory | No | Implemented |
| UPLOAD_STORAGE_BUCKET | Backend | Default upload storage bucket | No | Implemented |
| JWT_SECRET_KEY | Backend | JWT access-token signing key | Yes | Configured locally |
| JWT_ISSUER | Backend | JWT token issuer | No | Implemented |
| JWT_AUDIENCE | Backend | JWT token audience | No | Implemented |
| JWT_ACCESS_TOKEN_EXPIRE_MINUTES | Backend | JWT access-token lifetime | No | Implemented |
| OBJECT_STORAGE_PROVIDER | Backend | Selects the object storage implementation | No | Implemented |
| S3_ENDPOINT_URL | Backend | S3-compatible storage endpoint | No | Configured for local development |
| S3_BUCKET | Backend | Private object storage bucket | No | Configured: recon-x-private-dev |
| S3_REGION | Backend | S3-compatible storage region | No | Configured |
| S3_ACCESS_KEY_ID | Backend | S3-compatible storage access key | Yes | Configured locally |
| S3_SECRET_ACCESS_KEY | Backend | S3-compatible storage secret | Yes | Configured locally |
| S3_PRESIGNED_URL_EXPIRY_SECONDS | Backend | Presigned download URL validity period | No | Implemented |
| REDIS_URL | Backend | Redis broker URL used by Celery background workers | No | Implemented; local development uses Redis on localhost:6379/0 |

## Planned Variables

| Variable | Scope | Purpose | Status |
|---|---|---|---|
| LLM_PROVIDER | Backend | LLM provider selection | Planned |
| GEMINI_API_KEY | Backend | Gemini integration | Planned |
| OPENAI_COMPAT_API_KEY | Backend | OpenAI-compatible provider integration | Planned |
| VITE_API_BASE_URL | Frontend | Backend API base URL | Planned |

## Security Rules

- Never commit local `.env` files or credentials.
- Maintain `.env.example` with safe placeholders only.
- Never expose backend secrets through frontend environment variables.
- Never print secret values in logs or terminal verification commands.
- Register new environment variables whenever configuration is introduced.
- Do not use development placeholders as production credentials.
- Use the restricted application database user for backend access.
- Never use the Atlas Admin account in application code.
- Keep object storage private; do not expose public bucket access.
- Use server-side storage configuration for all backend storage operations.

## Notes

- MongoDB Atlas development cluster: `reconx-dev`.
- Database: `RECON_X_DEV`.
- Application database user: `reconx_app_user`.
- MongoDB connectivity was verified independently and through the FastAPI readiness endpoint.
- All 15 MongoDB document models, indexes and tenant-scoped repositories are implemented.
- JWT authentication and role-based access control are implemented.
- S3-compatible object storage is configured using the local SILO server.
- The storage adapter supports local private storage and S3-compatible storage.
- CSV and XLSX parsing implementation is available in the ingestion module.
- Redis is configured for the Chapter 22 Celery background ingestion worker. LLM provider configuration remains planned for its designated chapter.
- Planned variables must be introduced in their relevant implementation chapters.

## Chapter 28 - Discrepancy Detection

- No new environment variables were introduced.
- Existing matching ruleset configuration is reused.
- No fixed company-specific financial discrepancy threshold was added.

## Chapter 32 ? LLM Environment Variables

| Variable | Required when | Secret? | Default / safe example |
|---|---|---|---|
| LLM_PROVIDER | Selecting primary provider | No | mock |
| LLM_FALLBACK_PROVIDERS | Configuring fallbacks | No | Empty |
| LLM_TIMEOUT_SECONDS | Provider timeout | No | 20 |
| GEMINI_API_KEY | Gemini enabled | Yes | Unset |
| GEMINI_MODEL | Gemini enabled | No | gemini-2.5-flash |
| OPENAI_COMPAT_API_KEY | Remote compatible provider | Yes | Unset |
| OPENAI_COMPAT_BASE_URL | Remote compatible provider | No | https://api.openai.com/v1 |
| OPENAI_COMPAT_MODEL | Remote compatible provider | No | gpt-4o-mini |
| LOCAL_LLM_BASE_URL | Local provider | No | http://localhost:11434/v1 |
| LOCAL_LLM_MODEL | Local provider | No | llama3.2:3b |

Real credentials remain only in the ignored local .env file.

## Chapter 33 - Configuration

- No new environment variables introduced.
- Chapter 33 uses the existing Chapter 32 LLM provider configuration.
- Prompt templates and output validation limits are defined in application code.
- No credentials or provider settings are added by this chapter.

## Chapter 34 - Input and Prompt-Injection Guardrails

- No new environment variables were introduced.
- Existing Chapter 32 LLM configuration remains unchanged.
