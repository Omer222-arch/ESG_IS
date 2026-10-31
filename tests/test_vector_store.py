from __future__ import annotations

from src.vector_store import EsgVectorStore, VectorStoreError


class FakeCollection:
    def __init__(self):
        self.items = {}

    def get(self, ids, include):
        return {"ids": [identifier for identifier in ids if identifier in self.items]}

    def upsert(self, ids, documents, metadatas, embeddings):
        for identifier, document, metadata, embedding in zip(ids, documents, metadatas, embeddings):
            self.items[identifier] = (document, metadata, embedding)

    def query(self, query_embeddings, n_results, include):
        rows = list(self.items.items())[:n_results]
        return {"ids": [[identifier for identifier, _ in rows]], "documents": [[item[0] for _, item in rows]], "metadatas": [[item[1] for _, item in rows]], "distances": [[0.1 for _ in rows]]}


class FakeClient:
    def __init__(self):
        self.collection = FakeCollection()

    def get_or_create_collection(self, name, embedding_function):
        assert embedding_function is None
        return self.collection


def test_chroma_seed_retrieve_metadata_and_restart_are_idempotent(tmp_path):
    client = FakeClient()
    factory = lambda _: client
    first = EsgVectorStore(tmp_path, "esg", client_factory=factory)
    assert first.seed() == 5
    result = first.retrieve("What does SFDR Article 8 require?")
    assert result[0]["metadata"]["standard"] == "SASB" or result[0]["metadata"]["standard"] == "SFDR"
    assert result[0]["id"] and 0 <= result[0]["score"] <= 1
    restarted = EsgVectorStore(tmp_path, "esg", client_factory=factory)
    assert restarted.seed() == 0


def test_chroma_initialization_failure_is_controlled(tmp_path):
    def broken_factory(_):
        raise RuntimeError("broken")
    store = EsgVectorStore(tmp_path, "esg", client_factory=broken_factory)
    try:
        store.initialize()
    except VectorStoreError as exc:
        assert "initialize" in str(exc).lower()
    else:
        raise AssertionError("expected a controlled Chroma initialization error")
