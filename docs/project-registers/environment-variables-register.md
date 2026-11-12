
# RECON X - Environment Variables Register

**Last Updated:** 12 November 2026

## Current Status

The Chapter 08 environment and secret-handling baseline has been implemented.

The backend uses Pydantic Settings to load configuration from `backend/.env`. The local `.env` file is excluded from Git, while `.env.example` is retained as a tracked configuration template.

## Implemented Variables

| Variable | Scope | Purpose | Secret? | Status |
|---|---|---|---|---|
| APP_NAME | Backend | Application display name | No | Implemented |
| APP_VERSION | Backend | Application version | No | Implemented |
| API_V1_PREFIX | Backend | Versioned API route prefix | No | Implemented |
| ENVIRONMENT | Backend | Runtime environment | No | Implemented |
| DEBUG | Backend | FastAPI debug configuration | No | Implemented |
| SECRET_KEY | Backend | Local development security placeholder | Yes | Placeholder only |

## Planned Variables

| Variable | Scope | Purpose | Status |
|---|---|---|---|
| MONGODB_URI | Backend | MongoDB Atlas connection | Planned |
| MONGODB_DATABASE | Backend | Database name | Planned |
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

## Notes

- The local `.env` file currently contains dummy development values only.
- Database, Redis, authentication, storage and LLM integrations are not configured yet.
- Planned variables must be validated and introduced in their relevant implementation chapters.
