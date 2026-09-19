# 🤖 Automatización Poliedro — Frontera Celular SAS

Sistema de automatización de browser y desktop para el proceso diario de **volantes y planillas** en el sistema Poliedro y el software TNS (Portal TNS / Cartera).

---

## 📋 ¿Qué hace este proyecto?

El bot ejecuta de forma automática el flujo completo de trabajo que normalmente hace un operador a mano:

1. **Inicia sesión en Poliedro** con usuario, contraseña y token 2FA.
2. **Descarga los volantes del día** (o de un rango de fechas configurable) para cada oficina registrada.
3. **Captura screenshots** de cada volante y los guarda organizados por fecha y oficina.
4. **Abre el módulo de planillado** en Poliedro y, por cada volante:
   - Llena el formulario con los datos del asesor, la oficina y el producto.
   - Consulta el tipo de plan de cada activación (portabilidad, línea nueva, upgrade) en **TNS**.
   - Ajusta los checkboxes de la tabla de planilla para que el efectivo cuadre con el valor del volante.
   - Maneja casos especiales de **tarjeta de crédito mixta** y portabilidades antiguas.
   - **Simula, genera e imprime** la planilla (3 copias) directamente desde Chrome.
5. **Guarda reportes** de progreso, usuarios no encontrados y portabilidades faltantes.

---

## 🗂️ Estructura del proyecto

```
Automatizacion/
├── main.py                          # Punto de entrada CLI mínimo (modo debug)
├── desktop_app.py                   # Punto de entrada principal (GUI + CLI)
├── build_windows.bat                # Script para compilar el .exe con PyInstaller
├── requirements.txt                 # Dependencias Python
├── .env                             # Variables de entorno (NO se sube al repo)
├── .env.example                     # Plantilla de variables de entorno
└── app/
    ├── GUI/
    │   └── main.py                  # Interfaz gráfica Tkinter
    ├── browser/
    │   ├── driver.py                # Crea el WebDriver de Chrome
    │   └── actions.py               # Acciones Selenium reutilizables
    ├── config/
    │   ├── settings.py              # Lee variables de entorno y define constantes
    │   └── selectors.py             # IDs y selectores CSS/XPath de Poliedro
    ├── desktop/
    │   ├── actions.py               # Automatización de TNS con pywinauto
    │   └── helpers.py               # Comparación de nombres y clasificación de planes
    ├── flows/
    │   ├── flyers/
    │   │   ├── auth.py              # Login en Poliedro + orquestación del flujo
    │   │   ├── actions.py           # Descarga e iteración de volantes
    │   │   └── helpers.py           # Fechas de consulta y construcción de datos
    │   └── spreadsheets/
    │       ├── main.py              # Lógica principal de planillado
    │       ├── planilla_actions.py  # Interacciones con la tabla de planilla
    │       └── helpers.py           # Utilidades de texto, fechas y dinero
    ├── printing/
    │   └── planilla.py              # Inyecta CSS de impresión y lanza window.print()
    ├── storage/
    │   ├── main.py                  # Crea carpetas de capturas organizadas por fecha
    │   ├── spreadsheet_progress.py  # Guarda progreso de planillas en JSON
    │   ├── not_found_users.py       # Exporta usuarios no encontrados a CSV
    │   └── portabilidades.py        # Exporta portabilidades faltantes a Excel
    └── template/
        └── codes_places/
            └── main.py              # Lista de oficinas con sus códigos
```

---

## 📁 Descripción detallada de cada archivo

### Raíz del proyecto

| Archivo | Descripción |
|---|---|
| `main.py` | Entrada mínima que llama directamente a `login()`. Útil para pruebas rápidas en terminal. |
| `desktop_app.py` | Punto de entrada oficial. Parsea argumentos CLI (`--run-automation`, `--offices`) y decide si abrir la GUI o correr la automatización sin interfaz. |
| `build_windows.bat` | Compila el proyecto en un único `.exe` con PyInstaller para distribución en Windows. |
| `requirements.txt` | Lista las dependencias: `selenium`, `pywinauto`, `openpyxl`, `rapidfuzz`. |
| `.env.example` | Plantilla con todas las variables de entorno disponibles y sus valores por defecto. Copiar a `.env` y completar. |

---

### `app/GUI/main.py` — Interfaz gráfica

Interfaz Tkinter con múltiples pestañas que permite:

- **Configurar** todas las variables de entorno (credenciales, rutas, impresora) sin editar el `.env` a mano.
- **Seleccionar oficinas** específicas a procesar (o todas).
- **Ingresar el token** de Poliedro antes de iniciar.
- **Ejecutar la automatización** en un hilo separado y ver el log en tiempo real.
- **Cancelar** la ejecución en curso.

La GUI llama a `desktop_app.py` como subproceso para poder matar el proceso limpiamente si el usuario cancela.

---

### `app/browser/`

#### `driver.py`

Crea el `webdriver.Chrome` con las preferencias de impresión preconfiguradas:
- **Impresora destino** (`PRINTER_NAME`): se establece como destino por defecto en Chrome.
- **Tamaño carta**, sin encabezados/pies de página, con colores, sin dúplex.
- **Escala de impresión** (`PRINT_SCALE`, por defecto `80%`).
- Argumento `--kiosk-printing` para que Chrome imprima sin mostrar el diálogo.
- Soporte modo `--headless` para ejecución invisible.

#### `actions.py`

Funciones Selenium de bajo nivel usadas en todo el proyecto:

| Función | Descripción |
|---|---|
| `open_url(driver, url)` | Navega a una URL y espera que el DOM esté listo (`readyState == "complete"`). |
| `wait_clickable(driver, by, value)` | Espera hasta que un elemento sea clickeable. |
| `wait_present(driver, by, value)` | Espera hasta que un elemento esté presente en el DOM. |
| `click(driver, by, value)` | Espera a que sea clickeable y hace click. |
| `type_text(driver, by, value, text)` | Limpia un campo y escribe texto con pausas para evitar problemas de timing. |
| `selectInSelect(driver, by, value, option)` | Selecciona una opción en un `<select>` de HTML con reintento por `StaleElementReferenceException`. |
| `enfocar_chrome(driver)` | Trae la ventana de Chrome al frente y le da el foco. |
| `capture_screenshot(driver, filename)` | Toma una captura a tamaño completo de la página y la guarda en `CAPTURAS_DIR`. |

---

### `app/config/`

#### `settings.py`

Carga el archivo `.env` (y opcionalmente `dist/.env`) e expone constantes:

| Variable | Descripción | Default |
|---|---|---|
| `POLIEDRO_URL` | URL de login de Poliedro | URL de producción Comcel |
| `POLIEDRO_USERNAME` | Usuario Poliedro | — |
| `POLIEDRO_PASSWORD` | Contraseña Poliedro | — |
| `DEFAULT_TIMEOUT` | Timeout general de Selenium (segundos) | `10` |
| `FORM_READY_DELAY_SECONDS` | Pausa antes de enviar formularios | `4` |
| `PRINTER_NAME` | Nombre de la impresora de Windows | — |
| `HEADLESS` | Ejecutar Chrome sin ventana | `false` |
| `PRINT_FLYERS` | Habilitar/deshabilitar impresión de volantes | `true` |
| `PRINT_SCALE` | Escala de impresión (%) | `80` |
| `CAPTURAS_DIR` | Ruta donde se guardan screenshots y reportes | Ruta en Windows |
| `VOLANTES_FECHA_INICIAL` | Fecha inicio para consulta (`dd/mm/yyyy`) | — (usa ayer) |
| `VOLANTES_FECHA_FINAL` | Fecha fin para consulta (`dd/mm/yyyy`) | — (usa ayer) |
| `TNS_OFFICE` | Código de empresa en TNS | — |
| `TNS_USERNAME` | Usuario de TNS | — |
| `TNS_PASSWORD` | Contraseña de TNS | — |
| `TNS_APP_PATH` | Ruta al ejecutable de Portal TNS | — |

#### `selectors.py`

Centraliza **todos los IDs y selectores CSS/XPath** de las páginas de Poliedro. Si Poliedro cambia su HTML, este es el único archivo que hay que tocar. Incluye selectores para: login, token, módulo de volantes, módulo de planillado y tabla de resultados.

---

### `app/flows/flyers/`

#### `auth.py`

Orquestador principal del flujo completo:

1. Crea el driver de Chrome.
2. Abre Poliedro y llama a `submit_credentials()`.
3. Pide el token (por `stdin` o variable de entorno `AUTOMATION_TOKEN`).
4. Llama a `submit_token()`.
5. Llama a `download_flyers()` para obtener todos los datos de volantes.
6. Llama a `abrir_planillado()` para ir al módulo de planillas.
7. Por cada volante, llama a `go_to_spreadsheets()` para generar la planilla.
8. Cierra el driver al finalizar (incluso si hay error).

#### `actions.py`

Lógica de navegación y extracción de volantes:

- **`download_flyers()`**: navega al módulo de migración → sección de Volantes NIT.
- **`get_flyers()`**: itera sobre cada oficina y cada fecha de consulta. Para cada volante: filtra usuarios omitidos, captura screenshots, extrae código de usuario y valor, y opcionalmente envía a imprimir.
- **`obtener_volantes_por_oficina()`**: llena el formulario de búsqueda (distribuidor, tipo `"V"`, fecha) y hace click en Consultar.
- **`asegurar_formulario_volantes()`**: verifica que el formulario esté visible; si no, navega directamente a la URL.

#### `helpers.py`

Utilidades para fechas y datos de volantes:

| Función | Descripción |
|---|---|
| `obtener_fechas_consulta_volantes()` | Retorna las fechas a consultar. Si es lunes retorna sábado + domingo. Respeta el rango configurado en `.env`. |
| `obtener_fechas_configuradas()` | Parsea y valida el rango de fechas del `.env`. |
| `normalizar_dinero(valor)` | Extrae solo los dígitos de un string monetario. |
| `construir_datos_volante(...)` | Construye el diccionario estándar de un volante con todos sus campos. |

---

### `app/flows/spreadsheets/`

#### `main.py`

El archivo más complejo del proyecto. Implementa `go_to_spreadsheets()`, que:

1. **Extrae parámetros** del volante (código usuario, código oficina, fecha, productos).
2. **Llena el formulario** de planillado con `llenar_formulario_planillado()`.
3. Si el sistema indica que no hay planilla disponible, continúa con el siguiente producto.
4. **Clasifica filas** de la tabla: llama a `manejar_tns()` por cada activación no portabilidad, para saber si es línea nueva, upgrade o portabilidad.
5. **Ajusta checkboxes**: desmarca líneas nuevas y upgrades según lo indicado por TNS.
6. **Valida el dinero**: compara la suma de la tabla con el valor del volante.
7. **Maneja portabilidades antiguas**: si el monto no coincide, va eliminando portabilidades antiguas hasta cuadrar.
8. **Maneja tarjeta de crédito**: si hay montos de TC en la simulación, genera planillas individuales para aislar esas ventas.
9. **Genera e imprime** la planilla con `generar_e_imprimir_planilla()`.
10. **Guarda progreso** en `planillas_progreso.json` para poder reanudar si se interrumpe.

Otras funciones relevantes:

| Función | Descripción |
|---|---|
| `mantener_sesion_poliedro()` | Ejecuta un mousemove y fetch periódico para evitar timeout de sesión mientras se trabaja en TNS. |
| `simular_planilla()` | Hace click en "Simular" y lee el valor total y tarjeta de crédito. |
| `excluir_todas_las_facturas()` | Marca todos los checkboxes de la tabla (los marcados quedan excluidos). |
| `seleccionar_facturas_solo_tarjeta_credito()` | Prueba cada factura individualmente para encontrar una con TC cuyo efectivo no supere el saldo. |
| `guardar_captura_planilla_generada()` | Toma screenshot de la planilla generada antes de imprimirla. |

#### `planilla_actions.py`

Interacciones específicas con la tabla HTML de planilla:

| Función | Descripción |
|---|---|
| `abrir_planillado()` | Navega al formulario de generación de planillas (por menú o URL directa). |
| `llenar_formulario_planillado()` | Selecciona todos los dropdowns del formulario y confirma. Incluye lógica de calendario para seleccionar la fecha inicial. |
| `obtener_filas_planilla()` | Lee todas las filas de la tabla, filtrando activaciones de hoy o posteriores al volante. Clasifica filas anteriores como "portabilidad". |
| `check_first_checkbox()` | Hace click en el checkbox de la cabecera para seleccionar todas las filas. |
| `get_checkbox_por_usuario()` | Busca el checkbox de una fila específica por código de usuario y fecha de activación. |
| `validate_money()` | Calcula la suma de las filas no excluidas y la compara con el valor del volante. |
| `obtener_porta_antigua()` | Encuentra la portabilidad incluida más antigua (para desmarcarla y reducir el total). |
| `contar_portabilidades_restantes()` | Cuenta cuántas portabilidades del resultado de TNS están aún incluidas en la tabla. |
| `seleccionar_fecha_inicial_planilla()` | Usa el widget de calendario de ASP.NET para navegar al mes correcto y seleccionar el día. |

#### `helpers.py`

Utilidades pequeñas de texto y fechas:

| Función | Descripción |
|---|---|
| `limpiar_texto()` | Elimina espacios non-breaking y espacios extra. |
| `normalizar_dinero()` | Extrae dígitos de un string monetario. |
| `parsear_fecha()` | Parsea fechas con formato `dd/mm/yyyy hh:mm:ss a.m./p.m.`. |
| `clasificar_fecha_activacion()` | Determina si una fecha de activación es anterior, posterior o la misma que el volante. |
| `obtener_valor_select()` | Busca un valor en el diccionario del volante probando múltiples claves. |
| `obtener_valores_producto()` | Retorna la lista de productos a procesar (`["3", "7", "5"]` por defecto). |

---

### `app/desktop/`

#### `actions.py`

Automatiza el **Portal TNS** (aplicación de escritorio Windows) usando `pywinauto`:

| Función | Descripción |
|---|---|
| `entrar_tns()` | Lanza el ejecutable de TNS, espera la ventana de login, e ingresa oficina, usuario y contraseña. |
| `ingresar_a_cartera()` | Navega dentro de TNS: Empresa → Cartera → Movimientos → Recibos. |
| `manejar_tns()` | Función principal: busca un usuario en TNS probando múltiples variantes del nombre, lee la factura y clasifica el tipo de plan. |
| `leer_factura_tns()` | Abre el detalle de una fila, lee el campo de descripción y llama a `clasificar_tipo_plan()`. |
| `cerrar_popup_tns_si_existe()` | Detecta y cierra popups de "Recibo de Caja" que aparecen durante la búsqueda. |
| `obtener_nombre_fila_tns()` | Extrae el nombre del cliente de una fila de resultados. |
| `obtener_texto_celda()` | Intenta leer el texto de una celda por múltiples vías (iface_value, legacy_properties, texts(), children()). |
| `log_tns()` | Imprime un bloque de log formateado con pprint para debugging. |

#### `helpers.py`

Lógica de comparación de nombres y clasificación de planes:

| Función | Descripción |
|---|---|
| `normalizar_texto_tns()` | Elimina tildes y normaliza a mayúsculas. |
| `calcular_similitud_nombres()` | Compara nombres usando `rapidfuzz.token_sort_ratio` (o `difflib` como fallback). Considera 100% cuando difieren solo en una palabra. |
| `calcular_similitud_por_palabras()` | Empareja palabras individualmente con la mejor similitud posible. |
| `obtener_variantes_busqueda_usuario()` | Genera variantes del nombre en distinto orden para maximizar las chances de encontrar el usuario en TNS. |
| `clasificar_tipo_plan()` | Determina si el texto de una factura TNS corresponde a `portabilidad`, `linea_nueva`, `upgrade` u `otro`. |

**Constante**: `TNS_MATCH_MIN_SCORE = 90` — similitud mínima para aceptar un resultado de TNS.

---

### `app/printing/planilla.py`

Módulo de impresión:

| Función | Descripción |
|---|---|
| `aplicar_configuracion_impresion(driver, ajustar_zoom)` | Inyecta CSS en la página para controlar el layout de impresión: tamaño carta, márgenes, anchos de columna fijos, ocultar botones. Si `ajustar_zoom=True` activa el modo compacto con fuente más pequeña. |
| `imprimir_copias(driver, copias)` | Llama a `window.print()` N veces (por defecto 3 copias) con una pausa entre cada una. |

---

### `app/storage/`

#### `main.py`

Gestión de carpetas para guardar archivos:
- **`rutaGuardado()`**: retorna y crea si no existe `CAPTURAS_DIR`.
- **`createFolders(fecha)`**: crea `CAPTURAS_DIR/volantes dd-mm-yyyy/`.
- **`get_office_folder(codeplace, fecha)`**: crea y retorna `CAPTURAS_DIR/volantes dd-mm-yyyy/<nombre_oficina>/`.

#### `spreadsheet_progress.py`

Persistencia de progreso en `planillas_progreso.json`:
- Cada volante tiene una clave única `fecha|codigo_oficina|codigo_usuario|dinero`.
- Guarda el **valor acumulado aplicado** y el detalle de cada planilla generada.
- `obtener_valor_aplicado()`: lee cuánto se ha aplicado ya para reanudar si el proceso se interrumpe.
- `registrar_planilla_generada()`: actualiza el progreso y retorna el nuevo total aplicado.

#### `not_found_users.py`

Exporta a `usuarios_no_encontrados.csv` los asesores que no se encontraron en TNS, con columnas: fecha, código oficina, código usuario, nombre, producto, fecha activación, valor planilla, error y acción sugerida.

#### `portabilidades.py`

Exporta a `portabilidades_faltantes.xlsx` la cantidad de portabilidades que no pudieron cuadrarse con el valor del volante, acumulando por oficina si ya existe una entrada.

---

### `app/template/codes_places/main.py`

Lista estática de las **oficinas registradas** en el sistema, usada para:
- Saber qué códigos pasar al formulario de Poliedro (`poliedro_code`).
- Saber qué código usar en la planilla (`planilla_code`).
- Identificar oficinas por nombre en logs y carpetas de capturas.

Cada oficina tiene: `name`, `office_code`, `poliedro_code`, `planilla_code`, `usuarios`.

---

## 🚀 Instalación y configuración

### Requisitos
- **Windows** (requerido para pywinauto y el Portal TNS)
- **Python 3.10+**
- **Google Chrome** instalado
- **Portal TNS** instalado en el equipo

### Pasos

```bash
# 1. Clonar el repositorio
git clone <url-del-repo>
cd Automatizacion

# 2. Crear entorno virtual
python -m venv .venv
.venv\Scripts\activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
copy .env.example .env
# Editar .env con tus credenciales
```

### Variables obligatorias en `.env`

```env
POLIEDRO_USERNAME=tu_usuario
POLIEDRO_PASSWORD=tu_contraseña

TNS_OFFICE=FRONTERA CELULAR SAS
TNS_USERNAME=tu_usuario_tns
TNS_PASSWORD=tu_contraseña_tns
TNS_APP_PATH=C:\ruta\al\PortalTNS.exe

PRINTER=Nombre de tu impresora en Windows
CAPTURAS_DIR=D:\ruta\donde\guardar\capturas
```

---

## ▶️ Uso

### Con interfaz gráfica (recomendado)
```bash
python desktop_app.py
```

### Sin interfaz, todas las oficinas
```bash
python desktop_app.py --run-automation
```

### Sin interfaz, oficinas específicas
```bash
python desktop_app.py --run-automation --offices 01,02,05
```

### Proporcionar token por variable de entorno
```bash
set AUTOMATION_TOKEN=tu_token_de_poliedro
python desktop_app.py --run-automation
```

---

## 🏗️ Compilar ejecutable para distribución

```bat
build_windows.bat
```

Genera `dist\AutomatizacionPoliedro.exe`. Copiar junto con el archivo `.env` configurado.

---

## 📂 Archivos generados en ejecución

Todos se guardan dentro de `CAPTURAS_DIR`:

```
CAPTURAS_DIR/
└── volantes dd-mm-yyyy/
    ├── <nombre_oficina>/
    │   ├── Lista_Volantes_<oficina>_<fecha>_<n>.png   # Lista de volantes
    │   ├── screenshot_<oficina>_<fecha>_<n>.png       # Detalle del volante
    │   └── planilla_generada_<oficina>_<usuario>_...png
    ├── usuarios_no_encontrados.csv                    # Asesores no encontrados en TNS
    └── portabilidades_faltantes.xlsx                  # Portabilidades sin cuadrar
planillas_progreso.json                                # Progreso acumulado de planillas
```

---

## 🔧 Configuración avanzada

| Variable `.env` | Descripción |
|---|---|
| `PRINT_FLYERS=false` | Desactiva la impresión de volantes (solo hace capturas). |
| `HEADLESS=true` | Ejecuta Chrome sin ventana visible. |
| `PRINT_SCALE=80` | Escala de impresión en %. Rango válido: 10–200. |
| `VOLANTES_FECHA_INICIAL=15/09/2026` | Procesa desde esta fecha en lugar de "ayer". |
| `VOLANTES_FECHA_FINAL=17/09/2026` | Procesa hasta esta fecha. |
| `FORM_READY_DELAY_SECONDS=4` | Pausa (segundos) antes de enviar formularios. Subir si la conexión es lenta. |
| `DEFAULT_TIMEOUT=10` | Timeout de espera de elementos Selenium en segundos. |

---

## 🐛 Depuración

El proyecto imprime logs detallados por `stdout`. Los bloques de TNS tienen el formato:

```
========== DICT QUE SE ENVIA A TNS ==========
{'codigo_activacion': '45096806', ...}
==============================================
```

Los usuarios que fallan en TNS se registran en `usuarios_no_encontrados.csv` con el mensaje de error exacto.

Si el proceso se interrumpe a mitad, el archivo `planillas_progreso.json` permite que la siguiente ejecución **reanude desde donde quedó**, descontando lo ya aplicado del saldo pendiente.

---

## 📦 Dependencias

| Paquete | Uso |
|---|---|
| `selenium >= 4.11` | Automatización del navegador Chrome (Poliedro) |
| `pywinauto` | Automatización del escritorio Windows (Portal TNS) |
| `openpyxl` | Leer/escribir archivos Excel (portabilidades faltantes) |
| `rapidfuzz` | Comparación difusa de nombres de asesores |

> Selenium Manager (incluido en Selenium 4) descarga automáticamente el ChromeDriver compatible con la versión de Chrome instalada.
