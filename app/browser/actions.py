from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import StaleElementReferenceException
import time
from pathlib import Path

from app.config.settings import CAPTURAS_DIR, DEFAULT_TIMEOUT


def open_url(driver, url: str) -> None:
    driver.get(url)
    WebDriverWait(driver, DEFAULT_TIMEOUT).until(
        lambda current_driver: (
            current_driver.execute_script("return document.readyState") == "complete"
        )
    )


def wait_clickable(driver, by: By, value: str, timeout: int = DEFAULT_TIMEOUT):
    return WebDriverWait(driver, timeout).until(EC.element_to_be_clickable((by, value)))


def wait_present(driver, by: By, value: str, timeout: int = DEFAULT_TIMEOUT):
    return WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((by, value))
    )


def click(driver, by: By, value: str, timeout: int = DEFAULT_TIMEOUT) -> None:
    element = wait_clickable(driver, by, value, timeout)
    element.click()


def type_text(
    driver, by: By, value: str, text: str, timeout: int = DEFAULT_TIMEOUT
) -> None:
    element = wait_clickable(driver, by, value, timeout)
    time.sleep(2)
    element.click()
    time.sleep(2)
    element.clear()
    time.sleep(2)
    element.send_keys(text)


def selectInSelect(
    driver, by: By, value: str, option: str, timeout: int = DEFAULT_TIMEOUT
) -> None:
    def seleccionar(_driver):
        try:
            element = wait_present(_driver, by, value, timeout)
            select = Select(element)
            select.select_by_value(option)
            return True
        except (StaleElementReferenceException, Exception):
            return False

    if not WebDriverWait(driver, timeout).until(seleccionar):
        raise TimeoutError(f"No fue posible seleccionar {option} en {value}")


def enfocar_chrome(driver) -> None:
    driver.switch_to.window(driver.current_window_handle)
    driver.execute_script("window.focus();")
    time.sleep(1)


def capture_screenshot(driver, filename: str) -> None:
    screenshot_path = Path(filename)
    if not screenshot_path.is_absolute():
        screenshot_path = CAPTURAS_DIR / screenshot_path
    screenshot_path.parent.mkdir(exist_ok=True, parents=True)

    original_size = driver.get_window_size()
    try:
        size = driver.execute_script(
            """
            return {
                width: Math.max(
                    document.body.scrollWidth,
                    document.documentElement.scrollWidth,
                    window.innerWidth
                ),
                height: Math.max(
                    document.body.scrollHeight,
                    document.documentElement.scrollHeight,
                    window.innerHeight
                )
            };
            """
        )
        width = min(max(int(size.get("width", 1366)), 1366), 1920)
        height = min(max(int(size.get("height", 900)), 900), 12000)
        driver.set_window_size(width, height)
        time.sleep(1)
        driver.save_screenshot(str(screenshot_path))
    finally:
        driver.set_window_size(original_size["width"], original_size["height"])
