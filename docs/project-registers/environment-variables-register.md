
# RECON X - Environment Variables Register

**Last Updated:** 12 November 2026

## Current Status

The backend uses Pydantic Settings to load configuration from `backend/.env`. The local `.env` file is excluded from Git, while `.env.example` contains safe placeholders.

MongoDB Atlas connectivity is integrated into the FastAPI application through synchronous PyMongo.

## Implemented Variables

| Variable | Scope | Purpose | Secret? | Status |
|---|---|---|---|---|
| APP_NAME | Backend | Application display name | No | Implemented |
| APP_VERSION | Backend | Application version | No | Implemented |
| API_V1_PREFIX | Backend | Versioned API route prefix | No | Implemented |
| ENVIRONMENT | Backend | Runtime environment | No | Implemented |
| DEBUG | Backend | FastAPI debug configuration | No | Implemented |
| SECRET_KEY | Backend | Application security placeholder | Yes | Placeholder only |
| MONGODB_URI | Backend | MongoDB Atlas connection URI | Yes | Configured and application connection verified |
| MONGODB_DATABASE | Backend | Application database name | No | Configured: RECON_X_DEV |
| MONGODB_SERVER_SELECTION_TIMEOUT_MS | Backend | MongoDB server selection timeout | No | Implemented default: 5000 |
| MONGODB_CONNECT_TIMEOUT_MS | Backend | MongoDB connection timeout | No | Implemented default: 5000 |
| MONGODB_SOCKET_TIMEOUT_MS | Backend | MongoDB socket timeout | No | Implemented default: 10000 |
| MONGODB_MAX_POOL_SIZE | Backend | Maximum MongoDB connection pool size | No | Implemented default: 20 |

## Planned Variables

| Variable | Scope | Purpose | Status |
|---|---|---|---|
| REDIS_URL | Backend | Redis connection | Planned |
| JWT_SECRET_KEY | Backend | Authentication token signing | Planned |
| OBJECT_STORAGE_PROVIDER | Backend | Object storage provider | Planned |
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

## Notes

- MongoDB Atlas development cluster: `reconx-dev`.
- Database: `RECON_X_DEV`.
- Application database user: `reconx_app_user`.
- MongoDB connectivity was verified independently and through the FastAPI readiness endpoint.
- Collections, indexes and tenant-scoped repositories are not yet implemented.
- Planned variables must be introduced in their relevant implementation chapters.