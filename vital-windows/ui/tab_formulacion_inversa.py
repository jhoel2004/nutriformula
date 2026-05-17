# ui/tab_formulacion_inversa.py
import numpy as np
from scipy.optimize import linprog
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
                             QTableWidgetItem, QHeaderView, QComboBox,
                             QLabel, QSplitter, QPushButton, QDoubleSpinBox, QGroupBox, QMessageBox, QRadioButton, QFrame, QScrollArea)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QBrush, QFont

from app.database import get_all_insumos, GestorFormulacionesBD

COLS_RES = ["Insumo", "% en Ración", "kg necesarios", "Costo"]

class TabFormulacionInversa(QWidget):
    # Señal para enviar datos al Tab de Formulación normal
    enviar_formulacion = pyqtSignal(list, float, str) # [(id_insumo, tanteo), ...], total_kg, modo ('kg' o 'porcentaje')
    formulacion_guardada = pyqtSignal()  # emitida tras guardar para refrescar tab animales

    def __init__(self):
        super().__init__()
        self.insumos_db = []
        self._resultado_optimo = None
        self.gestor_bd = GestorFormulacionesBD()
        self.setup_ui()
        self.load_insumos()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # ==========================================
        # PANEL IZQ: Metas Nutricionales
        # ==========================================
        panel_izq = QWidget()
        lay_izq = QVBoxLayout(panel_izq)

        group_metas = QGroupBox("INGRESA TUS METAS NUTRICIONALES")
        lay_metas = QVBoxLayout()
        
        # Animal y nombre de Etapa
        top_metas = QHBoxLayout()
        
        lbl_animal = QLabel("Animal:")
        lbl_animal.setStyleSheet("font-weight: bold; font-size: 13px;")
        top_metas.addWidget(lbl_animal)
        
        self.combo_animal_inv = QComboBox()
        self.combo_animal_inv.setMinimumWidth(200)
        self.combo_animal_inv.currentIndexChanged.connect(self._on_animal_inv_changed)
        top_metas.addWidget(self.combo_animal_inv)
        
        top_metas.addSpacing(16)
        
        lbl_historial = QLabel("Referencia Historial:")
        lbl_historial.setStyleSheet("font-weight: bold; font-size: 13px;")
        top_metas.addWidget(lbl_historial)
        
        self.combo_historial_inv = QComboBox()
        self.combo_historial_inv.setMinimumWidth(220)
        self.combo_historial_inv.setEditable(True)
        self.combo_historial_inv.lineEdit().setPlaceholderText("Nombre de nueva fórmula")
        top_metas.addWidget(self.combo_historial_inv)
        
        top_metas.addSpacing(8)
        
        self.btn_importar = QPushButton("📥 Importar de Historial")
        self.btn_importar.setStyleSheet("background-color: #8E44AD; color: white; font-weight: bold; padding: 6px 10px; border-radius: 4px;")
        self.btn_importar.setToolTip("Cargar metas desde una fórmula guardada")
        self.btn_importar.clicked.connect(self._importar_requerimientos)
        top_metas.addWidget(self.btn_importar)
        
        top_metas.addStretch()
        
        lay_metas.addLayout(top_metas)
        
        # Grid para las metas
        lay_grid = QVBoxLayout()
        
        # Cabeceras
        hdr = QHBoxLayout()
        hdr.addWidget(QLabel("Nutriente"), 2)
        hdr.addWidget(QLabel("Mínimo"), 1)
        hdr.addWidget(QLabel("Máximo"), 1)
        lay_grid.addLayout(hdr)
        
        self.spins_metas = {}
        nutrientes_def = [
            ("Proteína %",  "proteina", 15.0, 100.0),
            ("EM Kcal/kg",  "em_kcal", 2700.0, 9000.0),
            ("Fibra %",     "fibra", 0.0, 8.0),
            ("Grasa %",     "grasa", 0.0, 100.0),
            ("Calcio %",    "calcio", 0.35, 4.5),
            ("Fósforo %",   "fosforo", 0.3, 20.0),
            ("Lisina %",    "lisina", 0.6, 20.0),
            ("Metionina %", "metionina", 0.25, 20.0),
            ("Colina mg/kg","colina_mgr", 0.0, 5000.0)
        ]

        for lbl_text, key, def_min, def_max in nutrientes_def:
            row = QHBoxLayout()
            row.addWidget(QLabel(lbl_text), 2)
            
            spin_min = QDoubleSpinBox()
            spin_min.setRange(0, 99999)
            spin_min.setDecimals(2)
            spin_min.setValue(def_min)
            row.addWidget(spin_min, 1)
            
            spin_max = QDoubleSpinBox()
            spin_max.setRange(0, 99999)
            spin_max.setDecimals(2)
            spin_max.setValue(def_max)
            row.addWidget(spin_max, 1)
            
            self.spins_metas[key] = (spin_min, spin_max)
            lay_grid.addLayout(row)
            
        lay_metas.addLayout(lay_grid)

        # Separador
        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine); sep.setFrameShadow(QFrame.Shadow.Sunken)
        lay_metas.addWidget(sep)

        # Total Ración
        lay_total = QHBoxLayout()
        lay_total.addWidget(QLabel("Total de ración a preparar:"))
        self.spin_total_kg = QDoubleSpinBox()
        self.spin_total_kg.setRange(0.1, 99999)
        self.spin_total_kg.setValue(100.0)
        lay_total.addWidget(self.spin_total_kg)
        lay_total.addWidget(QLabel("kg"))
        lay_metas.addLayout(lay_total)



        # Botón Calcular
        btn_calcular = QPushButton("⚡ CALCULAR FORMULACIÓN")
        btn_calcular.setStyleSheet("background-color: #27AE60; color: white; font-weight: bold; padding: 12px; margin-top: 10px;")
        btn_calcular.clicked.connect(self.calcular_optimo)
        lay_metas.addWidget(btn_calcular)

        group_metas.setLayout(lay_metas)
        
        scroll_izq = QScrollArea()
        scroll_izq.setWidget(group_metas)
        scroll_izq.setWidgetResizable(True)
        lay_izq.addWidget(scroll_izq)

        splitter.addWidget(panel_izq)

        # ==========================================
        # PANEL DER: Insumos y Resultados (Usando QSplitter vertical)
        # ==========================================
        panel_der = QSplitter(Qt.Orientation.Vertical)

        group_insumos = QGroupBox("Ingredientes disponibles para usar")
        lay_ins = QVBoxLayout()
        self.table_disponibles = QTableWidget()
        self.table_disponibles.setColumnCount(4)
        self.table_disponibles.setHorizontalHeaderLabels(["Usar", "Ingrediente", "Mín %", "Máx %"])
        self.table_disponibles.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_disponibles.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table_disponibles.setColumnWidth(0, 40)
        self.table_disponibles.setColumnWidth(2, 60)
        self.table_disponibles.setColumnWidth(3, 60)
        lay_ins.addWidget(self.table_disponibles)
        group_insumos.setLayout(lay_ins)
        panel_der.addWidget(group_insumos)

        # Splitter horizontal para separar insumos de resultados (opcional)
        self.group_resultados = QGroupBox("Resultado")
        self.group_resultados.setVisible(False)
        lay_res = QVBoxLayout()
        
        self.lbl_mensaje_res = QLabel()
        self.lbl_mensaje_res.setWordWrap(True)
        lay_res.addWidget(self.lbl_mensaje_res)

        self.table_resultados = QTableWidget()
        self.table_resultados.setColumnCount(len(COLS_RES))
        self.table_resultados.setHorizontalHeaderLabels(COLS_RES)
        self.table_resultados.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        lay_res.addWidget(self.table_resultados)

        # Botones de acción final
        lay_acciones = QHBoxLayout()
        self.btn_enviar = QPushButton("📋 Enviar al Tab de Formulación")
        self.btn_enviar.setStyleSheet("background-color: #2980B9; color: white; padding: 8px;")
        self.btn_enviar.clicked.connect(self.enviar_a_formulacion)
        
        # Guardar como fórmula
        self.btn_guardar_inv = QPushButton("✅ Guardar Resultado como Nueva Fórmula")
        self.btn_guardar_inv.setStyleSheet("background-color: #27AE60; color: white; font-weight: bold; padding: 8px 15px; border-radius: 4px;")
        self.btn_guardar_inv.clicked.connect(self._guardar_como_formula)
        lay_acciones.addWidget(self.btn_guardar_inv)
        lay_acciones.addWidget(self.btn_enviar)
        lay_res.addLayout(lay_acciones)

        self.group_resultados.setLayout(lay_res)
        panel_der.addWidget(self.group_resultados)
        
        # Opcional: que el resultado esté visible por defecto o se muestre cuando se calcula
        self.group_resultados.setVisible(True)

        splitter.addWidget(panel_der)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([1000, 1000])
        panel_der.setSizes([1000, 1000])
        layout.addWidget(splitter)
        
        self._cargar_animales()

    def _cargar_animales(self):
        from app.database import get_all_animales
        animales = get_all_animales()
        self.combo_animal_inv.blockSignals(True)
        self.combo_animal_inv.clear()
        for a in animales:
            self.combo_animal_inv.addItem(a['nombre'], a['id'])
        self.combo_animal_inv.blockSignals(False)
        if animales:
            self._on_animal_inv_changed(0)

    def _on_animal_inv_changed(self, index):
        """Cuando cambia el animal, cargar su historial de fórmulas en el combo."""
        if index < 0:
            return
        animal_id = self.combo_animal_inv.itemData(index)
        if animal_id is None:
            return
        self._historial_inv_list = self.gestor_bd.listar_formulaciones(animal_id=animal_id)
        self.combo_historial_inv.blockSignals(True)
        self.combo_historial_inv.clear()
        for f in self._historial_inv_list:
            self.combo_historial_inv.addItem(f['nombre'], f['id'])
        self.combo_historial_inv.blockSignals(False)

    def _importar_requerimientos(self):
        """Importa los valores de una formulación guardada a los spinboxes de metas."""
        idx = self.combo_historial_inv.currentIndex()
        formulaciones = getattr(self, '_historial_inv_list', [])
        if idx < 0 or idx >= len(formulaciones):
            QMessageBox.warning(self, "Sin Selección", "Selecciona una fórmula del historial para importar.")
            return
        
        f_resumen = formulaciones[idx]
        f = self.gestor_bd.cargar_formulacion(f_resumen['id'])
        if not f: return

        nuts = f.get('resultados_nutricionales', {})
        mapping = {
            'proteina': 'proteina_total',
            'em_kcal': 'em_total',
            'fibra': 'fibra_total',
            'grasa': 'grasa_total',
            'calcio': 'calcio_total',
            'fosforo': 'fosforo_total',
            'lisina': 'lisina_total',
            'metionina': 'metionina_total',
            'colina_mgr': 'colina_total',
        }
        for key_meta, key_db in mapping.items():
            spin_min, spin_max = self.spins_metas[key_meta]
            val = nuts.get(key_db, 0)
            if val > 0:
                spin_min.setValue(val * 0.98) # Margen de 2% para optimizar
                spin_max.setValue(val * 1.02)
        QMessageBox.information(self, "Importado", f"Valores de '{f['nombre']}' cargados como metas (con margen ±2%).")

    def load_insumos(self):
        self.insumos_db = get_all_insumos()
        self.table_disponibles.setRowCount(0)
        for ins in self.insumos_db:
            row = self.table_disponibles.rowCount()
            self.table_disponibles.insertRow(row)
            
            chk = QTableWidgetItem()
            chk.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            chk.setCheckState(Qt.CheckState.Checked)
            self.table_disponibles.setItem(row, 0, chk)
            
            self.table_disponibles.setItem(row, 1, QTableWidgetItem(ins['nombre']))
            
            spin_min = QDoubleSpinBox()
            spin_min.setRange(0, 100); spin_min.setDecimals(1); spin_min.setValue(0)
            self.table_disponibles.setCellWidget(row, 2, spin_min)
            
            spin_max = QDoubleSpinBox()
            spin_max.setRange(0, 100); spin_max.setDecimals(1); spin_max.setValue(100)
            self.table_disponibles.setCellWidget(row, 3, spin_max)

    def calcular_optimo(self):
        ingredientes_disponibles = []
        limites_por_ingrediente = {}
        
        for r in range(self.table_disponibles.rowCount()):
            if self.table_disponibles.item(r, 0).checkState() == Qt.CheckState.Checked:
                ins = self.insumos_db[r]
                ingredientes_disponibles.append(ins)
                min_pct = self.table_disponibles.cellWidget(r, 2).value()
                max_pct = self.table_disponibles.cellWidget(r, 3).value()
                limites_por_ingrediente[ins['id']] = (min_pct, max_pct)

        if len(ingredientes_disponibles) < 2:
            QMessageBox.warning(self, "Error", "Seleccione al menos 2 ingredientes.")
            return

        metas_min = {}
        metas_max = {}
        for key, (spin_min, spin_max) in self.spins_metas.items():
            val_min = spin_min.value()
            val_max = spin_max.value()
            # Si el usuario deja en 0 el max, significa que no lo quiere evaluar o es 0 real. Asumimos que si max < min, usa min
            if val_max < val_min:
                val_max = val_min
            metas_min[key] = val_min
            metas_max[key] = val_max

        total_kg = self.spin_total_kg.value()

        # Algoritmo inverso exacto del prompt
        n = len(ingredientes_disponibles)
        nutrientes = ['proteina', 'em_kcal', 'fibra', 'grasa', 'calcio', 'fosforo', 'lisina', 'metionina', 'colina_mgr']
        
        c = [ing['precio_kg'] if ing['precio_kg'] > 0 else 1.0 for ing in ingredientes_disponibles]
        
        A_eq = [np.ones(n)]
        b_eq = [1.0]
        
        A_ub = []
        b_ub = []
        for nutriente in nutrientes:
            vals = [ing.get(nutriente, 0) for ing in ingredientes_disponibles]
            if nutriente in metas_min and metas_min[nutriente] > 0:
                A_ub.append([-v for v in vals])
                b_ub.append(-metas_min[nutriente])
            if nutriente in metas_max and metas_max[nutriente] < 99999: # Si es el top maximo ignorar
                A_ub.append(vals)
                b_ub.append(metas_max[nutriente])
        
        bounds = []
        for ing in ingredientes_disponibles:
            lo, hi = limites_por_ingrediente.get(ing['id'], (0.0, 100.0))
            bounds.append((lo/100.0, hi/100.0))
        
        self.group_resultados.setVisible(True)
        
        try:
            # high es el metodo por defecto ahora en scipy linprog moderno
            if not A_ub: # Sin restricciones de desigualdad
                resultado = linprog(c, A_eq=A_eq, b_eq=b_eq, bounds=bounds, method='highs')
            else:
                resultado = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq, bounds=bounds, method='highs')
            
            if resultado.success:
                proporciones = {ing['id']: resultado.x[i] * 100 
                               for i, ing in enumerate(ingredientes_disponibles)
                               if resultado.x[i] > 0.0001}
                self.mostrar_exito(ingredientes_disponibles, proporciones, total_kg)
            else:
                self.mostrar_fracaso(resultado, ingredientes_disponibles, metas_min, metas_max, limites_por_ingrediente)
                
        except Exception as e:
            QMessageBox.critical(self, "Error de cálculo", str(e))

    def mostrar_exito(self, ingredientes_disponibles, proporciones, total_kg):
        self.lbl_mensaje_res.setText("✅ Solución encontrada.")
        self.lbl_mensaje_res.setStyleSheet("color: #27AE60; font-weight: bold; font-size: 14px;")
        self.btn_enviar.setEnabled(True)
        self.table_resultados.setRowCount(0)
        
        costo_total = 0
        self._resultado_optimo = []

        for ing in ingredientes_disponibles:
            if ing['id'] in proporciones:
                pct = proporciones[ing['id']]
                kg_nec = (pct / 100.0) * total_kg
                costo = kg_nec * ing['precio_kg']
                costo_total += costo
                
                self._resultado_optimo.append((ing['id'], kg_nec))
                
                row = self.table_resultados.rowCount()
                self.table_resultados.insertRow(row)
                self.table_resultados.setItem(row, 0, QTableWidgetItem(ing['nombre']))
                self.table_resultados.setItem(row, 1, QTableWidgetItem(f"{pct:.2f}%"))
                self.table_resultados.setItem(row, 2, QTableWidgetItem(f"{kg_nec:.2f} kg"))
                self.table_resultados.setItem(row, 3, QTableWidgetItem(f"Bs. {costo:.2f}"))

        # Totales
        row = self.table_resultados.rowCount()
        self.table_resultados.insertRow(row)
        for i, val in enumerate(["TOTAL", "100.00%", f"{total_kg:.2f} kg", f"Bs. {costo_total:.2f}"]):
            item = QTableWidgetItem(val)
            f = item.font()
            f.setBold(True)
            item.setFont(f)
            item.setBackground(QBrush(QColor("#E8F8F5")))
            self.table_resultados.setItem(row, i, item)

    def mostrar_fracaso(self, resultado, ingredientes_disponibles, metas_min, metas_max, limites_por_ingrediente):
        self.table_resultados.setRowCount(0)
        self.btn_enviar.setEnabled(False)
        self._resultado_optimo = None
        
        # Diagnóstico humanizado
        diagnostico = self._diagnosticar_infactibilidad(ingredientes_disponibles, metas_min, metas_max, limites_por_ingrediente)
        
        msg = "❌ No es posible cumplir todas las metas con los ingredientes seleccionados.\n\n"
        if diagnostico['conflictos']:
            msg += "DIAGNÓSTICO:\n"
            for c in diagnostico['conflictos']:
                msg += f"  • {c}\n"
        if diagnostico['sugerencias']:
            msg += "\n💡 SUGERENCIAS:\n"
            for s in diagnostico['sugerencias']:
                msg += f"  • {s}\n"
        if not diagnostico['conflictos']:
            msg += f"Detalle técnico: {resultado.message}\n"
        
        self.lbl_mensaje_res.setText(msg)
        self.lbl_mensaje_res.setStyleSheet("color: #E74C3C; font-weight: bold; font-size: 13px;")

    def _diagnosticar_infactibilidad(self, ingredientes, metas_min, metas_max, limites):
        """Analiza por qué el solver falló y genera mensajes biológicos."""
        nutrientes = ['proteina', 'em_kcal', 'fibra', 'grasa', 'calcio', 'fosforo', 'lisina', 'metionina', 'colina_mgr']
        nombres_es = {
            'proteina': 'Proteína %', 'em_kcal': 'Energía Kcal/kg', 'fibra': 'Fibra %',
            'grasa': 'Grasa %', 'calcio': 'Calcio %', 'fosforo': 'Fósforo %',
            'lisina': 'Lisina %', 'metionina': 'Metionina %', 'colina_mgr': 'Colina mg/kg'
        }
        conflictos = []
        sugerencias = []
        
        for nut in nutrientes:
            vals = [ing.get(nut, 0) for ing in ingredientes]
            if not vals:
                continue
            # Rango alcanzable (promedio ponderado máx/mín posible)
            val_max_posible = max(vals)
            val_min_posible = min(vals)
            
            meta_min = metas_min.get(nut, 0)
            meta_max = metas_max.get(nut, 99999)
            
            nombre = nombres_es.get(nut, nut)
            
            if meta_min > 0 and val_max_posible < meta_min:
                conflictos.append(f"{nombre}: Mínimo requerido {meta_min:.1f}, pero el máximo alcanzable es {val_max_posible:.1f}")
            if meta_max < 99999 and val_min_posible > meta_max:
                conflictos.append(f"{nombre}: Máximo permitido {meta_max:.1f}, pero el mínimo posible es {val_min_posible:.1f}")
        
        # Sugerir ingredientes no seleccionados
        if conflictos:
            ids_sel = {ing['id'] for ing in ingredientes}
            for nut in nutrientes:
                meta_min = metas_min.get(nut, 0)
                vals_sel = [ing.get(nut, 0) for ing in ingredientes]
                if meta_min > 0 and vals_sel and max(vals_sel) < meta_min:
                    # Buscar ingredientes no seleccionados con alto valor
                    mejores = []
                    for ins in self.insumos_db:
                        if ins['id'] not in ids_sel and ins.get(nut, 0) > meta_min:
                            mejores.append((ins['nombre'], ins.get(nut, 0)))
                    mejores.sort(key=lambda x: x[1], reverse=True)
                    if mejores[:3]:
                        nombres = ', '.join([f"{n} ({v:.1f})" for n, v in mejores[:3]])
                        sugerencias.append(f"Para {nombres_es.get(nut, nut)}: prueba agregar {nombres}")
        
        return {'conflictos': conflictos, 'sugerencias': sugerencias}

    def enviar_a_formulacion(self):
        if self._resultado_optimo:
            self.enviar_formulacion.emit(self._resultado_optimo, self.spin_total_kg.value(), 'kg')
            QMessageBox.information(self, "Enviado", "Formulación enviada al Tab de Formulación principal. Ve allí para guardarla o exportarla a PDF.")

    # ---------------------------------------------------------------
    # Guardar formulación en el historial del Animal
    # ---------------------------------------------------------------
    def _guardar_como_formula(self):
        """Guarda el resultado actual como una nueva formulación en el historial."""
        if not self._resultado_optimo:
            QMessageBox.warning(self, "Sin resultado", "Primero debes calcular una formulación con éxito.")
            return

        nombre_form = self.combo_historial_inv.currentText().strip()
        if not nombre_form:
            QMessageBox.warning(self, "Error", "Ingresa un nombre para la fórmula.")
            self.combo_historial_inv.setFocus()
            return

        animal_idx = self.combo_animal_inv.currentIndex()
        animal_id = self.combo_animal_inv.itemData(animal_idx) if animal_idx >= 0 else None

        # Preparar datos para el gestor de BD
        total_kg = self.spin_total_kg.value()
        
        # Calcular nutricionales del resultado
        nuts = {k: 0.0 for k in ['proteina_total', 'em_total', 'fibra_total', 'grasa_total', 'calcio_total', 'fosforo_total', 'lisina_total', 'metionina_total', 'colina_total']}
        ingredientes_para_db = []
        
        for ins_id, kg_nec in self._resultado_optimo:
            ins = next((i for i in self.insumos_db if i['id'] == ins_id), None)
            if not ins: continue
            
            porc = (kg_nec / total_kg) * 100.0
            ingredientes_para_db.append({
                'insumo_id': ins_id,
                'nombre_insumo': ins['nombre'],
                'tanteo_kg': kg_nec,
                'porcentaje': porc,
                'precio_kg': ins['precio_kg'],
                'proteina_aportada': (ins['proteina'] * porc / 100),
                'em_aportada': (ins['em_kcal'] * porc / 100),
                'fibra_aportada': (ins['fibra'] * porc / 100),
                'grasa_aportada': (ins['grasa'] * porc / 100),
                'calcio_aportado': (ins['calcio'] * porc / 100),
                'fosforo_aportado': (ins['fosforo'] * porc / 100),
                'lisina_aportada': (ins['lisina'] * porc / 100),
                'metionina_aportada': (ins['metionina'] * porc / 100),
                'colina_aportada': (ins['colina_mgr'] * porc / 100),
            })
            
            for k_nut in nuts:
                key_ins = k_nut.replace('_total', '').replace('em', 'em_kcal').replace('colina', 'colina_mgr')
                nuts[k_nut] += (ins.get(key_ins, 0) * porc / 100)

        data_form = {
            'nombre': nombre_form,
            'animal_id': animal_id,
            'total_kg': total_kg,
            'modo': 'kilogramos',
            'tipo': 'optimizada',
            'resultados_nutricionales': nuts,
            'ingredientes': ingredientes_para_db,
            'costo_por_kg': sum(i['tanteo_kg']*i['precio_kg'] for i in ingredientes_para_db) / total_kg if total_kg > 0 else 0,
            'costo_por_tonelada': (sum(i['tanteo_kg']*i['precio_kg'] for i in ingredientes_para_db) / total_kg * 1000) if total_kg > 0 else 0,
            'instrucciones_preparacion': f"Formulación generada automáticamente para {nombre_form}.",
            'notas_generales': "Optimización por programación lineal."
        }

        fid = self.gestor_bd.guardar_formulacion(data_form)
        if fid:
            QMessageBox.information(self, "Éxito", f"Formulación '{nombre_form}' guardada correctamente en el historial.")
            self.formulacion_guardada.emit() # Refrescar otras tabs
            self._on_animal_inv_changed(animal_idx) # Refrescar combo local
        else:
            QMessageBox.critical(self, "Error", "No se pudo guardar la formulación en la base de datos.")
