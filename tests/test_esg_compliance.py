from __future__ import annotations

from src.esg_compliance import EsgComplianceAgent
from src.vector_store import EsgVectorStore


class FakeEmbeddingProvider:
    def embed_documents(self, texts):
        return [[1.0, 0.0, 0.0] for _ in texts]


def make_store(tmp_path):
    class FakeCollection:
        def __init__(self):
            self.items = {
                "sfdr-article-8": (
                    "SFDR Article 8 products must document how promoted environmental or social characteristics are monitored.",
                    {
                        "source": "SFDR",
                        "standard": "SFDR",
                    },
                ),
                "eu-taxonomy": (
                    "EU Taxonomy alignment assesses eligible activities using turnover, capital expenditure, and operating expenditure indicators.",
                    {
                        "source": "EU Taxonomy",
                        "standard": "EU Taxonomy",
                    },
                ),
            }

        def query(self, query_embeddings, n_results, include):
            rows = list(self.items.items())[:n_results]

            return {
                "ids": [[item[0] for item in rows]],
                "documents": [[item[1][0] for item in rows]],
                "metadatas": [[item[1][1] for item in rows]],
                "distances": [[0.1 for _ in rows]],
            }

        def get(self, ids, include):
            return {"ids": [item for item in ids if item in self.items]}

        def upsert(self, ids, documents, metadatas, embeddings):
            pass

    collection = FakeCollection()

    class FakeClient:
        def get_or_create_collection(self, name, embedding_function):
            return collection

    store = EsgVectorStore(
        persist_directory=tmp_path,
        collection_name="test",
        embedding_provider=FakeEmbeddingProvider(),
        client_factory=lambda _: FakeClient(),
    )

    return store


def test_esg_agent_retrieves_context(tmp_path):
    store = make_store(tmp_path)

    agent = EsgComplianceAgent(
        vector_store=store,
        top_k=2,
    )

    result = agent.run(
        "What are the requirements of SFDR Article 8?"
    )

    assert result["status"] == "success"
    assert len(result["retrieved_context"]) == 2
    assert result["confidence"] == 0.9
    assert "SFDR" in result["standards_found"]


def test_esg_agent_preserves_source_metadata(tmp_path):
    store = make_store(tmp_path)

    agent = EsgComplianceAgent(vector_store=store)

    result = agent.run("What does SFDR require?")

    assert result["source_metadata"]
    assert result["source_metadata"][0]["standard"] == "SFDR"
    assert result["source_metadata"][0]["document_id"] == "sfdr-article-8"


def test_esg_agent_handles_empty_query(tmp_path):
    store = make_store(tmp_path)

    agent = EsgComplianceAgent(vector_store=store)

    result = agent.run("   ")

    assert result["status"] == "empty"
    assert result["confidence"] == 0.0
    assert result["retrieved_context"] == []


def test_esg_agent_low_confidence(tmp_path):
    class LowScoreStore:
        def retrieve(self, query, limit):
            return [
                {
                    "id": "unknown",
                    "text": "Some ESG context.",
                    "metadata": {
                        "source": "Test",
                        "standard": "Test",
                    },
                    "score": 0.2,
                }
            ]

    agent = EsgComplianceAgent(
        vector_store=LowScoreStore(),
        confidence_threshold=0.5,
    )

    result = agent.run("Some ESG question")

    assert result["status"] == "low_confidence"
    assert result["confidence"] == 0.2