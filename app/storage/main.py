from __future__ import annotations

from pathlib import Path
import datetime

from app.config.settings import CAPTURAS_DIR


def rutaGuardado() -> Path:
    CAPTURAS_DIR.mkdir(exist_ok=True, parents=True)
    return CAPTURAS_DIR


def _normalizar_fecha_carpeta(fecha: datetime.date | str | None) -> datetime.date:
    if fecha is None:
        return datetime.date.today() - datetime.timedelta(days=1)
    if isinstance(fecha, datetime.datetime):
        return fecha.date()
    if isinstance(fecha, datetime.date):
        return fecha
    try:
        return datetime.datetime.strptime(fecha.strip(), "%d/%m/%Y").date()
    except ValueError as error:
        raise ValueError(f"Fecha de carpeta invalida: {fecha!r}. Usa dd/mm/yyyy.") from error


def createFolders(fecha: datetime.date | str | None = None) -> Path:
    ruta = rutaGuardado()
    fecha_carpeta = _normalizar_fecha_carpeta(fecha).strftime("%d-%m-%Y")
    folder = ruta / f"volantes {fecha_carpeta}"
    folder.mkdir(exist_ok=True, parents=True)
    return folder


def get_office_folder(
    codeplace: str,
    fecha: datetime.date | str | None = None,
) -> Path:
    folder = createFolders(fecha) / codeplace
    folder.mkdir(parents=True, exist_ok=True)
    return folder


if __name__ == "__main__":
    createFolders()
