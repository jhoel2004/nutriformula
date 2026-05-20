# ui/panel_alertas.py — Panel lateral de alertas VITAL v2.0
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QScrollArea, QFrame, QSizePolicy)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor

from app.database import obtener_alertas_no_leidas, marcar_alerta_leida, get_connection
from app.config import COLORS, BTN_MUTED
import sqlite3

class AlertaItem(QFrame):
    def __init__(self, alerta_id, tipo, mensaje, fecha, parent=None):
        super().__init__(parent)
        self.alerta_id = alerta_id
        self.setStyleSheet(f"background:{COLORS['bg_surface']}; border-radius:6px; border:1px solid {COLORS['bg_border']}; margin-bottom:5px;")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        
        # Color según tipo
        color = COLORS['text']
        icono = "ℹ️"
        if tipo == 'stock': 
            color = COLORS['danger']
            icono = "🔴"
        elif tipo == 'precio':
            color = COLORS['warning']
            icono = "🟡"
        elif tipo == 'nutricion':
            color = COLORS['danger']
            icono = "🔴"
            
        header = QHBoxLayout()
        lbl_tipo = QLabel(f"{icono} {tipo.upper()}")
        lbl_tipo.setStyleSheet(f"color:{color}; font-weight:bold; font-size:10px; border:none;")
        
        lbl_fecha = QLabel(fecha[:16])
        lbl_fecha.setStyleSheet(f"color:{COLORS['text_dim']}; font-size:9px; border:none;")
        
        header.addWidget(lbl_tipo)
        header.addStretch()
        header.addWidget(lbl_fecha)
        layout.addLayout(header)
        
        lbl_msg = QLabel(mensaje)
        lbl_msg.setWordWrap(True)
        lbl_msg.setStyleSheet(f"color:{COLORS['text']}; font-size:11px; border:none;")
        layout.addWidget(lbl_msg)

class PanelAlertas(QWidget):
    # Señal para notificar a la ventana principal de la cantidad de alertas no leídas
    alertas_cambiadas = pyqtSignal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(280)
        self.setStyleSheet(f"background:{COLORS['bg_deeper']}; border-left:1px solid {COLORS['bg_border']};")
        self.setup_ui()
        self.load_alertas()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 15, 10, 10)
        
        # Header
        header = QHBoxLayout()
        titulo = QLabel("🔔 Centro de Alertas")
        titulo.setStyleSheet(f"font-size:14px; font-weight:bold; color:{COLORS['text']}; border:none;")
        
        btn_cerrar = QPushButton("❌")
        btn_cerrar.setFixedSize(24, 24)
        btn_cerrar.setStyleSheet("background:transparent; border:none;")
        btn_cerrar.clicked.connect(self.hide)
        
        header.addWidget(titulo)
        header.addStretch()
        header.addWidget(btn_cerrar)
        layout.addLayout(header)
        
        # Actions
        btn_marcar_todas = QPushButton("Marcar todas como leídas")
        btn_marcar_todas.setStyleSheet(BTN_MUTED)
        btn_marcar_todas.clicked.connect(self.marcar_todas_leidas)
        layout.addWidget(btn_marcar_todas)
        
        # Scroll Area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setStyleSheet("background:transparent; border:none;")
        
        self.container = QWidget()
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.container_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll.setWidget(self.container)
        
        layout.addWidget(self.scroll)

    def load_alertas(self):
        # Limpiar existentes
        for i in reversed(range(self.container_layout.count())): 
            widget = self.container_layout.itemAt(i).widget()
            if widget is not None: 
                widget.setParent(None)
                
        alertas = obtener_alertas_no_leidas()
        self.alertas_cambiadas.emit(len(alertas))
        
        if not alertas:
            lbl = QLabel("No hay alertas nuevas.")
            lbl.setStyleSheet(f"color:{COLORS['text_dim']}; font-style:italic; border:none;")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.container_layout.addWidget(lbl)
            return
            
        for a in alertas:
            item = AlertaItem(a['id'], a['tipo'], a['mensaje'], a['fecha'])
            self.container_layout.addWidget(item)

    def marcar_todas_leidas(self):
        alertas = obtener_alertas_no_leidas()
        for a in alertas:
            marcar_alerta_leida(a['id'])
        self.load_alertas()
