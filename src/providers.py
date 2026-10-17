"""Model providers for the HR Policy and Leave Assistant."""
from __future__ import annotations
import time
import hashlib
import json
import re
from typing import Any, Protocol
from uuid import uuid4

from .contracts import ModelToolCall, ModelTurn


class ModelProvider(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...

    def respond(
        self,
        *,
        input_data: str | list[Any],
        instructions: str,
        tools: list[dict[str, Any]],
        safety_identifier: str,
        max_output_tokens: int,
    ) -> ModelTurn: ...


class OpenAIProvider:
    """OpenAI Responses API untuk LLM dan OpenAI Embeddings."""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-6-luna",
        embedding_model: str = "text-embedding-3-small",
        embedding_dimensions: int = 1536,
    ) -> None:
        from openai import OpenAI

        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.embedding_model = embedding_model
        self.embedding_dimensions = embedding_dimensions

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        response = self.client.embeddings.create(
            model=self.embedding_model,
            input=texts,
            dimensions=self.embedding_dimensions,
        )

        return [
            item.embedding
            for item in sorted(response.data, key=lambda item: item.index)
        ]
    
    def respond(
        self,
        *,
        input_data: str | list[Any],
        instructions: str,
        tools: list[dict[str, Any]],
        safety_identifier: str,
        max_output_tokens: int,
    ) -> ModelTurn:
        response = self.client.responses.create(
            model=self.model,
            instructions=instructions,
            input=input_data,
            tools=tools,
            max_output_tokens=max_output_tokens,
            safety_identifier=safety_identifier,
        )

        tool_calls = []

        for item in response.output:
            if item.type == "function_call":
                tool_calls.append(
                    ModelToolCall(
                        call_id=item.call_id,
                        name=item.name,
                        arguments=json.loads(item.arguments or "{}"),
                    )
                )

        usage = response.usage

        return ModelTurn(
            response_id=response.id,
            text=response.output_text or "",
            tool_calls=tool_calls,
            output_items=[
                {
                    "type": "function_call",
                    "call_id": item.call_id,
                    "name": item.name,
                    "arguments": item.arguments,
                }
                for item in response.output
                if item.type == "function_call"
            ],
            input_tokens=usage.input_tokens if usage else 0,
            output_tokens=usage.output_tokens if usage else 0,
        )
    
class DeterministicProvider:
    """Provider simulasi untuk pengujian lokal tanpa jaringan."""

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors = []
        for text in texts:
            vector = [0.0] * 8
            for word in re.findall(r"\w+", text.lower()):
                digest = hashlib.sha256(word.encode("utf-8")).digest()
                vector[digest[0] % 8] += 1.0

            magnitude = sum(value**2 for value in vector) ** 0.5
            if magnitude > 0:
                vector = [value / magnitude for value in vector]
            vectors.append(vector)
        return vectors

    def respond(self, **kwargs: Any) -> ModelTurn:
        input_data = kwargs.get("input_data", "")
        messages = [input_data] if isinstance(input_data, str) else input_data

        user_text = ""
        for item in messages:
            if isinstance(item, str):
                user_text = item
            elif isinstance(item, dict) and item.get("role") == "user":
                content = item.get("content", "")
                if isinstance(content, str):
                    user_text = content

        user_lower = user_text.lower()
        tool_outputs = [
            item
            for item in messages
            if isinstance(item, dict)
            and item.get("type") == "function_call_output"
        ]

        if tool_outputs:
            output = tool_outputs[-1].get("output", "")
            if not isinstance(output, str):
                output = json.dumps(output, ensure_ascii=False, default=str)

            try:
                parsed = json.loads(output)
            except (json.JSONDecodeError, TypeError):
                parsed = {}

            documents = parsed.get("documents", []) if isinstance(parsed, dict) else []
            if isinstance(documents, list) and documents:
                first_doc = documents[0]
                answer = (
                    f"Berdasarkan kebijakan HR: {first_doc['content']} "
                    f"[{first_doc['document_id']}]"
                )
            elif isinstance(parsed, dict) and "balances" in parsed:
                answer = "Saldo cuti Anda: " + json.dumps(
                    parsed["balances"], ensure_ascii=False, default=str
                )
            else:
                answer = "Informasi kebijakan HR tidak ditemukan dalam dokumen yang tersedia."

            return ModelTurn(
                response_id="deterministic-final",
                text=answer,
                tool_calls=[],
                output_items=[],
                input_tokens=0,
                output_tokens=0,
            )

        if any(
            phrase in user_lower
            for phrase in (
                "saldo cuti saya",
                "sisa cuti saya",
                "leave balance",
                "my balance",
            )
        ):
            tool_name = "get_my_leave_balance"
            arguments = {}
        elif any(
            phrase in user_lower
            for phrase in ("ajukan cuti", "mengajukan cuti", "request leave")
        ):
            return ModelTurn(
                response_id="deterministic-clarify",
                text=(
                    "Untuk menyiapkan pengajuan cuti, mohon berikan tanggal mulai, "
                    "tanggal selesai, jenis cuti, dan alasan."
                ),
            )
        else:
            tool_name = "search_hr_policy"
            arguments = {"query": user_text, "top_k": 3}

        call = ModelToolCall(
            call_id="deterministic-call-001",
            name=tool_name,
            arguments=arguments,
        )
        return ModelTurn(
            response_id="deterministic-tool-call",
            text="",
            tool_calls=[call],
            output_items=[],
            input_tokens=0,
            output_tokens=0,
        )

