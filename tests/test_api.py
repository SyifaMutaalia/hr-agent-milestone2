from __future__ import annotations

from fastapi.testclient import TestClient


AUTH = {"Authorization": "Bearer token-alya"}


def test_health_and_auth_contract(client: TestClient) -> None:
    assert client.get("/healthz").json() == {"status": "ok"}
    assert client.post("/api/v1/chat", json={"message": "saldo cuti"}).status_code == 401


def test_chat_returns_contract_and_trace(client: TestClient) -> None:
    response = client.post("/api/v1/chat", headers=AUTH, json={"message": "Berapa jatah cuti tahunan?"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["outcome"] == "answered"
    assert payload["citations"][0]["document_id"] == "HR-LEAVE-001"
    trace = client.get(f"/api/v1/traces/{payload['trace_id']}", headers=AUTH)
    assert trace.status_code == 200
    assert "message" not in trace.json()


def test_monitoring_is_admin_only(client: TestClient) -> None:
    assert client.get("/api/v1/monitoring/summary", headers=AUTH).status_code == 403
    response = client.get(
        "/api/v1/monitoring/summary", headers={"Authorization": "Bearer token-admin"}
    )
    assert response.status_code == 200


def test_trace_cannot_be_read_by_another_employee(client: TestClient) -> None:
    chat = client.post("/api/v1/chat", headers=AUTH, json={"message": "saldo saya"}).json()
    response = client.get(
        f"/api/v1/traces/{chat['trace_id']}",
        headers={"Authorization": "Bearer token-bima"},
    )
    assert response.status_code == 403

def test_hr_cannot_confirm_employee_proposal(client):
    response = client.post(
        "/api/v1/action-proposals/AP-TEST/confirm",
        headers={"Authorization": "Bearer token-hr-admin"},
        json={"idempotency_key": "idem-hr-test-12345"},
    )

    assert response.status_code == 403


def test_hr_cannot_access_employee_leave_history(client):
    response = client.get(
        "/api/v1/leave-requests/me",
        headers={"Authorization": "Bearer token-hr-admin"},
    )

    assert response.status_code == 403
def test_hr_can_access_leave_requests(client):
    response = client.get(
        "/api/v1/hr/leave-requests",
        headers={
            "Authorization": "Bearer token-hr-admin"
        },
    )

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_employees_cannot_access_hr_leave_requests(client):
    for token in ["token-alya", "token-bima"]:
        response = client.get(
            "/api/v1/hr/leave-requests",
            headers={
                "Authorization": f"Bearer {token}"
            },
        )

        assert response.status_code == 403


def test_monitor_cannot_access_hr_leave_requests(client):
    response = client.get(
        "/api/v1/hr/leave-requests",
        headers={
            "Authorization": "Bearer token-admin"
        },
    )

    assert response.status_code == 403


def test_unauthenticated_user_cannot_access_hr_leave_requests(client):
    response = client.get(
        "/api/v1/hr/leave-requests"
    )

    assert response.status_code == 401
from datetime import datetime, date, timezone
from src.contracts import LeaveRequestView


def test_hr_sees_pending_requests_from_both_employees(
    client, repository
):
    repository.requests["EMP-001"] = [
        LeaveRequestView(
            request_id="LR-ALYA-001",
            leave_type="annual",
            start_date=date(2026, 11, 10),
            end_date=date(2026, 11, 11),
            business_days=2,
            status="pending_manager_review",
            created_at=datetime.now(timezone.utc),
        )
    ]

    repository.requests["EMP-002"] = [
        LeaveRequestView(
            request_id="LR-BIMA-001",
            leave_type="annual",
            start_date=date(2026, 11, 12),
            end_date=date(2026, 11, 13),
            business_days=2,
            status="pending_manager_review",
            created_at=datetime.now(timezone.utc),
        )
    ]

    response = client.get(
        "/api/v1/hr/leave-requests",
        headers={
            "Authorization": "Bearer token-hr-admin"
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 2
    assert {item["employee_id"] for item in data} == {
        "EMP-001",
        "EMP-002",
    }
    assert {item["employee_name"] for item in data} == {
        "Alya Pratama",
        "Bima Santoso",
    }
    assert all(
        item["status"] == "pending_manager_review"
        for item in data
    )
def test_only_hr_can_decide_leave_requests(client):
    request_id = "LR-TEST-AUTH"

    for token in ("token-alya", "token-bima", "token-admin"):
        response = client.patch(
            f"/api/v1/hr/leave-requests/{request_id}/decision",
            headers={"Authorization": f"Bearer {token}"},
            json={"decision": "approved"},
        )

        assert response.status_code == 403


def test_unauthenticated_user_cannot_decide_leave(client):
    response = client.patch(
        "/api/v1/hr/leave-requests/LR-TEST/decision",
        json={"decision": "approved"},
    )

    assert response.status_code == 401


def test_invalid_hr_decision_is_rejected(client):
    response = client.patch(
        "/api/v1/hr/leave-requests/LR-TEST/decision",
        headers={"Authorization": "Bearer token-hr-admin"},
        json={"decision": "auto_approved"},
    )

    assert response.status_code == 422
def test_hr_can_approve_leave_request(client, repository):
    from datetime import date, datetime, timezone
    from src.contracts import LeaveRequestView

    request_id = "LR-TEST-APPROVE"

    repository.requests.setdefault("EMP-001", []).append(
        LeaveRequestView(
            request_id=request_id,
            leave_type="annual",
            start_date=date(2026, 11, 2),
            end_date=date(2026, 11, 4),
            business_days=3,
            status="pending_manager_review",
            created_at=datetime.now(timezone.utc),
        )
    )

    response = client.patch(
        f"/api/v1/hr/leave-requests/{request_id}/decision",
        headers={"Authorization": "Bearer token-hr-admin"},
        json={"decision": "approved"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "approved"

    # Pastikan keputusan tersimpan.
    requests = repository.list_leave_requests("EMP-001")
    assert any(
        r.request_id == request_id and r.status == "approved"
        for r in requests
    )

    # Pengajuan yang sudah diputuskan tidak boleh diputuskan ulang.
    second_response = client.patch(
        f"/api/v1/hr/leave-requests/{request_id}/decision",
        headers={"Authorization": "Bearer token-hr-admin"},
        json={"decision": "rejected"},
    )

    assert second_response.status_code == 409
def test_hr_can_reject_leave_request(client, repository):
    from datetime import date, datetime, timezone
    from src.contracts import LeaveRequestView

    request_id = "LR-TEST-REJECT"

    repository.requests.setdefault("EMP-002", []).append(
        LeaveRequestView(
            request_id=request_id,
            leave_type="annual",
            start_date=date(2026, 11, 9),
            end_date=date(2026, 11, 10),
            business_days=2,
            status="pending_manager_review",
            created_at=datetime.now(timezone.utc),
        )
    )

    response = client.patch(
        f"/api/v1/hr/leave-requests/{request_id}/decision",
        headers={"Authorization": "Bearer token-hr-admin"},
        json={"decision": "rejected"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "rejected"

    # Bima dapat melihat status penolakan miliknya.
    employee_response = client.get(
        "/api/v1/leave-requests/me",
        headers={"Authorization": "Bearer token-bima"},
    )

    assert employee_response.status_code == 200
    assert any(
        item["request_id"] == request_id
        and item["status"] == "rejected"
        for item in employee_response.json()
    )

    # Alya tidak boleh melihat pengajuan Bima.
    alya_response = client.get(
        "/api/v1/leave-requests/me",
        headers={"Authorization": "Bearer token-alya"},
    )

    assert alya_response.status_code == 200
    assert all(
        item["request_id"] != request_id
        for item in alya_response.json()
    )