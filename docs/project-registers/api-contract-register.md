
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

- All future API routes must follow the `/api/v1` versioning convention.
- The health endpoint checks API liveness independently of database readiness.
- The readiness endpoint reports MongoDB connectivity.
