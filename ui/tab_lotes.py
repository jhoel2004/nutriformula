# ui/tab_lotes.py — Módulo de Trazabilidad de Producción VITAL v2.0
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QTableWidget, QTableWidgetItem, QLabel,
                             QHeaderView, QAbstractItemView, QComboBox,
                             QDialog, QFormLayout, QDoubleSpinBox,
                             QDialogButtonBox, QLineEdit, QTextEdit,
                             QMessageBox, QDateEdit, QGroupBox, QSplitter)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QColor

from app.database import (GestorFormulacionesBD, listar_lotes, insertar_lote,
                          actualizar_estado_lote, get_all_insumos, actualizar_stock,
                          get_connection, get_config_empresa)
from app.config import ESTILO_TABLA, COLORS, BTN_PRIMARY, BTN_ACCENT, BTN_WARNING, BTN_MUTED
import sqlite3

class DialogoNuevoLote(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nuevo Lote de Producción")
        self.setMinimumWidth(400)
        self.gestor = GestorFormulacionesBD()
        self.formulaciones = self.gestor.listar_formulaciones()
        
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.txt_nombre = QLineEdit()
        self.txt_nombre.setPlaceholderText("Ej: Lote 001 Ponedoras Mayo")
        
        self.combo_form = QComboBox()
        for f in self.formulaciones:
            self.combo_form.addItem(f"{f['nombre']} ({f.get('animal_nombre', '')})", f['id'])
        
        self.spin_kg = QDoubleSpinBox()
        self.spin_kg.setRange(1, 99999)
        self.spin_kg.setSuffix(" kg")
        self.spin_kg.setValue(100)
        
        self.date_fecha = QDateEdit()
        self.date_fecha.setCalendarPopup(True)
        self.date_fecha.setDate(QDate.currentDate())
        
        self.txt_notas = QTextEdit()
        self.txt_notas.setMaximumHeight(80)

        form.addRow("Nombre del Lote:", self.txt_nombre)
        form.addRow("Formulación Base:", self.combo_form)
        form.addRow("Cantidad a Producir:", self.spin_kg)
        form.addRow("Fecha:", self.date_fecha)
        form.addRow("Notas:", self.txt_notas)
        layout.addLayout(form)
        
        self.lbl_info = QLabel("Al guardar, se verificará el stock y se descontará automáticamente.")
        self.lbl_info.setStyleSheet(f"color:{COLORS['text_dim']}; font-style:italic;")
        layout.addWidget(self.lbl_info)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.verificar_y_aceptar)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)
        
    def verificar_y_aceptar(self):
        nombre = self.txt_nombre.text().strip()
        if not nombre:
            QMessageBox.warning(self, "Error", "El nombre del lote es obligatorio.")
            return
        
        form_id = self.combo_form.currentData()
        if not form_id:
            QMessageBox.warning(self, "Error", "Seleccione una formulación.")
            return
            
        kg_totales = self.spin_kg.value()
        form_completa = self.gestor.cargar_formulacion(form_id)
        if not form_completa or form_completa.get('total_kg', 0) == 0:
            QMessageBox.warning(self, "Error", "Formulación inválida.")
            return
            
        # Calcular proporción
        factor = kg_totales / form_completa['total_kg']
        
        insumos = get_all_insumos()
        insumos_dict = {i['id']: i for i in insumos}
        
        faltantes = []
        descuentos = [] # (insumo_id, descontar_kg, nuevo_costo_total_para_lote)
        costo_total_lote = 0
        
        for ing in form_completa['ingredientes']:
            i_id = ing['insumo_id']
            kg_necesarios = ing['tanteo_kg'] * factor
            ins_db = insumos_dict.get(i_id, {})
            stock_actual = ins_db.get('stock_kg', 0)
            precio = ins_db.get('precio_kg', 0)
            
            if stock_actual < kg_necesarios:
                faltantes.append(f"{ing['nombre_insumo']}: Faltan {kg_necesarios - stock_actual:.1f} kg")
            else:
                descuentos.append((i_id, kg_necesarios))
                costo_total_lote += kg_necesarios * precio
                
        if faltantes:
            msg = "No hay stock suficiente para producir este lote:\n\n" + "\n".join(faltantes)
            QMessageBox.critical(self, "Stock Insuficiente", msg)
            return
            
        # Si llega aquí, hay stock.
        # Confirmar
        resp = QMessageBox.question(self, "Confirmar Lote", 
            f"¿Crear lote y descontar {kg_totales} kg de inventario?\nCosto estimado: {costo_total_lote:.2f}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            
        if resp == QMessageBox.StandardButton.Yes:
            self.resultado = {
                'formulacion_id': form_id,
                'nombre': nombre,
                'fecha': self.date_fecha.date().toString(Qt.DateFormat.ISODate),
                'cantidad_kg': kg_totales,
                'costo_total': costo_total_lote,
                'notas': self.txt_notas.toPlainText(),
                'descuentos': descuentos,
                'form_completa': form_completa,
                'factor': factor
            }
            self.accept()

class TabLotes(QWidget):
    def __init__(self, db=None):
        super().__init__()
        self.moneda = get_config_empresa('moneda', '$')
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 10)

        titulo = QLabel("🏭 Trazabilidad de Lotes de Producción")
        titulo.setStyleSheet(f"font-size:18px;font-weight:bold;color:{COLORS['text']};padding:5px 0;")
        layout.addWidget(titulo)

        # ── Controles ──────────────────────────────
        top = QHBoxLayout()
        self.btn_nuevo = QPushButton("➕ Nuevo Lote")
        self.btn_nuevo.setStyleSheet(BTN_PRIMARY)
        self.btn_nuevo.clicked.connect(self.nuevo_lote)

        self.combo_estado = QComboBox()
        self.combo_estado.addItems(["Todos", "producido", "en_uso", "agotado"])
        self.combo_estado.currentTextChanged.connect(self.load_data)

        self.btn_actualizar = QPushButton("🔄 Actualizar")
        self.btn_actualizar.clicked.connect(self.load_data)

        top.addWidget(self.btn_nuevo)
        top.addStretch()
        top.addWidget(QLabel("Filtrar Estado:"))
        top.addWidget(self.combo_estado)
        top.addWidget(self.btn_actualizar)
        layout.addLayout(top)

        # ── Splitter: Tabla y Detalles ──────────────────────────────
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Tabla principal
        self.table = QTableWidget()
        headers = ["Nombre Lote", "Formulación", "Animal", "Fecha", "Kg Prod.", "Costo", "Estado"]
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setStyleSheet(ESTILO_TABLA)
        self.table.itemSelectionChanged.connect(self.mostrar_detalle)
        splitter.addWidget(self.table)

        # Panel de Detalle
        detalle_widget = QWidget()
        det_layout = QVBoxLayout(detalle_widget)
        self.lbl_det_titulo = QLabel("Detalle de Lote")
        self.lbl_det_titulo.setStyleSheet("font-weight:bold; font-size:14px;")
        det_layout.addWidget(self.lbl_det_titulo)
        
        self.txt_detalle = QTextEdit()
        self.txt_detalle.setReadOnly(True)
        self.txt_detalle.setStyleSheet(f"background:{COLORS['bg_surface']}; color:{COLORS['text']}; border:1px solid {COLORS['bg_border']};")
        det_layout.addWidget(self.txt_detalle)

        # Controles de Estado
        btn_est_layout = QHBoxLayout()
        self.btn_uso = QPushButton("Marcar En Uso")
        self.btn_uso.setStyleSheet(BTN_ACCENT)
        self.btn_uso.clicked.connect(lambda: self.cambiar_estado("en_uso"))
        
        self.btn_agotado = QPushButton("Marcar Agotado")
        self.btn_agotado.setStyleSheet(BTN_WARNING)
        self.btn_agotado.clicked.connect(lambda: self.cambiar_estado("agotado"))

        self.btn_exportar = QPushButton("Exportar Etiqueta")
        self.btn_exportar.setStyleSheet(BTN_MUTED)
        self.btn_exportar.clicked.connect(self.exportar_etiqueta)

        btn_est_layout.addWidget(self.btn_uso)
        btn_est_layout.addWidget(self.btn_agotado)
        det_layout.addLayout(btn_est_layout)
        det_layout.addWidget(self.btn_exportar)
        
        splitter.addWidget(detalle_widget)
        splitter.setSizes([600, 300])
        
        layout.addWidget(splitter)
        self.lotes_data = []

    def load_data(self):
        est = self.combo_estado.currentText()
        if est == "Todos": est = None
        self.lotes_data = listar_lotes(estado=est)
        
        self.table.setRowCount(0)
        for lote in self.lotes_data:
            row = self.table.rowCount()
            self.table.insertRow(row)
            items = [
                lote['nombre'],
                lote.get('formulacion_nombre', ''),
                lote.get('animal_nombre', ''),
                lote['fecha'][:10],
                f"{lote.get('cantidad_kg', 0):.1f}",
                f"{self.moneda}{lote.get('costo_total', 0):.2f}",
                lote.get('estado', '')
            ]
            for col, val in enumerate(items):
                item = QTableWidgetItem(str(val))
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if col == 0:
                    item.setData(Qt.ItemDataRole.UserRole, lote['id'])
                if col == 6:
                    if val == "producido": item.setForeground(QColor(COLORS['primary_light']))
                    elif val == "en_uso": item.setForeground(QColor(COLORS['accent']))
                    elif val == "agotado": item.setForeground(QColor(COLORS['text_dim']))
                self.table.setItem(row, col, item)

    def nuevo_lote(self):
        dlg = DialogoNuevoLote(self)
        if dlg.exec():
            datos = dlg.resultado
            descuentos = datos.pop('descuentos')
            form_completa = datos.pop('form_completa')
            factor = datos.pop('factor')
            
            lote_id = insertar_lote(datos)
            if lote_id:
                # Descontar stock
                try:
                    conn = get_connection()
                    cursor = conn.cursor()
                    for i_id, desc_kg in descuentos:
                        cursor.execute('UPDATE insumos SET stock_kg = stock_kg - ? WHERE id = ?', (desc_kg, i_id))
                    conn.commit()
                    conn.close()
                    QMessageBox.information(self, "Lote Creado", "Se ha registrado el lote y descontado el inventario.")
                    self.load_data()
                except Exception as e:
                    QMessageBox.warning(self, "Error de Stock", f"No se pudo descontar el stock: {e}")

    def get_selected_lote(self):
        row = self.table.currentRow()
        if row < 0: return None
        lote_id = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        return next((l for l in self.lotes_data if l['id'] == lote_id), None)

    def mostrar_detalle(self):
        lote = self.get_selected_lote()
        if not lote: return
        
        self.lbl_det_titulo.setText(f"Lote: {lote['nombre']}")
        
        texto = f"Formulación: {lote.get('formulacion_nombre','')}\n"
        texto += f"Animal: {lote.get('animal_nombre','')}\n"
        texto += f"Fecha: {lote['fecha'][:10]}\n"
        texto += f"Cantidad: {lote.get('cantidad_kg',0):.1f} kg\n"
        texto += f"Costo Total: {self.moneda}{lote.get('costo_total',0):.2f}\n"
        texto += f"Estado: {lote.get('estado','')}\n"
        if lote.get('notas'):
            texto += f"Notas: {lote['notas']}\n"
            
        texto += "\n-- Ingredientes requeridos --\n"
        # Obtener detalle de ingredientes. 
        # (Idealmente guardar el detalle exacto del lote, aquí lo recalculamos base la formulación para mostrar)
        gestor = GestorFormulacionesBD()
        form_id = lote.get('formulacion_id')
        if form_id:
            form = gestor.cargar_formulacion(form_id)
            if form and form.get('total_kg', 0) > 0:
                factor = lote.get('cantidad_kg', 0) / form['total_kg']
                for ing in form['ingredientes']:
                    kg = ing['tanteo_kg'] * factor
                    texto += f"• {ing['nombre_insumo']}: {kg:.2f} kg\n"
                    
        self.txt_detalle.setPlainText(texto)

    def cambiar_estado(self, nuevo_estado):
        lote = self.get_selected_lote()
        if not lote: return
        
        if actualizar_estado_lote(lote['id'], nuevo_estado):
            self.load_data()

    def exportar_etiqueta(self):
        lote = self.get_selected_lote()
        if not lote: return
        
        from PyQt6.QtWidgets import QFileDialog
        from app.exporter import Exporter
        
        ruta, _ = QFileDialog.getSaveFileName(
            self, "Exportar Etiqueta de Lote", f"Etiqueta_{lote['nombre']}.pdf",
            "Archivos PDF (*.pdf)"
        )
        if not ruta: return
        
        gestor = GestorFormulacionesBD()
        form = gestor.cargar_formulacion(lote.get('formulacion_id'))
        
        datos = {
            'lote_nombre': lote['nombre'],
            'fecha': lote['fecha'][:10],
            'animal': lote.get('animal_nombre',''),
            'cantidad': lote.get('cantidad_kg',0),
            'form_nombre': lote.get('formulacion_nombre',''),
            'instrucciones': form.get('instrucciones_preparacion','') if form else ''
        }
        
        try:
            Exporter.exportar_etiqueta_lote(ruta, datos)
            QMessageBox.information(self, "Etiqueta Exportada", f"Guardada en:\n{ruta}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Fallo al exportar etiqueta: {e}")
