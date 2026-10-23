"""Strict tool schemas and deterministic tool execution."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any, Callable
from uuid import uuid4

from fastapi import requests
from openai import auth
from openai import auth
from pydantic import ValidationError

from .config import Settings
from .contracts import (
    ActionProposal,
    AuthContext,
    PrepareLeaveArgs,
    SearchPolicyArgs,
    TicketArgs,
)
from .domain import DomainError, validate_leave_request
from .retrieval import RetrievalService
from .repository import Repository


TOOL_SCHEMAS: list[dict[str, Any]] = [
    
    {
        "type": "function",
        "name": "get_my_leave_requests",
        "description": (
            "Retrieve the authenticated employee's leave requests "
            "and their actual statuses from the database. "
            "Use when an employee asks about their leave status, "
            "approval progress, or submission history. "
            "Never accepts an employee ID."
        ),
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        },
    },

    {
        "type": "function",
        "name": "search_hr_policy",
        "description": (
            "Search official HR policy documents. Use this when the user "
            "asks about HR rules, leave policy, eligibility, remote work, "
            "or other policy questions."
        ),
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "HR policy question or search query.",
                },
                "top_k": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 10,
                    "description": "Maximum number of policy chunks.",
                },
            },
            "required": ["query", "top_k"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "get_my_leave_balance",
        "description": (
            "Return leave balances for the currently authenticated employee. "
            "Never accepts another employee ID."
        ),
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "prepare_leave_request",
        "description": (
            "Validate a leave request and create a proposal for the "
            "authenticated employee. This does not submit or approve leave."
        ),
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "start_date": {
                    "type": "string",
                    "format": "date",
                },
                "end_date": {
                    "type": "string",
                    "format": "date",
                },
                "leave_type": {
                    "type": "string",
                    "enum": ["annual", "sick", "parental"],
                },
                "reason": {
                    "type": "string",
                },
            },
            "required": [
                "start_date",
                "end_date",
                "leave_type",
                "reason",
            ],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "create_hr_ticket",
        "description": (
            "Create an HR escalation ticket when policy evidence is "
            "insufficient, conflicting, or human HR review is required."
        ),
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "enum": [
                        "policy_clarification",
                        "leave_exception",
                        "balance_issue",
                        "eligibility_review",
                        "other",
                    ],
                },
                "summary": {
                    "type": "string",
                },
            },
            "required": ["category", "summary"],
            "additionalProperties": False,
        },
    },
]


class ToolExecutor:
    def __init__(
        self,
        repository: Repository,
        retrieval: RetrievalService,
        settings: Settings,
        today_factory: Callable[[], date] | None = None,
    ) -> None:
        self.repository = repository
        self.retrieval = retrieval
        self.settings = settings
        self.today_factory = today_factory or date.today

    def execute(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        auth: AuthContext,
    ) -> dict[str, Any]:
        """
        Execute one approved tool.

        Identity-sensitive operations always use auth.employee_id.
        The model cannot choose another employee.
        """
        employee_only_tools = {
            "get_my_leave_balance",
            "get_my_leave_requests",
            "prepare_leave_request",
            "create_hr_ticket",
        }

        if (
            tool_name in employee_only_tools
            and auth.role != "employee"
        ):
            raise PermissionError(
                "This tool is restricted to employees"
            )

        if tool_name == "search_hr_policy":
            args = SearchPolicyArgs.model_validate(arguments)

            chunks = self.retrieval.search(
                args.query,
                top_k=args.top_k,
            )

            return {
                "documents": [
                    {
                        "document_id": chunk.document_id,
                        "title": chunk.title,
                        "section": chunk.section,
                        "version": chunk.version,
                        "effective_date": (
                            chunk.effective_date.isoformat()
                            if chunk.effective_date
                            else None
                        ),
                        "content": chunk.content,
                        "score": chunk.score,
                    }
                    for chunk in chunks
                ]
            }

        if tool_name == "get_my_leave_balance":
            if arguments:
                raise ValueError(
                    "get_my_leave_balance does not accept arguments"
                )

            balances = self.repository.get_balances(
                auth.employee_id
            )

            return {
                "employee_id": auth.employee_id,
                "balances": [
                    balance.model_dump(mode="json")
                    for balance in balances
                ],
            }

        if tool_name == "get_my_leave_requests":
            if auth.role != "employee":
                raise DomainError(
                    "Hanya pegawai yang dapat melihat pengajuan cutinya."
                )

            requests = self.repository.list_leave_requests(
                auth.employee_id
            )

            return {
                "employee_id": auth.employee_id,
                "requests": [
                    item.model_dump(mode="json")
                    for item in requests
                ],
                "total": len(requests),
            }

        if tool_name == "prepare_leave_request":
            args = PrepareLeaveArgs.model_validate(arguments)

            balances = self.repository.get_balances(
                auth.employee_id
            )

            overlaps = self.repository.has_overlap(
                auth.employee_id,
                args.start_date,
                args.end_date,
            )

            business_day_count, checks = validate_leave_request(
                args=args,
                balances=balances,
                overlaps=overlaps,
                today=self.today_factory(),
            )

            proposal_id = f"AP-{uuid4().hex[:12].upper()}"

            proposal = ActionProposal(
                proposal_id=proposal_id,
                leave_type=args.leave_type,
                start_date=args.start_date,
                end_date=args.end_date,
                business_days=business_day_count,
                reason=args.reason,
                expires_at=(
                    datetime.now(timezone.utc)
                    + timedelta(
                        minutes=self.settings.proposal_ttl_minutes
                    )
                ),
                validation_summary=checks,
            )

            self.repository.save_proposal(
                auth.employee_id,
                proposal,
            )

            return {
                "proposal": proposal.model_dump(mode="json"),
                "requires_confirmation": True,
                "status": "proposal_only",
            }

        if tool_name == "create_hr_ticket":
            args = TicketArgs.model_validate(arguments)

            ticket_id = self.repository.create_ticket(
                auth.employee_id,
                args.category,
                args.summary,
            )

            return {
                "ticket_id": ticket_id,
                "status": "created",
            }

        raise ValueError(f"Unknown tool: {tool_name}")

