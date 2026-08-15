from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
import re
import time
from datetime import datetime

from app.browser.actions import capture_screenshot, click, enfocar_chrome, wait_present
from app.desktop.actions import entrar_tns, ingresar_a_cartera, manejar_tns, log_tns
from app.config.selectors import (
    BUTTON_CONTINUAR,
    BUTTON_GENERAR_PLANILLA,
    BUTTON_NOT_SPREADSHEET,
    BUTTON_SIMULAR,
    SELECT_GENERATION_TYPE,
    SELECT_USER_NAME,
    TABLE_PLANILLA,
    VALOR_TOTAL_TABLA_PLANILLA,
    TARJETA_CREDITO_TABLA_PLANILLA
)
from app.flows.spreadsheets.helpers import (
    normalizar_dinero,
    obtener_valor_select,
    obtener_valores_producto,
)
from app.flows.spreadsheets.planilla_actions import (
    abrir_planillado,
    check_first_checkbox,
    contar_portabilidades_restantes,
    get_checkbox_por_usuario,
    llenar_formulario_planillado,
    obtener_filas_planilla,
    obtener_porta_antigua,
    validate_money,
)
from app.storage.spreadsheet_progress import (
    obtener_productos_generados,
    obtener_valor_aplicado,
    registrar_planilla_generada,
)
from app.storage.not_found_users import guardar_usuarios_no_encontrados
from app.storage.main import get_office_folder
from app.template.codes_places.main import OFFICES
from app.printing.planilla import aplicar_configuracion_impresion, imprimir_copias


POLIEDRO_KEEPALIVE_INTERVAL_SECONDS = 45
ultimo_keepalive_poliedro = 0.0


def mantener_sesion_poliedro(driver, forzar: bool = False) -> None:
    global ultimo_keepalive_poliedro

    ahora = time.monotonic()
    if not forzar and ahora - ultimo_keepalive_poliedro < POLIEDRO_KEEPALIVE_INTERVAL_SECONDS:
        return

    try:
        driver.execute_script(
            """
            document.dispatchEvent(new MouseEvent('mousemove', {
                bubbles: true,
                clientX: 10 + Math.floor(Math.random() * 20),
                clientY: 10 + Math.floor(Math.random() * 20)
            }));

            if (window.fetch && window.location && window.location.href) {
                fetch(window.location.href, {
                    method: 'GET',
                    credentials: 'include',
                    cache: 'no-store'
                }).catch(() => {});
            }
            """
        )
        ultimo_keepalive_poliedro = ahora
        print("Sesion Poliedro mantenida activa.")
    except Exception as error:
        print(f"No fue posible mantener activa la sesion Poliedro: {error}")

def obtener_valor_tarjeta_credito(driver) -> int:
    try:
        valor_tarjeta_credito = wait_present(
            driver,
            By.ID,
            TARJETA_CREDITO_TABLA_PLANILLA,
            timeout=3,
        )
        return normalizar_dinero(valor_tarjeta_credito.text)
    except TimeoutException:
        return 0


def simular_planilla(driver, espera: int = 5) -> dict:
    click(driver, By.ID, BUTTON_SIMULAR, timeout=10)
    time.sleep(espera)
    total = wait_present(driver, By.ID, VALOR_TOTAL_TABLA_PLANILLA, timeout=10)
    valor_total = normalizar_dinero(total.text)
    valor_tarjeta_credito = obtener_valor_tarjeta_credito(driver)
    return {
        "valor_total": valor_total,
        "valor_tarjeta_credito": valor_tarjeta_credito,
        "valor_para_volante": max(valor_total - valor_tarjeta_credito, 0),
    }


def obtener_saldo_pendiente_inicial(datos_volante: dict | None, dinero_volante: int) -> int:
    valor_aplicado = obtener_valor_aplicado(datos_volante) if datos_volante else 0
    saldo_pendiente = max(dinero_volante - valor_aplicado, 0)
    if valor_aplicado:
        print(
            f"Reanudando volante. Total volante: {dinero_volante}. "
            f"Ya aplicado: {valor_aplicado}. Saldo pendiente: {saldo_pendiente}"
        )
    return saldo_pendiente


def guardar_progreso_planilla(
    datos_volante: dict | None,
    producto: str,
    valores_planilla: dict,
) -> None:
    if datos_volante is None:
        return
    valor_aplicado = registrar_planilla_generada(datos_volante, producto, valores_planilla)
    print(f"Progreso guardado del volante. Valor aplicado acumulado: {valor_aplicado}")


def _limpiar_parte_nombre_archivo(valor: object) -> str:
    texto = re.sub(r'[<>:"/\\|?*]+', "_", str(valor or "").strip())
    return "_".join(texto.split()) or "sin_dato"


def guardar_captura_planilla_generada(
    driver,
    datos_volante: dict | None,
    producto: str,
) -> None:
    if not datos_volante:
        print("No se guardo captura de la planilla generada: faltan los datos del volante.")
        return

    office_code = str(datos_volante.get("office_code", "")).strip()
    oficina = next(
        (
            item["name"]
            for item in OFFICES
            if item["office_code"] == office_code
        ),
        office_code or "SIN OFICINA",
    )
    fecha_volante = str(datos_volante.get("fecha", "")).strip()
    folder = get_office_folder(oficina, fecha_volante or None)
    usuario = datos_volante.get("codigo_usuario", datos_volante.get("usuario", ""))
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = (
        f"planilla_generada_{_limpiar_parte_nombre_archivo(oficina)}_"
        f"{_limpiar_parte_nombre_archivo(usuario)}_producto_"
        f"{_limpiar_parte_nombre_archivo(producto)}_{timestamp}.png"
    )
    screenshot_path = folder / filename
    capture_screenshot(driver, str(screenshot_path))
    print(f"Captura de planilla generada guardada en: {screenshot_path}")


def generar_e_imprimir_planilla(
    driver,
    datos_volante: dict | None,
    producto: str,
    espera: int = 5,
    ajustar_zoom: bool = False,
    valores_planilla: dict | None = None,
) -> dict:
    enfocar_chrome(driver)
    if valores_planilla is None:
        valores_planilla = simular_planilla(driver, espera=espera)
    click(driver, By.ID, BUTTON_GENERAR_PLANILLA, timeout=10)
    time.sleep(espera)
    guardar_captura_planilla_generada(driver, datos_volante, producto)
    aplicar_configuracion_impresion(driver, ajustar_zoom=ajustar_zoom)
    imprimir_copias(driver, copias=3)
    time.sleep(espera)
    click(driver, By.ID, BUTTON_CONTINUAR, timeout=10)
    time.sleep(espera)
    return valores_planilla

def go_to_spreadsheets(driver, datos_volante: dict | None = None, ventana_tns=None):
    try:
        from app.config.selectors import START_DATE

        try:
            wait_present(driver, By.ID, SELECT_USER_NAME, timeout=5)
        except TimeoutException:
            abrir_planillado(driver)
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
        fecha_volante = obtener_valor_select(datos_volante, "fecha")
        productos = obtener_valores_producto(datos_volante)
        tipo_generacion = "1"
        tipo_planillado = "1"
        planilla = "1"

        log_tns("DICT VOLANTE RECIBIDO PARA PLANILLADO", datos_volante)
        log_tns(
            "PARAMETROS PLANILLADO ARMADOS",
            {
                "codigo_activacion": codigo_activacion,
                "codigo_oficina": codigo_oficina,
                "fecha_volante": fecha_volante,
                "productos": productos,
                "tipo_generacion": tipo_generacion,
                "tipo_planillado": tipo_planillado,
                "planilla": planilla,
                "start_date": START_DATE,
            },
        )

        if not codigo_activacion:
            raise ValueError("Falta codigo de usuario en los datos del volante")
        if not codigo_oficina:
            raise ValueError("Falta codigo de oficina en los datos del volante")
        if not fecha_volante:
            raise ValueError("Falta la fecha seleccionada en los datos del volante")

        dinero_volante = None
        if datos_volante is not None:
            dinero_volante = datos_volante.get("dinero")
            if dinero_volante is None:
                dinero_volante = datos_volante.get("dinero_volante")
        if isinstance(dinero_volante, str):
            dinero_volante = normalizar_dinero(dinero_volante)
        if dinero_volante is None:
            raise ValueError("Falta dinero del volante para validar la planilla")
        saldo_pendiente = obtener_saldo_pendiente_inicial(datos_volante, dinero_volante)
        volante_en_cero = dinero_volante == 0
        productos_generados = obtener_productos_generados(datos_volante) if datos_volante else set()
        if productos_generados:
            productos = [producto for producto in productos if producto not in productos_generados]
            print(
                "Productos ya generados para este volante, se omiten: "
                f"{', '.join(sorted(productos_generados))}"
            )

        for producto in productos:
            if saldo_pendiente <= 0 and not volante_en_cero:
                return ventana_tns

            enfocar_chrome(driver)
            print(f"Llenando formulario de planillado para producto {producto}")
            try:
                llenar_formulario_planillado(
                    driver,
                    codigo_activacion,
                    codigo_oficina,
                    tipo_generacion,
                    tipo_planillado,
                    planilla,
                    producto,
                    START_DATE,
                    fecha_volante,
                )
            except TimeoutException:
                print("No aparecio completo el formulario de planillado. Reabriendo y reintentando...")
                abrir_planillado(driver)
                llenar_formulario_planillado(
                    driver,
                    codigo_activacion,
                    codigo_oficina,
                    tipo_generacion,
                    tipo_planillado,
                    planilla,
                    producto,
                    START_DATE,
                    fecha_volante,
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

            if volante_en_cero:
                valores_planilla = generar_e_imprimir_planilla(
                    driver,
                    datos_volante,
                    producto,
                    espera=2,
                    ajustar_zoom=True,
                )
                guardar_progreso_planilla(datos_volante, producto, valores_planilla)
                print(
                    f"Volante en 0: producto {producto} generado por tarjeta credito. "
                    f"Total planilla: {valores_planilla['valor_total']}. "
                    f"Tarjeta credito: {valores_planilla['valor_tarjeta_credito']}."
                )
                continue

            if producto in {"3", "7"}:
                valores_planilla = generar_e_imprimir_planilla(
                    driver,
                    datos_volante,
                    producto,
                    espera=2,
                )
                guardar_progreso_planilla(datos_volante, producto, valores_planilla)
                saldo_pendiente -= valores_planilla["valor_para_volante"]
                print(
                    f"Producto {producto}: generado {valores_planilla['valor_total']}. "
                    f"Tarjeta credito aparte: {valores_planilla['valor_tarjeta_credito']}. "
                    f"Valor aplicado al volante: {valores_planilla['valor_para_volante']}. "
                    f"Saldo pendiente: {max(saldo_pendiente, 0)}"
                )
                continue

            time.sleep(10)
            check_first_checkbox(driver)
            time.sleep(2)

            resultados = obtener_filas_planilla(driver, fecha_volante)
            log_tns(
                "RESULTADOS OBTENIDOS DE LA PLANILLA",
                {
                    "producto": producto,
                    "codigo_oficina_planilla": codigo_oficina,
                    "codigo_usuario_volante": codigo_activacion,
                    "fecha_volante": fecha_volante,
                    "cantidad_resultados": len(resultados),
                    "resultados": resultados,
                },
            )

            resultados_tns = [
                item.copy()
                for item in resultados
                if item.get("tipo_plan") == "portabilidad"
            ]
            resultados_a_consultar_tns = [
                item
                for item in resultados
                if item.get("tipo_plan") != "portabilidad"
            ]

            if resultados_tns:
                log_tns(
                    "FILAS ANTERIORES CLASIFICADAS COMO PORTABILIDAD",
                    {
                        "fecha_volante": fecha_volante,
                        "cantidad": len(resultados_tns),
                        "resultados": resultados_tns,
                    },
                )

            if resultados_a_consultar_tns:
                mantener_sesion_poliedro(driver, forzar=True)
                if ventana_tns is None:
                    ventana_tns = entrar_tns()
                    ventana_tns = ingresar_a_cartera(ventana_tns)
            for item in resultados_a_consultar_tns:
                try:
                    log_tns(
                        "DICT QUE SE ENVIA A TNS",
                        {
                            "producto": producto,
                            "codigo_oficina_planilla": codigo_oficina,
                            "codigo_usuario_volante": codigo_activacion,
                            "item": item,
                        },
                    )
                    resultado = manejar_tns(
                        ventana_tns,
                        item,
                        mantener_sesion=lambda: mantener_sesion_poliedro(driver),
                    )
                    log_tns("RESULTADO DEVUELTO POR TNS", resultado)
                    mantener_sesion_poliedro(driver)
                except ValueError as error:
                    log_tns(
                        "ERROR BUSCANDO ITEM EN TNS",
                        {
                            "producto": producto,
                            "codigo_oficina_planilla": codigo_oficina,
                            "codigo_usuario_volante": codigo_activacion,
                            "item": item,
                            "error": str(error),
                        },
                    )
                    resultado = item.copy()
                    resultado["tipo_plan"] = "no_encontrado"
                    resultado["error_tns"] = str(error)
                    resultado["accion"] = "Se omite la oficina y se sacara manual"
                    resultado["codigo_oficina_planilla"] = codigo_oficina
                    resultado["codigo_usuario_volante"] = codigo_activacion
                    resultado["producto"] = producto
                    resultado["fecha_volante"] = fecha_volante

                resultados_tns.append(resultado)

                if resultado["tipo_plan"] == "linea_nueva":
                    checkbox = get_checkbox_por_usuario(
                        driver,
                        resultado["usuario"],
                        resultado.get("fecha_activacion"),
                    )
                    if checkbox and checkbox.is_selected():
                        checkbox.click()
                elif resultado["tipo_plan"] == "upgrade":
                    checkbox = get_checkbox_por_usuario(
                        driver,
                        resultado["usuario"],
                        resultado.get("fecha_activacion"),
                    )
                    if checkbox and checkbox.is_selected():
                        checkbox.click()

            usuarios_no_encontrados = [
                item
                for item in resultados_tns
                if item.get("tipo_plan") == "no_encontrado"
            ]
            guardar_usuarios_no_encontrados(usuarios_no_encontrados)
            if usuarios_no_encontrados:
                usuarios = ", ".join(item.get("usuario", "") for item in usuarios_no_encontrados)
                print(
                    "Usuarios no encontrados en TNS. "
                    f"Se omite la oficina y se sacara manual: {usuarios}"
                )
                try:
                    abrir_planillado(driver, forzar=True)
                except Exception as error:
                    print(f"No fue posible volver al formulario de planillado: {error}")
                return ventana_tns

            enfocar_chrome(driver)
            validacion = validate_money(driver, saldo_pendiente, fecha_volante)
            print(
                "Portabilidades restantes: "
                f"{contar_portabilidades_restantes(driver, resultados_tns, fecha_volante)}"
            )
            todas_son_portabilidad = (
                resultados_tns
                and all(item.get("tipo_plan") == "portabilidad" for item in resultados_tns)
            )

            while not validacion["coincide"] and validacion["faltante"] > 0:
                porta_antigua = obtener_porta_antigua(
                    driver,
                    resultados_tns,
                    fecha_volante,
                )
                if porta_antigua is None:
                    break

                if porta_antigua["checkbox"].is_selected():
                    porta_antigua["checkbox"].click()
                validacion = validate_money(driver, saldo_pendiente, fecha_volante)
                print(
                    "Portabilidades restantes: "
                    f"{contar_portabilidades_restantes(driver, resultados_tns, fecha_volante)}"
                )

            if todas_son_portabilidad and not validacion["coincide"]:
                print(
                    "Todas las filas son portabilidad; se genera con las mas antiguas "
                    f"por {validacion['suma_planilla']} de {saldo_pendiente}"
                )

            valores_planilla = simular_planilla(driver)
            while valores_planilla["valor_para_volante"] < saldo_pendiente:
                porta_antigua = obtener_porta_antigua(
                    driver,
                    resultados_tns,
                    fecha_volante,
                )
                if porta_antigua is None:
                    break

                if porta_antigua["checkbox"].is_selected():
                    porta_antigua["checkbox"].click()
                valores_planilla = simular_planilla(driver)
                print(
                    "Ajustando pago mixto con portabilidad. "
                    f"Efectivo: {valores_planilla['valor_para_volante']}. "
                    f"Tarjeta credito: {valores_planilla['valor_tarjeta_credito']}. "
                    f"Saldo pendiente: {saldo_pendiente}"
                )

            efectivo_coincide = (
                valores_planilla["valor_para_volante"] == saldo_pendiente
            )

            if efectivo_coincide or todas_son_portabilidad:
                valores_planilla = generar_e_imprimir_planilla(
                    driver,
                    datos_volante,
                    producto,
                    ajustar_zoom=True,
                    valores_planilla=valores_planilla,
                )
                guardar_progreso_planilla(datos_volante, producto, valores_planilla)
                saldo_pendiente -= valores_planilla["valor_para_volante"]
                print(
                    f"Producto {producto}: generado {valores_planilla['valor_total']}. "
                    f"Tarjeta credito aparte: {valores_planilla['valor_tarjeta_credito']}. "
                    f"Valor aplicado al volante: {valores_planilla['valor_para_volante']}. "
                    f"Saldo pendiente: {max(saldo_pendiente, 0)}"
                )
                #return ventana_tns
            else:
                print(
                    f"Producto {producto}: el efectivo de la planilla no coincide con "
                    f"el saldo del volante. Total planilla: {valores_planilla['valor_total']}. "
                    f"Tarjeta credito: {valores_planilla['valor_tarjeta_credito']}. "
                    f"Efectivo: {valores_planilla['valor_para_volante']}. "
                    f"Saldo pendiente: {saldo_pendiente}. No se genera planilla."
                )

        return ventana_tns

    except Exception as e:
        raise Exception(f"Error al ir a las planillas: {e}") from e
