"""Demo-only reset endpoint."""

from __future__ import annotations

import os
import secrets

from fastapi import APIRouter, Header, HTTPException


def demo_reset_router(repository):
    router = APIRouter()

    @router.post("/api/v1/demo/reset", tags=["demo"])
    def reset_demo_data(
        x_demo_reset_secret: str | None = Header(default=None),
    ):
        environment = os.getenv("ENVIRONMENT", "development").lower()
        enabled = os.getenv("ENABLE_DEMO_RESET", "").lower() == "true"
        secret = os.getenv("DEMO_RESET_SECRET", "")

        if environment not in {"development", "demo", "test"} or not enabled:
            raise HTTPException(status_code=404, detail="Not found")

        if (
            not secret
            or not x_demo_reset_secret
            or not secrets.compare_digest(secret, x_demo_reset_secret)
        ):
            raise HTTPException(status_code=403, detail="Forbidden")

        reset = getattr(repository, "reset_demo_leave_data", None)

        if not callable(reset):
            raise HTTPException(
                status_code=501,
                detail="Reset not supported by repository",
            )

        return reset()

    return router