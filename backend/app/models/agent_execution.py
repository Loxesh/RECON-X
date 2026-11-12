
from pydantic import Field

from app.models.base import TenantDocument


class AgentExecutionDocument(TenantDocument):
    job_id: str = Field(min_length=1)
    workflow_run_id: str = Field(min_length=1)

    agent_name: str = Field(min_length=1)
    step: str = Field(min_length=1)
    attempt: int = Field(default=1, ge=1)

    status: str = "PENDING"
    input_hash: str = Field(min_length=1)

    output_summary_redacted: str | None = None
    duration_ms: int | None = Field(default=None, ge=0)
    error_code: str | None = None
