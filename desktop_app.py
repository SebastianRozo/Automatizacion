from __future__ import annotations

import argparse
import os
import traceback


def run_automation(selected_office_codes: list[str] | None = None) -> int:
    try:
        from app.flows.flyers.auth import login

        login(
            token=os.getenv("AUTOMATION_TOKEN") or None,
            selected_office_codes=selected_office_codes,
        )
        return 0
    except Exception:
        traceback.print_exc()
        return 1


def run_gui() -> int:
    from app.GUI.main import main

    main()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Automatizacion Poliedro")
    parser.add_argument(
        "--run-automation",
        action="store_true",
        help="Ejecuta la automatizacion sin abrir la interfaz grafica",
    )
    parser.add_argument(
        "--offices",
        default="",
        help="Codigos de oficinas a procesar separados por comas",
    )
    args = parser.parse_args()

    if args.run_automation:
        selected_office_codes = [
            code.strip()
            for code in args.offices.split(",")
            if code.strip()
        ]
        return run_automation(selected_office_codes or None)
    return run_gui()


if __name__ == "__main__":
    raise SystemExit(main())
