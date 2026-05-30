import csv

from app.storage.main import createFolders


def guardar_usuarios_no_encontrados(usuarios_no_encontrados: list[dict]) -> None:
    if not usuarios_no_encontrados:
        return

    ruta_reporte = createFolders() / "usuarios_no_encontrados.csv"
    encabezados = [
        "fecha",
        "codigo_oficina_planilla",
        "codigo_usuario_volante",
        "usuario_no_encontrado",
        "producto",
        "fecha_activacion",
        "valor_planilla",
        "error_tns",
        "accion",
    ]

    escribir_encabezado = not ruta_reporte.exists()
    with ruta_reporte.open("a", newline="", encoding="utf-8") as archivo:
        escritor = csv.writer(archivo)
        if escribir_encabezado:
            escritor.writerow(encabezados)

        for usuario in usuarios_no_encontrados:
            escritor.writerow([
                usuario.get("fecha_volante", ""),
                usuario.get("codigo_oficina_planilla", ""),
                usuario.get("codigo_usuario_volante", ""),
                usuario.get("usuario", ""),
                usuario.get("producto", ""),
                usuario.get("fecha_activacion", ""),
                usuario.get("vr_total_planilla", ""),
                usuario.get("error_tns", ""),
                usuario.get("accion", ""),
            ])
