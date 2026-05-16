from selenium.webdriver.common.by import By
import os
import time

from app.browser.actions import click, open_url, type_text, wait_clickable
from app.browser.driver import create_driver
from app.config.selectors import (
    LOGIN_BUTTON_ID,
    PASSWORD_INPUT_ID,
    SELECTOR_FLYERS_NIT,
    SELECTOR_MIGRATION_BUTTON,
    TOKEN_INPUT_ID,
    TOKEN_LOGIN_BUTTON_ID,
    USER_INPUT_ID,
)
from app.config.settings import (
    FORM_READY_DELAY_SECONDS,
    POLIEDRO_PASSWORD,
    POLIEDRO_URL,
    POLIEDRO_USERNAME,
)
from app.flows.flyers.actions import download_flyers
from app.flows.spreadsheets.main import go_to_spreadsheets
from app.flows.spreadsheets.planilla_actions import abrir_planillado
from app.template.plantillaExcel.main import actualizar_excel

def login(token: str | None = None) -> None:
    driver = create_driver()

    try:
        open_url(driver, POLIEDRO_URL)
        submit_credentials(driver, POLIEDRO_USERNAME, POLIEDRO_PASSWORD)
        token = token or os.getenv("AUTOMATION_TOKEN") or input("Ingrese el token: ")
        submit_token(driver, token)
        datos_volantes = download_flyers(driver, SELECTOR_MIGRATION_BUTTON, SELECTOR_FLYERS_NIT)
        #actualizar_excel(datos_volantes)
        time.sleep(3)
        abrir_planillado(driver)

        ventana_tns = None
        for datos_volante in datos_volantes:
            print(f"Procesando planilla con datos: {datos_volante}")
            ventana_tns = go_to_spreadsheets(driver, datos_volante, ventana_tns)
            time.sleep(3)
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
        print(
            "Formulario de login completo. "
            f"Esperando {FORM_READY_DELAY_SECONDS}s antes de enviar."
        )
        time.sleep(FORM_READY_DELAY_SECONDS)
        click(driver, By.ID, LOGIN_BUTTON_ID)
        wait_clickable(driver, By.ID, TOKEN_INPUT_ID)
    except Exception as e:
        raise Exception("Error al ingresar los datos de usuario") from e


def submit_token(driver, token: str) -> None:
    try:
        type_text(driver, By.ID, TOKEN_INPUT_ID, token)
        print(
            "Formulario de token completo. "
            f"Esperando {FORM_READY_DELAY_SECONDS}s antes de enviar."
        )
        time.sleep(FORM_READY_DELAY_SECONDS)
        click(driver, By.ID, TOKEN_LOGIN_BUTTON_ID)
    except Exception as e:
        raise Exception("Error obtener el token") from e
