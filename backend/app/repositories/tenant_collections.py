
"""Collection-specific repositories for tenant-owned documents."""

from pymongo.database import Database

from app.repositories.base import BaseRepository


class UserRepository(BaseRepository):
    def __init__(self, database: Database, org_id: str):
        super().__init__(database["users"], org_id)


class UploadedFileRepository(BaseRepository):
    def __init__(self, database: Database, org_id: str):
        super().__init__(database["uploaded_files"], org_id)


class IngestionJobRepository(BaseRepository):
    def __init__(self, database: Database, org_id: str):
        super().__init__(database["ingestion_jobs"], org_id)


class TransactionRepository(BaseRepository):
    def __init__(self, database: Database, org_id: str):
        super().__init__(database["transactions"], org_id)


class ReconciliationJobRepository(BaseRepository):
    def __init__(self, database: Database, org_id: str):
        super().__init__(database["reconciliation_jobs"], org_id)


class MatchResultRepository(BaseRepository):
    def __init__(self, database: Database, org_id: str):
        super().__init__(database["match_results"], org_id)


class ExceptionRepository(BaseRepository):
    def __init__(self, database: Database, org_id: str):
        super().__init__(database["exceptions"], org_id)


class InvestigationRepository(BaseRepository):
    def __init__(self, database: Database, org_id: str):
        super().__init__(database["investigations"], org_id)


class AgentExecutionRepository(BaseRepository):
    def __init__(self, database: Database, org_id: str):
        super().__init__(database["agent_executions"], org_id)


class WorkflowRunRepository(BaseRepository):
    def __init__(self, database: Database, org_id: str):
        super().__init__(database["workflow_runs"], org_id)


class ApprovalRepository(BaseRepository):
    def __init__(self, database: Database, org_id: str):
        super().__init__(database["approvals"], org_id)


class ReportRepository(BaseRepository):
    def __init__(self, database: Database, org_id: str):
        super().__init__(database["reports"], org_id)


class LLMUsageRepository(BaseRepository):
    def __init__(self, database: Database, org_id: str):
        super().__init__(database["llm_usage"], org_id)
