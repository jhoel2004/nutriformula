# app/config.py — Configuración centralizada de VITAL v2.0
import json
import os
from app.utils import get_system_font, get_data_dir

FONT = get_system_font()

# ══════════════════════════════════════════════════════════════════════
# Paleta de colores profesional
# ══════════════════════════════════════════════════════════════════════
COLORS = {
    'bg_dark':       '#1E1E2E',
    'bg_surface':    '#252538',
    'bg_deeper':     '#0F0F1E',
    'bg_border':     '#2A2A4A',
    'primary':       '#2D7D46',
    'primary_light': '#5CB85C',
    'primary_dark':  '#1B4F2E',
    'accent':        '#5BC0DE',
    'warning':       '#F0AD4E',
    'danger':        '#D9534F',
    'muted':         '#6060A0',
    'text':          '#E0E0F0',
    'text_dim':      '#A0A0C0',
    'text_faint':    '#505070',
    'gold':          '#F0D060',
    # Semáforo
    'semaforo_ok':   '#1A3A2A',
    'semaforo_warn': '#3A2A0A',
    'semaforo_bad':  '#3A1A1A',
}

# ══════════════════════════════════════════════════════════════════════
# Estilos CSS reutilizables para tablas
# ══════════════════════════════════════════════════════════════════════
ESTILO_TABLA = f"""
    QTableWidget {{
        background-color: {COLORS['bg_dark']};
        alternate-background-color: {COLORS['bg_surface']};
        color: {COLORS['text']};
        gridline-color: {COLORS['bg_border']};
        border: 1px solid {COLORS['bg_border']};
        font-family: "{FONT}";
        font-size: 11px;
    }}
    QTableWidget::item {{
        background-color: {COLORS['bg_dark']};
        color: {COLORS['text']};
        padding: 4px 6px;
        border: none;
    }}
    QTableWidget::item:selected {{
        background-color: {COLORS['primary']};
        color: white;
    }}
    QTableWidget::item:hover {{
        background-color: {COLORS['bg_border']};
    }}
    QHeaderView::section {{
        background-color: {COLORS['bg_deeper']};
        color: {COLORS['muted']};
        padding: 6px 8px;
        border: none;
        border-right: 1px solid {COLORS['bg_border']};
        border-bottom: 2px solid {COLORS['primary']};
        font-weight: bold;
        font-size: 10px;
        font-family: "{FONT}";
    }}
    QScrollBar:vertical {{
        background: {COLORS['bg_dark']}; width: 8px;
    }}
    QScrollBar::handle:vertical {{
        background: {COLORS['bg_border']}; border-radius: 4px; min-height: 20px;
    }}
    QScrollBar::handle:vertical:hover {{ background: {COLORS['primary']}; }}
"""

# ══════════════════════════════════════════════════════════════════════
# Estilos de botones reutilizables
# ══════════════════════════════════════════════════════════════════════
BTN_PRIMARY = f"background-color:{COLORS['primary']};color:white;font-weight:bold;padding:6px 14px;border-radius:4px;"
BTN_ACCENT  = f"background-color:{COLORS['accent']};color:white;font-weight:bold;padding:6px 14px;border-radius:4px;"
BTN_DANGER  = f"background-color:{COLORS['danger']};color:white;font-weight:bold;padding:6px 14px;border-radius:4px;"
BTN_WARNING = f"background-color:{COLORS['warning']};color:white;font-weight:bold;padding:6px 14px;border-radius:4px;"
BTN_MUTED   = f"background-color:{COLORS['bg_border']};color:{COLORS['text_dim']};font-weight:bold;padding:6px 14px;border-radius:4px;"

# ══════════════════════════════════════════════════════════════════════
# Límites de inclusión por insumo (% máximo recomendado en la ración)
# ══════════════════════════════════════════════════════════════════════
LIMITES_INCLUSION = {
    'melaza':                15.0,
    'harina de pescado':      8.0,
    'gallinaza aves':        10.0,
    'aceite vegetal':        10.0,
    'aceite de palma':       10.0,
    'aceite de soya':        10.0,
    'bagazo de caña azúcar': 20.0,
    'harina de sangre':       5.0,
    'harina de plumas':       5.0,
    'glicerina cruda':        5.0,
    'sal común (nacl)':       0.5,
    'bicarbonato de sodio':   0.5,
    'dl-metionina':           0.5,
    'lisina sintética l-lys': 1.0,
}

# Rango saludable Ca:P
CA_P_MIN = 1.2
CA_P_MAX = 2.0

# ══════════════════════════════════════════════════════════════════════
# Configuración de usuario (archivos recientes, etc.)
# ══════════════════════════════════════════════════════════════════════
CONFIG_FILE = str(get_data_dir() / 'config.json')


def cargar_config():
    if not os.path.exists(CONFIG_FILE):
        return {"archivos_recientes": []}
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {"archivos_recientes": []}


def guardar_config(config):
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
