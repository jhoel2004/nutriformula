import json
import os

CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".nutriformula", "config.json")

def cargar_config():
    if not os.path.exists(CONFIG_FILE):
        return {"archivos_recientes": []}
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {"archivos_recientes": []}

def guardar_config(config):
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2)

