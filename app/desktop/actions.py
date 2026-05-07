from pywinauto import Desktop
import os
import time
import unicodedata
from app.config.settings import TNS_USERNAME, TNS_PASSWORD,TNS_OFFICE


#SCRIPT PARA MANEJAR TNS FUNCIONANDO 
def obtener_texto_celda(celda):
    try:
        valor = celda.iface_value.CurrentValue
        if valor and valor != celda.window_text():
            return valor.strip()
    except Exception:
        pass

    try:
        valor = celda.legacy_properties().get("Value", "")
        if valor and valor != celda.window_text():
            return valor.strip()
    except Exception:
        pass

    try:
        textos = [texto.strip() for texto in celda.texts() if texto and texto.strip()]
        textos = [texto for texto in textos if texto != celda.window_text()]
        if textos:
            return textos[0]
    except Exception:
        pass

    try:
        for hijo in celda.children():
            texto = hijo.window_text().strip()
            if texto:
                return texto
    except Exception:
        pass

    return celda.window_text().strip()


def normalizar_texto_tns(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto or "")
    texto = "".join(caracter for caracter in texto if not unicodedata.combining(caracter))
    return " ".join(texto.upper().split())


def obtener_variantes_busqueda_usuario(usuario: str) -> list[str]:
    partes = " ".join((usuario or "").split()).split()
    variantes = []

    def agregar_variante(partes_variante: list[str]) -> None:
        variante = " ".join(partes_variante).strip()
        if variante and variante not in variantes:
            variantes.append(variante)

    agregar_variante(partes)

    if len(partes) == 2:
        agregar_variante([partes[1], partes[0]])
    elif len(partes) >= 3:
        primera = partes[0]
        ultima = partes[-1]
        primer_apellido = partes[-2]

        agregar_variante([primer_apellido, primera])
        agregar_variante([primera, ultima])
        agregar_variante([ultima, primera])

        if len(partes) >= 4:
            segundo_nombre = partes[1]

            agregar_variante([primera, primer_apellido])
            agregar_variante([primera, segundo_nombre, ultima])
            agregar_variante([ultima, primera, segundo_nombre])

        agregar_variante([*partes[-2:], *partes[:-2]])
        agregar_variante([partes[-1], *partes[:-1]])

    return variantes


def cerrar_popup_tns_si_existe(ventana, timeout=2) -> bool:
    fin = time.time() + timeout
    desktop = Desktop(backend="uia")
    proceso_tns = ventana.element_info.process_id

    while time.time() < fin:
        for posible_popup in desktop.windows():
            try:
                popup = desktop.window(handle=posible_popup.handle)
                if popup.element_info.process_id != proceso_tns:
                    continue

                aceptar = popup.child_window(title="Aceptar", control_type="Button")
                if not aceptar.exists(timeout=0.2):
                    continue

                textos_popup = [popup.window_text()]
                textos_popup.extend(
                    hijo.window_text()
                    for hijo in popup.descendants()
                    if hijo.window_text()
                )
                texto_popup = normalizar_texto_tns(" ".join(textos_popup))

                if "RECIBO DE CAJA" in texto_popup:
                    aceptar.click_input()
                    time.sleep(1)
                    return True
            except Exception:
                pass

        time.sleep(0.2)

    return False


def obtener_descripciones_tabla(tabla) -> list[str]:
    descripciones = []
    vistos = set()

    for celda in tabla.descendants(control_type="DataItem"):
        titulo = normalizar_texto_tns(celda.window_text())
        if not titulo.startswith("DESCRIPCION FILA "):
            continue

        texto = obtener_texto_celda(celda).strip()
        texto_normalizado = normalizar_texto_tns(texto)
        if not texto_normalizado or texto_normalizado in vistos:
            continue

        vistos.add(texto_normalizado)
        descripciones.append(texto)

    return descripciones


def clasificar_tipo_plan(*bloques: str) -> tuple[str, str]:
    texto_analisis = normalizar_texto_tns(" ".join(bloque for bloque in bloques if bloque))

    reglas = [
        ("portabilidad", (("PORTABILIDAD",),)),
        ("linea_nueva", (("LINEA NUEVA",),)),
        ("upgrade", (("MIGRACION UPGRADE",), ("MIGRACION", "UPGRADE"))),
    ]

    for tipo_plan, grupos in reglas:
        if any(all(clave in texto_analisis for clave in grupo) for grupo in grupos):
            return tipo_plan, texto_analisis

    return "otro", texto_analisis


def enfocar_tns(ventana) -> None:
    try:
        ventana.restore()
    except Exception:
        pass
    ventana.set_focus()
    time.sleep(1)


def obtener_filas_facturas_tns(ventana, limite: int = 20):
    filas = []
    for numero_fila in range(1, limite + 1):
        fila = ventana.child_window(title=f"Fila {numero_fila}", control_type="ListItem")
        if not fila.exists(timeout=0.2):
            if numero_fila == 1:
                return filas
            break
        filas.append(numero_fila)
    return filas


def volver_a_resultados_tns(ventana) -> None:
    panel_atras = ventana.child_window(
        auto_id="windowsUIButtonPanelCloseButton",
        control_type="Pane",
    )
    btn_atras = panel_atras.child_window(control_type="Button")
    btn_atras.click_input()
    time.sleep(2)
    ventana.child_window(auto_id="Buscar", control_type="Edit").wait("visible", timeout=10)


def leer_factura_tns(ventana, item: dict, numero_fila: int) -> dict:
    fila = ventana.child_window(title=f"Fila {numero_fila}", control_type="ListItem")
    fila.double_click_input()
    time.sleep(2)

    try:
        tabla = ventana.child_window(auto_id="GridControlDetalle", control_type="Table")
        detalle = ventana.child_window(auto_id="EdDetalle", control_type="Edit")
        detalle.wait("visible", timeout=10)
        texto_detalle = detalle.get_value() or ""
        descripciones = obtener_descripciones_tabla(tabla)
        descripcion_principal = descripciones[0] if descripciones else ""
        tipo_plan, texto_clasificacion = clasificar_tipo_plan(texto_detalle, *descripciones)
    finally:
        volver_a_resultados_tns(ventana)

    resultado = item.copy()
    resultado["descripcion_tns"] = descripcion_principal
    resultado["descripciones_tns"] = descripciones
    resultado["detalle_tns"] = texto_detalle
    resultado["texto_clasificacion_tns"] = texto_clasificacion
    resultado["tipo_plan"] = tipo_plan
    resultado["fila_tns"] = numero_fila
    return resultado


def esperar_ventana_login_tns(timeout=120):
    desktop = Desktop(backend="uia")
    fin = time.time() + timeout
    while time.time() < fin:
        ventanas = desktop.windows(title_re=".*Portal TNS.*")
        for v in ventanas:
            ventana = desktop.window(handle=v.handle)
            oficina = ventana.child_window(auto_id="txtEmpresa", control_type="Edit")
            if oficina.exists():
                ventana.wait("visible", timeout=10)
                oficina.wait("visible", timeout=10)
                return ventana
        time.sleep(1)
    raise TimeoutError("No apareció la ventana de login de TNS con txtEmpresa")

def entrar_tns():
    os.startfile(r"C:\Users\Sebas\OneDrive\Escritorio\Portal TNS.appref-ms")
    time.sleep(5)
    ventana = esperar_ventana_login_tns()
    ventana.wait("visible", timeout=20)
    time.sleep(3)
    ventana.set_focus()
    #Poner Oficina
    Oficina = ventana.child_window(auto_id="txtEmpresa", control_type="Edit")
    Oficina.click_input()
    Oficina.set_edit_text(TNS_OFFICE)
    time.sleep(2)

    #Poner Usuario
    usuario = ventana.child_window(auto_id="txtUsuario", control_type="Edit")
    usuario.click_input()
    usuario.set_edit_text(TNS_USERNAME)
    time.sleep(2)

    #Poner Contraseña
    contraseña = ventana.child_window(auto_id="txtClave", control_type="Edit")
    contraseña.click_input()
    contraseña.set_edit_text(TNS_PASSWORD)
    time.sleep(2)

    #Boton Ingresar 
    ingresar = ventana.child_window(auto_id="btnIngresar", control_type="Button")
    ingresar.click_input()
    time.sleep(1)

    return ventana


def ingresar_a_cartera(ventana):
    time.sleep(4)
    ventana = Desktop(backend="uia").window(title="Portal TNS", auto_id="MainForm", control_type="Window")
    empresa = ventana.child_window(title="FRONTERA CELULAR SAS", control_type="ListItem")
    empresa.click_input()
    time.sleep(2)
    cartera = ventana.child_window(title="Cartera", control_type="ListItem")
    cartera.click_input()
    time.sleep(2)
    movimientos = ventana.child_window(title="Movimientos", control_type="ListItem")
    movimientos.click_input()
    time.sleep(2)
    recibos = ventana.child_window(title="Recibos", control_type="ListItem")
    recibos.click_input()
    time.sleep(4)
    return ventana


def manejar_tns(ventana, item: dict):
    enfocar_tns(ventana)
    buscar = ventana.child_window(auto_id="Buscar", control_type="Edit")
    buscar.click_input()
    tipos_validos = {"portabilidad", "linea_nueva", "upgrade"}
    ultimo_resultado = None

    for busqueda_usuario in obtener_variantes_busqueda_usuario(item["usuario"]):
        buscar.click_input()
        buscar.set_edit_text(busqueda_usuario)
        time.sleep(1)
        buscar.type_keys("{ENTER}")
        time.sleep(2)
        if cerrar_popup_tns_si_existe(ventana):
            buscar.click_input()
            continue

        filas = obtener_filas_facturas_tns(ventana)
        for numero_fila in filas:
            try:
                resultado = leer_factura_tns(ventana, item, numero_fila)
            except Exception:
                continue

            ultimo_resultado = resultado
            if resultado["tipo_plan"] in tipos_validos:
                return resultado

    if ultimo_resultado is None:
        raise ValueError(f"No se encontro el usuario en TNS: {item['usuario']}")

    return ultimo_resultado
