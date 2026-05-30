from urllib.parse import urljoin
import time
from datetime import date

from selenium.webdriver.common.by import By
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from app.browser.actions import click, open_url, selectInSelect, wait_present
from app.config.selectors import (
    BUTTON_CONFIRMAR_GENERACION,
    BUTTON_MENU,
    BUTTON_SPREADSHEETS,
    BUTTON_YES_SPREADSHEET,
    GENERATE_SPREADSHEETS,
    GO_TO_SPREADHEETS,
    SELECT_GENERATION_TYPE,
    SELECT_OFFICE,
    SELECT_PRODUCT,
    SELECT_SPREADSHEET_IN_SPREADSHEET,
    SELECT_SPREADSHEET_TYPE,
    SELECT_SPREADSHEETS,
    SELECT_TYPE_OF_SALE,
    SELECT_USER_NAME,
    TABLE_PLANILLA,
)
from app.config.settings import FORM_READY_DELAY_SECONDS
from app.flows.spreadsheets.helpers import (
    limpiar_texto,
    normalizar_dinero,
    parsear_fecha,
)


FORMULARIO_PLANILLADO_PATH = "/RPlanillado/GestionPlanillas/Generar/FiltrosPlanilla.aspx"


def es_fecha_activacion_hoy(fecha_activacion: str) -> bool:
    try:
        return parsear_fecha(fecha_activacion).date() == date.today()
    except ValueError:
        return False


def obtener_filas_planilla(driver) -> list[dict]:
    tabla = driver.find_element(By.ID, TABLE_PLANILLA)
    filas = tabla.find_elements(By.TAG_NAME, "tr")[1:]
    resultados = []
    for fila in filas:
        columnas = fila.find_elements(By.TAG_NAME, "td")
        if not columnas:
            continue
        fecha_activacion = limpiar_texto(columnas[8].text)
        if es_fecha_activacion_hoy(fecha_activacion):
            print(f"Fila omitida por ser activacion de hoy: {fecha_activacion}")
            continue

        resultados.append({
            "usuario": limpiar_texto(columnas[4].text),
            "fecha_activacion": fecha_activacion,
            "vr_total_planilla": normalizar_dinero(columnas[12].text),
        })
    return resultados


def check_first_checkbox(driver) -> None:
    tabla = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, TABLE_PLANILLA))
    )

    checkbox_header = tabla.find_element(
        By.CSS_SELECTOR,
        "tr.headerTablePl th input[type='checkbox']",
    )

    try:
        checkbox_header.click()
    except Exception:
        driver.execute_script("arguments[0].click();", checkbox_header)


def get_checkbox_por_usuario(driver, usuario_objetivo: str, fecha_activacion_objetivo: str | None = None):
    tabla = driver.find_element(By.ID, TABLE_PLANILLA)
    filas = tabla.find_elements(By.TAG_NAME, "tr")[1:]
    for fila in filas:
        columnas = fila.find_elements(By.TAG_NAME, "td")
        if not columnas:
            continue
        usuario = limpiar_texto(columnas[4].text)
        fecha_activacion = limpiar_texto(columnas[8].text)
        if fecha_activacion_objetivo and fecha_activacion != fecha_activacion_objetivo:
            continue
        checkbox = columnas[0].find_element(By.CSS_SELECTOR, "input[type='checkbox']")
        if usuario == usuario_objetivo:
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
        if not checkbox.is_selected():
            usuario = limpiar_texto(columnas[4].text)
            fecha_activacion = limpiar_texto(columnas[8].text)
            if es_fecha_activacion_hoy(fecha_activacion):
                continue
            plan = limpiar_texto(columnas[9].text)
            vr_total = normalizar_dinero(columnas[12].text)
            suma_planilla += vr_total
            filas_marcadas.append({
                "usuario": usuario,
                "fecha_activacion": fecha_activacion,
                "plan": plan,
                "vr_total_planilla": vr_total,
            })
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


def obtener_porta_antigua(driver, resultados_tns: list[dict]):
    tipos_por_usuario = {
        item["usuario"]: item["tipo_plan"]
        for item in resultados_tns
    }
    tabla = driver.find_element(By.ID, TABLE_PLANILLA)
    filas = tabla.find_elements(By.TAG_NAME, "tr")[1:]
    portabilidades = []
    for fila in filas:
        columnas = fila.find_elements(By.TAG_NAME, "td")
        if not columnas:
            continue
        usuario = limpiar_texto(columnas[4].text)
        fecha_activacion = limpiar_texto(columnas[8].text)
        if es_fecha_activacion_hoy(fecha_activacion):
            continue
        plan = limpiar_texto(columnas[9].text)
        vr_total = normalizar_dinero(columnas[12].text)
        checkbox = columnas[0].find_element(By.CSS_SELECTOR, "input[type='checkbox']")
        if tipos_por_usuario.get(usuario) == "portabilidad" and checkbox.is_selected():
            portabilidades.append({
                "usuario": usuario,
                "fecha_activacion": fecha_activacion,
                "plan": plan,
                "vr_total_planilla": vr_total,
                "checkbox": checkbox,
            })
    if not portabilidades:
        return None
    return min(
        portabilidades,
        key=lambda fila: parsear_fecha(fila["fecha_activacion"]),
    )


def contar_portabilidades_restantes(driver, resultados_tns: list[dict]) -> int:
    usuarios_portabilidad = {
        item["usuario"]
        for item in resultados_tns
        if item.get("tipo_plan") == "portabilidad"
    }

    if not usuarios_portabilidad:
        return 0

    tabla = driver.find_element(By.ID, TABLE_PLANILLA)
    filas = tabla.find_elements(By.TAG_NAME, "tr")[1:]
    cantidad = 0

    for fila in filas:
        columnas = fila.find_elements(By.TAG_NAME, "td")
        if not columnas:
            continue

        usuario = limpiar_texto(columnas[4].text)
        fecha_activacion = limpiar_texto(columnas[8].text)
        if es_fecha_activacion_hoy(fecha_activacion):
            continue
        checkbox = columnas[0].find_element(By.CSS_SELECTOR, "input[type='checkbox']")

        if usuario in usuarios_portabilidad and not checkbox.is_selected():
            cantidad += 1

    return cantidad


def seleccionar_primer_dia_mes(driver, start_date_id: str) -> None:
    click(driver, By.ID, start_date_id)
    time.sleep(1)

    candidatos = [
        "//td[normalize-space(.)='1' and not(contains(@class,'other')) and not(contains(@class,'disabled'))]",
        "//a[normalize-space(.)='1']",
        "//span[normalize-space(.)='1']",
    ]

    fin = time.time() + 10
    while time.time() < fin:
        for xpath in candidatos:
            elementos = driver.find_elements(By.XPATH, xpath)
            for elemento in elementos:
                if not elemento.is_displayed():
                    continue
                try:
                    elemento.click()
                except Exception:
                    driver.execute_script("arguments[0].click();", elemento)
                return
        time.sleep(1)

    raise TimeoutException("No fue posible seleccionar el dia 1 del calendario")


def click_con_reintento(driver, by, value: str, intentos: int = 3) -> None:
    ultimo_error = None
    for _ in range(intentos):
        try:
            click(driver, by, value)
            return
        except StaleElementReferenceException as error:
            ultimo_error = error
            time.sleep(1)

    if ultimo_error is not None:
        raise ultimo_error


def abrir_planillado(driver, forzar: bool = False) -> None:
    if not forzar and driver.find_elements(By.ID, SELECT_USER_NAME):
        return

    if forzar:
        open_url(driver, urljoin(driver.current_url, FORMULARIO_PLANILLADO_PATH))
        wait_present(driver, By.ID, SELECT_USER_NAME)
        return

    time.sleep(3)
    try:
        click(driver, By.CSS_SELECTOR, BUTTON_MENU, timeout=5)
        time.sleep(1)
        click(driver, By.CSS_SELECTOR, BUTTON_SPREADSHEETS)
        time.sleep(1)
        click(driver, By.XPATH, SELECT_SPREADSHEETS)
        time.sleep(3)
        click(driver, By.CSS_SELECTOR, GO_TO_SPREADHEETS)
        time.sleep(3)

        try:
            click(driver, By.CSS_SELECTOR, GENERATE_SPREADSHEETS, timeout=5)
        except TimeoutException:
            open_url(driver, urljoin(driver.current_url, FORMULARIO_PLANILLADO_PATH))
    except Exception:
        open_url(driver, urljoin(driver.current_url, FORMULARIO_PLANILLADO_PATH))

    time.sleep(3)
    wait_present(driver, By.ID, SELECT_USER_NAME)


def llenar_formulario_planillado(
    driver,
    codigo_activacion: str,
    codigo_oficina: str,
    tipo_generacion: str,
    tipo_planillado: str,
    planilla: str,
    producto: str,
    start_date_id: str,
) -> None:
    time.sleep(FORM_READY_DELAY_SECONDS)
    WebDriverWait(driver, 20).until(
        EC.visibility_of_element_located((By.ID, SELECT_GENERATION_TYPE))
    )
    WebDriverWait(driver, 20).until(
        EC.element_to_be_clickable((By.ID, SELECT_GENERATION_TYPE))
    )

    selectInSelect(driver, By.ID, SELECT_USER_NAME, codigo_activacion, timeout=20)
    time.sleep(2)
    selectInSelect(driver, By.ID, SELECT_OFFICE, codigo_oficina, timeout=20)
    time.sleep(2)
    selectInSelect(driver, By.ID, SELECT_GENERATION_TYPE, tipo_generacion, timeout=20)
    time.sleep(2)
    selectInSelect(driver, By.ID, SELECT_SPREADSHEET_TYPE, tipo_planillado, timeout=20)
    time.sleep(2)
    selectInSelect(driver, By.ID, SELECT_SPREADSHEET_IN_SPREADSHEET, planilla, timeout=20)
    time.sleep(2)
    WebDriverWait(driver, 25).until(
        EC.element_to_be_clickable((By.ID, SELECT_PRODUCT))
    )
    selectInSelect(driver, By.ID, SELECT_PRODUCT, producto, timeout=25)
    time.sleep(3)
    selectInSelect(driver, By.ID, SELECT_TYPE_OF_SALE, "1", timeout=20)
    time.sleep(FORM_READY_DELAY_SECONDS)

    time.sleep(2)
    seleccionar_primer_dia_mes(driver, start_date_id)
    time.sleep(2)
    click_con_reintento(driver, By.ID, BUTTON_CONFIRMAR_GENERACION)
    time.sleep(2)
    click(driver, By.ID, BUTTON_YES_SPREADSHEET, timeout=3)
    time.sleep(2)

    
