"""Security helpers for production authentication sessions."""

import secrets
from datetime import datetime, timedelta, timezone

from .security import token_hash


SESSION_DURATION_HOURS = 8


def create_session_token() -> tuple[str, str, datetime]:
    """Generate a session token, its hash, and expiration time."""

    token = secrets.token_urlsafe(48)
    hashed_token = token_hash(token)

    expires_at = datetime.now(timezone.utc) + timedelta(
        hours=SESSION_DURATION_HOURS
    )

    return token, hashed_token, expires_at

from uuid import uuid4

import psycopg


def save_session(
    database_url: str,
    employee_id: str,
    hashed_token: str,
    expires_at: datetime,
) -> None:
    """Save a production session in PostgreSQL."""

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO auth_sessions (
                    session_id,
                    employee_id,
                    token_hash,
                    expires_at
                )
                VALUES (%s, %s, %s, %s)
                """,
                (
                    uuid4(),
                    employee_id,
                    hashed_token,
                    expires_at,
                ),
            )
from .contracts import AuthContext


def authenticate_session(
    database_url: str,
    token: str,
) -> AuthContext | None:
    """Validate an active, unexpired production session."""

    if not token:
        return None

    hashed_token = token_hash(token)

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    e.employee_id,
                    e.display_name,
                    e.role
                FROM auth_sessions AS s
                JOIN employees AS e
                    ON e.employee_id = s.employee_id
                JOIN employee_credentials AS c
                    ON c.employee_id = e.employee_id
                WHERE s.token_hash = %s
                  AND s.revoked_at IS NULL
                  AND s.expires_at > NOW()
                  AND c.is_active = TRUE
                """,
                (hashed_token,),
            )

            row = cur.fetchone()

    if row is None:
        return None

    return AuthContext(
        employee_id=row[0],
        display_name=row[1],
        role=row[2],
    )
from .password_security import verify_password


def login_with_password(
    database_url: str,
    email: str,
    password: str,
) -> tuple[str, AuthContext] | None:
    """Verify credentials and create a new login session."""

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    e.employee_id,
                    e.display_name,
                    e.role,
                    c.password_hash
                FROM employee_credentials AS c
                JOIN employees AS e
                    ON e.employee_id = c.employee_id
                WHERE LOWER(c.email) = LOWER(%s)
                  AND c.is_active = TRUE
                """,
                (email.strip(),),
            )

            row = cur.fetchone()

    if row is None:
        return None

    employee_id, display_name, role, password_hash = row

    if not verify_password(password, password_hash):
        return None

    token, hashed_token, expires_at = create_session_token()

    save_session(
        database_url=database_url,
        employee_id=employee_id,
        hashed_token=hashed_token,
        expires_at=expires_at,
    )

    user = AuthContext(
        employee_id=employee_id,
        display_name=display_name,
        role=role,
    )

    return token, user