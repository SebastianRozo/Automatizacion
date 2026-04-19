from pathlib import Path
import datetime


def rutaGuardado() -> Path:
    escritorio = Path.home()
    possible_desktops = [
        escritorio / "Desktop",
        escritorio / "Escritorio",
        escritorio / "OneDrive" / "Desktop",
        escritorio / "OneDrive" / "Escritorio",
    ]

    for desktop in possible_desktops:
        if desktop.exists():
            return desktop
    raise FileNotFoundError("No se encontro la carpeta del escritorio")


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
