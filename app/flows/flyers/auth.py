from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import TimeoutException
import time
import datetime
from urllib.parse import urljoin

from app.browser.actions import (
    click,
    open_url,
    type_text,
    wait_clickable,
    wait_present,
    selectInSelect,
    capture_screenshot,
)
from app.flows.spreadsheets.main import go_to_spreadsheets
from app.storage.main import get_office_folder
from app.browser.driver import create_driver
from app.template.codes_places.main import OFFICES
from app.config.selectors import (
    LOGIN_BUTTON_ID,
    PASSWORD_INPUT_ID,
    SELECTOR_FLYERS_NIT,
    TOKEN_INPUT_ID,
    TOKEN_LOGIN_BUTTON_ID,
    USER_INPUT_ID,
    SELECTOR_MIGRATION_BUTTON,
    SELECT_DISTRIBUTOR,
    SELECT_TYPE,
    SELECT_FINALDATE,
    SELECT_INITIALDATE,
    BUTTON_FLYERS,
    BUTTON_NEW_SEARCH,
    SELECT_ALL_VOLANTES,
    BOTON_CANCELAR_VOLANTE,
    SELECT_OFFICE,
)
from app.config.settings import POLIEDRO_PASSWORD, POLIEDRO_URL, POLIEDRO_USERNAME


VOLANTES_INDEX_PATH = "/Recaudo.PS/VolantesNIT/Index"


def login() -> None:
    driver = create_driver()

    try:
        open_url(driver, POLIEDRO_URL)
        submit_credentials(driver, POLIEDRO_USERNAME, POLIEDRO_PASSWORD)
        token = input("Ingrese el token: ")
        submit_token(driver, token)
        #downloadFlyers(driver)
        time.sleep(3)
        go_to_spreadsheets(driver)
        time.sleep(25)
    finally:
        driver.quit()


def submit_credentials(driver, username: str, password: str) -> None:

    try:
        if not username or not password:
            raise ValueError(
                "Faltan credenciales. Configura POLIEDRO_USERNAME y POLIEDRO_PASSWORD "
            )

        type_text(driver, By.ID, USER_INPUT_ID, username)

        type_text(driver, By.ID, PASSWORD_INPUT_ID, password)
        click(driver, By.ID, LOGIN_BUTTON_ID)
        wait_clickable(driver, By.ID, TOKEN_INPUT_ID)
    except Exception as e:
        raise Exception("Error al ingresar los datos de usuario")


def submit_token(driver, token: str) -> None:
    try:
        type_text(driver, By.ID, TOKEN_INPUT_ID, token)
        click(driver, By.ID, TOKEN_LOGIN_BUTTON_ID)
    except Exception as e:
        raise Exception("Error obtener el token")


def getBeforeDay() -> str:
    yesterday = datetime.date.today() - datetime.timedelta(days=1)
    return yesterday

# Esto limpia el valor del dinero para dejarlo solo como numero entero.
def normalizar_dinero(valor: str) -> int:
    solo_digitos = "".join(caracter for caracter in valor if caracter.isdigit())
    return int(solo_digitos) if solo_digitos else 0

# Esto construye el diccionario final combinando oficina,
# usuario del volante y dinero ya normalizado.
def construir_datos_volante(
    usuario_volante: str,
    office_code: str,
    poliedro_code: str,
    dinero_volante: str,
) -> dict:
    usuario = usuario_volante.strip()
    return {
        "office_code": office_code.strip(),
        "poliedro_code": poliedro_code.strip(),
        "usuario": usuario,
        "dinero": normalizar_dinero(dinero_volante),
    }


# Esto toma la oficina directamente desde el select del formulario.
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

def obtenerVolantesPorOficina(driver, codeplace):
    try:
        # Esto es para busqueda de los volantes por oficina
        asegurar_formulario_volantes(driver)
        selectInSelect(driver, By.ID, SELECT_DISTRIBUTOR, codeplace)
        selectInSelect(driver, By.ID, SELECT_TYPE, "V")
        type_text(
            driver, By.ID, SELECT_INITIALDATE, getBeforeDay().strftime("%d/%m/%Y")
        )
        type_text(driver, By.ID, SELECT_FINALDATE, getBeforeDay().strftime("%d/%m/%Y"))
        click(driver, By.ID, BUTTON_FLYERS)
    except Exception as e:
        raise Exception(f"Error al obtener los volantes: {e}") from e


def getFlyers(driver) -> str:
    try:
        for office in OFFICES:
            codeplace = office["poliedro_code"]
            office_name = office["name"]
            time.sleep(1)
            obtenerVolantesPorOficina(driver, codeplace)
            # VALIDACION DE CAMPO DE VALOR EFECTIVO
            No_hay_volante = driver.find_elements(By.ID, "MessageSinReg")
            if No_hay_volante:
                print("NO HAY VOLANTES EN ESTA OFICINA")
                continue
            else:
                cantidadDeVolantes = driver.find_elements(
                    By.CSS_SELECTOR, SELECT_ALL_VOLANTES
                )
                hrefs_volantes = [
                    volante.get_attribute("href")
                    for volante in cantidadDeVolantes
                    if volante.get_attribute("href")
                ]

                for i, href_volante in enumerate(hrefs_volantes):
                    if i > 0:
                        time.sleep(1)
                        obtenerVolantesPorOficina(driver, codeplace)
                    time.sleep(1)
                    cantidadDeVolantes = driver.find_elements(
                        By.CSS_SELECTOR, SELECT_ALL_VOLANTES
                    )

                    volante_objetivo = None
                    for volante in cantidadDeVolantes:
                        if volante.get_attribute("href") == href_volante:
                            volante_objetivo = volante
                            break

                    if volante_objetivo is None:
                        print(
                            f"NO SE ENCONTRO EL VOLANTE {i} EN LA OFICINA {office_name}"
                        )
                        continue

                    # Esto vuelve a leer las filas de la tabla para sacar dinero y usuario
                    # desde las columnas antes de abrir el detalle del volante.
                    filas = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
                    if i < len(filas):
                        columnas = filas[i].find_elements(By.TAG_NAME, "td")
                        dinero_volante = columnas[1].text.strip()
                        usuario_volante = columnas[3].text.strip()

                        datos_volante = construir_datos_volante(
                            usuario_volante,
                            office["office_code"],
                            office["poliedro_code"],
                            dinero_volante,
                        )
                        print(datos_volante)

                    volante_objetivo.click()
                    time.sleep(3)
                    # Se deja desactivado el envio a impresion por ahora.
                    # click(driver, By.ID, BUTTON_SEND_PRINT_FLYERS)
                    driver.execute_script("document.body.style.zoom='50%'")
                    time.sleep(2)
                    # Para crear la carpeta y subcarpeta de los volantes
                    folder = get_office_folder(office_name)
                    capture_screenshot(
                        driver, f"{folder}/screenshot_{office_name}_{i}.png"
                    )
                    time.sleep(3)
                    # Sin impresion activa, no se necesita cerrar el panel de Chrome.
                    # cerrar_ventana_chrome()
                    time.sleep(1)
                    click(driver, By.ID, BOTON_CANCELAR_VOLANTE)
                    asegurar_formulario_volantes(driver)
    except Exception as e:
        raise Exception(f"Error al obtener los volantes: {e}") from e


def downloadFlyers(driver) -> None:
    try:
        click(driver, By.CSS_SELECTOR, SELECTOR_MIGRATION_BUTTON)
        click(driver, By.CSS_SELECTOR, SELECTOR_FLYERS_NIT)
        getFlyers(driver)
    except Exception as e:
        raise Exception(f"Error al descargar los volantes: {e}") from e
    print("Esperando a que carguen los volantes...")
