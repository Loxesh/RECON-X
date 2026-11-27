"""Registration of tenant-scoped research tools."""

from pymongo.database import Database

from app.agents.tool_registry import ToolRegistry
from app.knowledge.research_service import ResearchKnowledgeService
from app.knowledge.schemas import ResearchQuery, ResearchToolResult


def register_research_tools(
    *,
    database: Database,
    registry: ToolRegistry,
) -> None:
    """Register and explicitly grant Research Agent capabilities."""

    service = ResearchKnowledgeService(database)

    async def prior_exceptions(
        query: ResearchQuery,
    ) -> ResearchToolResult:
        return await service.list_prior_exceptions(query)

    async def prior_jobs(
        query: ResearchQuery,
    ) -> ResearchToolResult:
        return await service.list_prior_jobs(query)

    async def rule_history(
        query: ResearchQuery,
    ) -> ResearchToolResult:
        return await service.list_rule_history(query)

    tools = (
        ("research.list_prior_exceptions", prior_exceptions),
        ("research.list_prior_jobs", prior_jobs),
        ("research.list_rule_history", rule_history),
    )

    for name, handler in tools:
        registry.register_tool(
            name=name,
            input_model=ResearchQuery,
            output_model=ResearchToolResult,
            handler=handler,
            timeout_seconds=10.0,
        )
        registry.grant_tool(
            agent_name="research_agent",
            tool_name=name,
        )