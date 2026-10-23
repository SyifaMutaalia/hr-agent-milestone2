from pathlib import Path

import psycopg

from src.config import get_settings


def main():
    settings = get_settings()

    if not settings.database_url:
        raise RuntimeError("DATABASE_URL belum dikonfigurasi")

    sql = Path("sql/auth_schema.sql").read_text(encoding="utf-8")

    with psycopg.connect(settings.database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)

    print("Migrasi autentikasi berhasil.")


if __name__ == "__main__":
    main()
