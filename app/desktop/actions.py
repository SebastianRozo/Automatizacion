from pywinauto import Application
import os
import time
from app.config.settings import TNS_USERNAME, TNS_PASSWORD,TNS_OFFICE


#SCRIPT PARA MANEJAR TNS FUNCIONANDO 
def entrar_tns():
    os.startfile(r"C:\Users\Sebas\OneDrive\Escritorio\Portal TNS.appref-ms")
    time.sleep(5)
    app = Application(backend="uia").connect(title_re=".*Portal TNS.*",timeout=10)
    ventana = app.window(title_re=".*Portal TNS.*")
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
def manejar_tns(item: dict):
    ventana = entrar_tns()
    time.sleep(7)
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
    buscar = ventana.child_window(auto_id="Buscar", control_type="Edit")
    buscar.click_input()
    buscar.set_edit_text(item["usuario"])
    time.sleep(1)
    buscar.type_keys("{ENTER}")
    time.sleep(2)
    fila = ventana.child_window(title="Fila 1", control_type="ListItem")
    fila.double_click_input()
    time.sleep(2)
    print(ventana.print_control_identifiers())
    tipo_plan = "valor_extraido_de_tns"
    item["tipo_plan"] = tipo_plan
    return item