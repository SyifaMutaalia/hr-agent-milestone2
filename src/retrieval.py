"""Hybrid retrieval service for HR policy documents."""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from .contracts import PolicyChunk


class RetrievalService:
    def __init__(
        self,
        repository,
        provider,
        cache,
        index_version: str | int,
    ) -> None:
        self.repository = repository
        self.provider = provider
        self.cache = cache
        self.index_version = str(index_version)

    def _cache_key(self, query: str, top_k: int) -> str:
        normalized = " ".join(query.lower().split())

        digest = hashlib.sha256(
            normalized.encode("utf-8")
        ).hexdigest()

        return (
            f"retrieval:{self.index_version}:"
            f"{top_k}:{digest}"
        )

    @staticmethod
    def _tokens(value: str) -> set[str]:
        return {
            token
            for token in re.findall(r"[a-zA-Z0-9]+", value.lower())
            if len(token) >= 2
        }

    @staticmethod
    def _chunk_key(chunk: PolicyChunk) -> str:
        return (
            f"{chunk.document_id}|"
            f"{chunk.section}|"
            f"{chunk.content}"
        )

    def _keyword_score(
        self,
        query: str,
        chunk: PolicyChunk,
    ) -> float:
        query_tokens = self._tokens(query)

        if not query_tokens:
            return 0.0

        searchable = " ".join(
            [
                chunk.document_id,
                chunk.title,
                chunk.section,
                chunk.content,
            ]
        )

        document_tokens = self._tokens(searchable)

        matches = len(query_tokens & document_tokens)

        return matches / len(query_tokens)

    def _rrf(
        self,
        lexical: list[PolicyChunk],
        vector: list[PolicyChunk],
        k: int = 60,
    ) -> dict[str, float]:
        scores: dict[str, float] = {}

        for ranking in (lexical, vector):
            for rank, chunk in enumerate(ranking, start=1):
                key = self._chunk_key(chunk)

                scores[key] = (
                    scores.get(key, 0.0)
                    + 1.0 / (k + rank)
                )

        return scores

    def search(
        self,
        query: str,
        top_k: int = 3,
    ) -> list[PolicyChunk]:
        query = query.strip()

        if not query:
            return []

        top_k = max(1, min(top_k, 10))
        cache_key = self._cache_key(query, top_k)

        
        try:
            cached = self.cache.get(cache_key)

            if cached:
                if isinstance(cached, str):
                    cached = json.loads(cached)

                return [
                    PolicyChunk.model_validate(item)
                    for item in cached
                ]
        except Exception:
            pass

    
        candidate_limit = max(top_k * 4, 8)

        lexical = self.repository.lexical_search(
            query,
            candidate_limit,
        )

        try:
            embeddings = self.provider.embed([query])

            query_embedding = (
                embeddings[0]
                if embeddings
                else []
            )
        except Exception:
            
            query_embedding = []

        vector: list[PolicyChunk] = []

        if query_embedding:
            try:
                vector = self.repository.vector_search(
                    query_embedding,
                    candidate_limit,
                )
            except Exception:
                vector = []

        rrf_scores = self._rrf(
            lexical=lexical,
            vector=vector,
        )

        candidates: dict[str, PolicyChunk] = {}

        for chunk in lexical + vector:
            candidates[self._chunk_key(chunk)] = chunk

        ranked: list[tuple[float, PolicyChunk]] = []

        for key, chunk in candidates.items():
            fusion_score = rrf_scores.get(key, 0.0)
            keyword_score = self._keyword_score(
                query,
                chunk,
            )

            final_score = fusion_score + keyword_score

            ranked.append(
                (
                    final_score,
                    chunk.model_copy(
                        update={"score": final_score}
                    ),
                )
            )

        ranked.sort(
            key=lambda item: item[0],
            reverse=True,
        )

        results = [
            chunk
            for _, chunk in ranked[:top_k]
        ]

        try:
            payload: list[dict[str, Any]] = [
                item.model_dump(mode="json")
                for item in results
            ]

            self.cache.set(cache_key, payload)
        except Exception:
            pass

        return results