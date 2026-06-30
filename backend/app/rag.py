from __future__ import annotations

import hashlib
import logging
from pathlib import Path

import chromadb
import numpy as np

logger = logging.getLogger(__name__)


class RunbookRag:
    def __init__(self, host: str, port: int, runbook_path: str) -> None:
        self.host = host
        self.port = port
        self.runbook_path = Path(runbook_path)
        self.collection_name = "vyomm_runbooks"
        self.collection = None

    def startup(self) -> None:
        try:
            client = chromadb.HttpClient(host=self.host, port=self.port)
            self.collection = client.get_or_create_collection(self.collection_name)
            docs = []
            ids = []
            metas = []
            embeddings = []
            for path in sorted(self.runbook_path.glob("*.md")):
                text = path.read_text(encoding="utf-8")
                docs.append(text)
                ids.append(path.stem)
                metas.append({"source": path.name, "title": path.stem.replace("_", " ").title()})
                embeddings.append(_embed(text))
            if docs:
                self.collection.upsert(ids=ids, documents=docs, metadatas=metas, embeddings=embeddings)
                logger.info("Embedded %s runbooks into ChromaDB", len(docs))
        except Exception:
            logger.exception("ChromaDB unavailable; local runbook fallback will be used")
            self.collection = None

    def retrieve(self, query: str, limit: int = 2) -> list[dict[str, str]]:
        if self.collection:
            try:
                result = self.collection.query(query_embeddings=[_embed(query)], n_results=limit)
                docs = result.get("documents", [[]])[0]
                metas = result.get("metadatas", [[]])[0]
                return [
                    {"title": meta.get("title", "Runbook"), "source": meta.get("source", ""), "content": doc}
                    for doc, meta in zip(docs, metas, strict=False)
                ]
            except Exception:
                logger.exception("Runbook query failed; falling back to local scan")
        return self._local_scan(query, limit)

    def _local_scan(self, query: str, limit: int) -> list[dict[str, str]]:
        terms = set(query.lower().replace("_", " ").split())
        ranked = []
        for path in sorted(self.runbook_path.glob("*.md")):
            text = path.read_text(encoding="utf-8")
            score = sum(1 for term in terms if term in text.lower() or term in path.stem)
            ranked.append((score, path, text))
        ranked.sort(reverse=True, key=lambda item: item[0])
        return [
            {"title": path.stem.replace("_", " ").title(), "source": path.name, "content": text}
            for _, path, text in ranked[:limit]
        ]


def _embed(text: str, dimensions: int = 384) -> list[float]:
    vector = np.zeros(dimensions, dtype=np.float32)
    for token in text.lower().split():
        digest = hashlib.sha256(token.encode()).digest()
        idx = int.from_bytes(digest[:4], "little") % dimensions
        vector[idx] += 1.0
    norm = np.linalg.norm(vector)
    if norm > 0:
        vector = vector / norm
    return vector.tolist()
