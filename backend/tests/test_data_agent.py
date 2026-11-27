from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.agents.base_agent import AgentContext, AgentStatus
from app.agents.data_agent import DataAgent
from app.agents.tool_registry import ToolRegistry


@pytest.mark.asyncio
async def test_data_agent_detects_canonical_quality_issues():
    agent = DataAgent(tool_registry=ToolRegistry())

    transaction_id = "507f1f77bcf86cd799439011"

    context = AgentContext(
        org_id="org-1",
        job_id="job-1",
        workflow_run_id="run-1",
        correlation_id="corr-1",
    )

    payload = {
        "records": [
            {
                "id": transaction_id,
                "org_id": "org-1",
                "job_id": "job-1",
                "file_id": "file-1",
                "source_type": "BANK",
                "source_row": 1,
                "txn_ref": None,
                "reference_norm": None,
                "txn_date": datetime.now(timezone.utc),
                "amount": Decimal("100.00"),
                "currency": "INR",
                "direction": "CREDIT",
                "description_raw": None,
                "description_norm": None,
                "fingerprint": "fingerprint-1",
                "validity": "INVALID",
                "validation_errors": [{"code": "INVALID_ROW"}],
                "raw_row": {},
                "flags": [],
            }
        ]
    }

    result = await agent.run(payload=payload, context=context)

    assert result.status == AgentStatus.SUCCESS
    assert result.output is not None
    assert result.output.inspected_count == 1
    assert result.output.finding_count >= 4

    codes = {finding.code for finding in result.output.findings}

    assert "INVALID_TRANSACTION" in codes
    assert "VALIDATION_ERRORS_PRESENT" in codes
    assert "MISSING_REFERENCE" in codes
    assert "MISSING_NORMALISED_DESCRIPTION" in codes

    assert transaction_id in result.output.evidence_ids