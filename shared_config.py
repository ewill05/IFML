# shared_config.py
import json, os

CONFIG_PATH = os.path.join(os.path.expanduser("~"), ".ifml_config.json")

def _read_cfg():
    if not os.path.exists(CONFIG_PATH):
        return {}
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _write_cfg(cfg):
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)

def set_db_path(path: str):
    cfg = _read_cfg()
    cfg["species_db_path"] = path
    _write_cfg(cfg)

def get_db_path(default: str = "") -> str:
    return _read_cfg().get("species_db_path", default)
