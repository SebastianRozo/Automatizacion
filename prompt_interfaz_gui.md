# Prompt para generar la interfaz grafica de escritorio

```text
Quiero que revises este proyecto Python y me generes una interfaz grafica de escritorio para la automatizacion existente.

Contexto del codigo:
- La app principal esta en `main.py` y `app/main.py`.
- El flujo actual arranca con `app.flows.flyers.auth.login()`.
- En `app/flows/flyers/auth.py`, el login usa Selenium, toma `POLIEDRO_USERNAME` y `POLIEDRO_PASSWORD` desde `.env`, y actualmente pide el token con `input("Ingrese el token: ")`.
- En `app/config/settings.py` se cargan variables desde `.env`: `POLIEDRO_URL`, `POLIEDRO_USERNAME`, `POLIEDRO_PASSWORD`, `TNS_OFFICE`, `TNS_USERNAME`, `TNS_PASSWORD`, `PRINTER`, `HEADLESS`, `DEFAULT_TIMEOUT`, `FORM_READY_DELAY_SECONDS`.
- En `app/desktop/actions.py`, la funcion `entrar_tns()` abre Portal TNS y llena oficina, usuario y contrasena con `TNS_OFFICE`, `TNS_USERNAME`, `TNS_PASSWORD`.
- Actualmente los logs son `print(...)` repartidos en archivos como `auth.py`, `flyers/actions.py` y `spreadsheets/main.py`.

Objetivo:
Crear una app de escritorio con interfaz grafica para ejecutar esta automatizacion sin usar consola.

Requisitos de interfaz:
1. Usar Python. Preferiblemente `tkinter`/`ttk` para no agregar dependencias pesadas, salvo que justifiques otra opcion.
2. Crear una ventana principal con estas secciones:
   - Configuracion Poliedro:
     - URL
     - Usuario
     - Contrasena, con campo tipo password
   - Configuracion TNS:
     - Oficina
     - Usuario
     - Contrasena, con campo tipo password
   - Configuracion general:
     - Impresora
     - Checkbox `HEADLESS`
     - Delay del formulario
   - Token:
     - Campo para ingresar el token manualmente
     - El token no debe guardarse en `.env`
   - Controles:
     - Boton "Iniciar"
     - Boton "Detener" si es viable
     - Estado actual del proceso
   - Logs:
     - Un panel tipo consola, oscuro, monoespaciado, con scroll
     - Mostrar ahi todos los `print`, errores y progreso del proceso en tiempo real
3. La interfaz no debe congelarse mientras corre Selenium/pywinauto. Ejecutar la automatizacion en un thread separado.
4. Redirigir `stdout` y `stderr` al panel de logs de la interfaz.
5. Guardar las credenciales/configuracion en `.env`, excepto el token.
6. Mantener las contrasenas en campos ocultos.
7. Antes de iniciar, validar que no falten:
   - `POLIEDRO_USERNAME`
   - `POLIEDRO_PASSWORD`
   - `TNS_OFFICE`
   - `TNS_USERNAME`
   - `TNS_PASSWORD`
   - token
8. Refactorizar lo minimo necesario:
   - Evitar que `login()` use `input()`.
   - Permitir pasar el token desde la GUI.
   - Mantener el flujo existente de Selenium y TNS.
9. Manejar errores con `try/except` y mostrarlos en los logs.
10. Dejar el punto de entrada claro, por ejemplo `desktop_app.py` o similar.

Importante:
- No imprimas contrasenas ni token en los logs.
- No rompas el flujo actual de automatizacion.
- Hace cambios pequenos y ordenados.
- Explicame que archivos modificaste y como ejecutar la interfaz.
- Si necesitas cambiar firmas de funciones, hacelo de forma simple y explicita.
```
