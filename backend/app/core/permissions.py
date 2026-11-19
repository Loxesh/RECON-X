
"""Central role-to-permission policy for RECON X."""

from enum import StrEnum


class Role(StrEnum):
    ORG_ADMIN = "org_admin"
    FINANCE_ANALYST = "finance_analyst"
    AUDITOR = "auditor"


class Permission(StrEnum):
    UPLOADS_CREATE = "uploads:create"
    UPLOADS_READ = "uploads:read"

    JOBS_CREATE = "jobs:create"
    JOBS_READ = "jobs:read"
    JOBS_START = "jobs:start"
    JOBS_CANCEL = "jobs:cancel"

    MATCHES_READ = "matches:read"
    TRANSACTIONS_READ = "transactions:read"

    EXCEPTIONS_READ = "exceptions:read"
    INVESTIGATIONS_READ = "investigations:read"
    INVESTIGATIONS_CREATE = "investigations:create"

    REVIEWS_READ = "reviews:read"
    REVIEWS_DECIDE = "reviews:decide"
    REVIEWS_SIGNOFF = "reviews:signoff"

    REPORTS_CREATE = "reports:create"
    REPORTS_READ = "reports:read"

    AUDIT_READ = "audit:read"
    AUDIT_VERIFY = "audit:verify"

    COST_READ = "cost:read"
    USERS_MANAGE = "users:manage"
    ORG_SETTINGS = "org:settings"


ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    Role.ORG_ADMIN.value: frozenset(permission.value for permission in Permission),

    Role.FINANCE_ANALYST.value: frozenset({
        Permission.UPLOADS_CREATE.value,
        Permission.UPLOADS_READ.value,
        Permission.JOBS_CREATE.value,
        Permission.JOBS_READ.value,
        Permission.JOBS_START.value,
        Permission.JOBS_CANCEL.value,
        Permission.MATCHES_READ.value,
        Permission.TRANSACTIONS_READ.value,
        Permission.EXCEPTIONS_READ.value,
        Permission.INVESTIGATIONS_READ.value,
        Permission.INVESTIGATIONS_CREATE.value,
        Permission.REVIEWS_READ.value,
        Permission.REVIEWS_DECIDE.value,
        Permission.REPORTS_CREATE.value,
        Permission.REPORTS_READ.value,
    }),

    Role.AUDITOR.value: frozenset({
        Permission.UPLOADS_READ.value,
        Permission.JOBS_READ.value,
        Permission.MATCHES_READ.value,
        Permission.TRANSACTIONS_READ.value,
        Permission.EXCEPTIONS_READ.value,
        Permission.INVESTIGATIONS_READ.value,
        Permission.REVIEWS_READ.value,
        Permission.REPORTS_READ.value,
        Permission.AUDIT_READ.value,
        Permission.AUDIT_VERIFY.value,
        Permission.COST_READ.value,
    }),
}


def has_permission(
    roles: list[str],
    permission: str,
) -> bool:
    """Return True when at least one assigned role grants permission."""

    if not isinstance(roles, list):
        return False

    return any(
        permission in ROLE_PERMISSIONS.get(role, frozenset())
        for role in roles
    )
