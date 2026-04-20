import argparse
import time
from datetime import datetime
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select


BUTTON_SPREADSHEETS = "a[href='/POL_MENU/Menu/GoToApp?IdItem=504']"
SELECT_SPREADSHEETS = "//a[contains(normalize-space(.), 'Planillado')]"
GO_TO_SPREADHEETS = "a[href='/POL_MENU/Menu/GoToApp?IdItem=251']"
GENERATE_SPREADSHEETS = "a[href='/GestionPlanillas/Generar/FiltrosPlanilla.aspx']"
SELECT_USER_NAME = "cpContenido_WucFiltrosPlanilla_DdlCodActivacion"
SELECT_OFFICE = "cpContenido_WucFiltrosPlanilla_DdlPuntoDeVenta"
SELECT_GENERATION_TYPE = "cpContenido_WucFiltrosPlanilla_DdlTipoGeneracion"
SELECT_SPREADSHEET_TYPE = "cpContenido_WucFiltrosPlanilla_DdlTipoPlanillado"
SELECT_SPREADSHEET_IN_SPREADSHEET = "cpContenido_WucFiltrosPlanilla_DdlPlanilla"
SELECT_PRODUCT = "cpContenido_WucFiltrosPlanilla_DdlProducto"
SELECT_TYPE_OF_SALE = "cpContenido_WucFiltrosPlanilla_DdlTipoVenta"
START_DATE = "cpContenido_WucFiltrosPlanilla_LblTxtFechaInicial"
END_DATE = "cpContenido_WucFiltrosPlanilla_LblTxtFechaFinal"
BUTTON_CONFIRMAR_GENERACION = "cpContenido_WucFiltrosPlanilla_BtnAceptar"
BUTTON_SIMULAR = "btnSimularMock"
BUTTON_GENERAR_PLANILLA = "btnGenerarPlanillaMock"
TABLE_PLANILLA = "cpContenido_WucFiltrosPlanilla_WucCargaInicialPlanilla_GrvRegistros"

DESCRIPCIONES_TNS_MOCK = {
    "YAMILE VILLAMIZAR ALBARRACIN": "LINEA NUEVA 26.1 E 46.9",
    "MARIA PORTA ANTIGUA": "PORTABILIDAD BASICA",
    "ANA PORTA NUEVA": "PORTABILIDAD PLUS",
    "CARLOS UPGRADE": "MIGRACION UPGRADE PREMIUM",
    "OTRO USUARIO": "PLAN LIBRE",
}


def crear_driver(headless: bool) -> webdriver.Chrome:
    options = webdriver.ChromeOptions()
    if headless:
        options.add_argument("--headless=new")
    return webdriver.Chrome(options=options)


def limpiar_texto(valor: str) -> str:
    valor = valor.replace("\xa0", " ").strip()
    return "" if valor == " " else valor


def normalizar_dinero(valor: str) -> int:
    solo_digitos = "".join(c for c in valor if c.isdigit())
    return int(solo_digitos) if solo_digitos else 0


def imprimir_y_log(driver: webdriver.Chrome, texto: str) -> None:
    print(texto)
    driver.execute_script("appendLog(arguments[0]);", texto)


def click_css(driver: webdriver.Chrome, selector: str) -> None:
    driver.find_element(By.CSS_SELECTOR, selector).click()


def click_xpath(driver: webdriver.Chrome, selector: str) -> None:
    driver.find_element(By.XPATH, selector).click()


def select_by_value(driver: webdriver.Chrome, element_id: str, value: str) -> None:
    Select(driver.find_element(By.ID, element_id)).select_by_value(value)


def set_input_value(driver: webdriver.Chrome, element_id: str, value: str) -> None:
    element = driver.find_element(By.ID, element_id)
    element.clear()
    element.send_keys(value)


def click_id_js(driver: webdriver.Chrome, element_id: str) -> None:
    driver.execute_script("document.getElementById(arguments[0]).click();", element_id)


def click_element_js(driver: webdriver.Chrome, element) -> None:
    driver.execute_script("arguments[0].click();", element)


def obtener_filas_planilla(driver) -> list[dict]:
    filas = driver.find_elements(
        By.CSS_SELECTOR,
        "#cpContenido_WucConsultarPlanilla_WucConsultarDatosPlanilla_GrvResultadosEstaticos tbody tr",
    )
    resultados = []
    for fila in filas[1:]:
        columnas = fila.find_elements(By.TAG_NAME, "td")
        if not columnas:
            continue
        resultados.append({
            "usuario": limpiar_texto(columnas[3].text),
            "fecha_activacion": limpiar_texto(columnas[7].text),
            "vr_total_planilla": normalizar_dinero(columnas[11].text),
        })
    return resultados


def manejar_tns_mock(item: dict):
    descripcion = DESCRIPCIONES_TNS_MOCK.get(item["usuario"], "PLAN LIBRE")
    descripcion = descripcion.strip().upper()
    if "PORTABILIDAD" in descripcion:
        tipo_plan = "portabilidad"
    elif "LINEA NUEVA" in descripcion:
        tipo_plan = "linea_nueva"
    elif "MIGRACION UPGRADE" in descripcion:
        tipo_plan = "upgrade"
    else:
        tipo_plan = "otro"

    item["descripcion_tns"] = descripcion
    item["tipo_plan"] = tipo_plan
    return item


def get_checkbox_por_usuario(driver, usuario_objetivo: str):
    tabla = driver.find_element(By.ID, TABLE_PLANILLA)
    filas = tabla.find_elements(By.TAG_NAME, "tr")[1:]
    for fila in filas:
        columnas = fila.find_elements(By.TAG_NAME, "td")
        if not columnas:
            continue
        usuario = limpiar_texto(columnas[4].text)
        checkbox = columnas[0].find_element(By.CSS_SELECTOR, "input[type='checkbox']")
        if usuario == usuario_objetivo:
            driver.execute_script("resaltarFilaPorNumero(arguments[0]);", limpiar_texto(columnas[1].text))
            return checkbox
    return None


def validate_money(driver, dinero_volante: int) -> dict:
    tabla = driver.find_element(By.ID, TABLE_PLANILLA)
    filas = tabla.find_elements(By.TAG_NAME, "tr")[1:]
    suma_planilla = 0
    filas_marcadas = []

    for fila in filas:
        columnas = fila.find_elements(By.TAG_NAME, "td")
        if not columnas:
            continue
        checkbox = columnas[0].find_element(By.CSS_SELECTOR, "input[type='checkbox']")
        if checkbox.is_selected():
            usuario = limpiar_texto(columnas[4].text)
            fecha_activacion = limpiar_texto(columnas[8].text)
            plan = limpiar_texto(columnas[9].text)
            vr_total = normalizar_dinero(columnas[12].text)
            suma_planilla += vr_total
            filas_marcadas.append({
                "usuario": usuario,
                "fecha_activacion": fecha_activacion,
                "plan": plan,
                "vr_total_planilla": vr_total,
            })

    driver.execute_script("actualizarResumen();")
    return {
        "dinero_volante": dinero_volante,
        "suma_planilla": suma_planilla,
        "coincide": suma_planilla == dinero_volante,
        "faltante": max(dinero_volante - suma_planilla, 0),
        "excedente": max(suma_planilla - dinero_volante, 0),
        "filas_marcadas": filas_marcadas,
    }


def contar_planes_marcados(driver) -> int:
    tabla = driver.find_element(By.ID, TABLE_PLANILLA)
    filas = tabla.find_elements(By.TAG_NAME, "tr")[1:]
    cantidad = 0
    for fila in filas:
        columnas = fila.find_elements(By.TAG_NAME, "td")
        if not columnas:
            continue
        checkbox = columnas[0].find_element(By.CSS_SELECTOR, "input[type='checkbox']")
        if checkbox.is_selected():
            cantidad += 1
    return cantidad


def parsear_fecha(fecha: str) -> datetime:
    fecha = limpiar_texto(fecha)
    fecha = fecha.replace("a.m.", "AM").replace("p.m.", "PM")
    return datetime.strptime(fecha, "%d/%m/%Y %I:%M:%S %p")


def obtener_porta_antigua(driver, resultados_tns: list[dict]):
    tipos_por_usuario = {item["usuario"]: item["tipo_plan"] for item in resultados_tns}
    tabla = driver.find_element(By.ID, TABLE_PLANILLA)
    filas = tabla.find_elements(By.TAG_NAME, "tr")[1:]
    portabilidades = []

    for fila in filas:
        columnas = fila.find_elements(By.TAG_NAME, "td")
        if not columnas:
            continue
        usuario = limpiar_texto(columnas[4].text)
        fecha_activacion = limpiar_texto(columnas[8].text)
        plan = limpiar_texto(columnas[9].text)
        vr_total = normalizar_dinero(columnas[12].text)
        checkbox = columnas[0].find_element(By.CSS_SELECTOR, "input[type='checkbox']")
        if tipos_por_usuario.get(usuario) == "portabilidad" and not checkbox.is_selected():
            portabilidades.append({
                "usuario": usuario,
                "fecha_activacion": fecha_activacion,
                "plan": plan,
                "vr_total_planilla": vr_total,
                "checkbox": checkbox,
            })

    if not portabilidades:
        return None

    return min(portabilidades, key=lambda fila: parsear_fecha(fila["fecha_activacion"]))


def contar_portabilidades_restantes(driver, resultados_tns: list[dict]) -> int:
    usuarios_portabilidad = {
        item["usuario"]
        for item in resultados_tns
        if item.get("tipo_plan") == "portabilidad"
    }

    if not usuarios_portabilidad:
        driver.execute_script("setPortabilidadesRestantes(arguments[0]);", 0)
        return 0

    tabla = driver.find_element(By.ID, TABLE_PLANILLA)
    filas = tabla.find_elements(By.TAG_NAME, "tr")[1:]
    cantidad = 0
    for fila in filas:
        columnas = fila.find_elements(By.TAG_NAME, "td")
        if not columnas:
            continue
        usuario = limpiar_texto(columnas[4].text)
        checkbox = columnas[0].find_element(By.CSS_SELECTOR, "input[type='checkbox']")
        if usuario in usuarios_portabilidad and not checkbox.is_selected():
            cantidad += 1

    driver.execute_script("setPortabilidadesRestantes(arguments[0]);", cantidad)
    return cantidad


def desmarcar_todo(driver) -> None:
    tabla = driver.find_element(By.ID, TABLE_PLANILLA)
    filas = tabla.find_elements(By.TAG_NAME, "tr")[1:]
    for fila in filas:
        columnas = fila.find_elements(By.TAG_NAME, "td")
        if not columnas:
            continue
        checkbox = columnas[0].find_element(By.CSS_SELECTOR, "input[type='checkbox']")
        if checkbox.is_selected():
            click_element_js(driver, checkbox)
    driver.execute_script("actualizarResumen();")


def navegar_hasta_generar(driver: webdriver.Chrome, delay: float) -> None:
    click_css(driver, BUTTON_SPREADSHEETS)
    imprimir_y_log(driver, "Click menu Planillado")
    time.sleep(delay)

    click_xpath(driver, SELECT_SPREADSHEETS)
    imprimir_y_log(driver, "Click acceso Planillado")
    time.sleep(delay)

    click_css(driver, GO_TO_SPREADHEETS)
    imprimir_y_log(driver, "Click Gestion Planillas")
    time.sleep(delay)

    click_css(driver, GENERATE_SPREADSHEETS)
    imprimir_y_log(driver, "Click Generar Planilla")
    time.sleep(delay)


def llenar_formulario_generacion(driver: webdriver.Chrome, datos_volante: dict, producto: str, delay: float) -> None:
    select_by_value(driver, SELECT_USER_NAME, datos_volante["codigo_activacion"])
    time.sleep(delay)
    select_by_value(driver, SELECT_OFFICE, datos_volante["poliedro_code"])
    time.sleep(delay)
    select_by_value(driver, SELECT_TYPE_OF_SALE, datos_volante.get("tipo_venta", "4"))
    time.sleep(delay)
    select_by_value(driver, SELECT_GENERATION_TYPE, datos_volante.get("tipo_generacion", "1"))
    time.sleep(delay)
    select_by_value(driver, SELECT_SPREADSHEET_TYPE, datos_volante.get("tipo_planillado", "1"))
    time.sleep(delay)
    select_by_value(driver, SELECT_SPREADSHEET_IN_SPREADSHEET, datos_volante.get("planilla", "1"))
    time.sleep(delay)
    select_by_value(driver, SELECT_PRODUCT, producto)
    time.sleep(delay)
    set_input_value(driver, START_DATE, datos_volante.get("fecha_inicial", "20/04/2026"))
    time.sleep(delay)
    set_input_value(driver, END_DATE, datos_volante.get("fecha_final", "20/04/2026"))
    time.sleep(delay)
    driver.execute_script("setDineroVolante(arguments[0]);", datos_volante["dinero"])


def procesar_producto(driver: webdriver.Chrome, datos_volante: dict, producto: str, delay: float, solo_formulario: bool) -> bool:
    llenar_formulario_generacion(driver, datos_volante, producto, delay)
    imprimir_y_log(driver, f"Formulario listo para producto {producto}")
    time.sleep(delay)

    if solo_formulario:
        imprimir_y_log(driver, "Modo solo formulario activo. No se ejecuta Generar ni el flujo posterior.")
        return True

    driver.find_element(By.ID, BUTTON_CONFIRMAR_GENERACION).click()
    imprimir_y_log(driver, f"Generando mock para producto {producto}")
    time.sleep(delay)

    desmarcar_todo(driver)
    resultados = obtener_filas_planilla(driver)
    resultados_tns = []
    driver.execute_script("setUsuariosProcesados(arguments[0]);", len(resultados))

    for item in resultados:
        imprimir_y_log(driver, f"Consulta: {item}")
        resultado = manejar_tns_mock(item)
        resultados_tns.append(resultado)

        if resultado["tipo_plan"] == "linea_nueva":
            checkbox = get_checkbox_por_usuario(driver, resultado["usuario"])
            if checkbox and not checkbox.is_selected():
                click_element_js(driver, checkbox)
                driver.execute_script("actualizarResumen();")
                imprimir_y_log(driver, f"Checkbox linea_nueva marcado para {resultado['usuario']}")
        elif resultado["tipo_plan"] == "upgrade":
            checkbox = get_checkbox_por_usuario(driver, resultado["usuario"])
            if checkbox and not checkbox.is_selected():
                click_element_js(driver, checkbox)
                driver.execute_script("actualizarResumen();")
                imprimir_y_log(driver, f"Checkbox upgrade marcado para {resultado['usuario']}")

        imprimir_y_log(driver, f"TNS: {resultado}")
        imprimir_y_log(driver, f"Planes marcados: {contar_planes_marcados(driver)}")
        imprimir_y_log(driver, f"Portabilidades restantes: {contar_portabilidades_restantes(driver, resultados_tns)}")
        time.sleep(delay)

    validacion = validate_money(driver, datos_volante["dinero"])
    imprimir_y_log(driver, f"Validacion inicial: {validacion}")
    imprimir_y_log(driver, f"Portabilidades restantes: {contar_portabilidades_restantes(driver, resultados_tns)}")
    time.sleep(delay)

    while not validacion["coincide"] and validacion["faltante"] > 0:
        porta_antigua = obtener_porta_antigua(driver, resultados_tns)
        if porta_antigua is None:
            imprimir_y_log(driver, "No hay mas portabilidades para marcar en este producto")
            break

        click_element_js(driver, porta_antigua["checkbox"])
        driver.execute_script("actualizarResumen();")
        imprimir_y_log(driver, f"Portabilidad mas antigua marcada: {porta_antigua}")
        imprimir_y_log(driver, f"Planes marcados: {contar_planes_marcados(driver)}")
        imprimir_y_log(driver, f"Portabilidades restantes: {contar_portabilidades_restantes(driver, resultados_tns)}")
        validacion = validate_money(driver, datos_volante["dinero"])
        imprimir_y_log(driver, f"Validacion despues de portabilidad: {validacion}")
        time.sleep(delay)

    if validacion["coincide"]:
        click_id_js(driver, BUTTON_SIMULAR)
        time.sleep(delay)
        click_id_js(driver, BUTTON_GENERAR_PLANILLA)
        imprimir_y_log(driver, f"Flujo completado con producto {producto}")
        return True

    imprimir_y_log(driver, f"Producto {producto} no logro cuadrar el dinero")
    return False


def ejecutar_flujo_completo(driver: webdriver.Chrome, datos_volante: dict, delay: float, solo_formulario: bool) -> None:
    html_path = Path(__file__).with_name("flujo_real_mock.html").resolve()
    driver.get(html_path.as_uri())
    driver.execute_script("limpiarLog();")
    driver.execute_script("setDineroVolante(arguments[0]);", datos_volante["dinero"])
    imprimir_y_log(driver, f"Datos volante: {datos_volante}")
    time.sleep(delay)

    navegar_hasta_generar(driver, delay)

    for producto in datos_volante.get("productos", ["3", "5", "7"]):
        exito = procesar_producto(driver, datos_volante, producto, delay, solo_formulario)
        if exito:
            break


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--delay", type=float, default=1.2)
    parser.add_argument("--pause-final", type=float, default=8.0)
    parser.add_argument("--solo-formulario", action="store_true")
    args = parser.parse_args()

    datos_volante = {
        "office_code": "02",
        "poliedro_code": "D1262.00002",
        "usuario": "VOLANTE MOCK",
        "codigo_activacion": "45965517",
        "dinero": 111900,
        "tipo_venta": "4",
        "tipo_generacion": "1",
        "tipo_planillado": "1",
        "planilla": "1",
        "productos": ["3", "5", "7"],
        "fecha_inicial": "20/04/2026",
        "fecha_final": "20/04/2026",
    }

    driver = crear_driver(args.headless)
    try:
        ejecutar_flujo_completo(driver, datos_volante, args.delay, args.solo_formulario)
        time.sleep(args.pause_final)
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
