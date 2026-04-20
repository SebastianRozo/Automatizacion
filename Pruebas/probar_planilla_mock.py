from datetime import datetime
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By


TABLE_PLANILLA = "cpContenido_WucFiltrosPlanilla_WucCargaInicialPlanilla_GrvRegistros"


def crear_driver() -> webdriver.Chrome:
    options = webdriver.ChromeOptions()
    #options.add_argument("--headless=new")
    return webdriver.Chrome(options=options)


def normalizar_dinero(valor: str) -> int:
    solo_digitos = "".join(caracter for caracter in valor if caracter.isdigit())
    return int(solo_digitos) if solo_digitos else 0


def normalizar_texto(valor: str) -> str:
    return " ".join((valor or "").strip().upper().split())


def clasificar_tipo_plan(plan: str) -> str:
    texto = normalizar_texto(plan)

    if "PORTABILIDAD" in texto:
        return "portabilidad"
    if "LINEA NUEVA" in texto:
        return "linea_nueva"
    if "MIGRACION UPGRADE" in texto or "UPGRADE" in texto:
        return "upgrade"
    return "otro"


def desmarcar_todas_las_filas(filas: list[dict]) -> None:
    for fila in filas:
        checkbox = fila["checkbox"]
        if checkbox.is_selected():
            checkbox.click()
        fila["marcada"] = False


def obtener_filas_planilla(driver: webdriver.Chrome) -> list[dict]:
    tabla = driver.find_element(By.ID, TABLE_PLANILLA)
    filas_html = tabla.find_elements(By.TAG_NAME, "tr")[1:]
    resultados = []

    for fila_html in filas_html:
        columnas = fila_html.find_elements(By.TAG_NAME, "td")
        if not columnas:
            continue

        checkbox = columnas[0].find_element(By.CSS_SELECTOR, "input[type='checkbox']")
        plan = columnas[9].text.strip()

        resultados.append({
            "numero": columnas[1].text.strip(),
            "fecha_activacion": columnas[8].text.strip(),
            "plan": plan,
            "tipo_plan": clasificar_tipo_plan(plan),
            "vr_total": normalizar_dinero(columnas[12].text),
            "checkbox": checkbox,
            "marcada": checkbox.is_selected(),
        })

    return resultados


def marcar_filas_por_tipo(filas: list[dict], tipo_plan_objetivo: str) -> None:
    for fila in filas:
        if fila["tipo_plan"] != tipo_plan_objetivo:
            continue

        checkbox = fila["checkbox"]
        if not checkbox.is_selected():
            checkbox.click()
        fila["marcada"] = True


def sumar_filas_marcadas(filas: list[dict]) -> int:
    return sum(fila["vr_total"] for fila in filas if fila["checkbox"].is_selected())


def contar_planes_marcados(filas: list[dict]) -> int:
    return sum(1 for fila in filas if fila["checkbox"].is_selected())


def parsear_fecha(fecha: str) -> datetime:
    return datetime.strptime(fecha.strip(), "%d/%m/%Y")


def obtener_portabilidad_mas_antigua(filas: list[dict]) -> dict | None:
    portabilidades = [
        fila
        for fila in filas
        if fila["checkbox"].is_selected() and fila["tipo_plan"] == "portabilidad"
    ]

    if not portabilidades:
        return None

    return min(portabilidades, key=lambda fila: parsear_fecha(fila["fecha_activacion"]))


def ejecutar_logica(driver: webdriver.Chrome, tipo_plan: str, dinero_volante: int) -> dict:
    filas = obtener_filas_planilla(driver)
    desmarcar_todas_las_filas(filas)
    marcar_filas_por_tipo(filas, tipo_plan)

    suma = sumar_filas_marcadas(filas)
    planes_restantes = contar_planes_marcados(filas)
    simular = suma == dinero_volante
    portabilidad_removida = None

    while suma > dinero_volante and not simular:
        portabilidad_antigua = obtener_portabilidad_mas_antigua(filas)
        if not portabilidad_antigua:
            break

        portabilidad_antigua["checkbox"].click()
        portabilidad_antigua["marcada"] = False
        portabilidad_removida = {
            "numero": portabilidad_antigua["numero"],
            "fecha_activacion": portabilidad_antigua["fecha_activacion"],
            "plan": portabilidad_antigua["plan"],
            "vr_total": portabilidad_antigua["vr_total"],
        }
        suma = sumar_filas_marcadas(filas)
        planes_restantes = contar_planes_marcados(filas)
        simular = suma == dinero_volante

    return {
        "tipo_plan": tipo_plan,
        "dinero_volante": dinero_volante,
        "suma_marcada": suma,
        "planes_restantes": planes_restantes,
        "simular": simular,
        "portabilidad_removida": portabilidad_removida,
    }


def imprimir_resultado(resultado: dict) -> None:
    print(f"Tipo plan: {resultado['tipo_plan']}")
    print(f"Dinero volante: {resultado['dinero_volante']}")
    print(f"Suma marcada: {resultado['suma_marcada']}")
    print(f"Planes restantes: {resultado['planes_restantes']}")
    print(f"Simular: {resultado['simular']}")
    if resultado["portabilidad_removida"]:
        removida = resultado["portabilidad_removida"]
        print(
            "Portabilidad removida: "
            f"No. {removida['numero']} | "
            f"Fecha {removida['fecha_activacion']} | "
            f"Valor {removida['vr_total']}"
        )
    print("-" * 60)


def main() -> None:
    html_path = Path(__file__).with_name("planilla_mock.html").resolve()
    driver = crear_driver()

    try:
        driver.get(html_path.as_uri())

        escenarios = [
            {"tipo_plan": "linea_nueva", "dinero_volante": 20000},
            {"tipo_plan": "upgrade", "dinero_volante": 40000},
            {"tipo_plan": "portabilidad", "dinero_volante": 25000},
        ]

        for escenario in escenarios:
            driver.get(html_path.as_uri())
            resultado = ejecutar_logica(
                driver,
                escenario["tipo_plan"],
                escenario["dinero_volante"],
            )
            imprimir_resultado(resultado)
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
