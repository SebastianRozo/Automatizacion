import json
from datetime import datetime

from app.config.settings import BASE_DIR


PROGRESS_FILE = BASE_DIR / "planillas_progreso.json"


def _volante_key(datos_volante: dict) -> str:
    partes = [
        datos_volante.get("fecha", ""),
        datos_volante.get("codigo_oficina_planilla", ""),
        datos_volante.get("codigo_usuario", datos_volante.get("usuario", "")),
        str(datos_volante.get("dinero", datos_volante.get("dinero_volante", ""))),
    ]
    return "|".join(str(parte).strip() for parte in partes)


def _load_progress() -> dict:
    if not PROGRESS_FILE.exists():
        return {}

    try:
        return json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_progress(progress: dict) -> None:
    PROGRESS_FILE.write_text(
        json.dumps(progress, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def obtener_valor_aplicado(datos_volante: dict) -> int:
    progress = _load_progress()
    item = progress.get(_volante_key(datos_volante), {})
    return int(item.get("valor_aplicado", 0) or 0)


def obtener_productos_generados(datos_volante: dict) -> set[str]:
    progress = _load_progress()
    item = progress.get(_volante_key(datos_volante), {})
    return {
        str(planilla.get("producto", "")).strip()
        for planilla in item.get("planillas", [])
        if str(planilla.get("producto", "")).strip()
    }


def registrar_planilla_generada(
    datos_volante: dict,
    producto: str,
    valores_planilla: dict,
) -> int:
    progress = _load_progress()
    key = _volante_key(datos_volante)
    item = progress.setdefault(
        key,
        {
            "fecha_volante": datos_volante.get("fecha", ""),
            "codigo_oficina_planilla": datos_volante.get("codigo_oficina_planilla", ""),
            "codigo_usuario": datos_volante.get("codigo_usuario", datos_volante.get("usuario", "")),
            "dinero_volante": datos_volante.get("dinero", datos_volante.get("dinero_volante", 0)),
            "valor_aplicado": 0,
            "planillas": [],
        },
    )

    valor_para_volante = int(valores_planilla.get("valor_para_volante", 0) or 0)
    item["valor_aplicado"] = int(item.get("valor_aplicado", 0) or 0) + valor_para_volante
    item.setdefault("planillas", []).append(
        {
            "fecha_registro": datetime.now().isoformat(timespec="seconds"),
            "producto": str(producto),
            "valor_total": int(valores_planilla.get("valor_total", 0) or 0),
            "valor_tarjeta_credito": int(valores_planilla.get("valor_tarjeta_credito", 0) or 0),
            "valor_para_volante": valor_para_volante,
        }
    )
    _save_progress(progress)
    return item["valor_aplicado"]
