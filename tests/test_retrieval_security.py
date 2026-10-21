from __future__ import annotations

from src.cache import NullCache
from src.providers import DeterministicProvider
from src.repository import MemoryRepository
from src.retrieval import RetrievalService
from src.security import redact


def test_hybrid_retrieval_prefers_lexical_match(repository: MemoryRepository) -> None:
    service = RetrievalService(repository, DeterministicProvider(), NullCache(), 0)
    results = service.search("jatah cuti tahunan", top_k=2)
    assert results[0].document_id == "HR-LEAVE-001"


def test_redaction_covers_sensitive_patterns() -> None:
    value = redact(
        "Hubungi alya@example.com atau 081234567890; token-secret_ABCDEF123; diagnosis: diabetes."
    )
    assert "alya@example.com" not in value
    assert "081234567890" not in value
    assert "ABCDEF123" not in value
    assert "diabetes" not in value


def test_balance_tool_has_no_cross_employee_argument(client) -> None:
    response = client.post(
        "/api/v1/chat",
        headers={"Authorization": "Bearer token-alya"},
        json={"message": "Tampilkan saldo EMP-002"},
    )
    assert response.status_code == 200
    trace = client.get(
        f"/api/v1/traces/{response.json()['trace_id']}",
        headers={"Authorization": "Bearer token-alya"},
    ).json()
    assert trace["employee_id"] == "EMP-001"
from src.contracts import AuthContext
from src.tools import ToolExecutor
from src.config import Settings
from unittest.mock import Mock
import pytest


def test_monitor_cannot_access_employee_balance():
    tools = ToolExecutor(
        repository=Mock(),
        retrieval=Mock(),
        settings=Mock(),
    )

    monitor = AuthContext(
        employee_id="ADM-001",
        display_name="Monitoring Admin",
        role="monitoring_admin",
    )

    with pytest.raises(PermissionError):
        tools.execute(
            tool_name="get_my_leave_balance",
            arguments={},
            auth=monitor,
        )


def test_monitor_cannot_prepare_leave_request():
    tools = ToolExecutor(
        repository=Mock(),
        retrieval=Mock(),
        settings=Mock(),
    )

    monitor = AuthContext(
        employee_id="ADM-001",
        display_name="Monitoring Admin",
        role="monitoring_admin",
    )

    with pytest.raises(PermissionError):
        tools.execute(
            tool_name="prepare_leave_request",
            arguments={
                "leave_type": "annual",
                "start_date": "2026-11-10",
                "end_date": "2026-11-11",
                "reason": "Keperluan pribadi",
            },
            auth=monitor,
        )
def test_employee_balance_isolation(repository, settings):
    from src.contracts import AuthContext
    from src.tools import ToolExecutor
    from unittest.mock import Mock

    tools = ToolExecutor(
        repository=repository,
        retrieval=Mock(),
        settings=settings,
    )

    alya = AuthContext(
        employee_id="EMP-001",
        display_name="Alya",
        role="employee",
    )

    bima = AuthContext(
        employee_id="EMP-002",
        display_name="Bima",
        role="employee",
    )

    alya_result = tools.execute(
        tool_name="get_my_leave_balance",
        arguments={},
        auth=alya,
    )

    bima_result = tools.execute(
        tool_name="get_my_leave_balance",
        arguments={},
        auth=bima,
    )

    assert alya_result["employee_id"] == "EMP-001"
    assert bima_result["employee_id"] == "EMP-002"

    alya_annual = next(
        item for item in alya_result["balances"]
        if item["leave_type"] == "annual"
    )

    bima_annual = next(
        item for item in bima_result["balances"]
        if item["leave_type"] == "annual"
    )

    assert alya_annual["available_days"] == 8
    assert bima_annual["available_days"] == 3


def test_employee_cannot_override_identity(repository, settings):
    from src.contracts import AuthContext
    from src.tools import ToolExecutor
    from unittest.mock import Mock
    import pytest

    tools = ToolExecutor(
        repository=repository,
        retrieval=Mock(),
        settings=settings,
    )

    bima = AuthContext(
        employee_id="EMP-002",
        display_name="Bima",
        role="employee",
    )

    with pytest.raises(ValueError):
        tools.execute(
            tool_name="get_my_leave_balance",
            arguments={"employee_id": "EMP-001"},
            auth=bima,
        )
def test_hr_cannot_use_employee_tools(repository, settings):
    from src.tools import ToolExecutor
    import pytest
    from unittest.mock import Mock

    hr = repository.authenticate("token-hr-admin")

    assert hr is not None
    assert hr.employee_id == "ADM-002"
    assert hr.role == "hr_admin"

    tools = ToolExecutor(
        repository=repository,
        retrieval=Mock(),
        settings=settings,
    )

    for tool_name, arguments in [
        ("get_my_leave_balance", {}),
        (
            "prepare_leave_request",
            {
                "leave_type": "annual",
                "start_date": "2026-11-10",
                "end_date": "2026-11-11",
                "reason": "Keperluan pribadi",
            },
        ),
        ("create_hr_ticket", {}),
    ]:
        with pytest.raises(PermissionError):
            tools.execute(
                tool_name=tool_name,
                arguments=arguments,
                auth=hr,
            )


def test_hr_cannot_access_monitoring(client):
    response = client.get(
        "/api/v1/monitoring/summary",
        headers={"Authorization": "Bearer token-hr-admin"},
    )

    assert response.status_code == 403