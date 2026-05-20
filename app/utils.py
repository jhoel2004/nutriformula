# app/utils.py — Utilidades multiplataforma para VITAL v2.0
import sys
import os
from pathlib import Path


def get_base_path() -> Path:
    """Ruta base: funciona en desarrollo Y en PyInstaller (.exe / binario Linux)."""
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS)
    return Path(__file__).parent.parent


def get_data_dir() -> Path:
    """
    Directorio de datos persistentes del usuario.
    Windows: C:/Users/<user>/AppData/Local/VITAL/
    Linux:   /home/<user>/.local/share/VITAL/
    """
    if sys.platform == 'win32':
        base = Path(os.environ.get('LOCALAPPDATA', str(Path.home())))
    else:
        base = Path.home() / '.local' / 'share'
    d = base / 'VITAL'
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_db_path() -> Path:
    return get_data_dir() / 'vital.db'


def get_exports_dir() -> Path:
    d = get_data_dir() / 'Exportaciones'
    d.mkdir(exist_ok=True)
    return d


def get_logo_path() -> Path:
    return get_base_path() / 'logo.png'


def resource_path(relative_path):
    """
    Compatibilidad con código anterior — redirige a get_base_path().
    """
    return str(get_base_path() / relative_path)


def force_utf8():
    """Acentos correctos en Windows — llamar al inicio de main.py."""
    if sys.platform == 'win32':
        try:
            import ctypes
            ctypes.windll.kernel32.SetConsoleOutputCP(65001)
        except Exception:
            pass
        os.environ['PYTHONIOENCODING'] = 'utf-8'


def get_system_font() -> str:
    return 'Segoe UI' if sys.platform == 'win32' else 'Ubuntu'
