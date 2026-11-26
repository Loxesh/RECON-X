
from decimal import Decimal

from app.llm.schemas import LLMResponse, LLMUsageContext
from app.llm.usage import LLMUsageRecorder


class FakeInsertResult:
    inserted_id = "fake-id"


class FakeCollection:
    def __init__(self):
        self.documents = []

    def insert_one(self, document):
        self.documents.append(document)
        return FakeInsertResult()


def test_usage_recorder_persists_tenant_scoped_usage():
    collection = FakeCollection()
    recorder = LLMUsageRecorder(collection)

    context = LLMUsageContext(
        org_id="ORG_TEST",
        job_id="JOB_TEST",
        agent_name="investigation_agent",
        task="investigation",
        tier="standard",
        correlation_id="CORR_TEST",
        estimated_cost=Decimal("0.025"),
        price_version="test-price-v1",
    )

    response = LLMResponse(
        content="Synthetic result",
        provider="mock",
        model="mock-v1",
        input_tokens=12,
        output_tokens=8,
        latency_ms=15,
    )

    recorder.record(context, response)

    assert len(collection.documents) == 1

    document = collection.documents[0]

    assert document["org_id"] == "ORG_TEST"
    assert document["job_id"] == "JOB_TEST"
    assert document["provider"] == "mock"
    assert document["input_tokens"] == 12
    assert document["output_tokens"] == 8
    assert document["price_version"] == "test-price-v1"
    assert document["status"] == "SUCCESS"
