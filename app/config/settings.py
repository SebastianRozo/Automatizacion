import os
import sys
from pathlib import Path


def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


BASE_DIR = _get_base_dir()
ENV_FILE = BASE_DIR / ".env"


def resource_path(relative_path: str) -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / relative_path
    return BASE_DIR / relative_path


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
TNS_APP_PATH = os.getenv("TNS_APP_PATH", "")

EXCEL_TEMPLATE_FILENAME = "M-GO-FT-02 Formato Consolidado pago de volantes V1.-1.xlsx"
DEFAULT_EXCEL_TEMPLATE_PATH = resource_path(
    f"app/template/plantillaExcel/{EXCEL_TEMPLATE_FILENAME}"
)
DEFAULT_EXCEL_OUTPUT_PATH = BASE_DIR / EXCEL_TEMPLATE_FILENAME
EXCEL_TEMPLATE_PATH = Path(
    os.getenv("EXCEL_TEMPLATE_PATH") or str(DEFAULT_EXCEL_TEMPLATE_PATH)
)
EXCEL_OUTPUT_PATH = Path(os.getenv("EXCEL_OUTPUT_PATH") or str(DEFAULT_EXCEL_OUTPUT_PATH))
