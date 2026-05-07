from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
import time
from datetime import datetime

from app.browser.actions import click, enfocar_chrome, wait_present
from app.desktop.actions import entrar_tns, ingresar_a_cartera, manejar_tns
from app.config.selectors import (
    BUTTON_CONTINUAR,
    BUTTON_GENERAR_PLANILLA,
    BUTTON_NOT_SPREADSHEET,
    BUTTON_SIMULAR,
    SELECT_GENERATION_TYPE,
    SELECT_USER_NAME,
    TABLE_PLANILLA,
    VALOR_TOTAL_TABLA_PLANILLA
)
from app.flows.spreadsheets.helpers import (
    normalizar_dinero,
    obtener_valor_select,
    obtener_valores_producto,
)
from app.flows.spreadsheets.planilla_actions import (
    check_first_checkbox,
    contar_portabilidades_restantes,
    get_checkbox_por_usuario,
    llenar_formulario_planillado,
    obtener_filas_planilla,
    obtener_porta_antigua,
    validate_money,
)
from app.storage.not_found_users import guardar_usuarios_no_encontrados


def generar_e_imprimir_planilla(driver, espera: int = 5, ajustar_zoom: bool = False) -> None:
    enfocar_chrome(driver)
    click(driver, By.ID, BUTTON_SIMULAR, timeout=10)
    time.sleep(espera)
    total = wait_present(driver, By.ID, VALOR_TOTAL_TABLA_PLANILLA, timeout=10)
    valor_producto = normalizar_dinero(total.text)

    click(driver, By.ID, BUTTON_GENERAR_PLANILLA, timeout=10)
    time.sleep(espera)
    if ajustar_zoom:
        driver.execute_script("""
                var style = document.createElement('style');
                style.innerHTML = `
                    @media print {
                        body {
                            zoom: 50%;
                        }
                    }
                `;
                document.head.appendChild(style);
            """)
    for _ in range(3):
        driver.execute_script("window.print();")
        time.sleep(2)
    time.sleep(espera)
    click(driver, By.ID, BUTTON_CONTINUAR, timeout=10)
    time.sleep(espera)
    return valor_producto

def go_to_spreadsheets(driver, datos_volante: dict | None = None, ventana_tns=None):
    try:
        from app.config.selectors import START_DATE

        wait_present(driver, By.ID, SELECT_USER_NAME)

        codigo_activacion = obtener_valor_select(
            datos_volante,
            "codigo_activacion",
            "codigo_usuario",
            "user_code",
        )
        codigo_oficina = obtener_valor_select(
            datos_volante,
            "codigo_oficina_planilla",
            "codigo_punto_venta",
            "planilla_code",
            "office_code",
        )
        productos = obtener_valores_producto(datos_volante)
        tipo_generacion = "1"
        tipo_planillado = "1"
        planilla = "1"

        if not codigo_activacion:
            raise ValueError("Falta codigo de usuario en los datos del volante")
        if not codigo_oficina:
            raise ValueError("Falta codigo de oficina en los datos del volante")

        dinero_volante = None
        if datos_volante is not None:
            dinero_volante = datos_volante.get("dinero") or datos_volante.get("dinero_volante")
        if isinstance(dinero_volante, str):
            dinero_volante = normalizar_dinero(dinero_volante)
        if dinero_volante is None:
            raise ValueError("Falta dinero del volante para validar la planilla")
        saldo_pendiente = dinero_volante

        for producto in productos:
            if saldo_pendiente <= 0:
                return ventana_tns

            enfocar_chrome(driver)
            llenar_formulario_planillado(
                driver,
                codigo_activacion,
                codigo_oficina,
                tipo_generacion,
                tipo_planillado,
                planilla,
                producto,
                START_DATE,
            )
            try:
                WebDriverWait(driver, 10).until(
                    EC.visibility_of_element_located((By.ID, BUTTON_NOT_SPREADSHEET))
                )
                click(driver, By.ID, BUTTON_NOT_SPREADSHEET, timeout=5)

                time.sleep(3)
                WebDriverWait(driver, 12).until(
                    EC.visibility_of_element_located((By.ID, SELECT_GENERATION_TYPE))
                )
                WebDriverWait(driver, 12).until(
                    EC.element_to_be_clickable((By.ID, SELECT_GENERATION_TYPE))
                )
                continue
            except TimeoutException:
                pass

            time.sleep(3)

            wait_present(driver, By.ID, TABLE_PLANILLA)

            if producto in {"3", "7"}:
                valor_producto = generar_e_imprimir_planilla(driver, espera=2)
                saldo_pendiente -= valor_producto
                print(
                    f"Producto {producto}: generado {valor_producto}. "
                    f"Saldo pendiente: {max(saldo_pendiente, 0)}"
                )
                continue

            screenshot_name = (
                f"tabla_planilla_{producto}_{datetime.today().strftime('%Y%m%d_%H%M%S')}.png"
            )
            driver.save_screenshot(screenshot_name)
            time.sleep(10)
            check_first_checkbox(driver)
            time.sleep(2)

            resultados = obtener_filas_planilla(driver)
            if len(resultados) == 1:
                checkbox = get_checkbox_por_usuario(driver, resultados[0]["usuario"])
                if checkbox and checkbox.is_selected():
                    checkbox.click()
                validacion = validate_money(driver, saldo_pendiente)
                if not validacion["coincide"]:
                    print(
                        f"Producto {producto}: un solo item por {validacion['suma_planilla']} "
                        f"no cuadra con saldo pendiente {saldo_pendiente}"
                    )
                generar_e_imprimir_planilla(driver, ajustar_zoom=True)
                return ventana_tns

            resultados_tns = []
            if ventana_tns is None:
                ventana_tns = entrar_tns()
                ventana_tns = ingresar_a_cartera(ventana_tns)
            for item in resultados:
                try:
                    resultado = manejar_tns(ventana_tns, item)
                except ValueError as error:
                    resultado = item.copy()
                    resultado["tipo_plan"] = "no_encontrado"
                    resultado["error_tns"] = str(error)
                    resultado["codigo_oficina_planilla"] = codigo_oficina
                    resultado["codigo_usuario_volante"] = codigo_activacion
                    resultado["producto"] = producto
                    resultado["fecha_volante"] = (
                        datos_volante.get("fecha") if datos_volante else ""
                    )

                resultados_tns.append(resultado)

                if resultado["tipo_plan"] == "linea_nueva":
                    checkbox = get_checkbox_por_usuario(driver, resultado["usuario"])
                    if checkbox and checkbox.is_selected():
                        checkbox.click()
                elif resultado["tipo_plan"] == "upgrade":
                    checkbox = get_checkbox_por_usuario(driver, resultado["usuario"])
                    if checkbox and checkbox.is_selected():
                        checkbox.click()

            usuarios_no_encontrados = [
                item
                for item in resultados_tns
                if item.get("tipo_plan") == "no_encontrado"
            ]
            guardar_usuarios_no_encontrados(usuarios_no_encontrados)

            enfocar_chrome(driver)
            validacion = validate_money(driver, saldo_pendiente)
            print(f"Portabilidades restantes: {contar_portabilidades_restantes(driver, resultados_tns)}")
            todas_son_portabilidad = (
                resultados_tns
                and not usuarios_no_encontrados
                and all(item.get("tipo_plan") == "portabilidad" for item in resultados_tns)
            )

            if not usuarios_no_encontrados:
                while not validacion["coincide"] and validacion["faltante"] > 0:
                    porta_antigua = obtener_porta_antigua(driver, resultados_tns)
                    if porta_antigua is None:
                        break

                    if porta_antigua["checkbox"].is_selected():
                        porta_antigua["checkbox"].click()
                    validacion = validate_money(driver, saldo_pendiente)
                    print(f"Portabilidades restantes: {contar_portabilidades_restantes(driver, resultados_tns)}")

            if todas_son_portabilidad and not validacion["coincide"]:
                print(
                    "Todas las filas son portabilidad; se genera con las mas antiguas "
                    f"por {validacion['suma_planilla']} de {saldo_pendiente}"
                )

            if validacion["coincide"] or usuarios_no_encontrados or todas_son_portabilidad:
                generar_e_imprimir_planilla(driver, ajustar_zoom=True)
                #return ventana_tns

        return ventana_tns

    except Exception as e:
        raise Exception(f"Error al ir a las planillas: {e}") from e
