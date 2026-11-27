import pytest

from app.agents.base_agent import AgentContext, AgentStatus
from app.agents.research_agent import ResearchAgent
from app.agents.tool_registry import ToolRegistry
from app.knowledge.schemas import ResearchQuery, ResearchToolResult


@pytest.mark.asyncio
async def test_research_agent_uses_tenant_from_trusted_context():
    registry = ToolRegistry()
    received_org_ids = []

    async def research_handler(
        query: ResearchQuery,
    ) -> ResearchToolResult:
        received_org_ids.append(query.org_id)

        return ResearchToolResult(
            records=[
                {
                    "record_id": "history-1",
                    "record_type": "EXCEPTION",
                    "job_id": "old-job",
                    "summary": "Previous reconciliation exception",
                    "citation": "exceptions/history-1",
                    "details": {},
                }
            ]
        )

    tool_names = ResearchAgent.TOOL_NAMES

    for tool_name in tool_names:
        registry.register_tool(
            name=tool_name,
            input_model=ResearchQuery,
            output_model=ResearchToolResult,
            handler=research_handler,
        )
        registry.grant_tool(
            agent_name="research_agent",
            tool_name=tool_name,
        )

    agent = ResearchAgent(tool_registry=registry)

    context = AgentContext(
        org_id="trusted-org",
        job_id="current-job",
        workflow_run_id="run-1",
        correlation_id="corr-1",
    )

    result = await agent.run(
        payload={"limit": 5},
        context=context,
    )

    assert result.status == AgentStatus.SUCCESS
    assert result.output is not None
    assert result.output.org_id == "trusted-org"
    assert result.output.current_job_id == "current-job"
    assert result.output.retrieved_count == 3
    assert received_org_ids == ["trusted-org"] * 3
    assert len(result.output.citations) == 1


@pytest.mark.asyncio
async def test_research_agent_cannot_use_ungranted_tools():
    registry = ToolRegistry()
    agent = ResearchAgent(tool_registry=registry)

    context = AgentContext(
        org_id="org-1",
        job_id="job-1",
        workflow_run_id="run-1",
        correlation_id="corr-1",
    )

    result = await agent.run(
        payload={},
        context=context,
    )

    assert result.status == AgentStatus.FAILED
    assert result.output is None