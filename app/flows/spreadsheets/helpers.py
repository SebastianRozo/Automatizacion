from __future__ import annotations

from datetime import datetime


def limpiar_texto(valor: str) -> str:
    valor = valor.replace("\xa0", " ").strip()
    return valor


def normalizar_dinero(valor: str) -> int:
    solo_digitos = "".join(c for c in valor if c.isdigit())
    return int(solo_digitos) if solo_digitos else 0


def parsear_fecha(fecha: str) -> datetime:
    fecha = limpiar_texto(fecha)
    fecha = fecha.replace("a.m.", "AM").replace("p.m.", "PM")
    return datetime.strptime(fecha, "%d/%m/%Y %I:%M:%S %p")


def clasificar_fecha_activacion(fecha_activacion: str, fecha_volante: str) -> str:
    fecha_activacion_dia = parsear_fecha(fecha_activacion).date()
    try:
        fecha_volante_dia = datetime.strptime(
            limpiar_texto(fecha_volante),
            "%d/%m/%Y",
        ).date()
    except ValueError as error:
        raise ValueError(
            f"Fecha de volante invalida: {fecha_volante!r}. Usa dd/mm/yyyy."
        ) from error

    if fecha_activacion_dia < fecha_volante_dia:
        return "anterior"
    if fecha_activacion_dia > fecha_volante_dia:
        return "posterior"
    return "misma_fecha"


def obtener_valor_select(datos_volante: dict | None, *claves, default: str | None = None) -> str | None:
    if datos_volante is None:
        return default

    for clave in claves:
        valor = datos_volante.get(clave)
        if valor:
            return str(valor)

    return default


def obtener_valores_producto(datos_volante: dict | None) -> list[str]:
    if datos_volante is None:
        return ["3", "7", "5"]

    productos = datos_volante.get("productos")
    if isinstance(productos, (list, tuple)):
        valores = [str(producto).strip() for producto in productos if str(producto).strip()]
        if valores:
            return valores

    producto = datos_volante.get("producto")
    if producto:
        return [str(producto).strip()]

    return ["3", "7", "5"]
