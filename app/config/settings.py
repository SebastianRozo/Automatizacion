import os
import sys
from pathlib import Path


def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


BASE_DIR = _get_base_dir()
ENV_FILE = BASE_DIR / ".env"
DIST_ENV_FILE = BASE_DIR / "dist" / ".env"

def _load_env_file(env_file: Path, override_empty: bool = False) -> None:
    if not env_file.exists():
        return

    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key not in os.environ or (override_empty and not os.environ.get(key)):
            os.environ[key] = value


_load_env_file(ENV_FILE)
if DIST_ENV_FILE != ENV_FILE:
    _load_env_file(DIST_ENV_FILE, override_empty=True)

POLIEDRO_URL = os.getenv(
    "POLIEDRO_URL", "https://poliedrodist.comcel.com.co/POL_LOGIN/login.aspx"
)
POLIEDRO_USERNAME = os.getenv("POLIEDRO_USERNAME", "")
POLIEDRO_PASSWORD = os.getenv("POLIEDRO_PASSWORD", "")
DEFAULT_TIMEOUT = int(os.getenv("DEFAULT_TIMEOUT", "10"))
FORM_READY_DELAY_SECONDS = float(os.getenv("FORM_READY_DELAY_SECONDS", "4"))
PRINTER_NAME = os.getenv("PRINTER", "")
HEADLESS = os.getenv("HEADLESS", "false").lower() == "true"
PRINT_SCALE = os.getenv("PRINT_SCALE", "70")
CAPTURAS_DIR = Path(
    os.getenv(
        "CAPTURAS_DIR",
        r"D:\Usuarios\ACTIVACIONES\Desktop\CAPTURA DE VOLANTES",
    )
)

VOLANTES_FECHA_INICIAL = os.getenv("VOLANTES_FECHA_INICIAL", "")
VOLANTES_FECHA_FINAL = os.getenv("VOLANTES_FECHA_FINAL", "")

TNS_OFFICE = os.getenv("TNS_OFFICE", "")
TNS_USERNAME = os.getenv("TNS_USERNAME", "")
TNS_PASSWORD = os.getenv("TNS_PASSWORD", "")
TNS_APP_PATH = os.getenv("TNS_APP_PATH", "")
