# app/main_window.py
import os
from PyQt6.QtWidgets import (QMainWindow, QStackedWidget, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QStatusBar, QMessageBox, QPushButton, QFrame,
                             QFileDialog, QInputDialog, QSizePolicy)
from PyQt6.QtGui import QAction, QKeySequence, QIcon
from PyQt6.QtCore import Qt, QTimer, QSize

from ui.tab_ingredientes import TabIngredientes
from ui.tab_calcular import TabCalcular
from ui.tab_formulaciones import TabFormulaciones
from ui.tab_graficas import TabGraficas
from ui.dialogs import ConfigDialog
from app.utils import resource_path

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VITAL v1.0 — Formulación de Raciones")
        self.setWindowIcon(QIcon(resource_path("logo.png")))
        self.setMinimumSize(1280, 800)
        self._formulacion_nombre = "Nueva Ración"

        self.setup_ui()

    # ================================================================
    # UI principal
    # ================================================================
    def setup_ui(self):
        # Contenedor principal horizontal
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── Barra Lateral (Sidebar) ──────────────────────────────────
        self.sidebar = QFrame()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setMouseTracking(True)
        self.sidebar.installEventFilter(self)
        
        self.sidebar.setStyleSheet("""
            QFrame#Sidebar {
                background-color: #1A1A2E;
                border-right: 1px solid #16213E;
            }
            QPushButton {
                background-color: transparent;
                color: #A0A0B8;
                text-align: left;
                padding: 15px 22px;
                font-size: 14px;
                font-weight: 500;
                border: none;
                border-left: 3px solid transparent;
            }
            QPushButton:hover {
                background-color: #16213E;
                color: #FFFFFF;
            }
            QPushButton:checked {
                background-color: #0F3460;
                color: #4ECCA3;
                font-weight: bold;
                border-left: 3px solid #4ECCA3;
            }
        """)
        self.sidebar.setFixedWidth(65) # Empieza colapsado
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(5)

        # Encabezado / Logo
        self.btn_toggle = QPushButton("  ☰")
        self.btn_toggle.setStyleSheet("font-size: 18px; padding: 20px 22px; color: #4ECCA3;")
        sidebar_layout.addWidget(self.btn_toggle)

        sidebar_layout.addSpacing(10)

        # Botones de navegación con nuevos iconos
        self.btn_ing = QPushButton("  📦")
        self.btn_ing.setToolTip("Insumos y Nutrientes")
        self.btn_ing.setCheckable(True)
        self.btn_ing.setChecked(True)
        self.btn_ing.clicked.connect(lambda: self._cambiar_pantalla(0, self.btn_ing))
        sidebar_layout.addWidget(self.btn_ing)

        self.btn_form = QPushButton("  🧪")
        self.btn_form.setToolTip("Formulación de Raciones")
        self.btn_form.setCheckable(True)
        self.btn_form.clicked.connect(lambda: self._cambiar_pantalla(1, self.btn_form))
        sidebar_layout.addWidget(self.btn_form)

        self.btn_graficas = QPushButton("  📈")
        self.btn_graficas.setToolTip("Análisis y Gráficas")
        self.btn_graficas.setCheckable(True)
        self.btn_graficas.clicked.connect(lambda: self._cambiar_pantalla(2, self.btn_graficas))
        sidebar_layout.addWidget(self.btn_graficas)

        self.btn_anim = QPushButton("  💾")
        self.btn_anim.setToolTip("Historial de Fórmulas")
        self.btn_anim.setCheckable(True)
        self.btn_anim.clicked.connect(lambda: self._cambiar_pantalla(3, self.btn_anim))
        sidebar_layout.addWidget(self.btn_anim)

        self.nav_buttons = [self.btn_ing, self.btn_form, self.btn_graficas, self.btn_anim]

        sidebar_layout.addStretch()
        
        main_layout.addWidget(self.sidebar)

        # ── Contenido Principal (StackedWidget) ───────────────────────
        self.stacked_widget = QStackedWidget()
        
        self.tab_ingredientes = TabIngredientes()
        self.tab_calcular = TabCalcular()
        self.tab_graficas = TabGraficas()
        self.tab_formulaciones = TabFormulaciones()

        self.stacked_widget.addWidget(self.tab_ingredientes)     # index 0
        self.stacked_widget.addWidget(self.tab_calcular)         # index 1
        self.stacked_widget.addWidget(self.tab_graficas)         # index 2
        self.stacked_widget.addWidget(self.tab_formulaciones)    # index 3

        main_layout.addWidget(self.stacked_widget, 1)

        # Cargar insumos
        self.tab_calcular.pagina_formular.load_insumos()

        self.stacked_widget.currentChanged.connect(self._on_tab_changed)

        # Conectar abrir formulación desde bd
        self.tab_formulaciones.abrir_formulacion.connect(self._abrir_formulacion_desde_bd)

        # Conectar tab_formulacion → actualizar gráficas en tiempo real
        self.tab_calcular.pagina_formular.table_tanteo.itemChanged.connect(self._sincronizar_graficas)
        # También sincronizar al cambiar al tab de gráficas
        self.stacked_widget.currentChanged.connect(self._on_tab_graficas_visible)

        # Conectar el autoformulador para recibir los resultados
        self.tab_calcular.enviar_formulacion.connect(self._recibir_autoformulacion)

        # ── Menú ──────────────────────────────────────────────────────
        self._build_menu()

        # ── Barra de estado ───────────────────────────────────────────
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        self.status_left   = QLabel(f"Formulación: {self._formulacion_nombre}")
        self.status_center = QLabel("Insumos activos: 0 | Total: 0 kg")
        self.status_right  = QLabel("Especie: — | Costo estimado: $0.00")
        self.statusbar.addWidget(self.status_left,   1)
        self.statusbar.addWidget(self.status_center, 1)
        self.statusbar.addWidget(self.status_right,  1)

    def _recibir_autoformulacion(self, resultado_optimo, total_kg, modo):
        """Recibe una formulación del optimizador y la carga en el tab de formulación."""
        self.stacked_widget.setCurrentIndex(1)
        self.tab_calcular.btn_formular.setChecked(True)
        self.tab_calcular._cambiar_modo(0)
        self.tab_calcular.pagina_formular._cargar_desde_optimizador(resultado_optimo)

    def _build_menu(self):
        menubar = self.menuBar()
        menu_archivo = menubar.addMenu("Archivo")

        act_pdf = QAction("Exportar PDF...", self)
        act_pdf.setShortcut("Ctrl+P")
        act_pdf.triggered.connect(self._exportar_pdf)
        menu_archivo.addAction(act_pdf)

        act_excel = QAction("Exportar Excel...", self)
        act_excel.setShortcut("Ctrl+E")
        act_excel.triggered.connect(self._exportar_excel)
        menu_archivo.addAction(act_excel)

    def eventFilter(self, obj, event):
        if obj == self.sidebar:
            # Detectar entrada y salida del ratón para expandir/colapsar
            if event.type() == event.Type.Enter:
                self._expand_sidebar()
            elif event.type() == event.Type.Leave:
                self._collapse_sidebar()
        return super().eventFilter(obj, event)

    def _expand_sidebar(self):
        self.sidebar.setFixedWidth(200)
        self.btn_toggle.setText("  ☰  Menú")
        self.btn_ing.setText("  📦  Insumos")
        self.btn_form.setText("  🧪  Formular")
        self.btn_graficas.setText("  📈  Gráficas")
        self.btn_anim.setText("  💾  Historial")

    def _collapse_sidebar(self):
        self.sidebar.setFixedWidth(65)
        self.btn_toggle.setText("  ☰")
        self.btn_ing.setText("  📦")
        self.btn_form.setText("  🧪")
        self.btn_graficas.setText("  📈")
        self.btn_anim.setText("  💾")

    def _toggle_sidebar(self):
        # Mantenemos por compatibilidad, pero ahora es automático
        if self.sidebar.width() == 200:
            self._collapse_sidebar()
        else:
            self._expand_sidebar()

    def _cambiar_pantalla(self, index, boton_presionado):
        self.stacked_widget.setCurrentIndex(index)
        for btn in self.nav_buttons:
            btn.setChecked(btn == boton_presionado)
        if index == 1:
            self.tab_calcular.pagina_formular.reload_animales()
        if index == 3:
            self.tab_formulaciones.load_formulaciones()
            self.tab_formulaciones.load_animales()

    # ================================================================
    # Carga de Formulación BD
    # ================================================================
    def _abrir_formulacion_desde_bd(self, form_data):
        self.tab_calcular.cargar_formulacion_desde_bd(form_data)
        self._cambiar_pantalla(1, self.btn_form)
        self._formulacion_nombre = form_data.get('nombre', 'Formulación')
        self.status_left.setText(f"Formulación: {self._formulacion_nombre}")
        self.statusbar.showMessage(f"✅ Formulación cargada: {self._formulacion_nombre}", 4000)

    def _exportar_pdf(self):
        ruta, _ = QFileDialog.getSaveFileName(
            self, "Exportar PDF", f"{self._formulacion_nombre}.pdf",
            "Archivos PDF (*.pdf)"
        )
        if not ruta:
            return
        try:
            tab = self.tab_calcular.pagina_formular
            # Obtener datos de cálculo actuales
            insumos_sel, tanteos = tab._get_seleccionados()
            if not insumos_sel:
                QMessageBox.warning(self, "Sin datos", "Agrega y selecciona insumos en la Formulación primero.")
                return
            from app.calculator import calcular_resultados
            modo = 'kg'
            res  = calcular_resultados(insumos_sel, tanteos, modo)
            especie = tab.combo_animal.currentText()
            instrucciones = tab.text_instrucciones.toPlainText()

            # Construir dict analisis desde la fórmula de referencia seleccionada
            analisis = {}
            f_ref = tab._formula_comparar or {}
            nutrientes_cols = ['proteina', 'em_kcal', 'fibra', 'grasa', 'calcio', 'fosforo', 'lisina', 'metionina', 'colina_mgr']

            nut_key_map = {
                'proteina': 'proteina_min', 'em_kcal': 'em_min', 'fibra': 'fibra_max',
                'grasa': 'grasa_max', 'calcio': 'calcio_min', 'fosforo': 'fosforo_min',
                'lisina': 'lisina_min', 'metionina': 'metionina_min', 'colina_mgr': 'colina_min'
            }
            nut_max_map = {'calcio': 'calcio_max', 'fibra': 'fibra_max', 'grasa': 'grasa_max'}

            for nut in nutrientes_cols:
                aportado = res['totales'].get(nut, 0)
                min_v = f_ref.get(nut_key_map.get(nut, ''), 0)
                max_v = f_ref.get(nut_max_map.get(nut, ''), None)
                analisis[nut.upper()] = (aportado, min_v, max_v)
                
            datos_pdf = {
                "especie": especie,
                "ingredientes": [{"nombre": ins['nombre'], "tanteo": p['porcentaje']} for ins, p in zip(insumos_sel, res['resultados_por_insumo'])],
                "instrucciones": instrucciones,
                "analisis": analisis,
                "totales": res['totales'],
                "insumos_sel": insumos_sel,
                "tanteos": tanteos,
                "modo": modo
            }
            
            Exporter.exportar_pdf_completo(ruta, datos_pdf)
            self.statusbar.showMessage(f"✅ PDF exportado: {ruta}", 5000)
            QMessageBox.information(self, "PDF Exportado", f"Reporte guardado en:\n{ruta}")
        except Exception as e:
            QMessageBox.critical(self, "Error al exportar PDF", str(e))

    def _exportar_excel(self):
        ruta, _ = QFileDialog.getSaveFileName(
            self, "Exportar Excel", f"{self._formulacion_nombre}.xlsx",
            "Archivos Excel (*.xlsx)"
        )
        if not ruta:
            return
        try:
            tab = self.tab_calcular.pagina_formular
            insumos_sel, tanteos = tab._get_seleccionados()
            if not insumos_sel:
                QMessageBox.warning(self, "Sin datos", "Agrega y selecciona insumos en la Formulación primero.")
                return
            from app.calculator import calcular_resultados
            from app.database import get_all_insumos
            modo = 'kg'
            res  = calcular_resultados(insumos_sel, tanteos, modo)
            Exporter.export_excel(ruta, get_all_insumos(), res['resultados_por_insumo'], res['totales'])
            self.statusbar.showMessage(f"✅ Excel exportado: {ruta}", 5000)
            QMessageBox.information(self, "Excel Exportado", f"Archivo guardado en:\n{ruta}")
        except Exception as e:
            QMessageBox.critical(self, "Error al exportar Excel", str(e))

    def _abrir_configuracion(self):
        dlg = ConfigDialog(self)
        dlg.exec()

    def _mostrar_ayuda(self):
        QMessageBox.information(
            self, "❓ Guía Rápida — VITAL",
            "<b>VITAL</b> — Guía de Uso Rápido<br><br>"
            "<b>📋 Ingredientes:</b> Ver, agregar, editar y eliminar insumos de la base de datos.<br><br>"
            "<b>🧮 Formulación:</b><br>"
            "1. Selecciona la especie animal.<br>"
            "2. Marca el ☑ de cada insumo que quieras incluir.<br>"
            "3. Escribe el tanteo (kg o %) en la columna <i>Tanteo</i>.<br>"
            "4. Los resultados se actualizan <b>automáticamente</b> en el panel derecho.<br>"
            "5. El semáforo (🟢🟡🔴) indica si cumple los requerimientos de la especie.<br><br>"
            "<b>📤 Exportar:</b> Usa la barra de herramientas para guardar PDF o Excel.<br><br>"
            "<b>Atajos:</b> Ctrl+N (nueva ración) | Ctrl+S (guardar) | Ctrl+P (PDF) | Ctrl+E (Excel)"
        )

    # ================================================================
    # Sincronización de Tabs
    # ================================================================
    def _on_tab_changed(self, index):
        pass

    def _sincronizar_graficas(self):
        """Envía los datos actuales de formulación al tab de Gráficas."""
        tab_f = self.tab_calcular.pagina_formular
        if not hasattr(tab_f, 'insumos_db') or not hasattr(tab_f, 'table_tanteo'):
            return
        from app.calculator import calcular_resultados
        insumos_sel, tanteos = [], []
        for row in range(tab_f.table_tanteo.rowCount()):
            t_item = tab_f.table_tanteo.item(row, 1)
            try:
                val = float(t_item.text().replace(',', '.')) if t_item else 0
            except ValueError:
                val = 0
            if val > 0:
                insumos_sel.append(tab_f.insumos_db[row])
                tanteos.append(val)
        if not insumos_sel:
            self.tab_graficas.update_datos([], {}, {})
            return
        modo = 'kg'
        resultado = calcular_resultados(insumos_sel, tanteos, modo)
        if resultado:
            ings_graf = []
            for item in resultado['resultados_por_insumo']:
                ing_db = next((i for i in insumos_sel if i['nombre'] == item['nombre']), {})
                ings_graf.append({
                    **item,
                    **{k: ing_db.get(k, 0) for k in
                       ['proteina', 'fibra', 'grasa', 'calcio', 'fosforo', 'lisina', 'metionina', 'colina_mgr']}
                })
            reqs = {}
            if tab_f._formula_comparar:
                et = tab_f._formula_comparar
                reqs = {
                    'proteina_min': et.get('proteina_min', 0),
                    'em_min': et.get('em_min', 0),
                    'fibra_max': et.get('fibra_max', 0),
                    'grasa_max': et.get('grasa_max', 0),
                    'calcio_min': et.get('calcio_min', 0),
                    'fosforo_min': et.get('fosforo_min', 0),
                    'lisina_min': et.get('lisina_min', 0),
                    'metionina_min': et.get('metionina_min', 0),
                }
            comparativa_nombre = tab_f.combo_comparar.currentText() if hasattr(tab_f, 'combo_comparar') else ""
            animal_id = tab_f.combo_animal.currentData() if hasattr(tab_f, 'combo_animal') else None
            
            self.tab_graficas.update_datos(ings_graf, resultado['totales'], reqs, comparativa_nombre,
                                          animal_id=animal_id)

    def _on_tab_graficas_visible(self, idx):
        """Cuando el usuario navega al tab de Gráficas, sincronizar datos."""
        if idx == 2:
            self._sincronizar_graficas()

    # ================================================================
    # Cierre
    # ================================================================
    def closeEvent(self, event):
        event.accept()
