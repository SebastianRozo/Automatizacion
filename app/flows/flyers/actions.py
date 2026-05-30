from urllib.parse import urljoin
import time

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import TimeoutException

from app.browser.actions import click, open_url, type_text, wait_present, selectInSelect, capture_screenshot
from app.config.selectors import (
    BOTON_CANCELAR_VOLANTE,
    BUTTON_FLYERS,
    BUTTON_SEND_PRINT_FLYERS,
    SELECT_ALL_VOLANTES,
    SELECT_DISTRIBUTOR,
    SELECT_FINALDATE,
    SELECT_INITIALDATE,
    SELECT_OFFICE,
    SELECT_TYPE,
)
from app.config.settings import FORM_READY_DELAY_SECONDS
from app.storage.main import get_office_folder
from app.template.codes_places.main import OFFICES
from app.flows.flyers.helpers import construir_datos_volante, obtener_fechas_consulta_volantes


VOLANTES_INDEX_PATH = "/Recaudo.PS/VolantesNIT/Index"
USUARIOS_VOLANTE_OMITIDOS_POR_OFICINA = {("01", "45096700"), ("02", "45096700")}


def obtener_oficina_desde_formulario(driver) -> str:
    select_oficina = Select(driver.find_element(By.ID, SELECT_OFFICE))
    return select_oficina.first_selected_option.text.strip()


def asegurar_formulario_volantes(driver) -> None:
    try:
        wait_present(driver, By.ID, SELECT_DISTRIBUTOR, timeout=5)
        return
    except TimeoutException:
        pass

    open_url(driver, urljoin(driver.current_url, VOLANTES_INDEX_PATH))
    wait_present(driver, By.ID, SELECT_DISTRIBUTOR)


def obtener_volantes_por_oficina(driver, codeplace, fecha_consulta):
    try:
        asegurar_formulario_volantes(driver)
        selectInSelect(driver, By.ID, SELECT_DISTRIBUTOR, codeplace)
        selectInSelect(driver, By.ID, SELECT_TYPE, "V")
        type_text(driver, By.ID, SELECT_INITIALDATE, fecha_consulta.strftime("%d/%m/%Y"))
        type_text(driver, By.ID, SELECT_FINALDATE, fecha_consulta.strftime("%d/%m/%Y"))
        print(
            "Formulario de consulta de volantes completo. "
            f"Fecha: {fecha_consulta.strftime('%d/%m/%Y')}. "
            f"Esperando {FORM_READY_DELAY_SECONDS}s antes de consultar."
        )
        time.sleep(FORM_READY_DELAY_SECONDS)
        click(driver, By.ID, BUTTON_FLYERS)
    except Exception as e:
        raise Exception(f"Error al obtener los volantes: {e}") from e


def get_flyers(driver) -> list[dict]:
    try:
        datos_volantes = []
        fechas_consulta = obtener_fechas_consulta_volantes()
        for office in OFFICES:
            codeplace = office["poliedro_code"]
            office_name = office["name"]

            for fecha_consulta in fechas_consulta:
                time.sleep(1)
                obtener_volantes_por_oficina(driver, codeplace, fecha_consulta)
                no_hay_volante = driver.find_elements(By.ID, "MessageSinReg")
                if no_hay_volante:
                    print(
                        f"NO HAY VOLANTES EN ESTA OFICINA PARA "
                        f"{fecha_consulta.strftime('%d/%m/%Y')}"
                    )
                    continue

                cantidad_de_volantes = driver.find_elements(By.CSS_SELECTOR, SELECT_ALL_VOLANTES)
                hrefs_volantes = [
                    volante.get_attribute("href")
                    for volante in cantidad_de_volantes
                    if volante.get_attribute("href")
                ]

                for i, href_volante in enumerate(hrefs_volantes):
                    if i > 0:
                        time.sleep(1)
                        obtener_volantes_por_oficina(driver, codeplace, fecha_consulta)
                    time.sleep(1)
                    cantidad_de_volantes = driver.find_elements(By.CSS_SELECTOR, SELECT_ALL_VOLANTES)

                    time.sleep(2)
                    folder = get_office_folder(office_name)
                    fecha_archivo = fecha_consulta.strftime("%Y%m%d")
                    capture_screenshot(driver, f"{folder}/Lista_Volantes_{office_name}_{fecha_archivo}_{i}.png")
                    time.sleep(1)

                    volante_objetivo = None
                    for volante in cantidad_de_volantes:
                        if volante.get_attribute("href") == href_volante:
                            volante_objetivo = volante
                            break

                    if volante_objetivo is None:
                        print(
                            f"NO SE ENCONTRO EL VOLANTE {i} EN LA OFICINA "
                            f"{office_name} PARA {fecha_consulta.strftime('%d/%m/%Y')}"
                        )
                        continue

                    filas = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
                    if i < len(filas):
                        columnas = filas[i].find_elements(By.TAG_NAME, "td")
                        dinero_volante = columnas[1].text.strip()
                        codigo_usuario = columnas[3].text.strip()

                        if (office["office_code"], codigo_usuario) in USUARIOS_VOLANTE_OMITIDOS_POR_OFICINA:
                            print(
                                f"Volante omitido para usuario {codigo_usuario} "
                                f"en oficina {office['office_code']} - {office_name}. Se sacara manual."
                            )
                            continue

                        datos_volante = construir_datos_volante(
                            codigo_usuario,
                            office["office_code"],
                            office["poliedro_code"],
                            office["planilla_code"],
                            dinero_volante,
                            fecha_consulta,
                        )
                        datos_volantes.append(datos_volante)

                    volante_objetivo.click()
                    time.sleep(3)
                    # Se deja desactivado el envio a impresion por ahora.
                   # click(driver, By.ID, BUTTON_SEND_PRINT_FLYERS)
                    time.sleep(2)
                    folder = get_office_folder(office_name)
                    capture_screenshot(driver, f"{folder}/screenshot_{office_name}_{fecha_archivo}_{i}.png")
                    time.sleep(1)
                    click(driver, By.ID, BOTON_CANCELAR_VOLANTE)
                    asegurar_formulario_volantes(driver)

        return datos_volantes
    except Exception as e:
        raise Exception(f"Error al obtener los volantes: {e}") from e


def download_flyers(driver, migration_selector: str, flyers_selector: str) -> list[dict]:
    try:
        click(driver, By.CSS_SELECTOR, migration_selector)
        click(driver, By.CSS_SELECTOR, flyers_selector)
        return get_flyers(driver)
    except Exception as e:
        raise Exception(f"Error al descargar los volantes: {e}") from e
