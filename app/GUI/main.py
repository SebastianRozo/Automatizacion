import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk
from app.template.codes_places.main import OFFICES
from app.config.settings import BASE_DIR, ENV_FILE


ENV_KEYS = [
    "POLIEDRO_URL",
    "POLIEDRO_USERNAME",
    "POLIEDRO_PASSWORD",
    "TNS_OFFICE",
    "TNS_USERNAME",
    "TNS_PASSWORD",
    "TNS_APP_PATH",
    "PRINTER",
    "HEADLESS",
    "PRINT_SCALE",
    "VOLANTES_FECHA_INICIAL",
    "VOLANTES_FECHA_FINAL",
    "DEFAULT_TIMEOUT",
    "FORM_READY_DELAY_SECONDS",
]

OBSOLETE_ENV_KEYS = {
    "PLANILLA_SALDO_PENDIENTE_MANUAL",
    "PLANILLA_REANUDAR_OFICINA",
    "PLANILLA_REANUDAR_USUARIO",
    "EXCEL_TEMPLATE_PATH",
    "EXCEL_OUTPUT_PATH",
    "PRINT_LANDSCAPE",
}

DEFAULTS = {
    "POLIEDRO_URL": "https://poliedrodist.comcel.com.co/POL_LOGIN/login.aspx",
    "HEADLESS": "false",
    "PRINT_SCALE": "70",
    "DEFAULT_TIMEOUT": "10",
    "FORM_READY_DELAY_SECONDS": "4",
}

REQUIRED_FIELDS = {
    "POLIEDRO_USERNAME": "Usuario Poliedro",
    "POLIEDRO_PASSWORD": "Contrasena Poliedro",
    "TNS_OFFICE": "Oficina TNS",
    "TNS_USERNAME": "Usuario TNS",
    "TNS_PASSWORD": "Contrasena TNS",
    "TNS_APP_PATH": "Ruta Portal TNS",
}


def read_env_file() -> dict[str, str]:
    values = DEFAULTS.copy()
    if not ENV_FILE.exists():
        return values

    for raw_line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def write_env_file(updated_values: dict[str, str]) -> None:
    existing = read_env_file()
    existing.update(updated_values)
    existing.pop("AUTOMATION_TOKEN", None)
    for key in OBSOLETE_ENV_KEYS:
        existing.pop(key, None)

    ordered_keys = [key for key in ENV_KEYS if key in existing]
    extra_keys = sorted(key for key in existing if key not in ordered_keys)
    lines = [f"{key}={existing.get(key, '')}" for key in [*ordered_keys, *extra_keys]]
    ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


class PoliedroApp(ttk.Frame):
    def __init__(self, root: tk.Tk) -> None:
        super().__init__(root, padding=16)
        self.root = root
        self.process: subprocess.Popen | None = None
        self.log_queue: queue.Queue[str] = queue.Queue()
        self.fields: dict[str, tk.StringVar] = {}
        self.headless_var = tk.BooleanVar(value=False)
        self.token_var = tk.StringVar()

        self.root.title("Automatizacion Poliedro")
        self.root.geometry("980x760")
        self.root.minsize(860, 650)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.pack(fill="both", expand=True)
        self._build_ui()
        self._load_values()
        self._poll_logs()

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)

        config_frame = ttk.Frame(self)
        config_frame.grid(row=0, column=0, sticky="ew")
        config_frame.columnconfigure(0, weight=1)
        config_frame.columnconfigure(1, weight=1)

        self._build_poliedro_section(config_frame)
        self._build_tns_section(config_frame)
        self._build_general_section()
        self._build_controls()
        self._build_logs()

    def _build_poliedro_section(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="Configuracion Poliedro", padding=12)
        frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=(0, 12))
        frame.columnconfigure(1, weight=1)

        self._add_entry(frame, "URL", "POLIEDRO_URL", 0)
        self._add_entry(frame, "Usuario", "POLIEDRO_USERNAME", 1)
        self._add_entry(frame, "Contrasena", "POLIEDRO_PASSWORD", 2, show="*")

    def _build_tns_section(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="Configuracion TNS", padding=12)
        frame.grid(row=0, column=1, sticky="nsew", padx=(8, 0), pady=(0, 12))
        frame.columnconfigure(1, weight=1)

        self._add_entry(frame, "Oficina", "TNS_OFFICE", 0)
        self._add_office_selector(frame,0)
        self._add_entry(frame, "Usuario", "TNS_USERNAME", 1)
        self._add_entry(frame, "Contrasena", "TNS_PASSWORD", 2, show="*")
        self._add_path_entry(frame, "Portal TNS", "TNS_APP_PATH", 3)

    def _build_general_section(self) -> None:
        frame = ttk.LabelFrame(self, text="Configuracion general", padding=12)
        frame.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        frame.columnconfigure(1, weight=1)
        frame.columnconfigure(4, weight=1)

        self._add_entry(frame, "Impresora", "PRINTER", 0, column=0)
        self._add_entry(frame, "Delay", "FORM_READY_DELAY_SECONDS", 0, column=3, width=10)

        headless = ttk.Checkbutton(frame, text="HEADLESS", variable=self.headless_var)
        headless.grid(row=1, column=0, sticky="w", pady=(8, 0))

        self._add_entry(frame, "Timeout", "DEFAULT_TIMEOUT", 1, column=1, width=10)
        self._add_entry(frame, "Escala impresion", "PRINT_SCALE", 1, column=3, width=10)
        self._add_entry(frame, "Fecha inicial volantes", "VOLANTES_FECHA_INICIAL", 3, column=0, width=16)
        self._add_entry(frame, "Fecha final volantes", "VOLANTES_FECHA_FINAL", 3, column=3, width=16)

    def _build_controls(self) -> None:
        frame = ttk.LabelFrame(self, text="Ejecucion", padding=12)
        frame.grid(row=2, column=0, sticky="ew", pady=(0, 12))
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text="Token").grid(row=0, column=0, sticky="w", padx=(0, 8))
        token_entry = ttk.Entry(frame, textvariable=self.token_var, show="*")
        token_entry.grid(row=0, column=1, sticky="ew", padx=(0, 12))
        token_entry.bind("<Return>", lambda _event: self.send_token())

        self.send_token_button = ttk.Button(
            frame,
            text="Enviar token",
            command=self.send_token,
            state="disabled",
        )
        self.send_token_button.grid(row=0, column=2, padx=(0, 8))

        self.start_button = ttk.Button(frame, text="Iniciar", command=self.start_automation)
        self.start_button.grid(row=0, column=3, padx=(0, 8))

        self.stop_button = ttk.Button(
            frame,
            text="Detener",
            command=self.stop_automation,
            state="disabled",
        )
        self.stop_button.grid(row=0, column=4)

        self.status_var = tk.StringVar(value="Listo")
        ttk.Label(frame, textvariable=self.status_var).grid(
            row=1, column=0, columnspan=5, sticky="w", pady=(10, 0)
        )

    def _build_logs(self) -> None:
        frame = ttk.LabelFrame(self, text="Logs", padding=8)
        frame.grid(row=3, column=0, sticky="nsew")
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

        self.log_text = scrolledtext.ScrolledText(
            frame,
            wrap="word",
            height=18,
            bg="#111827",
            fg="#e5e7eb",
            insertbackground="#e5e7eb",
            font=("Consolas", 10),
            state="disabled",
        )
        self.log_text.grid(row=0, column=0, sticky="nsew")
    def _add_office_selector(self,parent:ttk.Frame,row:int):
        var = tk.StringVar()
        self.fields['TNS_OFFICE']= var
        offices={f'{office["office_code"]} - {office['office_name']}' : office["office_code"] for office in OFFICES}
        ttk.label(parent, text="Oficina").grid(
            row = row , coliumn = 0, sticky = "w", padx=(0,8),pady = 4
        )
        selector = ttk.Combobox(
            parent,
            textvariable = var,
            values= list(offices.keys()),
            state = "readonly"
        )
        selector.grid(row = row, column= 1,sticky ="ew",pady=1)
    
    def guardar_codigo(_event=None):
        seleccion=selector.get()
        if seleccion in offices:
            var.set(offices[seleccion])

        selector.bind("<<ComboboxSelected>>", guardar_codigo)

    def _add_entry(
        self,
        parent: ttk.Frame,
        label: str,
        key: str,
        row: int,
        column: int = 0,
        width: int | None = None,
        show: str | None = None,
    ) -> None:
        var = tk.StringVar()
        self.fields[key] = var
        ttk.Label(parent, text=label).grid(row=row, column=column, sticky="w", padx=(0, 8), pady=4)
        entry = ttk.Entry(parent, textvariable=var, show=show, width=width)
        entry.grid(row=row, column=column + 1, sticky="ew", pady=4)

    def _add_path_entry(
        self,
        parent: ttk.Frame,
        label: str,
        key: str,
        row: int,
        column: int = 0,
        save_dialog: bool = False,
    ) -> None:
        self._add_entry(parent, label, key, row, column=column)
        button = ttk.Button(
            parent,
            text="Buscar",
            command=lambda: self._browse_path(key, save_dialog=save_dialog),
        )
        button.grid(row=row, column=column + 2, sticky="w", padx=(8, 0), pady=4)

    def _browse_path(self, key: str, save_dialog: bool = False) -> None:
        initial = self.fields[key].get().strip()
        initial_dir = str(Path(initial).parent) if initial else str(BASE_DIR)
        if save_dialog:
            selected = filedialog.asksaveasfilename(initialdir=initial_dir)
        else:
            selected = filedialog.askopenfilename(initialdir=initial_dir)
        if selected:
            self.fields[key].set(selected)

    def _load_values(self) -> None:
        values = read_env_file()
        for key, var in self.fields.items():
            var.set(values.get(key, DEFAULTS.get(key, "")))
        self.headless_var.set(values.get("HEADLESS", "false").lower() == "true")

    def _collect_values(self) -> dict[str, str]:
        values = {key: var.get().strip() for key, var in self.fields.items()}
        values["HEADLESS"] = "true" if self.headless_var.get() else "false"
        return values

    def _validate(self, values: dict[str, str]) -> bool:
        missing = [label for key, label in REQUIRED_FIELDS.items() if not values.get(key)]

        if missing:
            messagebox.showerror(
                "Faltan datos",
                "Completa estos campos antes de iniciar:\n\n" + "\n".join(missing),
            )
            return False

        fecha_inicial = values.get("VOLANTES_FECHA_INICIAL", "")
        fecha_final = values.get("VOLANTES_FECHA_FINAL", "")
        try:
            inicio = datetime.strptime(fecha_inicial, "%d/%m/%Y") if fecha_inicial else None
            fin = datetime.strptime(fecha_final, "%d/%m/%Y") if fecha_final else None
        except ValueError:
            messagebox.showerror(
                "Fecha invalida",
                "Las fechas de volantes deben estar en formato dd/mm/yyyy.",
            )
            return False

        if inicio and fin and inicio > fin:
            messagebox.showerror(
                "Rango invalido",
                "La fecha inicial de volantes no puede ser mayor que la fecha final.",
            )
            return False

        return True

    def start_automation(self) -> None:
        if self.process and self.process.poll() is None:
            return

        values = self._collect_values()
        token = self.token_var.get().strip()
        if not self._validate(values):
            return

        write_env_file(values)
        self._clear_logs()
        self._append_log("Configuracion guardada. Iniciando automatizacion...\n")

        command = self._automation_command()
        env = os.environ.copy()
        env.update(values)
        if token:
            env["AUTOMATION_TOKEN"] = token
        else:
            env.pop("AUTOMATION_TOKEN", None)
        env["PYTHONUNBUFFERED"] = "1"

        creationflags = 0
        if os.name == "nt":
            creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)

        try:
            self.process = subprocess.Popen(
                command,
                cwd=str(BASE_DIR),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.PIPE,
                text=True,
                bufsize=1,
                creationflags=creationflags,
            )
        except Exception as error:
            self.process = None
            messagebox.showerror("Error", f"No fue posible iniciar la automatizacion:\n{error}")
            return

        self.status_var.set("Ejecutando")
        self.start_button.configure(state="disabled")
        self.send_token_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        threading.Thread(target=self._read_process_output, daemon=True).start()

    def send_token(self) -> None:
        if not self.process or self.process.poll() is not None or self.process.stdin is None:
            return

        token = self.token_var.get().strip()
        if not token:
            messagebox.showerror("Falta token", "Ingresa el token generado en Poliedro.")
            return

        try:
            self.process.stdin.write(token + "\n")
            self.process.stdin.flush()
        except Exception as error:
            messagebox.showerror("Error", f"No fue posible enviar el token:\n{error}")
            return

        self.send_token_button.configure(state="disabled")
        self.status_var.set("Token enviado")
        self._append_log("Token enviado. Continuando automatizacion...\n")

    def stop_automation(self) -> None:
        if not self.process or self.process.poll() is not None:
            return

        self._append_log("\nDeteniendo automatizacion...\n")
        try:
            if os.name == "nt":
                subprocess.run(
                    ["taskkill", "/PID", str(self.process.pid), "/T", "/F"],
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            else:
                self.process.terminate()
        except Exception as error:
            self._append_log(f"No fue posible detener el proceso: {error}\n")

    def _automation_command(self) -> list[str]:
        if getattr(sys, "frozen", False):
            return [sys.executable, "--run-automation"]
        return [sys.executable, str(BASE_DIR / "desktop_app.py"), "--run-automation"]

    def _read_process_output(self) -> None:
        process = self.process
        if not process or process.stdout is None:
            return
        for line in process.stdout:
            self.log_queue.put(line)
        return_code = process.wait()
        self.log_queue.put(f"\nProceso finalizado con codigo {return_code}.\n")
        self.log_queue.put("__PROCESS_DONE__")

    def _poll_logs(self) -> None:
        while True:
            try:
                message = self.log_queue.get_nowait()
            except queue.Empty:
                break

            if message == "__PROCESS_DONE__":
                self.status_var.set("Listo")
                self.start_button.configure(state="normal")
                self.send_token_button.configure(state="disabled")
                self.stop_button.configure(state="disabled")
                continue

            if message.startswith("TOKEN_REQUIRED:"):
                self.status_var.set("Esperando token")
                self.send_token_button.configure(state="normal")
                self._append_log("Ingresa el token generado en Poliedro y presiona Enviar token.\n")
                continue

            self._append_log(message)

        self.root.after(100, self._poll_logs)

    def _append_log(self, text: str) -> None:
        self.log_text.configure(state="normal")
        self.log_text.insert("end", text)
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _clear_logs(self) -> None:
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

    def on_close(self) -> None:
        if self.process and self.process.poll() is None:
            if not messagebox.askyesno(
                "Automatizacion en ejecucion",
                "La automatizacion sigue en ejecucion. Deseas detenerla y cerrar?",
            ):
                return
            self.stop_automation()
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    PoliedroApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
