import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = BASE_DIR / ".env"


def _load_env_file(env_file: Path) -> None:
    if not env_file.exists():
        return

    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_env_file(ENV_FILE)

POLIEDRO_URL = os.getenv(
    "POLIEDRO_URL", "https://poliedrodist.comcel.com.co/POL_LOGIN/login.aspx"
)
POLIEDRO_USERNAME = os.getenv("POLIEDRO_USERNAME", "")
POLIEDRO_PASSWORD = os.getenv("POLIEDRO_PASSWORD", "")
DEFAULT_TIMEOUT = int(os.getenv("DEFAULT_TIMEOUT", "10"))
FORM_READY_DELAY_SECONDS = float(os.getenv("FORM_READY_DELAY_SECONDS", "4"))
PRINTER_NAME = os.getenv("PRINTER", "")
HEADLESS = os.getenv("HEADLESS", "false").lower() == "true"

TNS_OFFICE = os.getenv("TNS_OFFICE", "")
TNS_USERNAME = os.getenv("TNS_USERNAME", "")
TNS_PASSWORD = os.getenv("TNS_PASSWORD", "")
