"""Repository contracts. Implement MemoryRepository first, then PostgreSQL/pgvector."""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Protocol
from uuid import uuid4

from .contracts import (
    ActionProposal,
    ActionResult,
    AuthContext,
    LeaveBalance,
    LeaveRequestView,
    PolicyChunk,
)


class Repository(Protocol):
    def health(self) -> bool: ...
    def authenticate(self, token: str) -> AuthContext | None: ...
    def lexical_search(self, query: str, limit: int) -> list[PolicyChunk]: ...
    def vector_search(self, embedding: list[float], limit: int) -> list[PolicyChunk]: ...
    def get_balances(self, employee_id: str) -> list[LeaveBalance]: ...
    def has_overlap(self, employee_id: str, start: date, end: date) -> bool: ...
    def save_proposal(self, employee_id: str, proposal: ActionProposal) -> None: ...
    def get_proposal(self, proposal_id: str) -> tuple[str, ActionProposal] | None: ...
    def confirm_proposal(
        self,
        employee_id: str,
        proposal_id: str,
        idempotency_key: str,
    ) -> ActionResult: ...
    def list_leave_requests(self, employee_id: str) -> list[LeaveRequestView]: ...
    def create_ticket(self, employee_id: str, category: str, summary: str) -> str: ...
    def save_trace(self, trace: dict[str, Any]) -> None: ...
    def get_trace(self, trace_id: str) -> dict[str, Any] | None: ...
    def monitoring_summary(self) -> dict[str, Any]: ...


class ConflictError(RuntimeError):
    pass


class MemoryRepository:
    """In-memory repository used by deterministic/unit tests."""

    def __init__(self) -> None:
        self.chunks: list[PolicyChunk] = []

        self.identities: dict[str, AuthContext] = {
            "token-alya": AuthContext(
                employee_id="EMP-001",
                display_name="Alya Pratama",
                role="employee",
            ),
            "token-bima": AuthContext(
                employee_id="EMP-002",
                display_name="Bima Santoso",
                role="employee",
            ),
            "token-admin": AuthContext(
                employee_id="ADM-001",
                display_name="Monitoring Admin",
                role="monitoring_admin",
            ),
        }

        self.balances: dict[str, list[LeaveBalance]] = {
            "EMP-001": [
                LeaveBalance(
                    leave_type="annual",
                    available_days=8,
                    as_of_date=date(2026, 1, 1),
                ),
                LeaveBalance(
                    leave_type="sick",
                    available_days=10,
                    as_of_date=date(2026, 1, 1),
                ),
                LeaveBalance(
                    leave_type="parental",
                    available_days=60,
                    as_of_date=date(2026, 1, 1),
                ),
            ],
            "EMP-002": [
                LeaveBalance(
                    leave_type="annual",
                    available_days=3,
                    as_of_date=date(2026, 1, 1),
                ),
                LeaveBalance(
                    leave_type="sick",
                    available_days=10,
                    as_of_date=date(2026, 1, 1),
                ),
                LeaveBalance(
                    leave_type="parental",
                    available_days=60,
                    as_of_date=date(2026, 1, 1),
                ),
            ],
        }

        self.proposals: dict[str, tuple[str, ActionProposal]] = {}
        self.requests: dict[str, list[LeaveRequestView]] = {}
        self.confirmations: dict[str, tuple[str, str]] = {}
        self.tickets: list[dict[str, Any]] = []
        self.traces: dict[str, dict[str, Any]] = {}

    def health(self) -> bool:
        return True

    def authenticate(self, token: str) -> AuthContext | None:
        return self.identities.get(token)

    def lexical_search(
        self,
        query: str,
        limit: int,
    ) -> list[PolicyChunk]:
        terms = {
            term.lower()
            for term in query.split()
            if len(term.strip()) >= 2
        }

        scored: list[tuple[int, PolicyChunk]] = []

        for chunk in self.chunks:
            haystack = (
                f"{chunk.document_id} "
                f"{chunk.title} "
                f"{chunk.section} "
                f"{chunk.content}"
            ).lower()

            score = sum(1 for term in terms if term in haystack)

            if score > 0:
                scored.append((score, chunk))

        scored.sort(key=lambda item: item[0], reverse=True)

        return [
            chunk.model_copy(update={"score": float(score)})
            for score, chunk in scored[:limit]
        ]

    def vector_search(
        self,
        embedding: list[float],
        limit: int,
    ) -> list[PolicyChunk]:
        # MemoryRepository does not persist real embeddings.
        # Deterministic tests can still exercise hybrid retrieval through
        # lexical ranking while preserving the repository contract.
        return self.chunks[:limit]

    def get_balances(
        self,
        employee_id: str,
    ) -> list[LeaveBalance]:
        return list(self.balances.get(employee_id, []))

    def has_overlap(
        self,
        employee_id: str,
        start: date,
        end: date,
    ) -> bool:
        active_statuses = {
            "pending_manager_review",
            "approved",
        }

        for request in self.requests.get(employee_id, []):
            if request.status not in active_statuses:
                continue

            if start <= request.end_date and end >= request.start_date:
                return True

        return False

    def save_proposal(
        self,
        employee_id: str,
        proposal: ActionProposal,
    ) -> None:
        self.proposals[proposal.proposal_id] = (
            employee_id,
            proposal,
        )

    def get_proposal(
        self,
        proposal_id: str,
    ) -> tuple[str, ActionProposal] | None:
        return self.proposals.get(proposal_id)

    def confirm_proposal(
        self,
        employee_id: str,
        proposal_id: str,
        idempotency_key: str,
    ) -> ActionResult:
        stored = self.proposals.get(proposal_id)

        # Do not reveal whether another employee owns the proposal.
        if stored is None:
            raise KeyError(proposal_id)

        owner_id, proposal = stored

        if owner_id != employee_id:
            raise KeyError(proposal_id)

        if proposal.expires_at <= datetime.now(timezone.utc):
            raise ConflictError("proposal expired")

        existing_confirmation = self.confirmations.get(proposal_id)

        if existing_confirmation is not None:
            previous_key, request_id = existing_confirmation

            if previous_key != idempotency_key:
                raise ConflictError(
                    "proposal already confirmed with a different "
                    "idempotency key"
                )

            return ActionResult(
                request_id=request_id,
                status="pending_manager_review",
                idempotent_replay=True,
                audit_reference=f"AUD-{request_id}",
            )

        request_id = f"LR-{uuid4().hex[:12].upper()}"

        request = LeaveRequestView(
            request_id=request_id,
            leave_type=proposal.leave_type,
            start_date=proposal.start_date,
            end_date=proposal.end_date,
            business_days=proposal.business_days,
            status="pending_manager_review",
            created_at=datetime.now(timezone.utc),
        )

        self.requests.setdefault(employee_id, []).append(request)

        self.confirmations[proposal_id] = (
            idempotency_key,
            request_id,
        )

        return ActionResult(
            request_id=request_id,
            status="pending_manager_review",
            idempotent_replay=False,
            audit_reference=f"AUD-{request_id}",
        )

    def list_leave_requests(
        self,
        employee_id: str,
    ) -> list[LeaveRequestView]:
        return list(self.requests.get(employee_id, []))

    def create_ticket(
        self,
        employee_id: str,
        category: str,
        summary: str,
    ) -> str:
        ticket_id = f"HRT-{uuid4().hex[:12].upper()}"

        self.tickets.append(
            {
                "ticket_id": ticket_id,
                "employee_id": employee_id,
                "category": category,
                "summary": summary,
                "created_at": datetime.now(timezone.utc),
            }
        )

        return ticket_id

    def save_trace(
        self,
        trace: dict[str, Any],
    ) -> None:
        trace_id = trace.get("trace_id")

        if not trace_id:
            raise ValueError("trace_id is required")

        self.traces[trace_id] = dict(trace)

    def get_trace(
        self,
        trace_id: str,
    ) -> dict[str, Any] | None:
        trace = self.traces.get(trace_id)

        if trace is None:
            return None

        return dict(trace)

    def monitoring_summary(self) -> dict[str, Any]:
        total = len(self.traces)

        errors = sum(
            1
            for trace in self.traces.values()
            if trace.get("outcome") in {"error", "abstained"}
        )

        error_rate = errors / total if total else 0.0

        return {
            "total_traces": total,
            "error_count": errors,
            "error_rate": error_rate,
        }



class PostgresRepository:
    def __init__(
        self,
        database_url: str,
        embedding_dimensions: int,
    ) -> None:
        import psycopg
        from psycopg_pool import ConnectionPool

        self.database_url = database_url
        self.embedding_dimensions = embedding_dimensions

        self.pool = ConnectionPool(
            conninfo=database_url,
            min_size=1,
            max_size=5,
            max_idle=60,
            max_lifetime=1800,
            check=ConnectionPool.check_connection,
            open=True,
        )

    def health(self) -> bool:
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                return cur.fetchone()[0] == 1

    def authenticate(self, token: str) -> AuthContext | None:
        from .security import token_hash

        hashed = token_hash(token)

        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT employee_id, display_name, role
                    FROM employees
                    WHERE token_hash = %s
                    """,
                    (hashed,),
                )

                row = cur.fetchone()

        if row is None:
            return None

        return AuthContext(
            employee_id=row[0],
            display_name=row[1],
            role=row[2],
        )

    def get_balances(
        self,
        employee_id: str,
    ) -> list[LeaveBalance]:
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT leave_type, available_days, as_of_date
                    FROM leave_balances
                    WHERE employee_id = %s
                    ORDER BY leave_type
                    """,
                    (employee_id,),
                )

                rows = cur.fetchall()

        return [
            LeaveBalance(
                leave_type=row[0],
                available_days=row[1],
                as_of_date=row[2],
            )
            for row in rows
        ]

    
    
    def lexical_search(
        self,
        query: str,
        limit: int,
    ) -> list[PolicyChunk]:
        import re

        if not query.strip() or limit <= 0:
            return []

        stopwords = {
            "apa", "apakah", "yang", "dan", "atau",
            "di", "ke", "dari", "untuk", "dengan",
            "saya", "kalau", "bisa", "tidak",
        }

        terms = [
            term
            for term in re.findall(r"\w+", query.lower())
            if len(term) >= 3 and term not in stopwords
        ]

        if not terms:
            return []

        tsquery = " | ".join(terms)

        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        c.chunk_id,
                        c.document_id,
                        c.title,
                        c.section,
                        c.version,
                        c.effective_date,
                        c.content,
                        ts_rank(
                            c.search_vector,
                            to_tsquery('simple', %s)
                        ) AS score
                    FROM policy_chunks AS c
                    WHERE c.search_vector @@
                        to_tsquery('simple', %s)
                    ORDER BY score DESC, c.chunk_id
                    LIMIT %s
                    """,
                    (tsquery, tsquery, limit),
                )

                rows = cur.fetchall()

        return [
            PolicyChunk(
                chunk_id=row[0],
                document_id=row[1],
                title=row[2],
                section=row[3],
                version=row[4],
                effective_date=row[5],
                content=row[6],
                score=float(row[7]),
            )
            for row in rows
        ]

    def vector_search(
        self,
        embedding: list[float],
        limit: int,
    ) -> list[PolicyChunk]:
        from pinecone import Pinecone
        from .config import Settings

        if limit <= 0:
            return []

        if len(embedding) != self.embedding_dimensions:
            raise ValueError(
                "Dimensi embedding tidak sesuai dengan konfigurasi."
            )

        settings = Settings()

        pinecone = Pinecone(
            api_key=settings.pinecone_api_key
        )

        index = pinecone.Index(
            settings.pinecone_index_name
        )

        response = index.query(
            vector=embedding,
            top_k=limit,
            namespace=settings.pinecone_namespace,
            include_metadata=False,
        )

        matches = response.matches or []

        if not matches:
            return []

        chunk_ids = [match.id for match in matches]

        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        chunk_id,
                        document_id,
                        title,
                        section,
                        version,
                        effective_date,
                        content
                    FROM policy_chunks
                    WHERE chunk_id = ANY(%s)
                    """,
                    (chunk_ids,),
                )

                rows = cur.fetchall()

        chunks_by_id = {
            row[0]: PolicyChunk(
                chunk_id=row[0],
                document_id=row[1],
                title=row[2],
                section=row[3],
                version=row[4],
                effective_date=row[5],
                content=row[6],
                score=0.0,
            )
            for row in rows
        }

        
        return [
            chunks_by_id[match.id].model_copy(
                update={"score": float(match.score)}
            )
            for match in matches
            if (
             match.id in chunks_by_id
                and match.score is not None
            )
        ]

    
    def save_trace(self, trace: dict[str, Any]) -> None:
        """Save a sanitized agent execution trace to PostgreSQL."""
        import json

        trace_id = trace.get("trace_id")

        if not trace_id:
            raise ValueError("trace_id is required")

        employee_id = trace.get("employee_id")
        outcome = trace.get("outcome")

        # Hanya simpan metadata yang diizinkan.
        allowed_fields = {
            "trace_id",
            "outcome",
            "tool_calls",
            "usage",
            "latency_ms",
            "error",
        }

        trace_data = {
            key: value
            for key, value in trace.items()
            if key in allowed_fields
        }

        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO agent_traces (
                        trace_id,
                        employee_id,
                        outcome,
                        trace_data
                    )
                    VALUES (%s, %s, %s, %s::jsonb)
                    """,
                    (
                        trace_id,
                        employee_id,
                        outcome,
                        json.dumps(trace_data, default=str),
                    ),
                )

    def get_trace(
        self,
        trace_id: str,
    ) -> dict[str, Any] | None:
        """Retrieve a saved agent trace by its ID."""

        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        trace_id,
                        employee_id,
                        outcome,
                        trace_data,
                        created_at
                    FROM agent_traces
                    WHERE trace_id = %s
                    """,
                    (trace_id,),
                )

                row = cur.fetchone()

        if row is None:
            return None

        return {
            "trace_id": row[0],
            "employee_id": row[1],
            "outcome": row[2],
            "trace_data": row[3],
            "created_at": row[4].isoformat(),
        }

    def list_leave_requests(
        self,
        employee_id: str,
    ) -> list[LeaveRequestView]:
        """Retrieve leave requests belonging to one employee."""

        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        request_id,
                        leave_type,
                        start_date,
                        end_date,
                        business_days,
                        status,
                        created_at
                    FROM leave_requests
                    WHERE employee_id = %s
                    ORDER BY created_at DESC
                    """,
                    (employee_id,),
                )

                rows = cur.fetchall()

        return [
            LeaveRequestView(
                request_id=row[0],
                leave_type=row[1],
                start_date=row[2],
                end_date=row[3],
                business_days=row[4],
                status=row[5],
                created_at=row[6],
            )
            for row in rows
        ]

    def save_proposal(
        self,
        employee_id: str,
        proposal: ActionProposal,
    ) -> None:
        import json

        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO leave_proposals (
                        proposal_id,
                        employee_id,
                        action_type,
                        leave_type,
                        start_date,
                        end_date,
                        business_days,
                        reason,
                        validation_summary,
                        expires_at,
                        requires_confirmation
                    )
                    VALUES (
                        %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s
                    )
                    """,
                    (
                        proposal.proposal_id,
                        employee_id,
                        proposal.action_type,
                        proposal.leave_type,
                        proposal.start_date,
                        proposal.end_date,
                        proposal.business_days,
                        proposal.reason,
                        json.dumps(proposal.validation_summary),
                        proposal.expires_at,
                        proposal.requires_confirmation,
                    ),
                )

    def get_proposal(
        self,
        proposal_id: str,
    ) -> tuple[str, ActionProposal] | None:
        import json

        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        employee_id,
                        proposal_id,
                        action_type,
                        leave_type,
                        start_date,
                        end_date,
                        business_days,
                        reason,
                        validation_summary,
                        expires_at,
                        requires_confirmation
                    FROM leave_proposals
                    WHERE proposal_id = %s
                    """,
                    (proposal_id,),
                )
                row = cur.fetchone()

        if row is None:
            return None

        summary = row[8]
        if isinstance(summary, str):
            summary = json.loads(summary)

        proposal = ActionProposal(
            proposal_id=row[1],
            action_type=row[2],
            leave_type=row[3],
            start_date=row[4],
            end_date=row[5],
            business_days=row[6],
            reason=row[7],
            validation_summary=summary,
            expires_at=row[9],
            requires_confirmation=row[10],
        )

        return row[0], proposal

    def confirm_proposal(
        self,
        employee_id: str,
        proposal_id: str,
        idempotency_key: str,
    ) -> ActionResult:
        from datetime import datetime, timezone
        from uuid import uuid4

        with self.pool.connection() as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT
                            employee_id,
                            leave_type,
                            start_date,
                            end_date,
                            business_days,
                            expires_at
                        FROM leave_proposals
                        WHERE proposal_id = %s
                        FOR UPDATE
                        """,
                        (proposal_id,),
                    )

                    proposal = cur.fetchone()

                    if proposal is None:
                        raise KeyError(proposal_id)

                    owner_id = proposal[0]

                    if owner_id != employee_id:
                        raise KeyError(proposal_id)

                    cur.execute(
                        """
                        SELECT request_id, idempotency_key
                        FROM leave_requests
                        WHERE proposal_id = %s
                        """,
                        (proposal_id,),
                    )

                    existing = cur.fetchone()

                    if existing is not None:
                        request_id, previous_key = existing

                        if previous_key != idempotency_key:
                            raise ConflictError(
                                "proposal already confirmed with "
                                "a different idempotency key"
                            )

                        return ActionResult(
                            request_id=request_id,
                            status="pending_manager_review",
                            idempotent_replay=True,
                            audit_reference=f"AUD-{request_id}",
                        )

                    if proposal[5] <= datetime.now(timezone.utc):
                        raise ConflictError("proposal expired")

                    request_id = (
                        f"LR-{uuid4().hex[:12].upper()}"
                    )

                    cur.execute(
                        """
                        INSERT INTO leave_requests (
                            request_id,
                            proposal_id,
                            employee_id,
                            leave_type,
                            start_date,
                            end_date,
                            business_days,
                            status,
                            idempotency_key
                        )
                        VALUES (
                            %s, %s, %s, %s, %s,
                            %s, %s, %s, %s
                        )
                        """,
                        (
                            request_id,
                            proposal_id,
                            employee_id,
                            proposal[1],
                            proposal[2],
                            proposal[3],
                            proposal[4],
                            "pending_manager_review",
                            idempotency_key,
                        ),
                    )

        return ActionResult(
            request_id=request_id,
            status="pending_manager_review",
            idempotent_replay=False,
            audit_reference=f"AUD-{request_id}",
        )

    def has_overlap(
        self,
        employee_id: str,
        start: date,
        end: date,
    ) -> bool:
        """Check overlapping leave requests for an employee."""

        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT EXISTS (
                        SELECT 1
                        FROM leave_requests
                        WHERE employee_id = %s
                          AND start_date <= %s
                          AND end_date >= %s
                    )
                    """,
                    (
                        employee_id,
                        end,
                        start,
                    ),
                )

                return bool(cur.fetchone()[0])

    def monitoring_summary(self) -> dict[str, Any]:
        """Calculate monitoring metrics from PostgreSQL traces."""

        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        COUNT(*) AS run_count,

                        COUNT(*) FILTER (
                            WHERE trace_data->>'error' IS NOT NULL
                        ) AS error_count,

                        COALESCE(
                            PERCENTILE_CONT(0.95)
                            WITHIN GROUP (
                                ORDER BY (trace_data->>'latency_ms')::numeric
                            ),
                            0
                        ) AS p95_latency_ms,

                        COALESCE(
                            SUM(
                                jsonb_array_length(
                                    CASE
                                        WHEN jsonb_typeof(
                                            trace_data->'tool_calls'
                                        ) = 'array'
                                        THEN trace_data->'tool_calls'
                                        ELSE '[]'::jsonb
                                    END
                                )
                            ),
                            0
                        ) AS tool_calls

                    FROM agent_traces
                    """
                )

                row = cur.fetchone()

        run_count = int(row[0])
        error_count = int(row[1])

        return {
            "run_count": run_count,
            "error_count": error_count,
            "error_rate": (
                error_count / run_count if run_count else 0.0
            ),
            "p95_latency_ms": int(row[2]),
            "tool_calls": int(row[3]),
        }       

    def close(self) -> None:
        self.pool.close()
