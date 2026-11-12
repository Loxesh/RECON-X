# RECON X - Environment Variables Register

**Last Updated:** 12 November 2026

## Current Status

Environment configuration is scheduled for the environment configuration chapter.

No application environment variables have been formally configured or registered yet.

## Planned Variables

| Variable | Scope | Purpose | Status |
|---|---|---|---|
| VITE_API_BASE_URL | Frontend | Backend API base URL | Planned |
| DATABASE_URL | Backend | Database connection configuration | Planned |
| REDIS_URL | Backend | Redis connection configuration | Planned |
| SECRET_KEY | Backend | Application security configuration | Planned |
| LLM_PROVIDER | Backend | LLM provider selection | Planned |

## Security Rules

- Never commit `.env` files or credentials.
- Maintain a `.env.example` containing placeholders only.
- Never expose backend secrets through frontend environment variables.
- Register new variables whenever configuration is introduced.

## Notes

The planned variables above are not confirmed final configuration values. Their names and requirements must be validated against the approved architecture and implementation workbook before use.