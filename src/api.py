from __future__ import annotations

from typing import Literal
from .demo_reset import demo_reset_router
from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel

from .config import Settings, get_settings
from .contracts import AuthContext, ChatRequest, ConfirmActionRequest
from .repository import ConflictError

class HRDecisionRequest(BaseModel):
    decision: Literal["approved", "rejected"]
def build_runtime(settings: Settings):
    from .agent import AgentService
    from .cache import NullCache
    from .providers import OpenAIProvider, DeterministicProvider
    from .langchain_provider import LangChainProvider
    from .repository import PostgresRepository
    from .retrieval import RetrievalService
    from .tools import ToolExecutor

    if not settings.database_url:
        raise RuntimeError("DATABASE_URL belum dikonfigurasi.")

    repository = PostgresRepository(
        database_url=settings.database_url,
        embedding_dimensions=settings.embedding_dimensions,
    )

    if settings.model_mode == "fake":
        provider = DeterministicProvider()
    else:
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY belum dikonfigurasi.")

        if not settings.pinecone_api_key:
            raise RuntimeError("PINECONE_API_KEY belum dikonfigurasi.")

        ProviderClass = (
    LangChainProvider
    if settings.llm_provider == "langchain"
    else OpenAIProvider
)

    provider = ProviderClass(
    api_key=settings.openai_api_key,
    model=settings.openai_model,
    embedding_model=settings.embedding_model,
    embedding_dimensions=settings.embedding_dimensions,
)

    cache = NullCache()

    retrieval = RetrievalService(
        repository=repository,
        provider=provider,
        cache=cache,
        index_version=settings.policy_index_version,
    )

    tools = ToolExecutor(
        repository=repository,
        retrieval=retrieval,
        settings=settings,
    )

    agent = AgentService(
        repository=repository,
        provider=provider,
        tools=tools,
        settings=settings,
    )

    return repository, cache, agent


def create_app(
    *,
    settings: Settings | None = None,
    repository=None,
    cache=None,
    agent=None,
) -> FastAPI:
    app = FastAPI(
        title="HR Policy and Leave Assistant",
        version="1.0.0",
    )

    if repository is None or agent is None:
        raise RuntimeError(
            "Repository and AgentService must be initialized"
        )

    def get_current_user(
        authorization: str | None = Header(default=None),
    ) -> AuthContext:
        if not authorization:
            raise HTTPException(
                status_code=401,
                detail="Authentication required",
            )

        scheme, separator, token = authorization.partition(" ")

        if (
            not separator
            or scheme.lower() != "bearer"
            or not token.strip()
        ):
            raise HTTPException(
                status_code=401,
                detail="Invalid authorization header",
            )

        user = repository.authenticate(token.strip())

        if user is None:
            raise HTTPException(
                status_code=401,
                detail="Invalid authentication token",
            )

        return user

    @app.get("/healthz")
    def healthz():
        return {"status": "ok"}

    @app.post("/api/v1/chat")
    def chat(
        request: ChatRequest,
        user: AuthContext = Depends(get_current_user),
    ):
        response = agent.run(request, user)
        return response.model_dump(mode="json")
    @app.delete("/api/v1/conversations")
    def delete_all_conversations(
        user: AuthContext = Depends(get_current_user),
    ):
        if user.role != "employee":
            raise HTTPException(
                status_code=403,
                detail="Employee access required",
            )

        deleted_count = repository.delete_all_chat_history(
            employee_id=user.employee_id,
        )

        return {
            "status": "deleted",
            "deleted_messages": deleted_count,
        }

    @app.delete("/api/v1/conversations/{conversation_id}")
    def delete_conversation(
        conversation_id: str,
        user: AuthContext = Depends(get_current_user),
    ):
        if user.role != "employee":
            raise HTTPException(
                status_code=403,
                detail="Employee access required",
            )

        deleted_count = repository.delete_chat_history(
            employee_id=user.employee_id,
            conversation_id=conversation_id,
        )

        return {
            "status": "deleted",
            "conversation_id": conversation_id,
            "deleted_messages": deleted_count,
        }
    @app.get("/api/v1/traces/{trace_id}")
    def get_trace(
        trace_id: str,
        user: AuthContext = Depends(get_current_user),
    ):
        trace = repository.get_trace(trace_id)

        if trace is None:
            raise HTTPException(
                status_code=404,
                detail="Trace not found",
            )

        if (
            user.role != "monitoring_admin"
            and trace.get("employee_id") != user.employee_id
        ):
            raise HTTPException(
                status_code=403,
                detail="Access denied",
            )

        # Jangan mengembalikan pesan atau prompt mentah.
        return {
            key: value
            for key, value in trace.items()
            if key in {
                "trace_id",
                "employee_id",
                "outcome",
                "tool_calls",
                "usage",
                "latency_ms",
                "error",
            }
        }

    @app.get("/api/v1/monitoring/summary")
    def monitoring_summary(
        user: AuthContext = Depends(get_current_user),
    ):
        if user.role != "monitoring_admin":
            raise HTTPException(
                status_code=403,
                detail="Admin access required",
            )

        return repository.monitoring_summary()

    @app.get("/api/v1/monitoring/alerts")
    def monitoring_alerts(
        user: AuthContext = Depends(get_current_user),
    ):
        if user.role != "monitoring_admin":
            raise HTTPException(
                status_code=403,
                detail="Admin access required",
            )

        summary = repository.monitoring_summary()
        alerts = []

        if summary["run_count"] > 0:
            if summary["error_rate"] >= 0.20:
                alerts.append({
                    "type": "high_error_rate",
                    "severity": "warning",
                    "message": "Error rate AI Agent mencapai 20% atau lebih.",
                    "value": summary["error_rate"],
                })

            if summary["p95_latency_ms"] >= 30000:
                alerts.append({
                    "type": "high_latency",
                    "severity": "warning",
                    "message": "p95 latency mencapai 30 detik atau lebih.",
                    "value": summary["p95_latency_ms"],
                })

        return {
            "alert_count": len(alerts),
            "alerts": alerts,
        }

    @app.get("/api/v1/leave-requests/me")
    def my_leave_requests(
        user: AuthContext = Depends(get_current_user),
    ):
        if user.role != "employee":
            raise HTTPException(
                status_code=403,
                detail="Employee access required",
            )

        requests = repository.list_leave_requests(
            user.employee_id
        )

        return [
            item.model_dump(mode="json")
            for item in requests
        ]

    @app.get("/api/v1/hr/leave-requests")
    def hr_leave_requests(
        user: AuthContext = Depends(get_current_user),
    ):
        if user.role != "hr_admin":
            raise HTTPException(
                status_code=403,
                detail="HR Admin access required",
            )

        requests = repository.list_hr_leave_requests()

        return [
            item.model_dump(mode="json")
            for item in requests
        ]

    @app.patch("/api/v1/hr/leave-requests/{request_id}/decision")
    def decide_hr_leave_request(
        request_id: str,
        body: HRDecisionRequest,
        user: AuthContext = Depends(get_current_user),
    ):
        if user.role != "hr_admin":
            raise HTTPException(
                status_code=403,
                detail="HR Admin access required",
            )

        updated = repository.decide_hr_leave_request(
            request_id=request_id,
            decision=body.decision,
        )

        if not updated:
            raise HTTPException(
                status_code=409,
                detail="Pengajuan tidak ditemukan atau sudah diputuskan",
            )

        return {
            "request_id": request_id,
            "status": body.decision,
            "decided_by": user.employee_id,
        }
    @app.post("/api/v1/hr/demo/reset")
    def reset_hr_demo(
        user: AuthContext = Depends(get_current_user),
    ):
        if user.role != "hr_admin":
            raise HTTPException(
                status_code=403,
                detail="HR Admin access required",
            )

        if (
            settings.environment != "development"
            or not settings.demo_reset_enabled
        ):
            raise HTTPException(
                status_code=403,
                detail="Demo reset is disabled",
            )

        return repository.reset_demo_leave_data()

    @app.post("/api/v1/action-proposals/{proposal_id}/confirm")
    def confirm_action_proposal(
        proposal_id: str,
        payload: ConfirmActionRequest,
        user: AuthContext = Depends(get_current_user),
    ):
        if user.role != "employee":
            raise HTTPException(
                status_code=403,
                detail="Employee access required",
            )

        try:
            result = repository.confirm_proposal(
                employee_id=user.employee_id,
                proposal_id=proposal_id,
                idempotency_key=payload.idempotency_key,
            )

            return result.model_dump(mode="json")

        except KeyError:
            raise HTTPException(
                status_code=404,
                detail="Proposal tidak ditemukan",
            )

        except ConflictError as exc:
            raise HTTPException(
                status_code=409,
                detail=str(exc),
            )

    return app



def initialize_app() -> FastAPI:
    settings = get_settings()

    repository, cache, agent = build_runtime(settings)

    return create_app(
        settings=settings,
        repository=repository,
        cache=cache,
        agent=agent,
    )


app = initialize_app()