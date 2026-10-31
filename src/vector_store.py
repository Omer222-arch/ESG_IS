"""Persistent Chroma storage for the local ESG standards knowledge base."""
from __future__ import annotations
import hashlib
import math
import re
from pathlib import Path
from typing import Any, Callable, Protocol
from src.config import Settings, settings

SEED_DOCUMENTS = [("sasb-ghg", "SASB", "SASB TC-ES-110a.1 requires Scope 1 GHG emissions disclosure in metric tons CO2e with year-over-year trend."), ("sasb-materiality", "SASB", "SASB materiality is sector-specific. Industrial companies should disclose energy intensity per unit output."), ("iss-governance", "ISS", "ISS Governance QualityScore considers board independence in portfolio stewardship reviews."), ("sfdr-article-8", "SFDR", "SFDR Article 8 products must document how promoted environmental or social characteristics are monitored."), ("eu-taxonomy", "EU Taxonomy", "EU Taxonomy alignment assesses eligible activities using turnover, capital expenditure, and operating expenditure indicators.")]

class VectorStoreError(RuntimeError): pass
class EmbeddingProvider(Protocol):
    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

class DeterministicEmbeddings:
    dimensions = 64
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        vectors = []
        for text in texts:
            vector = [0.0] * self.dimensions
            for token in re.findall(r"[a-z0-9]+", text.lower()): vector[int(hashlib.sha256(token.encode()).hexdigest(), 16) % self.dimensions] += 1.0
            norm = math.sqrt(sum(value * value for value in vector)) or 1.0
            vectors.append([value / norm for value in vector])
        return vectors

class OpenAIEmbeddingsProvider:
    def __init__(self, config: Settings) -> None: self.config = config
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        try:
            from langchain_openai import OpenAIEmbeddings
            return OpenAIEmbeddings(model=self.config.openai_embedding_model, api_key=self.config.openai_api_key).embed_documents(texts)
        except Exception as exc: raise VectorStoreError("OpenAI embeddings are unavailable.") from exc

def _client_factory(path: Path) -> Any:
    try:
        import chromadb
        return chromadb.PersistentClient(path=str(path))
    except Exception as exc: raise VectorStoreError("Chroma is unavailable; install compatible chromadb dependencies.") from exc

class EsgVectorStore:
    def __init__(self, persist_directory: Path, collection_name: str, config: Settings = settings, embedding_provider: EmbeddingProvider | None = None, client_factory: Callable[[Path], Any] | None = None) -> None:
        self.persist_directory, self.collection_name = persist_directory, collection_name
        self.embedding_provider = (
            embedding_provider or DeterministicEmbeddings()
        )
        self._client_factory, self._collection = client_factory or _client_factory, None
    def initialize(self) -> None:
        try:
            self.persist_directory.mkdir(parents=True, exist_ok=True)
            self._collection = self._client_factory(self.persist_directory).get_or_create_collection(name=self.collection_name, embedding_function=None)
        except VectorStoreError: raise
        except Exception as exc: raise VectorStoreError("Unable to initialize the ESG Chroma collection.") from exc
    @property
    def collection(self) -> Any:
        if self._collection is None: self.initialize()
        return self._collection
    def add_documents(self, documents: list[dict[str, Any]]) -> int:
        if not documents: return 0
        try:
            ids = [item["id"] for item in documents]; existing = set(self.collection.get(ids=ids, include=[]).get("ids", [])); new = [item for item in documents if item["id"] not in existing]
            if not new: return 0
            texts = [item["text"] for item in new]
            self.collection.upsert(ids=[item["id"] for item in new], documents=texts, metadatas=[item["metadata"] for item in new], embeddings=self.embedding_provider.embed_documents(texts))
            return len(new)
        except VectorStoreError: raise
        except Exception as exc: raise VectorStoreError("Unable to persist ESG documents.") from exc
    def seed(self) -> int:
        return self.add_documents([{"id": ident, "text": text, "metadata": {"source": standard, "standard": standard}} for ident, standard, text in SEED_DOCUMENTS])
    def retrieve(self, query: str, limit: int = 4) -> list[dict[str, Any]]:
        if not query.strip(): return []
        try:
            result = self.collection.query(query_embeddings=self.embedding_provider.embed_documents([query]), n_results=limit, include=["documents", "metadatas", "distances"])
            docs, metadata, ids, distances = result.get("documents", [[]])[0] or [], result.get("metadatas", [[]])[0] or [], result.get("ids", [[]])[0] or [], result.get("distances", [[]])[0] or []
            return [{"id": ident, "text": text, "metadata": meta, "score": round(max(0.0, min(1.0, 1 - float(distance))), 3)} for ident, text, meta, distance in zip(ids, docs, metadata, distances)]
        except VectorStoreError: raise
        except Exception as exc: raise VectorStoreError("Unable to retrieve ESG context.") from exc
