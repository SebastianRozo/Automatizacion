import datetime


def get_before_day() -> datetime.date:
    return datetime.date.today() - datetime.timedelta(days=1)


def normalizar_dinero(valor: str) -> int:
    solo_digitos = "".join(caracter for caracter in valor if caracter.isdigit())
    return int(solo_digitos) if solo_digitos else 0


def construir_datos_volante(
    codigo_usuario: str,
    office_code: str,
    poliedro_code: str,
    codigo_oficina_planilla: str,
    dinero_volante: str,
) -> dict:
    codigo_usuario = codigo_usuario.strip()
    return {
        "fecha": get_before_day().strftime("%d/%m/%Y"),
        "office_code": office_code.strip(),
        "poliedro_code": poliedro_code.strip(),
        "codigo_oficina_planilla": codigo_oficina_planilla.strip(),
        "codigo_usuario": codigo_usuario,
        "usuario": codigo_usuario,
        "dinero": normalizar_dinero(dinero_volante),
    }
