# ui/tab_economia.py — Módulo de Análisis Económico VITAL v2.0
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QTableWidget, QTableWidgetItem, QLabel,
                             QHeaderView, QAbstractItemView, QComboBox,
                             QDoubleSpinBox, QGroupBox, QFormLayout, QMessageBox,
                             QScrollArea, QFrame)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from app.database import GestorFormulacionesBD, get_all_insumos, get_config_empresa, listar_lotes, get_connection
from app.config import ESTILO_TABLA, COLORS, BTN_PRIMARY, BTN_ACCENT
import sqlite3

class TabEconomia(QWidget):
    def __init__(self, db=None):
        super().__init__()
        self.gestor = GestorFormulacionesBD()
        self.moneda = get_config_empresa('moneda', '$')
        self.setup_ui()

    def setup_ui(self):
        # Usar QScrollArea porque hay mucho contenido
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        main_widget = QWidget()
        layout = QVBoxLayout(main_widget)
        layout.setContentsMargins(15, 15, 15, 10)

        titulo = QLabel("💰 Análisis Económico")
        titulo.setStyleSheet(f"font-size:18px;font-weight:bold;color:{COLORS['text']};padding:5px 0;")
        layout.addWidget(titulo)

        # ── WIDGETS DE RESUMEN (KPIs) ───────────────────────────────────
        kpi_layout = QHBoxLayout()
        self.kpi_formula_barata = self._crear_kpi("Fórmula más barata", "—")
        self.kpi_formula_cara = self._crear_kpi("Fórmula más cara", "—")
        self.kpi_ingrediente_caro = self._crear_kpi("Insumo más costoso", "—")
        self.kpi_ahorro = self._crear_kpi("Costo Promedio", "—")
        kpi_layout.addWidget(self.kpi_formula_barata)
        kpi_layout.addWidget(self.kpi_formula_cara)
        kpi_layout.addWidget(self.kpi_ingrediente_caro)
        kpi_layout.addWidget(self.kpi_ahorro)
        layout.addLayout(kpi_layout)

        # ── SECCIÓN 3: Simulador de variación de precios ─────────────────────────────────────
        sim_group = QGroupBox("🔄 Simulador de Variación de Precios")
        sim_group.setStyleSheet(f"QGroupBox{{color:{COLORS['text']};font-weight:bold;border:1px solid {COLORS['bg_border']};border-radius:6px;padding:10px;margin-top:8px;}}")
        sim_layout = QVBoxLayout(sim_group)
        
        sim_controls = QHBoxLayout()
        self.combo_insumo_sim = QComboBox()
        self.combo_insumo_sim.setMinimumWidth(200)
        self.spin_nuevo_precio = QDoubleSpinBox()
        self.spin_nuevo_precio.setRange(0, 99999)
        self.spin_nuevo_precio.setDecimals(2)
        self.spin_nuevo_precio.setPrefix(f"{self.moneda} ")
        self.btn_simular = QPushButton("Simular Impacto")
        self.btn_simular.setStyleSheet(BTN_ACCENT)
        self.btn_simular.clicked.connect(self.simular_cambio_precio)

        sim_controls.addWidget(QLabel("Insumo a modificar:"))
        sim_controls.addWidget(self.combo_insumo_sim, 2)
        sim_controls.addWidget(QLabel("Nuevo precio:"))
        sim_controls.addWidget(self.spin_nuevo_precio)
        sim_controls.addWidget(self.btn_simular)
        sim_layout.addLayout(sim_controls)

        self.lbl_resultado_sim = QLabel("Selecciona un insumo y cambia su precio para ver el impacto en las formulaciones guardadas.")
        self.lbl_resultado_sim.setStyleSheet(f"color:{COLORS['text_dim']};padding:4px;")
        sim_layout.addWidget(self.lbl_resultado_sim)

        self.table_simulacion = QTableWidget()
        sim_headers = ["Formulación", "Costo Actual", "Costo Simulado", "Diferencia"]
        self.table_simulacion.setColumnCount(len(sim_headers))
        self.table_simulacion.setHorizontalHeaderLabels(sim_headers)
        self.table_simulacion.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_simulacion.setAlternatingRowColors(True)
        self.table_simulacion.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table_simulacion.setStyleSheet(ESTILO_TABLA)
        self.table_simulacion.setMaximumHeight(150)
        sim_layout.addWidget(self.table_simulacion)
        
        layout.addWidget(sim_group)

        # ── Gráficas y Tablas ───────────────────────
        graficas_layout = QHBoxLayout()
        
        # Historial de costo por animal
        hist_group = QGroupBox("Costo Histórico por Animal")
        hist_group.setStyleSheet(f"QGroupBox{{color:{COLORS['text']};font-weight:bold;border:1px solid {COLORS['bg_border']};border-radius:6px;padding:10px;margin-top:8px;}}")
        hist_layout = QVBoxLayout(hist_group)
        self.combo_animal_hist = QComboBox()
        self.combo_animal_hist.currentIndexChanged.connect(self.actualizar_grafica_historico)
        hist_layout.addWidget(self.combo_animal_hist)
        
        self.fig_hist = Figure(figsize=(5, 3), dpi=100)
        self.fig_hist.patch.set_facecolor(COLORS['bg_surface'])
        self.canvas_hist = FigureCanvas(self.fig_hist)
        self.ax_hist = self.fig_hist.add_subplot(111)
        hist_layout.addWidget(self.canvas_hist)
        graficas_layout.addWidget(hist_group)

        # Resumen mensual de lotes
        mes_group = QGroupBox("Resumen Mensual de Producción")
        mes_group.setStyleSheet(f"QGroupBox{{color:{COLORS['text']};font-weight:bold;border:1px solid {COLORS['bg_border']};border-radius:6px;padding:10px;margin-top:8px;}}")
        mes_layout = QVBoxLayout(mes_group)
        self.fig_mes = Figure(figsize=(5, 3), dpi=100)
        self.fig_mes.patch.set_facecolor(COLORS['bg_surface'])
        self.canvas_mes = FigureCanvas(self.fig_mes)
        self.ax_mes = self.fig_mes.add_subplot(111)
        mes_layout.addWidget(self.canvas_mes)
        graficas_layout.addWidget(mes_group)

        layout.addLayout(graficas_layout)

        # ── Botones ──────────────────────────────────────────────────
        btn_layout = QHBoxLayout()
        btn_refresh = QPushButton("🔄 Actualizar Datos")
        btn_refresh.setStyleSheet(BTN_PRIMARY)
        btn_refresh.clicked.connect(self.load_data)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_refresh)
        layout.addLayout(btn_layout)

        scroll.setWidget(main_widget)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)

    def _crear_kpi(self, titulo, valor):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 8, 10, 8)
        widget.setStyleSheet(f"background:{COLORS['bg_surface']};border-radius:8px;border:1px solid {COLORS['bg_border']};")

        lbl_titulo = QLabel(titulo)
        lbl_titulo.setStyleSheet(f"color:{COLORS['text_dim']};font-size:11px;font-weight:bold;border:none;")
        lbl_titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lbl_valor = QLabel(valor)
        lbl_valor.setObjectName("kpi_value")
        lbl_valor.setStyleSheet(f"color:{COLORS['primary_light']};font-size:18px;font-weight:bold;border:none;")
        lbl_valor.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_valor.setWordWrap(True)

        layout.addWidget(lbl_titulo)
        layout.addWidget(lbl_valor)
        return widget

    def _set_kpi(self, widget, valor):
        lbl = widget.findChild(QLabel, "kpi_value")
        if lbl:
            lbl.setText(str(valor))

    def load_data(self):
        self.moneda = get_config_empresa('moneda', '$')
        formulaciones = self.gestor.listar_formulaciones()
        insumos = get_all_insumos()

        # KPIs
        if formulaciones:
            costos = [(f, f.get('costo_por_kg', 0) or 0) for f in formulaciones if (f.get('costo_por_kg') or 0) > 0]
            if costos:
                f_barata = min(costos, key=lambda x: x[1])
                f_cara = max(costos, key=lambda x: x[1])
                promedio = sum(x[1] for x in costos) / len(costos)
                
                self._set_kpi(self.kpi_formula_barata, f"{self.moneda}{f_barata[1]:.2f}\n({f_barata[0]['nombre'][:10]}...)")
                self._set_kpi(self.kpi_formula_cara, f"{self.moneda}{f_cara[1]:.2f}\n({f_cara[0]['nombre'][:10]}...)")
                self._set_kpi(self.kpi_ahorro, f"{self.moneda}{promedio:.2f}/kg")
        
        if insumos:
            caro = max(insumos, key=lambda x: x.get('precio_kg', 0) or 0)
            self._set_kpi(self.kpi_ingrediente_caro, f"{caro['nombre'][:18]}\n({self.moneda}{caro.get('precio_kg', 0):.2f})")

        # Llenar combo del simulador
        current_sim = self.combo_insumo_sim.currentData()
        self.combo_insumo_sim.clear()
        for ins in insumos:
            self.combo_insumo_sim.addItem(ins['nombre'], ins['id'])
        if current_sim:
            idx = self.combo_insumo_sim.findData(current_sim)
            if idx >= 0:
                self.combo_insumo_sim.setCurrentIndex(idx)

        # Llenar combo animal histórico
        self._cargar_animales_hist()
        self.actualizar_grafica_historico()
        self.actualizar_grafica_mensual()

    def _cargar_animales_hist(self):
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT id, nombre FROM animales ORDER BY nombre')
            animales = cursor.fetchall()
            conn.close()
            
            self.combo_animal_hist.blockSignals(True)
            self.combo_animal_hist.clear()
            self.combo_animal_hist.addItem("Todas las especies", None)
            for a_id, a_nombre in animales:
                self.combo_animal_hist.addItem(a_nombre, a_id)
            self.combo_animal_hist.blockSignals(False)
        except Exception as e:
            print(f"Error cargando animales: {e}")

    def actualizar_grafica_historico(self):
        animal_id = self.combo_animal_hist.currentData()
        formulaciones = self.gestor.listar_formulaciones(animal_id=animal_id)
        
        self.ax_hist.clear()
        self.ax_hist.set_facecolor(COLORS['bg_dark'])
        
        if not formulaciones:
            self.ax_hist.text(0.5, 0.5, "No hay datos", ha='center', va='center', color=COLORS['text_dim'])
        else:
            # Ordenar por fecha ascendente para la gráfica
            formulaciones.sort(key=lambda x: x.get('fecha_modificacion', ''))
            fechas = []
            costos = []
            nombres = []
            for f in formulaciones:
                f_date = f.get('fecha_modificacion', '')[:10]
                c = f.get('costo_por_kg', 0) or 0
                if c > 0:
                    fechas.append(f_date)
                    costos.append(c)
                    nombres.append(f['nombre'])
            
            if fechas:
                self.ax_hist.plot(range(len(fechas)), costos, marker='o', color=COLORS['primary_light'], linestyle='-')
                self.ax_hist.set_xticks(range(len(fechas)))
                # Rotar fechas si son muchas
                labels = [d[5:] for d in fechas] # MM-DD
                self.ax_hist.set_xticklabels(labels, rotation=45, color=COLORS['text'])
                self.ax_hist.tick_params(axis='y', colors=COLORS['text'])
                self.ax_hist.set_ylabel(f'Costo ({self.moneda}/kg)', color=COLORS['text_dim'])
                self.ax_hist.grid(True, linestyle='--', alpha=0.3, color=COLORS['bg_border'])
            else:
                 self.ax_hist.text(0.5, 0.5, "Costo $0", ha='center', va='center', color=COLORS['text_dim'])

        self.fig_hist.tight_layout()
        self.canvas_hist.draw()

    def actualizar_grafica_mensual(self):
        self.ax_mes.clear()
        self.ax_mes.set_facecolor(COLORS['bg_dark'])
        
        lotes = listar_lotes()
        if not lotes:
            self.ax_mes.text(0.5, 0.5, "No hay lotes producidos", ha='center', va='center', color=COLORS['text_dim'])
        else:
            meses_totales = {}
            for lote in lotes:
                mes = lote.get('fecha', '')[:7] # YYYY-MM
                kg = lote.get('cantidad_kg', 0) or 0
                meses_totales[mes] = meses_totales.get(mes, 0) + kg
            
            # Ordenar por mes
            meses_ordenados = sorted(meses_totales.keys())
            kg_por_mes = [meses_totales[m] for m in meses_ordenados]
            
            bars = self.ax_mes.bar(meses_ordenados, kg_por_mes, color=COLORS['accent'])
            self.ax_mes.set_ylabel('Producción (kg)', color=COLORS['text_dim'])
            self.ax_mes.tick_params(axis='x', colors=COLORS['text'], rotation=45)
            self.ax_mes.tick_params(axis='y', colors=COLORS['text'])
            self.ax_mes.grid(True, axis='y', linestyle='--', alpha=0.3, color=COLORS['bg_border'])

        self.fig_mes.tight_layout()
        self.canvas_mes.draw()

    def simular_cambio_precio(self):
        insumo_id = self.combo_insumo_sim.currentData()
        if not insumo_id:
            return
        nombre = self.combo_insumo_sim.currentText()
        nuevo_precio = self.spin_nuevo_precio.value()

        insumo_data = next((i for i in get_all_insumos() if i['id'] == insumo_id), None)
        if not insumo_data:
            return
        precio_actual = insumo_data.get('precio_kg', 0)
        
        diff_precio = nuevo_precio - precio_actual
        pct = (diff_precio / precio_actual * 100) if precio_actual > 0 else 0
        color = COLORS['danger'] if diff_precio > 0 else COLORS['primary_light']
        signo = "+" if diff_precio > 0 else ""
        
        self.lbl_resultado_sim.setText(
            f"<span style='color:{color};font-weight:bold;'>"
            f"Impacto por cambio de {signo}{self.moneda}{diff_precio:.2f}/kg ({signo}{pct:.1f}%) en «{nombre}»"
            f"</span> — Precio actual: {self.moneda}{precio_actual:.2f}"
        )

        # Buscar todas las formulaciones que contengan este insumo y simular
        try:
            conn = get_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Formulaciones con ese insumo
            cursor.execute('''
                SELECT DISTINCT f.id, f.nombre, f.costo_por_kg, fi.tanteo_kg, fi.precio_kg, f.total_kg
                FROM formulaciones f
                JOIN formulacion_ingredientes fi ON f.id = fi.formulacion_id
                WHERE fi.insumo_id = ?
            ''', (insumo_id,))
            forms = cursor.fetchall()
            conn.close()
            
            self.table_simulacion.setRowCount(0)
            for f in forms:
                form_id = f['id']
                form_nombre = f['nombre']
                costo_actual = f['costo_por_kg'] or 0
                tanteo_kg = f['tanteo_kg'] or 0
                total_kg = f['total_kg'] or 1 # evitar div0
                
                # Calcular el impacto en la formula (costo extra total / total kg de la formula)
                # O si calculamos todo de nuevo:
                # El costo total era = sum(precio*kg). El nuevo costo = costo_total_antiguo + (nuevo_precio - precio_actual)*tanteo_kg
                impacto_total = diff_precio * tanteo_kg
                impacto_por_kg = impacto_total / total_kg if total_kg > 0 else 0
                
                costo_simulado = costo_actual + impacto_por_kg
                diff_form = costo_simulado - costo_actual
                
                row = self.table_simulacion.rowCount()
                self.table_simulacion.insertRow(row)
                
                items = [
                    form_nombre,
                    f"{self.moneda}{costo_actual:.4f}",
                    f"{self.moneda}{costo_simulado:.4f}",
                    f"{'+' if diff_form>0 else ''}{self.moneda}{diff_form:.4f}"
                ]
                
                for col, val in enumerate(items):
                    item = QTableWidgetItem(str(val))
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    if col == 3:
                        item.setForeground(QColor(COLORS['danger'] if diff_form > 0 else COLORS['primary_light']))
                    self.table_simulacion.setItem(row, col, item)
                    
        except Exception as e:
            print(f"Error en simulador: {e}")
            QMessageBox.warning(self, "Error", f"Error calculando simulación: {e}")
