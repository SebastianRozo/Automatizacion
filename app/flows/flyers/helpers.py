import datetime

from app.config.settings import VOLANTES_FECHA_FINAL, VOLANTES_FECHA_INICIAL


def get_before_day() -> datetime.date:
    return datetime.date.today() - datetime.timedelta(days=1)


def obtener_fechas_consulta_volantes() -> list[datetime.date]:
    fechas_configuradas = obtener_fechas_configuradas()
    if fechas_configuradas:
        return fechas_configuradas

    hoy = datetime.date.today()
    ayer = hoy - datetime.timedelta(days=1)

    if hoy.weekday() == 0:
        hace_dos_dias = hoy - datetime.timedelta(days=2)
        return [hace_dos_dias, ayer]

    return [ayer]


def obtener_fechas_configuradas() -> list[datetime.date]:
    fecha_inicial = VOLANTES_FECHA_INICIAL.strip()
    fecha_final = VOLANTES_FECHA_FINAL.strip()
    if not fecha_inicial and not fecha_final:
        return []

    if fecha_inicial:
        inicio = parsear_fecha_volante(fecha_inicial, "VOLANTES_FECHA_INICIAL")
    else:
        inicio = parsear_fecha_volante(fecha_final, "VOLANTES_FECHA_FINAL")

    if fecha_final:
        fin = parsear_fecha_volante(fecha_final, "VOLANTES_FECHA_FINAL")
    else:
        fin = parsear_fecha_volante(fecha_inicial, "VOLANTES_FECHA_INICIAL")
    if inicio > fin:
        raise ValueError("VOLANTES_FECHA_INICIAL no puede ser mayor que VOLANTES_FECHA_FINAL")

    cantidad_dias = (fin - inicio).days + 1
    return [inicio + datetime.timedelta(days=dia) for dia in range(cantidad_dias)]


def parsear_fecha_volante(valor: str, nombre_variable: str) -> datetime.date:
    try:
        return datetime.datetime.strptime(valor, "%d/%m/%Y").date()
    except ValueError as error:
        raise ValueError(f"Formato invalido en {nombre_variable}. Usa dd/mm/yyyy.") from error


def normalizar_dinero(valor: str) -> int:
    solo_digitos = "".join(caracter for caracter in valor if caracter.isdigit())
    return int(solo_digitos) if solo_digitos else 0


def construir_datos_volante(
    codigo_usuario: str,
    office_code: str,
    poliedro_code: str,
    codigo_oficina_planilla: str,
    dinero_volante: str,
    fecha_volante: datetime.date,
) -> dict:
    codigo_usuario = codigo_usuario.strip()
    return {
        "fecha": fecha_volante.strftime("%d/%m/%Y"),
        "office_code": office_code.strip(),
        "poliedro_code": poliedro_code.strip(),
        "codigo_oficina_planilla": codigo_oficina_planilla.strip(),
        "codigo_usuario": codigo_usuario,
        "usuario": codigo_usuario,
        "dinero": normalizar_dinero(dinero_volante),
    }
