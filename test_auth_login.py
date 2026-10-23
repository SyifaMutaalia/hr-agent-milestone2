import getpass

from src.config import get_settings
from src.session_security import login_with_password

settings = get_settings()

if settings.environment.lower() != "development":
    raise RuntimeError("Pengujian hanya boleh di development.")

email = input("Email: ").strip()
password = getpass.getpass("Password: ")

result = login_with_password(
    database_url=settings.database_url,
    email=email,
    password=password,
)

if result is None:
    print("Login gagal: email atau password salah.")
else:
    token, user = result
    print("Login berhasil!")
    print("Nama:", user.display_name)
    print("Role:", user.role)
    print("Employee ID:", user.employee_id)