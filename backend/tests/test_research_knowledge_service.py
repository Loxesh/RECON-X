
import asyncio
from bson import ObjectId

from app.knowledge.research_service import ResearchKnowledgeService
from app.knowledge.schemas import ResearchQuery


class FakeCursor:
    def sort(self, *_args, **_kwargs):
        return self

    def skip(self, *_args, **_kwargs):
        return self

    def limit(self, *_args, **_kwargs):
        return self

    def __iter__(self):
        return iter([])


class FakeCollection:
    def __init__(self):
        self.queries = []

    def find(self, query):
        self.queries.append(query)
        return FakeCursor()


class FakeDatabase:
    def __init__(self):
        self.collections = {}

    def __getitem__(self, name):
        if name not in self.collections:
            self.collections[name] = FakeCollection()
        return self.collections[name]


def make_query():
    return ResearchQuery(
        org_id="trusted-org",
        current_job_id=str(ObjectId()),
        limit=10,
    )


def assert_tenant_filter(query):
    assert query["$and"][0] == {"org_id": "trusted-org"}


def test_prior_exceptions_are_tenant_scoped():
    database = FakeDatabase()
    service = ResearchKnowledgeService(database)

    asyncio.run(service.list_prior_exceptions(make_query()))

    query = database["exceptions"].queries[0]

    assert_tenant_filter(query)
    assert query["$and"][1]["job_id"]["$ne"]


def test_prior_jobs_are_tenant_scoped_and_exclude_current_job():
    database = FakeDatabase()
    service = ResearchKnowledgeService(database)

    request = make_query()
    asyncio.run(service.list_prior_jobs(request))

    query = database["reconciliation_jobs"].queries[0]

    assert_tenant_filter(query)
    assert query["$and"][1]["_id"]["$ne"] == ObjectId(
        request.current_job_id
    )


def test_rule_history_is_tenant_scoped_and_excludes_current_job():
    database = FakeDatabase()
    service = ResearchKnowledgeService(database)

    request = make_query()
    asyncio.run(service.list_rule_history(request))

    query = database["reconciliation_jobs"].queries[0]

    assert_tenant_filter(query)
    assert query["$and"][1]["_id"]["$ne"] == ObjectId(
        request.current_job_id
    )
