"""LangChain adapter for the existing HR Agent."""

from __future__ import annotations

import json
from typing import Any
import time
from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)


def convert_to_langchain_messages(
    input_data: str | list[Any],
    instructions: str,
) -> list[Any]:
    messages: list[Any] = [SystemMessage(content=instructions)]

    if isinstance(input_data, str):
        return messages + [HumanMessage(content=input_data)]

    for item in input_data:
        if not isinstance(item, dict):
            continue

        if item.get("role") == "user":
            messages.append(
                HumanMessage(content=item.get("content", ""))
            )

        elif item.get("role") == "assistant":
            messages.append(
                AIMessage(content=item.get("content", ""))
            )

        elif item.get("type") == "function_call":
            arguments = item.get("arguments", "{}")
            if isinstance(arguments, str):
                arguments = json.loads(arguments)

            messages.append(
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "id": item["call_id"],
                            "name": item["name"],
                            "args": arguments,
                        }
                    ],
                )
            )

        elif item.get("type") == "function_call_output":
            messages.append(
                ToolMessage(
                    content=item.get("output", ""),
                    tool_call_id=item["call_id"],
                )
            )

    return messages

from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from .contracts import ModelTurn, ModelToolCall


class LangChainProvider:
    """Provider LangChain untuk HR Agent."""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-6-luna",
        embedding_model: str = "text-embedding-3-small",
        embedding_dimensions: int = 1536,
    ) -> None:
        self.llm = ChatOpenAI(
            model=model,
            api_key=api_key,
        )

        self.embeddings = OpenAIEmbeddings(
            model=embedding_model,
            api_key=api_key,
            dimensions=embedding_dimensions,
        )

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        return self.embeddings.embed_documents(texts)
    def respond(
        self,
        *,
        input_data: str | list[Any],
        instructions: str,
        tools: list[dict[str, Any]],
        safety_identifier: str,
        max_output_tokens: int,
    ) -> ModelTurn:
        messages = convert_to_langchain_messages(
            input_data,
            instructions,
        )

        # Ubah format tools OpenAI Responses API
        # menjadi format yang diterima LangChain.
        langchain_tools = [
            {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["parameters"],
                },
            }
            for tool in tools
        ]

        llm = (
            self.llm.bind_tools(langchain_tools)
            if langchain_tools
            else self.llm
        )

        start_time = time.perf_counter()

        response = llm.invoke(
            messages,
            max_tokens=max_output_tokens,
        )

        elapsed = time.perf_counter() - start_time

        print(
            "[LLM TIMING]",
            f"duration={elapsed:.2f}s",
            flush=True,
        )

        print(
            "[TOOL CALL DEBUG]",
            f"tool_names={[call['name'] for call in response.tool_calls]}",
            flush=True,
        )
        print(
            "[LANGCHAIN DIAGNOSTIC]",
            f"content_type={type(response.content).__name__}",
            f"content_empty={not bool(response.content)}",
            f"tool_calls={len(response.tool_calls)}",
            f"finish_reason={response.response_metadata.get('finish_reason')}",
            f"usage={response.usage_metadata}",
            flush=True,
        )
        tool_calls = [
            ModelToolCall(
                call_id=call["id"],
                name=call["name"],
                arguments=call["args"],
            )
            for call in response.tool_calls
        ]

        output_items = [
            {
                "type": "function_call",
                "call_id": call.call_id,
                "name": call.name,
                "arguments": json.dumps(call.arguments),
            }
            for call in tool_calls
        ]

        usage = response.usage_metadata or {}

        return ModelTurn(
            response_id=response.id or "",
            text=(
                response.content
                if isinstance(response.content, str)
                else "\n".join(
                    block.get("text", "")
                    for block in response.content
                    if isinstance(block, dict)
                    and block.get("type") == "text"
                    and isinstance(block.get("text"), str)
                )
            ),
            tool_calls=tool_calls,
            output_items=output_items,
            input_tokens=usage.get("input_tokens", 0),
            output_tokens=usage.get("output_tokens", 0),
        )