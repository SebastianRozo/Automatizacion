from collections import Counter
from difflib import SequenceMatcher
import unicodedata

try:
    from rapidfuzz import fuzz as rapidfuzz_fuzz
except ImportError:
    rapidfuzz_fuzz = None


TNS_MATCH_MIN_SCORE = 90


def normalizar_texto_tns(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto or "")
    texto = "".join(caracter for caracter in texto if not unicodedata.combining(caracter))
    return " ".join(texto.upper().split())


def falta_una_palabra(partes_volante: list[str], partes_tns: list[str]) -> bool:
    if abs(len(partes_volante) - len(partes_tns)) != 1:
        return False

    nombre_corto, nombre_largo = sorted(
        [partes_volante, partes_tns],
        key=len,
    )
    return not (Counter(nombre_corto) - Counter(nombre_largo))


def calcular_similitud_nombres(usuario_volante: str, usuario_tns: str) -> float:
    usuario_volante = normalizar_texto_tns(usuario_volante)
    usuario_tns = normalizar_texto_tns(usuario_tns)
    if not usuario_volante or not usuario_tns:
        return 0.0
    if usuario_volante == usuario_tns:
        return 100.0
    partes_volante = usuario_volante.split()
    partes_tns = usuario_tns.split()

    if falta_una_palabra(partes_volante, partes_tns):
        return 100.0

    if rapidfuzz_fuzz is not None:
        similitud_texto = float(rapidfuzz_fuzz.token_sort_ratio(usuario_volante, usuario_tns))
    else:
        volante_ordenado = " ".join(sorted(usuario_volante.split()))
        tns_ordenado = " ".join(sorted(usuario_tns.split()))
        similitud_texto = SequenceMatcher(None, volante_ordenado, tns_ordenado).ratio() * 100

    similitud_palabras = calcular_similitud_por_palabras(usuario_volante, usuario_tns)
    return max(similitud_texto, similitud_palabras)


def calcular_similitud_palabra(palabra_volante: str, palabra_tns: str) -> float:
    if rapidfuzz_fuzz is not None:
        return float(rapidfuzz_fuzz.ratio(palabra_volante, palabra_tns))

    return SequenceMatcher(None, palabra_volante, palabra_tns).ratio() * 100


def calcular_similitud_por_palabras(usuario_volante: str, usuario_tns: str) -> float:
    palabras_volante = usuario_volante.split()
    palabras_tns = usuario_tns.split()
    if not palabras_volante or not palabras_tns:
        return 0.0

    pares = []
    for indice_volante, palabra_volante in enumerate(palabras_volante):
        for indice_tns, palabra_tns in enumerate(palabras_tns):
            pares.append((
                calcular_similitud_palabra(palabra_volante, palabra_tns),
                indice_volante,
                indice_tns,
            ))

    pares.sort(reverse=True)
    usados_volante = set()
    usados_tns = set()
    total = 0.0

    for similitud, indice_volante, indice_tns in pares:
        if indice_volante in usados_volante or indice_tns in usados_tns:
            continue

        usados_volante.add(indice_volante)
        usados_tns.add(indice_tns)
        total += similitud

        if len(usados_volante) == len(palabras_volante):
            break

    return total / len(palabras_volante)


def obtener_variantes_busqueda_usuario(usuario: str) -> list[str]:
    partes = " ".join((usuario or "").split()).split()
    variantes = []

    def agregar_variante(partes_variante: list[str]) -> None:
        variante = " ".join(partes_variante).strip()
        if variante and variante not in variantes:
            variantes.append(variante)

    agregar_variante(partes)

    if len(partes) == 2:
        agregar_variante([partes[1], partes[0]])
    elif len(partes) >= 3:
        primera = partes[0]
        ultima = partes[-1]
        primer_apellido = partes[-2]

        agregar_variante([primer_apellido, primera])
        agregar_variante([primera, ultima])
        agregar_variante([ultima, primera])

        if len(partes) >= 4:
            segundo_nombre = partes[1]

            agregar_variante([primera, primer_apellido])
            agregar_variante([primera, segundo_nombre, ultima])
            agregar_variante([primera,primer_apellido,ultima])
            agregar_variante([ultima, primera, segundo_nombre])

        agregar_variante([*partes[-2:], *partes[:-2]])
        agregar_variante([partes[-1], *partes[:-1]])

        for parte in partes[-2:]:
            agregar_variante([parte])

        for parte in partes[:-2]:
            agregar_variante([parte])

    return variantes


def clasificar_tipo_plan(*bloques: str) -> tuple[str, str]:
    texto_analisis = normalizar_texto_tns(" ".join(bloque for bloque in bloques if bloque))

    reglas = [
        ("portabilidad", (("PORTABILIDAD",),)),
        ("linea_nueva", (("LINEA NUEVA",),)),
        ("upgrade", (("MIGRACION UPGRADE",), ("MIGRACION", "UPGRADE"))),
    ]

    for tipo_plan, grupos in reglas:
        if any(all(clave in texto_analisis for clave in grupo) for grupo in grupos):
            return tipo_plan, texto_analisis

    return "otro", texto_analisis
