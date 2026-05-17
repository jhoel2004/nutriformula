# ui/tab_calcular.py
"""
Tab "Calcular" — unifica Formulación Manual y Formulación Inversa (Autoformular)
en un único tab con un switcher en la barra superior.
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget,
                              QLabel, QPushButton, QFrame, QInputDialog, QMessageBox)
from PyQt6.QtCore import Qt, pyqtSignal

from ui.tab_formulacion import TabFormulacion
from ui.tab_formulacion_inversa import TabFormulacionInversa
from app.database import GestorFormulacionesBD


ESTILO_BTN_MODO = """
    QPushButton {
        background: #1E1E2E;
        color: #6060A0;
        border: 1px solid #3A3A5A;
        border-radius: 6px;
        padding: 6px 20px;
        font-size: 12px;
        font-weight: bold;
    }
    QPushButton:hover {
        background: #2A2A4A;
        color: #A0A0D0;
    }
    QPushButton[activo="true"] {
        background: #2D7D46;
        color: white;
        border: 1px solid #3CB85C;
    }
"""


class TabCalcular(QWidget):
    """
    Tab unificado que contiene:
     - Modo 0 (✍️ Formular):      TabFormulacion
     - Modo 1 (⚡ Autoformular): TabFormulacionInversa
    """
    formulacion_guardada = pyqtSignal()
    enviar_formulacion   = pyqtSignal(list, float, str)

    def __init__(self):
        super().__init__()
        self.gestor_bd = GestorFormulacionesBD()
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Barra superior ───────────────────────────────────────────
        barra = QWidget()
        barra.setStyleSheet("background: #161625; border-bottom: 1px solid #2A2A4A;")
        barra.setFixedHeight(48)
        barra_lay = QHBoxLayout(barra)
        barra_lay.setContentsMargins(16, 4, 16, 4)
        barra_lay.setSpacing(8)

        lbl = QLabel("🧮  CALCULAR RACIÓN")
        lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #5CB85C;")
        barra_lay.addWidget(lbl)
        barra_lay.addStretch()

        lbl_modo = QLabel("Modo:")
        lbl_modo.setStyleSheet("color: #8080A0; font-size: 12px;")
        barra_lay.addWidget(lbl_modo)

        self.btn_formular      = QPushButton("✍️  Formular")
        self.btn_autoformular  = QPushButton("⚡  Autoformular")
        for btn in (self.btn_formular, self.btn_autoformular):
            btn.setStyleSheet(ESTILO_BTN_MODO)
            btn.setFixedHeight(32)

        self.btn_formular.setProperty("activo", "true")
        self.btn_formular.style().unpolish(self.btn_formular)
        self.btn_formular.style().polish(self.btn_formular)

        self.btn_formular.clicked.connect(lambda: self._cambiar_modo(0))
        self.btn_autoformular.clicked.connect(lambda: self._cambiar_modo(1))

        barra_lay.addWidget(self.btn_formular)
        barra_lay.addWidget(self.btn_autoformular)

        # Botón guardar en BD
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet("color: #2A2A4A;")
        sep.setFixedWidth(1)
        barra_lay.addWidget(sep)

        self.btn_nueva_form = QPushButton("✨ Nueva Formulación")
        self.btn_nueva_form.setStyleSheet(
            "background: #1A3A5C; color: #5BC0DE; border: 1px solid #2A5A8C;"
            "border-radius: 5px; padding: 5px 14px; font-weight: bold; font-size: 12px;"
        )
        self.btn_nueva_form.setFixedHeight(32)
        self.btn_nueva_form.clicked.connect(self._nueva_formulacion)
        barra_lay.addWidget(self.btn_nueva_form)

        root.addWidget(barra)

        # ── Stack de páginas ─────────────────────────────────────────
        self.stack = QStackedWidget()

        self.pagina_formular     = TabFormulacion()
        self.pagina_autoformular = TabFormulacionInversa()

        self.stack.addWidget(self.pagina_formular)      # índice 0
        self.stack.addWidget(self.pagina_autoformular)  # índice 1

        root.addWidget(self.stack)

        # Re-emitir señales internas
        self.pagina_formular.formulacion_guardada.connect(self.formulacion_guardada)
        self.pagina_autoformular.formulacion_guardada.connect(self.formulacion_guardada)
        self.pagina_autoformular.enviar_formulacion.connect(self.enviar_formulacion)

    # ────────────────────────────────────────────────────────────────
    # Cambiar modo
    # ────────────────────────────────────────────────────────────────
    def _cambiar_modo(self, idx):
        self.stack.setCurrentIndex(idx)
        activo_form  = "true"  if idx == 0 else "false"
        activo_auto  = "false" if idx == 0 else "true"

        self.btn_formular.setProperty("activo", activo_form)
        self.btn_autoformular.setProperty("activo", activo_auto)

        for btn in (self.btn_formular, self.btn_autoformular):
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    # ────────────────────────────────────────────────────────────────
    # Guardar formulación activa en BD
    # ────────────────────────────────────────────────────────────────
    def _nueva_formulacion(self):
        """Limpia la página de formulación actual."""
        if self.stack.currentIndex() == 0:
            self.pagina_formular.nueva_formulacion()
        else:
            QMessageBox.information(self, "Info", "El modo autoformular ya se limpia al generar nuevos resultados.")

    # ────────────────────────────────────────────────────────────────
    # API pública — cargar desde tab Formulaciones
    # ────────────────────────────────────────────────────────────────
    def cargar_formulacion_desde_bd(self, formulacion):
        """Carga una formulación guardada en el modo correspondiente."""
        if formulacion.get('tipo', 'manual') == 'manual':
            self._cambiar_modo(0)
            self.pagina_formular.cargar_desde_bd(formulacion)
        else:
            self._cambiar_modo(1)

    def load_insumos(self):
        self.pagina_formular.load_insumos()
        self.pagina_autoformular.load_insumos()
