# ui/tab_formulacion.py
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
                             QTableWidgetItem, QHeaderView, QComboBox,
                             QLabel, QLineEdit, QSplitter, QProgressBar,
                             QRadioButton, QButtonGroup, QGroupBox, QTextEdit,
                             QPushButton, QMessageBox, QDoubleSpinBox)
import json
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QBrush, QFont
from app.calculator import calcular_resultados, evaluar_cumplimiento, auditar_insumo, calcular_ratio_ca_p, verificar_limites_inclusion
from app.database import (get_all_insumos, get_all_animales, GestorFormulacionesBD)

import numpy as np
import matplotlib
matplotlib.use('QtAgg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# Columnas de resultados
COLS_RES = ["Insumo", "% en Ración", "Proteína%", "EM Kcal", "Fibra%", "Grasa%",
            "Calcio%", "Fósforo%", "Lisina%", "Metionina%", "Colina mg/kg"]

# Nutrientes en orden sincronizado con COLS_RES (desde índice 2)
NUTRIENTES_COLS = ['proteina', 'em_kcal', 'fibra', 'grasa', 'calcio', 'fosforo',
                   'lisina', 'metionina', 'colina_mgr']

# Colores para semáforo
COLOR_VERDE    = QColor("#2ECC71")
COLOR_AMARILLO = QColor("#F39C12")
COLOR_ROJO     = QColor("#E74C3C")
COLOR_TOTAL_BG = QColor("#1B4F2E")

class TabFormulacion(QWidget):
    """
    Pestaña principal de formulación.
    Permite cargar ingredientes, asignarles cantidades y ver los resultados
    nutricionales calculados en tiempo real.
    """
    
    formulacion_guardada = pyqtSignal()  # emitida tras guardar para refrescar tab animales

    def __init__(self):
        super().__init__()
        self.insumos_db = []
        self._block_signals = False   # evita recursión al actualizar celdas
        self._formula_comparar = None # dict con datos de la fórmula a comparar
        self._animal_nombre = ""      # nombre del animal seleccionado
        self.gestor_bd = GestorFormulacionesBD()
        self.setup_ui()

    # ---------------------------------------------------------------
    # UI
    # ---------------------------------------------------------------
    def setup_ui(self):
        layout = QVBoxLayout(self)

        # ── Panel superior: Detalles de la Formulación ───────────────────
        top = QHBoxLayout()

        lbl_nombre = QLabel("Nombre de la Formulación:")
        lbl_nombre.setStyleSheet("font-weight: bold; font-size: 13px;")
        self.input_nombre = QLineEdit()
        self.input_nombre.setMinimumWidth(250)
        self.input_nombre.setPlaceholderText("Ej. Ración Crecimiento Lote A")

        lbl_animal = QLabel("Animal:")
        lbl_animal.setStyleSheet("font-weight: bold; font-size: 13px;")
        self.combo_animal = QComboBox()
        self.combo_animal.setMinimumWidth(150)
        self.combo_animal.currentIndexChanged.connect(self._on_animal_changed)

        top.addWidget(lbl_nombre)
        top.addWidget(self.input_nombre)
        top.addSpacing(20)
        top.addWidget(lbl_animal)
        top.addWidget(self.combo_animal)
        top.addSpacing(20)
        
        self.btn_guardar = QPushButton("💾 Guardar Formulación")
        self.btn_guardar.setStyleSheet("""
            QPushButton {
                background-color: #27AE60;
                color: white;
                font-weight: bold;
                padding: 6px 15px;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #2ECC71; }
        """)
        self.btn_guardar.clicked.connect(self.guardar_formulacion_actual)
        top.addWidget(self.btn_guardar)
        
        top.addStretch()
        layout.addLayout(top)

        # ── Splitter izquierda / derecha ─────────────────────────────
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # ============================================================
        # PANEL IZQUIERDO — Selección y tanteo
        # ============================================================
        panel_izq = QWidget()
        lay_izq = QVBoxLayout(panel_izq)



        # Barra de búsqueda
        tools = QHBoxLayout()
        self.search_formulacion = QLineEdit()
        self.search_formulacion.setPlaceholderText("🔍 Buscar insumo en la lista...")
        self.search_formulacion.textChanged.connect(self.filter_insumos)
        tools.addWidget(self.search_formulacion)
        lay_izq.addLayout(tools)

        # Tabla de tanteo
        self.table_tanteo = QTableWidget()
        self.table_tanteo.setColumnCount(3)
        self.table_tanteo.setHorizontalHeaderLabels(["Insumo", "Tanteo (kg/%)", "Costo ($)"])
        self.table_tanteo.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_tanteo.setColumnWidth(1, 90)
        self.table_tanteo.setColumnWidth(2, 75)
        self.table_tanteo.setAlternatingRowColors(False)
        # Detectar cambios de valor de tanteo
        # Nota: Ahora usamos cellWidgets (SpinBoxes), por lo que itemChanged no detectará cambios en la columna 1
        self.table_tanteo.itemChanged.connect(self._on_item_changed)
        lay_izq.addWidget(self.table_tanteo)

        # Barra de progreso
        lbl_prog = QLabel("Porcentaje de la ración usado:")
        lay_izq.addWidget(lbl_prog)
        self.progress_total = QProgressBar()
        self.progress_total.setRange(0, 100)
        self.progress_total.setValue(0)
        lay_izq.addWidget(self.progress_total)

        # Resumen kg / %
        resumen = QHBoxLayout()
        self.lbl_total_kg  = QLabel("Total: 0.00 kg")
        self.lbl_total_pct = QLabel("(0.00 %)")
        self.lbl_total_kg.setStyleSheet("font-weight: bold;")
        resumen.addWidget(self.lbl_total_kg)
        resumen.addWidget(self.lbl_total_pct)
        resumen.addStretch()
        lay_izq.addLayout(resumen)

        splitter.addWidget(panel_izq)

        # ============================================================
        # PANEL DERECHO — Resultados en tiempo real
        # ============================================================
        panel_der = QWidget()
        lay_der = QVBoxLayout(panel_der)

        lbl_res = QLabel("Composición Nutricional de la Ración (en tiempo real)")
        lbl_res.setStyleSheet("font-weight: bold; font-size: 13px; color: #5CB85C;")
        lay_der.addWidget(lbl_res)

        self.table_resultados = QTableWidget()
        self.table_resultados.setColumnCount(len(COLS_RES))
        self.table_resultados.setHorizontalHeaderLabels(COLS_RES)
        self.table_resultados.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_resultados.setAlternatingRowColors(False)
        lay_der.addWidget(self.table_resultados)

        # Fila de totales destacada
        self.table_totales = QTableWidget()
        self.table_totales.setRowCount(1)
        self.table_totales.setColumnCount(len(COLS_RES))
        self.table_totales.setHorizontalHeaderLabels(COLS_RES)
        self.table_totales.setVerticalHeaderLabels(["TOTALES ▼"])
        self.table_totales.setMaximumHeight(55)
        self.table_totales.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        lay_der.addWidget(self.table_totales)

        self.lbl_costo = QLabel("Costo por kg: $0.00  |  Costo por tonelada: $0.00")
        self.lbl_costo.setStyleSheet(
            "font-weight: bold; font-size: 14px; color: #2C3E50; "
            "padding: 5px; background: #ECF0F1; border-radius: 4px;"
        )
        lay_der.addWidget(self.lbl_costo)

        # Fila de validación de salud preventiva
        self.lbl_salud = QLabel("Validación de Salud: Esperando cálculo...")
        self.lbl_salud.setStyleSheet("font-weight: bold; font-size: 13px; color: #7F8C8D; padding: 5px;")
        self.lbl_salud.setWordWrap(True)
        lay_der.addWidget(self.lbl_salud)

        # Gráfico de radar colapsable
        self.group_radar = QGroupBox("Gráfico Radar Comparativo (Target vs Calculado)")
        self.group_radar.setCheckable(True)
        self.group_radar.setChecked(False) # Colapsado por defecto según sugerencia
        lay_radar = QVBoxLayout(self.group_radar)

        # Controles internos del radar (Selección de comparativa)
        controles_radar = QHBoxLayout()
        
        lbl_comp = QLabel("Comparar con:")
        lbl_comp.setStyleSheet("font-weight: bold; font-size: 12px;")
        controles_radar.addWidget(lbl_comp)
        
        self.combo_comparar = QComboBox()
        self.combo_comparar.setMinimumWidth(180)
        self.combo_comparar.currentIndexChanged.connect(self._on_comparativa_changed)
        controles_radar.addWidget(self.combo_comparar)
        
        controles_radar.addSpacing(15)
        
        self.lbl_reqs = QLabel("")
        self.lbl_reqs.setStyleSheet("color:#5CB85C; font-size: 11px;")
        controles_radar.addWidget(self.lbl_reqs)
        
        self.btn_exportar_radar = QPushButton("📷 Exportar radar")
        self.btn_exportar_radar.setStyleSheet("padding: 4px 10px;")
        self.btn_exportar_radar.clicked.connect(self._exportar_radar)
        controles_radar.addWidget(self.btn_exportar_radar)
        
        controles_radar.addStretch()
        lay_radar.addLayout(controles_radar)
        
        self.figura_radar = Figure(figsize=(5, 4), dpi=100)
        self.canvas_radar = FigureCanvas(self.figura_radar)
        lay_radar.addWidget(self.canvas_radar)
        
        self.tabla_dif = QTableWidget()
        self.tabla_dif.setMaximumHeight(150)
        self.tabla_dif.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tabla_dif.setAlternatingRowColors(True)
        lay_radar.addWidget(self.tabla_dif)
        
        lay_der.addWidget(self.group_radar)
        self._conectar_tooltip_radar()


        # Instrucciones de preparación
        self.text_instrucciones = QTextEdit()
        self.text_instrucciones.setPlaceholderText("Instrucciones de preparación, observaciones o notas para la mezcla...")
        self.text_instrucciones.setMaximumHeight(80)
        lay_der.addWidget(self.text_instrucciones)

        splitter.addWidget(panel_der)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([1000, 1000])
        layout.addWidget(splitter)

        # Cargar animales en el combo al final de la inicialización de la UI
        self._cargar_animales()

    # ---------------------------------------------------------------
    # Helpers de Animal / Etapa
    # ---------------------------------------------------------------
    def _cargar_animales(self):
        """Rellena el combo de animales desde la BD."""
        self._block_signals = True
        self.combo_animal.clear()
        animales = get_all_animales()
        self._animales_list = animales
        for a in animales:
            self.combo_animal.addItem(a['nombre'], a['id'])
        self._block_signals = False
        if animales:
            self._on_animal_changed(0)

    def _on_animal_changed(self, index):
        if self._block_signals or index < 0:
            return
        animal_id = self.combo_animal.itemData(index)
        self._animal_nombre = self._animales_list[index]['nombre'] if index < len(self._animales_list) else ""
        
        self._block_signals = True
        self.combo_comparar.clear()
        self._comparaciones_list = []
        
        # Cargar Solo Formulaciones Guardadas
        formulaciones = self.gestor_bd.listar_formulaciones(animal_id=animal_id)
        if formulaciones:
            for f in formulaciones:
                self.combo_comparar.addItem(f"Fórmula: {f['nombre']}", f)
                self._comparaciones_list.append(f)
        
        self._block_signals = False
        if self.combo_comparar.count() > 0:
            self.combo_comparar.setCurrentIndex(0)
        else:
            self._formula_comparar = None
            self.lbl_reqs.setText("Sin fórmulas guardadas para comparar.")
            self._recalcular()

    def _on_comparativa_changed(self, index):
        if self._block_signals or index < 0 or index >= len(getattr(self, '_comparaciones_list', [])):
            return
        
        item = self._comparaciones_list[index]
        self._formula_comparar = item
        # Calcular densidad nutricional de la fórmula guardada
        tkg = item.get('total_kg', 1.0) or 1.0
        self.lbl_reqs.setText(
            f"Comparando con '{item['nombre']}' (Base 1kg)"
        )
        
        self._recalcular()

    def reload_animales(self):
        """Llamar desde main_window cuando se cambia al tab de formulación."""
        current_animal = self.combo_animal.currentText()
        self._cargar_animales()
        # Intentar restaurar la selección previa
        for i in range(self.combo_animal.count()):
            if self.combo_animal.itemText(i) == current_animal:
                self.combo_animal.setCurrentIndex(i)
                break

    # ---------------------------------------------------------------
    # Carga de datos
    # ---------------------------------------------------------------
    def load_insumos(self):
        """Carga todos los insumos activos desde la BD."""
        self.insumos_db = get_all_insumos()
        self._block_signals = True
        self.table_tanteo.setRowCount(0)

        for ins in self.insumos_db:
            row = self.table_tanteo.rowCount()
            self.table_tanteo.insertRow(row)

            # Insumo (columna 0)
            item_nombre = QTableWidgetItem(ins['nombre'])
            item_nombre.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self.table_tanteo.setItem(row, 0, item_nombre)

            # Tanteo (columna 1) con SpinBox para flechitas de 1kg en 1kg
            spin = QDoubleSpinBox()
            spin.setRange(0, 99999)
            spin.setDecimals(2)
            spin.setSingleStep(1.0)
            spin.setValue(0.0)
            spin.setAccelerated(True) # Hace que suba más rápido si mantienes presionado
            spin.setStyleSheet("QDoubleSpinBox { background-color: transparent; border: none; color: white; }")
            spin.valueChanged.connect(lambda v: QTimer.singleShot(50, self._recalcular))
            self.table_tanteo.setCellWidget(row, 1, spin)

            # Costo calculado (columna 2)
            item_costo = QTableWidgetItem("0.00")
            item_costo.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self.table_tanteo.setItem(row, 2, item_costo)

        self._block_signals = False
        self.filter_insumos(self.search_formulacion.text())

    def _cargar_desde_optimizador(self, resultado_optimo):
        """
        Recibe una lista de tuplas (insumo_id, kg) desde el autoformulador
        y las coloca en la tabla de tanteo.
        """
        self._block_signals = True
        # Limpiar tanteos previos
        for row in range(self.table_tanteo.rowCount()):
            spin = self.table_tanteo.cellWidget(row, 1)
            if spin:
                spin.setValue(0.0)
                
        # Llenar con los nuevos
        opt_dict = {str(item[0]): item[1] for item in resultado_optimo}
        
        for row in range(self.table_tanteo.rowCount()):
            if row < len(self.insumos_db):
                ins = self.insumos_db[row]
                ins_id = str(ins['id'])
                if ins_id in opt_dict:
                    spin = self.table_tanteo.cellWidget(row, 1)
                    if spin:
                        spin.setValue(opt_dict[ins_id])
                        
        self._block_signals = False
        self._recalcular()

    # ---------------------------------------------------------------
    # Métodos públicos de soporte
    # ---------------------------------------------------------------
    def _quitar_insumo_seleccionado(self):
        """Desmarca el/los insumos seleccionados en la tabla y pone tanteo a 0."""
        rows = set(idx.row() for idx in self.table_tanteo.selectedIndexes())
        if not rows:
            return
        self._block_signals = True
        for row in rows:
            spin = self.table_tanteo.cellWidget(row, 1)
            c = self.table_tanteo.item(row, 2)
            if spin:
                spin.setValue(0.0)
            if c:
                c.setText("0.00")
        self._block_signals = False
        self._recalcular()

    def _get_seleccionados(self):
        """Retorna (insumos_sel, tanteos) para los insumos actualmente marcados."""
        insumos_sel = []
        tanteos = []
        for row in range(self.table_tanteo.rowCount()):
            spin = self.table_tanteo.cellWidget(row, 1)
            val = spin.value() if spin else 0.0
            if val > 0:
                insumos_sel.append(self.insumos_db[row])
                tanteos.append(val)
        return insumos_sel, tanteos

    def guardar_formulacion_actual(self):
        """Recopila datos y guarda la formulación en la BD."""
        nombre = self.input_nombre.text().strip()
        if not nombre:
            QMessageBox.warning(self, "Error", "Debe ingresar un nombre para la formulación.")
            return

        animal_idx = self.combo_animal.currentIndex()
        if animal_idx < 0:
            return
        animal_id = self.combo_animal.itemData(animal_idx)
        
        insumos_sel, tanteos = self._get_seleccionados()
        if not insumos_sel:
            QMessageBox.warning(self, "Error", "Debe agregar al menos un insumo con cantidad > 0.")
            return

        # Calcular totales para guardar
        res = calcular_resultados(insumos_sel, tanteos, 'kg')
        totales = res['totales']
        
        datos = {
            'nombre': nombre,
            'animal_id': animal_id,
            'total_kg': res['suma_tanteos'],
            'costo_por_kg': totales.get('costo_kg', 0),
            'costo_por_tonelada': totales.get('costo_kg', 0) * 1000,
            'resultados_nutricionales': {
                'proteina_total': totales['proteina'],
                'em_total': totales['em_kcal'],
                'fibra_total': totales['fibra'],
                'grasa_total': totales['grasa'],
                'calcio_total': totales['calcio'],
                'fosforo_total': totales['fosforo'],
                'lisina_total': totales['lisina'],
                'metionina_total': totales['metionina'],
                'colina_total': totales.get('colina_mgr', 0),
            },
            'instrucciones_preparacion': self.text_instrucciones.toPlainText(),
            'ingredientes': [
                {'insumo_id': ins['id'], 'tanteo_kg': cant} 
                for ins, cant in zip(insumos_sel, tanteos)
            ]
        }
        
        fid = self.gestor_bd.guardar_formulacion(datos)
        if fid is not None:
            QMessageBox.information(self, "Éxito", "Formulación guardada correctamente.")
            self._on_animal_changed(self.combo_animal.currentIndex())
            self.formulacion_guardada.emit()
        else:
            QMessageBox.critical(self, "Error", "No se pudo guardar la formulación.")

    def nueva_formulacion(self):
        """Limpia todos los campos para una nueva formulación."""
        self.input_nombre.clear()
        self.text_instrucciones.clear()
        
        self._block_signals = True
        for row in range(self.table_tanteo.rowCount()):
            spin = self.table_tanteo.cellWidget(row, 1)
            if spin:
                spin.setValue(0.0)
        self._block_signals = False
        
        if hasattr(self, 'lbl_reqs'):
            self.lbl_reqs.setText("<b>Requerimientos:</b> Ninguno (Seleccione una fórmula para comparar)")
            self.lbl_reqs.setStyleSheet("color: #8080A0;")
        
        self._recalcular()
        QMessageBox.information(self, "Nueva Formulación", "Se han limpiado todos los campos.")

    # ---------------------------------------------------------------
    # Slots
    # ---------------------------------------------------------------
    def _on_item_changed(self, item):
        if self._block_signals:
            return
        if item.column() in (1,):
            QTimer.singleShot(0, self._recalcular)

    def _on_item_double_clicked(self, item):
        row = item.row()
        insumo = self.insumos_db[row]['nombre']
        spin = self.table_tanteo.cellWidget(row, 1)
        actual = spin.value() if spin else 0.0
        
        from PyQt6.QtWidgets import QInputDialog
        cantidad, ok = QInputDialog.getDouble(
            self,
            "Cantidad de Insumo",
            f"Ingrese la cantidad para '{insumo}':",
            actual, 0.0, 9999.0, 2
        )
        if ok and spin:
            spin.setValue(cantidad)
            # El cambio en el spin ya dispara _recalcular

    def filter_insumos(self, text):
        if not hasattr(self, 'search_formulacion'):
            return
        text = text.lower()
        for row in range(self.table_tanteo.rowCount()):
            item = self.table_tanteo.item(row, 0)
            if not item:
                continue
            match_texto = text in item.text().lower()
            self.table_tanteo.setRowHidden(row, not match_texto)

    # ---------------------------------------------------------------
    # Motor de cálculo reactivo
    # ---------------------------------------------------------------
    def _recalcular(self):
        self._block_signals = True
        
        if not hasattr(self, 'table_tanteo') or not hasattr(self, 'table_resultados'):
            self._block_signals = False
            return

        # Desactivar actualizaciones visuales de tablas para mejorar velocidad
        self.table_tanteo.setUpdatesEnabled(False)
        self.table_resultados.setUpdatesEnabled(False)
        self.table_totales.setUpdatesEnabled(False)

        insumos_sel = []
        tanteos = []
        ids_usados = set()
        
        # 1. Primera pasada: Recolectar datos
        for row in range(self.table_tanteo.rowCount()):
            spin = self.table_tanteo.cellWidget(row, 1)
            val = spin.value() if spin else 0.0

            if val > 0:
                insumos_sel.append(self.insumos_db[row])
                tanteos.append(val)
                ids_usados.add(row)

        modo = 'kg'
        resultado = calcular_resultados(insumos_sel, tanteos, modo) if insumos_sel else None

        # Requerimientos desde ración de referencia (BD)
        reqs = {}
        if self._formula_comparar:
            f_ref = self._formula_comparar
            tkg = f_ref.get('total_kg', 1.0) or 1.0
            
            # Normalizar ración de referencia a 1kg para usar como "mínimo" deseado
            reqs = {
                'proteina_min':  f_ref.get('proteina_total', 0) / tkg,
                'em_min':        f_ref.get('em_total', 0) / tkg,
                'fibra_max':     f_ref.get('fibra_total', 100) / tkg,
                'grasa_max':     f_ref.get('grasa_total', 100) / tkg,
                'calcio_min':    f_ref.get('calcio_total', 0) / tkg,
                'fosforo_min':   f_ref.get('fosforo_total', 0) / tkg,
                'lisina_min':    f_ref.get('lisina_total', 0) / tkg,
                'metionina_min': f_ref.get('metionina_total', 0) / tkg,
            }

        # ── Actualizar tabla de resultados ──────────────────────────
        self.table_resultados.setRowCount(0)

        if resultado:
            for item in resultado['resultados_por_insumo']:
                row_idx = self.table_resultados.rowCount()
                self.table_resultados.insertRow(row_idx)
                vals = [
                    item['nombre'],
                    f"{item['porcentaje']:.2f}",
                    f"{item['proteina']:.2f}",
                    f"{item['em_kcal']:.2f}",
                    f"{item['fibra']:.2f}",
                    f"{item['grasa']:.2f}",
                    f"{item['calcio']:.3f}",
                    f"{item['fosforo']:.3f}",
                    f"{item['lisina']:.3f}",
                    f"{item['metionina']:.3f}",
                    f"{item['colina_mgr']:.1f}",
                ]
                for col, v in enumerate(vals):
                    cell = QTableWidgetItem(v)
                    cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    cell.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                    self.table_resultados.setItem(row_idx, col, cell)

            # ── Fila de TOTALES ──────────────────────────────────────
            totales = resultado['totales']
            bold = QFont(); bold.setBold(True)
            total_vals = [
                "TOTALES",
                f"{resultado['suma_porcentajes']:.2f}",
                f"{totales['proteina']:.2f}",
                f"{totales['em_kcal']:.2f}",
                f"{totales['fibra']:.2f}",
                f"{totales['grasa']:.2f}",
                f"{totales['calcio']:.3f}",
                f"{totales['fosforo']:.3f}",
                f"{totales['lisina']:.3f}",
                f"{totales['metionina']:.3f}",
                f"{totales['colina_mgr']:.1f}",
            ]
            for col, v in enumerate(total_vals):
                cell = QTableWidgetItem(v)
                cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                cell.setFont(bold)
                cell.setFlags(Qt.ItemFlag.ItemIsEnabled)
                cell.setBackground(QBrush(COLOR_TOTAL_BG))
                self.table_totales.setItem(0, col, cell)

            # Colorear semáforo
            nut_keys = ['proteina', 'em_kcal', 'fibra', 'grasa', 'calcio',
                        'fosforo', 'lisina', 'metionina', 'colina_mgr']
            for i, nut in enumerate(nut_keys):
                col = i + 2
                estado = evaluar_cumplimiento(totales[nut], nut, reqs)
                color = {'verde': COLOR_VERDE, 'amarillo': COLOR_AMARILLO, 'rojo': COLOR_ROJO}.get(estado, COLOR_VERDE)
                self.table_totales.item(0, col).setBackground(QBrush(color))

            # ── Salud Preventiva ─────────────────────────────────────
            ratio_cap, estado_cap, msg_cap = calcular_ratio_ca_p(totales)
            alertas_toxicidad = verificar_limites_inclusion(insumos_sel, tanteos, modo)
            alertas_nombres = {a['nombre'] for a in alertas_toxicidad}
            
            msg_salud = msg_cap
            if alertas_toxicidad:
                msg_salud += " | LÍMITES SUPERADOS:"
                for a in alertas_toxicidad:
                    msg_salud += f" {a['nombre']} ({a['porcentaje_usado']:.1f}%)."
            
            color_salud = {"verde": "#27AE60", "amarillo": "#D35400", "rojo": "#C0392B"}.get(estado_cap, "#7F8C8D")
            if alertas_toxicidad: color_salud = "#C0392B"
            self.lbl_salud.setText(msg_salud)
            self.lbl_salud.setStyleSheet(f"font-weight: bold; color: {color_salud}; padding: 5px; border: 1px solid {color_salud}; border-radius: 4px;")
            
            # ── Costo ────────────────────────────────────────────────
            costo_kg  = totales['costo_kg']
            self.lbl_costo.setText(f"💲 Costo/kg: ${costo_kg:.4f}  |  Tonelada: ${costo_kg*1000:.2f}")

            # ── Barra progreso ───────────────────────────────────────
            suma_pct = min(resultado['suma_porcentajes'], 100)
            self.progress_total.setValue(int(suma_pct))
            self.progress_total.setStyleSheet(f"QProgressBar::chunk {{ background: {'#E74C3C' if resultado['suma_porcentajes'] > 100 else '#2ECC71'}; }}")
            self.lbl_total_kg.setText(f"Total: {resultado['suma_tanteos']:.2f} kg")
            self.lbl_total_pct.setText(f"({resultado['suma_porcentajes']:.2f} %)")

            # ── ESTILO DE TABLA TANTEO (Única pasada optimizada) ──────
            color_uso = QColor("#EC7063") # Rojo claro vivo para lo que se está usando
            color_toxic = QColor("#C0392B") # Rojo fuerte para toxicidad
            
            for row in range(self.table_tanteo.rowCount()):
                item_nombre = self.table_tanteo.item(row, 0)
                if not item_nombre: continue
                
                bg_color = None
                if item_nombre.text() in alertas_nombres:
                    bg_color = color_toxic
                elif row in ids_usados:
                    bg_color = color_uso
                
                brush = QBrush(bg_color) if bg_color else QBrush()
                t_color = QColor("white") # Siempre blanco para que sea legible en tema oscuro
                
                for col in range(self.table_tanteo.columnCount()):
                    it = self.table_tanteo.item(row, col)
                    if it: 
                        it.setBackground(brush)
                        it.setForeground(QBrush(t_color))
                
                # Sincronizar color con el SpinBox
                spin = self.table_tanteo.cellWidget(row, 1)
                if spin:
                    if bg_color:
                        spin.setStyleSheet(f"background-color: {bg_color.name()}; border: none; color: white;")
                    else:
                        spin.setStyleSheet("background-color: transparent; border: none; color: white;")

            # ── Gráfico de Radar (Diferido para no bloquear UI) ───────
            if self.group_radar.isChecked():
                # Añadimos el total_kg para la normalización en el radar
                totales['total_kg'] = resultado['suma_tanteos']
                
                # Si no hay target, usamos el mismo totales como referencia (círculo 1.0)
                target = self._formula_comparar if self._formula_comparar else None
                nombre_ref = self.combo_comparar.currentText() if target else ""
                QTimer.singleShot(10, lambda: self._actualizar_radar(totales, target, nombre_ref))

        else:
            # Limpiar si no hay datos
            self._limpiar_resultados()

        # Reactivar actualizaciones
        self.table_tanteo.setUpdatesEnabled(True)
        self.table_resultados.setUpdatesEnabled(True)
        self.table_totales.setUpdatesEnabled(True)
        self._block_signals = False

    def _limpiar_resultados(self):
        """Limpia los widgets de resultados cuando no hay selección."""
        self.table_resultados.setRowCount(0)
        self.table_totales.setRowCount(0)
        self.table_totales.setRowCount(1)
        self.progress_total.setValue(0)
        self.progress_total.setStyleSheet("")
        self.lbl_total_kg.setText("Total: 0.00 kg")
        self.lbl_total_pct.setText("(0.00 %)")
        self.lbl_costo.setText("Costo/kg: $0.00  |  Tonelada: $0.00")
        self.lbl_salud.setText("Validación de Salud: Esperando cálculo...")
        self.lbl_salud.setStyleSheet("font-weight: bold; font-size: 13px; color: #7F8C8D; padding: 5px;")
        self.figura_radar.clear()
        self.canvas_radar.draw()


    def _actualizar_radar(self, valores_actual, valores_referencia=None, nombre_ref=""):
        """
        Dibuja un gráfico de radar normalizado a 1kg.
        """
        self.figura_radar.clear()
        self.figura_radar.patch.set_facecolor('#1E1E2E')

        EJES = ['Proteína', 'EM Kcal', 'Fibra', 'Grasa',
                'Calcio', 'Fósforo', 'Lisina', 'Metionina']
        KEYS = ['proteina', 'em_kcal', 'fibra', 'grasa',
                'calcio', 'fosforo', 'lisina', 'metionina']

        N = len(EJES)
        angulos = [n / float(N) * 2 * np.pi for n in range(N)]
        angulos += angulos[:1]  # cerrar el polígono

        ax = self.figura_radar.add_subplot(111, polar=True, facecolor='#16213E')

        # ── Estética de la grilla ─────────────────────────────────────────
        ax.set_facecolor('#16213E')
        ax.spines['polar'].set_color('#2A2A4A')
        ax.grid(color='#2A2A4A', linestyle='--', linewidth=0.8, alpha=0.7)

        # Anillos de referencia en 0.5, 1.0, 1.5
        import matplotlib.pyplot as plt
        for nivel in [0.5, 1.0, 1.5]:
            circulo = plt.Circle(
                (0, 0), nivel,
                transform=ax.transData._b,
                fill=False,
                color='#3A3A6A' if nivel != 1.0 else '#5CB85C',
                linewidth=1.0 if nivel != 1.0 else 1.8,
                linestyle='--' if nivel != 1.0 else '-',
                alpha=0.6
            )
            # Etiquetas de nivel en el eje de Proteína
        ax.set_yticks([0.5, 1.0, 1.5])
        ax.set_yticklabels(['0.5x', '1.0x', '1.5x'],
                            color='#606090', fontsize=8)
        ax.set_ylim(0, 1.8)

        # Etiquetas de los ejes con color y tamaño
        ax.set_xticks(angulos[:-1])
        ax.set_xticklabels(EJES, color='#A0A0D0', fontsize=10, fontweight='bold')

        # Procesar los diccionarios (target vs actuales) para normalizar a 1kg
        def val_from_dict(d, key):
            if not d: return 0.0
            return float(d.get(key, 0.0) or 0.0)

        total_kg_actual = valores_actual.get('total_kg', 1.0)
        if total_kg_actual <= 0: total_kg_actual = 1.0
        valores_actual_1kg = {k: val_from_dict(valores_actual, k) / total_kg_actual for k in KEYS}

        valores_target_1kg = None
        if valores_referencia:
            tk_target = valores_referencia.get('total_kg', 1.0)
            if tk_target <= 0: tk_target = 1.0
            
            valores_target_1kg = {}
            for k in KEYS:
                k_bd = 'em_total' if k == 'em_kcal' else f"{k}_total"
                if k_bd in valores_referencia:
                    # Viene directo de listar_formulaciones (plano)
                    valores_target_1kg[k] = val_from_dict(valores_referencia, k_bd) / tk_target
                elif 'resultados_nutricionales' in valores_referencia and k_bd in valores_referencia['resultados_nutricionales']:
                    # Viene anidado
                    valores_target_1kg[k] = val_from_dict(valores_referencia['resultados_nutricionales'], k_bd) / tk_target
                else:
                    # Fallback
                    valores_target_1kg[k] = val_from_dict(valores_referencia, k) / tk_target


        # ── MODO SIN REFERENCIA: círculo base ─────────────────────────────
        if valores_target_1kg is None:
            vals = [valores_actual_1kg.get(k, 0) for k in KEYS]
            # normalizar_a_uno (todos 1.0)
            vals_norm = [1.0 for _ in vals] if sum(vals) > 0 else [0.0]*len(vals)
            vals_norm += vals_norm[:1]

            ax.fill(angulos, vals_norm,
                    color='#2D7D46', alpha=0.25)
            ax.plot(angulos, vals_norm,
                    color='#5CB85C', linewidth=2.5,
                    linestyle='-', label='Ración actual')
            ax.scatter(angulos[:-1], vals_norm[:-1],
                       color='#5CB85C', s=60, zorder=5)

            ax.set_title('Perfil Nutricional — Sin referencia\n(Modo base: 1.0 = tu ración actual)',
                         color='white', fontsize=12, fontweight='bold', pad=20)

        # ── MODO CON REFERENCIA: comparación ──────────────────────────────
        else:
            vals_ref  = [valores_target_1kg.get(k, 1) for k in KEYS]
            vals_act  = [valores_actual_1kg.get(k, 0) for k in KEYS]

            # Normalizar: referencia = 1.0, actual = relativo a referencia
            vals_ref_norm = [1.0] * N
            vals_act_norm = [
                (a / r) if r > 0 else 0.0
                for a, r in zip(vals_act, vals_ref)
            ]

            # Cerrar polígonos
            vals_ref_norm += vals_ref_norm[:1]
            vals_act_norm += vals_act_norm[:1]

            # Área de referencia (base = 1.0)
            ax.fill(angulos, vals_ref_norm,
                    color='#D9534F', alpha=0.15)
            ax.plot(angulos, vals_ref_norm,
                    color='#D9534F', linewidth=2.0,
                    linestyle='--',
                    label=f'Ref: {nombre_ref[:25]}')

            # Área actual
            ax.fill(angulos, vals_act_norm,
                    color='#5BC0DE', alpha=0.20)
            ax.plot(angulos, vals_act_norm,
                    color='#5BC0DE', linewidth=2.5,
                    linestyle='-', label='Ración actual')

            # Puntos con color según posición vs referencia
            for i, (ang, val) in enumerate(zip(angulos[:-1], vals_act_norm)):
                color_punto = '#5CB85C' if val >= 0.95 else (
                    '#F0AD4E' if val >= 0.80 else '#D9534F'
                )
                ax.scatter([ang], [val], color=color_punto, s=70, zorder=6)

            ax.set_title(
                f'Comparativa Nutricional — 1kg vs 1kg\n'
                f'Referencia: {nombre_ref[:30]}',
                color='white', fontsize=12, fontweight='bold', pad=20
            )

        # ── Leyenda ───────────────────────────────────────────────────────
        leyenda = ax.legend(
            loc='upper right',
            bbox_to_anchor=(1.35, 1.15),
            facecolor='#2A2A3E',
            edgecolor='#3A3A6A',
            labelcolor='white',
            fontsize=9
        )

        self.figura_radar.tight_layout()
        self.canvas_radar.draw()
        
        self.valores_actual = valores_actual_1kg
        self.valores_referencia = valores_target_1kg
        self._actualizar_tabla_diferencias(self.valores_actual, self.valores_referencia)
        
    def _actualizar_tabla_diferencias(self, valores_actual, valores_referencia=None):
        """
        Tabla de 4 columnas debajo del radar.
        """
        EJES = ['Proteína%', 'EM Kcal', 'Fibra%', 'Grasa%',
                'Calcio%', 'Fósforo%', 'Lisina%', 'Metionina%']
        KEYS = ['proteina', 'em_kcal', 'fibra', 'grasa',
                'calcio', 'fosforo', 'lisina', 'metionina']

        if valores_referencia is None:
            self.tabla_dif.setColumnCount(2)
            self.tabla_dif.setHorizontalHeaderLabels(['Nutriente', 'Valor (1kg)'])
            self.tabla_dif.setRowCount(len(KEYS))
            for i, (eje, key) in enumerate(zip(EJES, KEYS)):
                self.tabla_dif.setItem(i, 0, QTableWidgetItem(eje))
                self.tabla_dif.setItem(i, 1, QTableWidgetItem(
                    f"{valores_actual.get(key, 0):.4f}"
                ))
        else:
            self.tabla_dif.setColumnCount(4)
            self.tabla_dif.setHorizontalHeaderLabels([
                'Nutriente', 'Actual (1kg)', 'Referencia (1kg)', 'Ratio'
            ])
            self.tabla_dif.setRowCount(len(KEYS))
            for i, (eje, key) in enumerate(zip(EJES, KEYS)):
                val_act = valores_actual.get(key, 0)
                val_ref = valores_referencia.get(key, 0)
                ratio   = val_act / val_ref if val_ref > 0 else 0.0

                item_ratio = QTableWidgetItem(f"{ratio:.2f}x")

                if ratio >= 0.95:
                    item_ratio.setForeground(QColor('#5CB85C'))
                elif ratio >= 0.80:
                    item_ratio.setForeground(QColor('#F0AD4E'))
                else:
                    item_ratio.setForeground(QColor('#D9534F'))

                self.tabla_dif.setItem(i, 0, QTableWidgetItem(eje))
                self.tabla_dif.setItem(i, 1, QTableWidgetItem(f"{val_act:.4f}"))
                self.tabla_dif.setItem(i, 2, QTableWidgetItem(f"{val_ref:.4f}"))
                self.tabla_dif.setItem(i, 3, item_ratio)

    def _conectar_tooltip_radar(self):
        """
        Al mover el mouse sobre el gráfico, mostrar el valor exacto del punto más cercano.
        """
        self.valores_actual = {}
        self.valores_referencia = {}
        def on_hover(evento):
            if not evento.inaxes:
                return
            
            angulo_cursor = np.arctan2(evento.ydata, evento.xdata)
            if angulo_cursor < 0:
                angulo_cursor += 2 * np.pi

            KEYS  = ['proteina','em_kcal','fibra','grasa',
                     'calcio','fosforo','lisina','metionina']
            EJES  = ['Proteína','EM Kcal','Fibra','Grasa',
                     'Calcio','Fósforo','Lisina','Metionina']
            N     = len(KEYS)
            angulos_ejes = [n / float(N) * 2 * np.pi for n in range(N)]

            distancias = [abs(angulo_cursor - a) for a in angulos_ejes]
            idx_mas_cercano = distancias.index(min(distancias))

            nutriente = EJES[idx_mas_cercano]
            key       = KEYS[idx_mas_cercano]
            val_act   = self.valores_actual.get(key, 0) if hasattr(self, 'valores_actual') else 0

            texto = f"{nutriente}: {val_act:.4f} por kg"
            if hasattr(self, 'valores_referencia') and self.valores_referencia:
                val_ref = self.valores_referencia.get(key, 0)
                ratio   = val_act / val_ref if val_ref > 0 else 0
                texto  += f"\nRef: {val_ref:.4f}  |  Ratio: {ratio:.2f}x"

            self.canvas_radar.setToolTip(texto)

        self.canvas_radar.mpl_connect('motion_notify_event', on_hover)

    def _exportar_radar(self):
        from PyQt6.QtWidgets import QFileDialog
        ruta, _ = QFileDialog.getSaveFileName(
            self, "Exportar gráfico de radar",
            "radar_nutricional.png",
            "PNG (*.png);;PDF (*.pdf)"
        )
        if ruta:
            self.figura_radar.savefig(ruta, dpi=200, bbox_inches='tight',
                                facecolor='#1E1E2E')
            QMessageBox.information(self, "Exportado", "Gráfico exportado correctamente.")

    # ---------------------------------------------------------------
    # API Pública para Integración con TabCalcular
    # ---------------------------------------------------------------
    def _calcular_totales_dict(self):
        insumos, tanteos = self._get_seleccionados()
        if not insumos:
            return {}
        res = calcular_resultados(insumos, tanteos, 'kg')
        if not res:
            return {}
        totales = res['totales']
        return {
            'proteina_total': totales.get('proteina', 0),
            'em_total': totales.get('em_kcal', 0),
            'fibra_total': totales.get('fibra', 0),
            'grasa_total': totales.get('grasa', 0),
            'calcio_total': totales.get('calcio', 0),
            'fosforo_total': totales.get('fosforo', 0),
            'lisina_total': totales.get('lisina', 0),
            'metionina_total': totales.get('metionina', 0),
            'colina_total': totales.get('colina_mgr', 0),
        }

    def cargar_desde_bd(self, formulacion):
        """Carga una formulación guardada en la tabla."""
        self._block_signals = True
        
        # 1. Configurar Animal y Etapa
        animal_id = formulacion.get('animal_id')
        etapa_id = formulacion.get('etapa_id')
        
        if animal_id:
            idx = self.combo_animal.findData(animal_id)
            if idx >= 0:
                self.combo_animal.setCurrentIndex(idx)
                
        if etapa_id:
            idx = self.combo_etapa.findData(etapa_id)
            if idx >= 0:
                self.combo_etapa.setCurrentIndex(idx)
                
        # 2. Cargar Nombre e instrucciones
        if hasattr(self, 'input_nombre'):
            self.input_nombre.setText(formulacion.get('nombre', ''))

        if hasattr(self, 'text_instrucciones'):
            self.text_instrucciones.setPlainText(formulacion.get('instrucciones_preparacion', ''))

        # 3. Llenar tanteos
        ingredientes_dict = {ing['insumo_id']: ing['tanteo_kg'] for ing in formulacion.get('ingredientes', [])}
        
        for row in range(self.table_tanteo.rowCount()):
            insumo_db = self.insumos_db[row]
            tanteo_bd = ingredientes_dict.get(insumo_db['id'], 0.0)
            spin = self.table_tanteo.cellWidget(row, 1)
            if spin:
                spin.setValue(tanteo_bd)
                
        self._block_signals = False
        self._recalcular()
