from selenium import webdriver
import json
from app.config.settings import HEADLESS, PRINTER_NAME


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
        "version": 2,
    }
    prefs = {
        "printing.print_preview_sticky_settings.appState": json.dumps(app_state),
    }
    options.add_experimental_option("prefs", prefs)
    options.add_argument("--kiosk-printing")
    if HEADLESS:
        options.add_argument("--headless=new")

    return webdriver.Chrome(options=options)
