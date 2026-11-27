"""Research Agent using explicitly granted historical retrieval tools."""

from app.agents.base_agent import AgentContext, BaseAgent
from app.agents.research_agent.schemas import (
    HistoricalEvidence,
    ResearchAgentInput,
    ResearchAgentOutput,
)
from app.agents.tool_registry import ToolRegistry


class ResearchAgent(BaseAgent[ResearchAgentInput, ResearchAgentOutput]):
    agent_name = "research_agent"
    input_model = ResearchAgentInput
    output_model = ResearchAgentOutput

    TOOL_NAMES = (
        "research.list_prior_exceptions",
        "research.list_prior_jobs",
        "research.list_rule_history",
    )

    async def execute(
        self,
        input_data: ResearchAgentInput,
        context: AgentContext,
    ) -> ResearchAgentOutput:
        payload = {
            "org_id": context.org_id,
            "current_job_id": context.job_id,
            "exception_id": input_data.exception_id,
            "limit": input_data.limit,
        }

        evidence: list[HistoricalEvidence] = []

        for tool_name in self.TOOL_NAMES:
            result = await self.invoke_tool(
                tool_name=tool_name,
                payload=payload,
            )

            for record in result.records:
                evidence.append(
                    HistoricalEvidence.model_validate(record.model_dump())
                )

        citations = list(dict.fromkeys(
            item.citation for item in evidence
        ))

        return ResearchAgentOutput(
            org_id=context.org_id,
            current_job_id=context.job_id,
            evidence=evidence,
            citations=citations,
            retrieved_count=len(evidence),
        )

    @classmethod
    def create(
        cls,
        tool_registry: ToolRegistry,
        timeout_seconds: float = 30.0,
    ) -> "ResearchAgent":
        return cls(
            tool_registry=tool_registry,
            timeout_seconds=timeout_seconds,
        )