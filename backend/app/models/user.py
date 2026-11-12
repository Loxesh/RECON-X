
from datetime import datetime
from typing import Any

from pydantic import EmailStr, Field

from app.models.base import TenantDocument


class UserDocument(TenantDocument):
    email: EmailStr
    password_hash: str | None = None
    roles: list[str] = Field(default_factory=list)
    status: str = "ACTIVE"
    external_subject: str | None = None
    last_login: datetime | None = None
