import getpass
import psycopg

from src.config import get_settings
from src.password_security import hash_password


def main():
    settings = get_settings()

    if settings.environment.lower() != "development":
        raise RuntimeError(
            "Script ini hanya boleh dijalankan di development."
        )

    employee_id = input("Employee ID: ").strip()
    email = input("Email: ").strip().lower()
    password = getpass.getpass("Password: ")
    confirm = getpass.getpass("Konfirmasi password: ")

    if password != confirm:
        raise ValueError("Konfirmasi password tidak cocok.")

    if not email or "@" not in email:
        raise ValueError("Format email tidak valid.")

    password_hash = hash_password(password)

    with psycopg.connect(settings.database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO employee_credentials (
                    employee_id,
                    email,
                    password_hash
                )
                VALUES (%s, %s, %s)
                """,
                (employee_id, email, password_hash),
            )

    print("Akun berhasil dibuat.")


if __name__ == "__main__":
    main()