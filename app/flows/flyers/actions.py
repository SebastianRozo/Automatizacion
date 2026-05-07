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
from app.flows.flyers.helpers import construir_datos_volante, get_before_day


VOLANTES_INDEX_PATH = "/Recaudo.PS/VolantesNIT/Index"


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


def obtener_volantes_por_oficina(driver, codeplace):
    try:
        asegurar_formulario_volantes(driver)
        selectInSelect(driver, By.ID, SELECT_DISTRIBUTOR, codeplace)
        selectInSelect(driver, By.ID, SELECT_TYPE, "V")
        type_text(driver, By.ID, SELECT_INITIALDATE, get_before_day().strftime("%d/%m/%Y"))
        type_text(driver, By.ID, SELECT_FINALDATE, get_before_day().strftime("%d/%m/%Y"))
        print(
            "Formulario de consulta de volantes completo. "
            f"Esperando {FORM_READY_DELAY_SECONDS}s antes de consultar."
        )
        time.sleep(FORM_READY_DELAY_SECONDS)
        click(driver, By.ID, BUTTON_FLYERS)
    except Exception as e:
        raise Exception(f"Error al obtener los volantes: {e}") from e


def get_flyers(driver) -> list[dict]:
    try:
        datos_volantes = []
        for office in OFFICES:
            codeplace = office["poliedro_code"]
            office_name = office["name"]
            time.sleep(1)
            obtener_volantes_por_oficina(driver, codeplace)
            no_hay_volante = driver.find_elements(By.ID, "MessageSinReg")
            if no_hay_volante:
                print("NO HAY VOLANTES EN ESTA OFICINA")
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
                    obtener_volantes_por_oficina(driver, codeplace)
                time.sleep(1)
                cantidad_de_volantes = driver.find_elements(By.CSS_SELECTOR, SELECT_ALL_VOLANTES)

                driver.execute_script("document.body.style.zoom='100%'")
                time.sleep(2)
                folder = get_office_folder(office_name)
                capture_screenshot(driver, f"{folder}/Lista_Volantes_{office_name}_{i}.png")
                time.sleep(1)
                
                volante_objetivo = None
                for volante in cantidad_de_volantes:
                    if volante.get_attribute("href") == href_volante:
                        volante_objetivo = volante
                        break

                if volante_objetivo is None:
                    print(f"NO SE ENCONTRO EL VOLANTE {i} EN LA OFICINA {office_name}")
                    continue

                filas = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
                if i < len(filas):
                    columnas = filas[i].find_elements(By.TAG_NAME, "td")
                    dinero_volante = columnas[1].text.strip()
                    codigo_usuario = columnas[3].text.strip()

                    datos_volante = construir_datos_volante(
                        codigo_usuario,
                        office["office_code"],
                        office["poliedro_code"],
                        office["planilla_code"],
                        dinero_volante,
                    )
                    datos_volantes.append(datos_volante)

                volante_objetivo.click()
                time.sleep(3)
                # Se deja desactivado el envio a impresion por ahora.
                #click(driver, By.ID, BUTTON_SEND_PRINT_FLYERS)
                driver.execute_script("document.body.style.zoom='50%'")
                time.sleep(2)
                folder = get_office_folder(office_name)
                capture_screenshot(driver, f"{folder}/screenshot_{office_name}_{i}.png")
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
