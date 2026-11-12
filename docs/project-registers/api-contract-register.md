# RECON X - API Contract Register

**Last Updated:** 12 November 2026

## Implemented Endpoints

| Method | Endpoint | Purpose | Status |
|---|---|---|---|
| GET | /api/v1/health | Check backend API health | Implemented |

## Health Endpoint

- **Method:** GET
- **Path:** `/api/v1/health`
- **Expected HTTP Status:** 200

### Expected Response

```json
{
  "status": "healthy",
  "service": "recon-x-api",
  "api_version": "v1"
}
```

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

All future API routes must follow the `/api/v1` versioning convention.