from selenium import webdriver
import json
from app.config.settings import HEADLESS, PRINT_SCALE, PRINTER_NAME


LETTER_MEDIA_SIZE = {
    "name": "NA_LETTER",
    "width_microns": 215900,
    "height_microns": 279400,
    "is_default": True,
    "custom_display_name": "Carta",
}


def _normalizar_escala_impresion(value: str) -> str:
    try:
        escala = int(value)
    except (TypeError, ValueError):
        escala = 70
    return str(min(max(escala, 10), 200))


def create_driver() -> webdriver.Chrome:
    options = webdriver.ChromeOptions()
    app_state = {
        "recentDestinations": [
            {
                "id": PRINTER_NAME,
                "origin": "local",
                "account": "",
            }
        ],
        "selectedDestinationId": PRINTER_NAME,
        "mediaSize": LETTER_MEDIA_SIZE,
        "marginsType": 2,
        "isHeaderFooterEnabled": False,
        "isCssBackgroundEnabled": True,
        "isLandscapeEnabled": False,
        "isColorEnabled": True,
        "isCollateEnabled": True,
        "isDuplexEnabled": False,
        "scaling": _normalizar_escala_impresion(PRINT_SCALE),
        "scalingType": 4,
        "scalingTypePdf": 1,
        "version": 2,
    }
    prefs = {
        "printing.print_preview_sticky_settings.appState": json.dumps(app_state),
    }
    options.add_experimental_option("prefs", prefs)
    options.add_argument("--kiosk-printing")
    options.add_argument("--start-maximized")
    if HEADLESS:
        options.add_argument("--headless=new")

    # Selenium Manager detecta la version instalada de Chrome y obtiene el
    # ChromeDriver compatible. No se debe fijar un driver dentro del .exe.
    return webdriver.Chrome(options=options)
