from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
import time
from datetime import datetime
from urllib.parse import urljoin
from app.browser.actions import (
    click,
    open_url,
    type_text,
    wait_present,
    selectInSelect,
)
from app.desktop.actions import manejar_tns
from app.config.selectors import (
    BUTTON_MENU,
    BUTTON_SPREADSHEETS,
    SELECT_SPREADSHEETS,
    GO_TO_SPREADHEETS,
    GENERATE_SPREADSHEETS,
    BUTTON_CONFIRMAR_GENERACION,
    SELECT_USER_NAME,
    SELECT_OFFICE,
    SELECT_GENERATION_TYPE,
    SELECT_SPREADSHEET_TYPE,
    SELECT_SPREADSHEET_IN_SPREADSHEET,
    SELECT_PRODUCT,
    SELECT_TYPE_OF_SALE,
    TABLE_PLANILLA
)


def limpiar_texto(valor: str) -> str:
    valor = valor.replace("\xa0", " ").strip()
    return "" if valor == " " else valor


def normalizar_dinero(valor: str) -> int:
    solo_digitos = "".join(c for c in valor if c.isdigit())
    return int(solo_digitos) if solo_digitos else 0


def obtener_filas_planilla(driver) -> list[dict]:
    filas = driver.find_elements(
        By.CSS_SELECTOR,
        "#cpContenido_WucConsultarPlanilla_WucConsultarDatosPlanilla_GrvResultadosEstaticos tbody tr"
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
            return checkbox
    return None

def validate_money(driver,dinero_volante:int)->dict:
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
    return min(
        portabilidades,
        key=lambda fila: parsear_fecha(fila["fecha_activacion"])
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
        checkbox = columnas[0].find_element(By.CSS_SELECTOR, "input[type='checkbox']")

        if usuario in usuarios_portabilidad and not checkbox.is_selected():
            cantidad += 1

    return cantidad


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
        return ["3", "5", "7"]

    productos = datos_volante.get("productos")
    if isinstance(productos, (list, tuple)):
        valores = [str(producto).strip() for producto in productos if str(producto).strip()]
        if valores:
            return valores

    producto = datos_volante.get("producto")
    if producto:
        return [str(producto).strip()]

    return ["3", "5", "7"]

def go_to_spreadsheets(driver, datos_volante: dict | None = None) -> None:
    try:
        time.sleep(1)
        try:
            click(driver,By.CSS_SELECTOR,BUTTON_MENU,timeout=5)
        except Exception:
            open_url(driver, urljoin(driver.current_url, "/Recaudo.PS/Dispatcher/MainMenu"))

        time.sleep(1)
        click(driver,By.CSS_SELECTOR,BUTTON_SPREADSHEETS)
        time.sleep(1)
        click(driver,By.XPATH,SELECT_SPREADSHEETS)
        time.sleep(1)
        click(driver,By.CSS_SELECTOR,GO_TO_SPREADHEETS)
        time.sleep(1)

        click(driver,By.CSS_SELECTOR,GENERATE_SPREADSHEETS)
        time.sleep(1)

        codigo_activacion = obtener_valor_select(
            datos_volante,
            "codigo_activacion",
            "user_code",
            default="45965517",
        )
        codigo_oficina = obtener_valor_select(
            datos_volante,
            "codigo_punto_venta",
            "codigo_oficina_planilla",
            "poliedro_code",
        )
        tipo_venta = obtener_valor_select(datos_volante, "tipo_venta", default="4")
        tipo_generacion = obtener_valor_select(datos_volante, "tipo_generacion", default="1")
        tipo_planillado = obtener_valor_select(datos_volante, "tipo_planillado", default="1")
        planilla = obtener_valor_select(datos_volante, "planilla", default="1")
        productos = obtener_valores_producto(datos_volante)

        click(driver,By.ID,SELECT_USER_NAME)
        time.sleep(1)
        selectInSelect(driver,By.ID,SELECT_USER_NAME,codigo_activacion)

        time.sleep(1)
        click(driver,By.ID,SELECT_OFFICE)
        time.sleep(1)
        selectInSelect(driver,By.ID,SELECT_OFFICE,codigo_oficina)

        time.sleep(1)
        click(driver,By.ID,SELECT_TYPE_OF_SALE)
        time.sleep(1)
        selectInSelect(driver,By.ID,SELECT_TYPE_OF_SALE,tipo_venta)

        time.sleep(1)
        click(driver,By.ID,SELECT_GENERATION_TYPE)
        time.sleep(1)
        selectInSelect(driver,By.ID,SELECT_GENERATION_TYPE,tipo_generacion)

        time.sleep(1)
        click(driver,By.ID,SELECT_SPREADSHEET_TYPE)
        time.sleep(1)
        selectInSelect(driver,By.ID,SELECT_SPREADSHEET_TYPE,tipo_planillado)

        time.sleep(1)
        click(driver,By.ID,SELECT_SPREADSHEET_IN_SPREADSHEET)
        time.sleep(1)
        selectInSelect(driver,By.ID,SELECT_SPREADSHEET_IN_SPREADSHEET,planilla)

        for producto in productos:
            time.sleep(1)
            click(driver,By.ID,SELECT_PRODUCT)
            time.sleep(1)
            selectInSelect(driver,By.ID,SELECT_PRODUCT,producto)
            print(f"Formulario llenado hasta producto: {producto}")

            # time.sleep(1)
            # click(driver,By.ID,BUTTON_CONFIRMAR_GENERACION)
            # time.sleep(2)
            #
            # print(f"Producto generado: {producto}")
            #
            # resultados = obtener_filas_planilla(driver)
            # resultados_tns = []
            #
            # for item in resultados:
            #     resultado = manejar_tns(item)
            #     resultados_tns.append(resultado)
            #
            #     if resultado["tipo_plan"] == "linea_nueva":
            #         checkbox = get_checkbox_por_usuario(driver, resultado["usuario"])
            #         if checkbox and not checkbox.is_selected():
            #             checkbox.click()
            #     elif resultado["tipo_plan"] == "upgrade":
            #         checkbox = get_checkbox_por_usuario(driver,resultado["usuario"])
            #         if checkbox and not checkbox.is_selected():
            #             checkbox.click()
            #     print(resultado)
            #     print(f"Planes marcados: {contar_planes_marcados(driver)}")
            #
            # dinero_volante = None
            # if datos_volante is not None:
            #     dinero_volante = datos_volante.get("dinero")
            #     if dinero_volante is None:
            #         dinero_volante = datos_volante.get("dinero_volante")
            #
            # if dinero_volante is not None:
            #     validacion = validate_money(driver, dinero_volante)
            #     print(validacion)
            #     print(f"Portabilidades restantes: {contar_portabilidades_restantes(driver, resultados_tns)}")
            #
            #     while not validacion["coincide"] and validacion["faltante"] > 0:
            #         porta_antigua = obtener_porta_antigua(driver, resultados_tns)
            #         if porta_antigua is None:
            #             break
            #
            #         porta_antigua["checkbox"].click()
            #         print(f"Portabilidad mas antigua marcada: {porta_antigua}")
            #         print(f"Planes marcados: {contar_planes_marcados(driver)}")
            #         validacion = validate_money(driver, dinero_volante)
            #         print(validacion)
            #         print(f"Portabilidades restantes: {contar_portabilidades_restantes(driver, resultados_tns)}")
            #
            #     if validacion["coincide"]:
            #         break

            break

    except Exception as e:
        raise Exception(f"Error al ir a las planillas: {e}") from e
