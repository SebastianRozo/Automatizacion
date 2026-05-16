import argparse
import os
import traceback


def run_automation() -> int:
    try:
        from app.flows.flyers.auth import login

        login(token=os.getenv("AUTOMATION_TOKEN") or None)
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
    args = parser.parse_args()

    if args.run_automation:
        return run_automation()
    return run_gui()


if __name__ == "__main__":
    raise SystemExit(main())
