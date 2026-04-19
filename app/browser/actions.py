from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import StaleElementReferenceException
import time
from app.config.settings import DEFAULT_TIMEOUT


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
    wait_clickable(driver, by, value, timeout).click()


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
        element = wait_present(_driver, by, value, timeout)
        try:
            select = Select(element)
            select.select_by_value(option)
            return True
        except (StaleElementReferenceException, Exception):
            return False

    if not WebDriverWait(driver, timeout).until(seleccionar):
        raise TimeoutError(f"No fue posible seleccionar {option} en {value}")

def capture_screenshot(driver,filename:str)->None:
    driver.save_screenshot(filename)
