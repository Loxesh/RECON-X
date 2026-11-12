
# RECON X - MongoDB Atlas Development Setup

**Last Updated:** 12 November 2026

## 1. Atlas Project

- Project: RECON X Development
- Cluster: reconx-dev
- Provider: AWS
- Region: Mumbai
- Deployment tier: M0 Free
- MongoDB version: 8.0

## 2. Database

- Database name: RECON_X_DEV
- Application database user: reconx_app_user
- Authentication: Username and password
- Application role: readWrite
- Database scope: RECON_X_DEV
- Collection scope: All collections in the specified database

## 3. Network Security

- Development machine IP allowlisted through Atlas Network Access.
- Access is intended for development only.
- Do not use 0.0.0.0/0 as a permanent access rule.
- Review and update the allowlist if the development IP changes.

## 4. Backend Configuration

The following variables are configured in the local backend/.env file:

- MONGODB_URI
- MONGODB_DATABASE

The connection URI contains credentials and must never be committed, shared or printed in logs.

## 5. Connection Verification

- Driver: PyMongo
- Connection type: Synchronous
- DNS support: dnspython
- Verification: MongoDB admin ping command
- Result: Successful
- Database configured: RECON_X_DEV

## 6. Security Rules

- Use the restricted application database user for backend access.
- Do not use the Atlas Admin account in application code.
- Never commit connection strings or passwords.
- Keep local .env excluded from Git.
- Use tenant-scoped access in application repositories.
- Review network access rules before production deployment.

## 7. Current Limitations

- Application database lifecycle management is not yet implemented.
- Collections and indexes will be created in subsequent chapters.
- Tenant-scoped repositories will be implemented later.
- This setup is a development environment, not production infrastructure.
