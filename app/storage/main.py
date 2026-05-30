from pathlib import Path
import datetime

from app.config.settings import CAPTURAS_DIR


def rutaGuardado() -> Path:
    CAPTURAS_DIR.mkdir(exist_ok=True, parents=True)
    return CAPTURAS_DIR


def createFolders() -> Path:
    ruta = rutaGuardado()
    fecha = (datetime.date.today() - datetime.timedelta(days=1)).strftime("%d-%m-%Y")
    folder = ruta / f"volantes {fecha}"
    folder.mkdir(exist_ok=True, parents=True)
    return folder


def get_office_folder(codeplace: str) -> Path:
    folder = createFolders() / codeplace
    folder.mkdir(parents=True, exist_ok=True)
    return folder


if __name__ == "__main__":
    createFolders()
