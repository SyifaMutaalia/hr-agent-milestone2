
from pathlib import Path
from datetime import date

import psycopg

from src.config import Settings
from src.security import token_hash
from src.setup_lab import chunk_policy


def seed_employees(cur):
    employees = [
        ("EMP-001", "Alya Pratama", "employee", "token-alya"),
        ("EMP-002", "Bima Santoso", "employee", "token-bima"),
        ("ADM-001", "Monitoring Admin", "monitoring_admin", "token-admin"),
    ]

    for employee_id, name, role, token in employees:
        cur.execute(
            """
            INSERT INTO employees (
                employee_id, display_name, role, token_hash
            )
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (employee_id)
            DO UPDATE SET
                display_name = EXCLUDED.display_name,
                role = EXCLUDED.role,
                token_hash = EXCLUDED.token_hash
            """,
            (employee_id, name, role, token_hash(token)),
        )


def seed_balances(cur):
    balances = [
        ("EMP-001", "annual", 8),
        ("EMP-001", "sick", 10),
        ("EMP-001", "parental", 60),
        ("EMP-002", "annual", 3),
        ("EMP-002", "sick", 10),
        ("EMP-002", "parental", 60),
    ]

    for employee_id, leave_type, days in balances:
        cur.execute(
            """
            INSERT INTO leave_balances (
                employee_id, leave_type,
                available_days, as_of_date
            )
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (employee_id, leave_type)
            DO UPDATE SET
                available_days = EXCLUDED.available_days,
                as_of_date = EXCLUDED.as_of_date
            """,
            (employee_id, leave_type, days, date(2026, 1, 1)),
        )


def seed_policies(cur):
    policy_dir = Path("data/policies")
    total_chunks = 0

    for path in sorted(policy_dir.glob("*.md")):
        chunks = chunk_policy(path)

        if not chunks:
            continue

        first = chunks[0]

        cur.execute(
            """
            INSERT INTO policy_documents (
                document_id, title, version, effective_date
            )
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (document_id)
            DO UPDATE SET
                title = EXCLUDED.title,
                version = EXCLUDED.version,
                effective_date = EXCLUDED.effective_date
            """,
            (
                first["document_id"],
                first["title"],
                first["version"],
                first["effective_date"],
            ),
        )

        for chunk in chunks:
            cur.execute(
                """
                INSERT INTO policy_chunks (
                    chunk_id, document_id, title,
                    section, version, effective_date, content
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (chunk_id)
                DO UPDATE SET
                    title = EXCLUDED.title,
                    section = EXCLUDED.section,
                    version = EXCLUDED.version,
                    effective_date = EXCLUDED.effective_date,
                    content = EXCLUDED.content
                """,
                (
                    chunk["chunk_id"],
                    chunk["document_id"],
                    chunk["title"],
                    chunk["section"],
                    chunk["version"],
                    chunk["effective_date"],
                    chunk["content"],
                ),
            )

            total_chunks += 1

    return total_chunks


def main():
    settings = Settings()

    with psycopg.connect(settings.database_url) as conn:
        with conn.cursor() as cur:
            seed_employees(cur)
            seed_balances(cur)
            total_chunks = seed_policies(cur)

    print("Neon seeding berhasil.")
    print("Pegawai: 3")
    print("Saldo cuti: 6")
    print(f"Policy chunks diproses: {total_chunks}")


if __name__ == "__main__":
    main()
