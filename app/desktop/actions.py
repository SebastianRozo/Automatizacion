from pywinauto import Desktop
import os
import pprint
import time
from app.config.settings import TNS_USERNAME, TNS_PASSWORD, TNS_OFFICE, TNS_APP_PATH
from app.desktop.helpers import (
    TNS_MATCH_MIN_SCORE,
    calcular_similitud_nombres,
    clasificar_tipo_plan,
    normalizar_texto_tns,
    obtener_variantes_busqueda_usuario,
)

TNS_NOMBRE_FILA_INDICE = 5


def log_tns(titulo: str, data=None) -> None:
    print(f"\n========== {titulo} ==========", flush=True)
    if data is not None:
        pprint.pprint(data, width=120, sort_dicts=False)
    print("=" * (22 + len(titulo)), flush=True)


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


def obtener_textos_fila_tns(ventana, numero_fila: int) -> list[str]:
    fila = ventana.child_window(title=f"Fila {numero_fila}", control_type="ListItem")
    textos = []
    vistos = set()

    controles = [fila]
    try:
        controles.extend(fila.descendants())
    except Exception:
        pass

    for control in controles:
        try:
            texto = obtener_texto_celda(control).strip()
        except Exception:
            continue

        texto_normalizado = normalizar_texto_tns(texto)
        if not texto_normalizado or texto_normalizado in vistos:
            continue
        if texto_normalizado == f"FILA {numero_fila}":
            continue

        vistos.add(texto_normalizado)
        textos.append(texto)

    return textos


def obtener_nombre_fila_tns(ventana, numero_fila: int) -> str:
    textos = obtener_textos_fila_tns(ventana, numero_fila)
    if len(textos) > TNS_NOMBRE_FILA_INDICE:
        return textos[TNS_NOMBRE_FILA_INDICE].strip()

    if len(textos) > 8:
        return textos[8].strip()

    if textos and ";" in textos[0]:
        columnas = [columna.strip() for columna in textos[0].split(";") if columna.strip()]
        for indice in (4, 7, len(columnas) - 1):
            if 0 <= indice < len(columnas):
                return columnas[indice]

    return ""


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
    if not TNS_APP_PATH:
        raise ValueError("Falta TNS_APP_PATH en .env con la ruta de Portal TNS")
    os.startfile(TNS_APP_PATH)
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
    # Esperar explícitamente a que aparezca la ventana principal en lugar de un sleep fijo
    ventana = Desktop(backend="uia").window(title_re=".*Portal TNS.*", auto_id="MainForm", control_type="Window")
    ventana.wait("exists visible", timeout=40)
    time.sleep(1) # Pequeña pausa extra por si la interfaz está terminando de renderizar
    
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


def manejar_tns(ventana, item: dict, mantener_sesion=None):
    enfocar_tns(ventana)
    buscar = ventana.child_window(auto_id="Buscar", control_type="Edit")
    buscar.click_input()
    tipos_validos = {"portabilidad", "linea_nueva", "upgrade"}
    ultimo_resultado = None
    mejor_candidato = None
    variantes_busqueda = obtener_variantes_busqueda_usuario(item["usuario"])

    log_tns("ITEM RECIBIDO PARA BUSCAR EN TNS", item)
    log_tns(
        "VARIANTES DE BUSQUEDA TNS",
        {
            "usuario_original": item.get("usuario"),
            "variantes": variantes_busqueda,
        },
    )

    for busqueda_usuario in variantes_busqueda:
        if mantener_sesion is not None:
            mantener_sesion()
        print(f"[TNS] Buscando variante: {busqueda_usuario}", flush=True)
        buscar.click_input()
        buscar.set_edit_text(busqueda_usuario)
        time.sleep(1)
        buscar.type_keys("{ENTER}")
        time.sleep(2)
        if cerrar_popup_tns_si_existe(ventana):
            print(f"[TNS] Popup cerrado para busqueda: {busqueda_usuario}", flush=True)
            buscar.click_input()
            continue

        filas = obtener_filas_facturas_tns(ventana)
        log_tns(
            "FILAS ENCONTRADAS EN TNS",
            {
                "busqueda": busqueda_usuario,
                "filas": filas,
                "cantidad": len(filas),
            },
        )
        for numero_fila in filas:
            if mantener_sesion is not None:
                mantener_sesion()
            nombre_tns = obtener_nombre_fila_tns(ventana, numero_fila)
            similitud = calcular_similitud_nombres(item["usuario"], nombre_tns)
            coincidencia = {
                "usuario_poliedro": item.get("usuario"),
                "busqueda_usada": busqueda_usuario,
                "fila_tns": numero_fila,
                "nombre_tns": nombre_tns,
                "similitud": round(similitud, 1),
                "minimo_requerido": TNS_MATCH_MIN_SCORE,
                "aceptada_por_nombre": similitud >= TNS_MATCH_MIN_SCORE,
            }
            log_tns("COINCIDENCIA TNS", coincidencia)
            if mejor_candidato is None or similitud > mejor_candidato["similitud"]:
                mejor_candidato = {
                    "nombre": nombre_tns,
                    "similitud": similitud,
                    "busqueda": busqueda_usuario,
                    "fila": numero_fila,
                }

            if similitud < TNS_MATCH_MIN_SCORE:
                continue

            try:
                resultado = leer_factura_tns(ventana, item, numero_fila)
            except Exception as error:
                log_tns(
                    "ERROR LEYENDO FACTURA TNS",
                    {
                        **coincidencia,
                        "error": str(error),
                    },
                )
                continue

            resultado["usuario_tns"] = nombre_tns
            resultado["similitud_usuario_tns"] = round(similitud, 1)
            resultado["busqueda_tns"] = busqueda_usuario
            log_tns(
                "RESULTADO LEIDO DESDE TNS",
                {
                    "usuario_poliedro": item.get("usuario"),
                    "usuario_tns": nombre_tns,
                    "tipo_plan": resultado.get("tipo_plan"),
                    "descripcion_tns": resultado.get("descripcion_tns"),
                    "descripciones_tns": resultado.get("descripciones_tns"),
                    "similitud": round(similitud, 1),
                    "busqueda_tns": busqueda_usuario,
                },
            )
            ultimo_resultado = resultado
            if resultado["tipo_plan"] in tipos_validos:
                log_tns("RESULTADO ACEPTADO TNS", resultado)
                return resultado

    if ultimo_resultado is None:
        if mejor_candidato is not None:
            log_tns("MEJOR CANDIDATO TNS NO ACEPTADO", mejor_candidato)
            raise ValueError(
                f"No se encontro el usuario en TNS con similitud >= {TNS_MATCH_MIN_SCORE}%: "
                f"{item['usuario']}. Mejor candidato: "
                f"{mejor_candidato['nombre'] or '[sin nombre]'} "
                f"({mejor_candidato['similitud']:.1f}%)"
            )
        raise ValueError(f"No se encontro el usuario en TNS: {item['usuario']}")

    log_tns("ULTIMO RESULTADO TNS SIN TIPO VALIDO", ultimo_resultado)
    return ultimo_resultado
