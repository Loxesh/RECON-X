
from pymongo.collection import Collection

from app.llm.schemas import LLMResponse, LLMUsageContext
from app.models.bson import model_to_bson_document
from app.models.llm_usage import LLMUsageDocument


class LLMUsageRecorder:
    """Persist validated LLM usage in the existing tenant-owned collection."""

    def __init__(self, collection: Collection) -> None:
        self.collection = collection

    def record(
        self,
        context: LLMUsageContext,
        response: LLMResponse,
    ) -> None:
        document = LLMUsageDocument(
            org_id=context.org_id,
            job_id=context.job_id,
            agent_name=context.agent_name,
            task=context.task,
            provider=response.provider,
            model=response.model,
            tier=context.tier,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            est_cost=context.estimated_cost,
            currency=context.currency,
            price_version=context.price_version,
            latency_ms=response.latency_ms,
            status="SUCCESS",
            correlation_id=context.correlation_id,
        )

        self.collection.insert_one(
            model_to_bson_document(document)
        )
