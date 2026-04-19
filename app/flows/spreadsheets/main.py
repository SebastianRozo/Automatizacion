from app.config.selectors import SELECT_ASESOR
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
import time
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
    BUTTON_CONSULTAR_PLANILLA,
    SELECT_PUNTO_VENTA,
    SELECT_TIPO_VENTA,
    SELECT_TIPO_PLANILLADO,
    SELECT_PLANILLADO,
    SELECT_PRODUCTO,
    INPUT_PLANILLA,
    BOTON_SEGUIR,
    BOTON_ACEPTAR_CONSULTA
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

def go_to_spreadsheets(driver)-> None:
    try:
        #click(driver,By.CSS_SELECTOR,BUTTON_MENU)
        time.sleep(1)
        click(driver,By.CSS_SELECTOR,BUTTON_SPREADSHEETS)
        time.sleep(1)
        click(driver,By.XPATH,SELECT_SPREADSHEETS)
        time.sleep(1)
        click(driver,By.CSS_SELECTOR,GO_TO_SPREADHEETS)
        time.sleep(1)
        
        click(driver,By.CSS_SELECTOR,BUTTON_CONSULTAR_PLANILLA)
        time.sleep(1)
        click(driver,By.ID,SELECT_ASESOR)
        time.sleep(1)
        selectInSelect(driver,By.ID,SELECT_ASESOR,"45965517")

        time.sleep(1)
        click(driver,By.ID,SELECT_PUNTO_VENTA)
        time.sleep(1)
        selectInSelect(driver,By.ID,SELECT_PUNTO_VENTA,"D1262.00002")

        time.sleep(1)
        click(driver,By.ID,SELECT_TIPO_VENTA)
        time.sleep(1)
        selectInSelect(driver,By.ID,SELECT_TIPO_VENTA,"4")

        time.sleep(1)
        click(driver,By.ID,SELECT_TIPO_PLANILLADO)
        time.sleep(1)
        selectInSelect(driver,By.ID,SELECT_TIPO_PLANILLADO,"1")

        time.sleep(1)
        click(driver,By.ID,SELECT_PLANILLADO)
        time.sleep(1)
        selectInSelect(driver,By.ID,SELECT_PLANILLADO,"1")

        time.sleep(1)
        click(driver,By.ID,SELECT_PRODUCTO)
        time.sleep(1)
        selectInSelect(driver,By.ID,SELECT_PRODUCTO,"5")

        time.sleep(1)
        click(driver,By.ID,INPUT_PLANILLA)
        time.sleep(1)
        type_text(driver,By.ID,INPUT_PLANILLA,"25371759")

        time.sleep(1)
        click(driver,By.ID,BOTON_SEGUIR)

        time.sleep(1)
        click(driver,By.ID,BOTON_ACEPTAR_CONSULTA)
        time.sleep(2)
        resultados = obtener_filas_planilla(driver)
        for item in resultados:
            resultado = manejar_tns(item)
            print(resultado)
    except Exception as e:
        raise Exception(f"Error al ir a las planillas: {e}") from e
