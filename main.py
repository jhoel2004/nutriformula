# -*- coding: utf-8 -*-
import sys
import locale

# Auto-activar venv si se ejecuta sin él
import os
venv_python = os.path.join(os.path.dirname(__file__), 'venv', 'bin', 'python')
if os.path.exists(venv_python) and sys.executable != venv_python:
    import subprocess
    result = subprocess.run([venv_python] + sys.argv)
    sys.exit(result.returncode)

try:
    import qdarkstyle
    HAS_QDARKSTYLE = True
except ImportError:
    HAS_QDARKSTYLE = False

try:
    import darkdetect
except ImportError:
    darkdetect = None

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from app.database import init_db
from app.main_window import MainWindow

# Estilo oscuro de respaldo (si no hay qdarkstyle)
FALLBACK_DARK = """
    QWidget { background-color: #1E1E2E; color: #CDD6F4; font-family: 'Segoe UI', Arial; }
    QMainWindow, QDialog { background-color: #1E1E2E; }
    QTabWidget::pane { border: 1px solid #313244; }
    QHeaderView::section { background-color: #313244; color: #CDD6F4; }
    QTableWidget { gridline-color: #313244; alternate-background-color: #252535; }
    QPushButton { background-color: #313244; color: #CDD6F4; border-radius: 4px; padding: 4px 10px; }
    QPushButton:hover { background-color: #45475A; }
    QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QTextEdit {
        background-color: #313244; color: #CDD6F4;
        border: 1px solid #45475A; border-radius: 3px; padding: 2px 4px;
    }
    QLabel { color: #CDD6F4; }
    QScrollBar:vertical { background: #313244; width: 10px; }
    QScrollBar::handle:vertical { background: #585B70; border-radius: 5px; min-height: 20px; }
    QSplitter::handle { background: #313244; }
    QStatusBar { background: #181825; color: #CDD6F4; }
    QMenuBar { background: #181825; color: #CDD6F4; }
    QMenuBar::item:selected { background: #313244; }
    QMenu { background: #1E1E2E; color: #CDD6F4; border: 1px solid #45475A; }
    QMenu::item:selected { background: #313244; }
"""

def main():
    # Forzar UTF-8
    locale.setlocale(locale.LC_ALL, '')

    # 1. Inicializar base de datos
    init_db()

    # 2. Iniciar aplicación
    app = QApplication(sys.argv)
    app.setApplicationName("VITAL")

    # Aplicar tema oscuro
    if HAS_QDARKSTYLE:
        app.setStyleSheet(qdarkstyle.load_stylesheet(qt_api='pyqt6'))
    else:
        app.setStyleSheet(FALLBACK_DARK)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())

if __name__ == '__main__':
    main()

