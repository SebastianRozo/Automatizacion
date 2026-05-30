from selenium import webdriver
from selenium.webdriver.chrome.service import Service
import json
import sys
from pathlib import Path
from app.config.settings import HEADLESS, PRINT_LANDSCAPE, PRINT_SCALE, PRINTER_NAME


def _resource_path(relative_path: str) -> Path:
    base_path = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
    return base_path / relative_path


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
        "isHeaderFooterEnabled": False,
        "isCssBackgroundEnabled": True,
        "landscape": PRINT_LANDSCAPE,
        "marginsType": 2,
        "scaling": PRINT_SCALE,
        "scalingType": 3,
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

    chromedriver_path = _resource_path("app/browser/drivers/chromedriver.exe")
    service = Service(executable_path=str(chromedriver_path))
    return webdriver.Chrome(service=service, options=options)
