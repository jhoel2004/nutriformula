# ui/tab_formulaciones.py
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
                              QPushButton, QListWidget, QListWidgetItem,
                              QTableWidget, QTableWidgetItem, QHeaderView,
                              QAbstractItemView, QLabel, QMessageBox, QGroupBox,
                              QInputDialog)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from app.database import (get_all_animales, insert_animal, update_animal, delete_animal,
                           GestorFormulacionesBD)
from ui.dialogs import AnimalDialog

BTN_EDIT  = "background-color:#2471A3;color:white;font-weight:bold;padding:6px 12px;border-radius:4px;border:none;"
BTN_DEL   = "background-color:#C0392B;color:white;font-weight:bold;padding:6px 12px;border-radius:4px;border:none;"
BTN_ADD   = "background-color:#2D7D46;color:white;font-weight:bold;padding:6px 12px;border-radius:4px;border:none;"

class TabFormulaciones(QWidget):
    """
    Nuevo Tab "Formulaciones".
    Panel Izquierdo: Gestión de Animales
    Panel Derecho: Historial de Formulaciones Guardadas
    """
    abrir_formulacion = pyqtSignal(dict) # Emite la formulación a abrir en TabCalcular

    def __init__(self):
        super().__init__()
        self.animales = []
        self._animal_id = None
        self.gestor_bd = GestorFormulacionesBD()
        self.setup_ui()
        self.load_animales()
        self.load_formulaciones()

    def setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)

        lbl_title = QLabel("📁 Gestión de Historial y Animales")
        lbl_title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        root.addWidget(lbl_title)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        root.addWidget(splitter, 1)

        # =======================================================
        # PANEL IZQ: Animales
        # =======================================================
        panel_izq = QWidget()
        lay_izq = QVBoxLayout(panel_izq)
        lay_izq.setContentsMargins(0, 0, 6, 0)

        group_animales = QGroupBox("Animales / Especies")
        lay_a = QVBoxLayout(group_animales)
        self.list_animales = QListWidget()
        self.list_animales.setAlternatingRowColors(True)
        self.list_animales.currentRowChanged.connect(self._on_animal_changed)
        lay_a.addWidget(self.list_animales)

        btn_row_a = QHBoxLayout()
        btn_add_a = QPushButton("Agregar"); btn_add_a.setStyleSheet(BTN_ADD); btn_add_a.clicked.connect(self.agregar_animal)
        btn_edit_a = QPushButton("Modificar"); btn_edit_a.setStyleSheet(BTN_EDIT); btn_edit_a.clicked.connect(self.editar_animal)
        btn_del_a = QPushButton("Eliminar"); btn_del_a.setStyleSheet(BTN_DEL); btn_del_a.clicked.connect(self.eliminar_animal)
        btn_row_a.addWidget(btn_add_a); btn_row_a.addWidget(btn_edit_a); btn_row_a.addWidget(btn_del_a)
        lay_a.addLayout(btn_row_a)
        lay_izq.addWidget(group_animales, 1)

        splitter.addWidget(panel_izq)

        # =======================================================
        # PANEL DER: Formulaciones (Historial)
        # =======================================================
        panel_der = QWidget()
        lay_der = QVBoxLayout(panel_der)
        lay_der.setContentsMargins(6, 0, 0, 0)

        # -- Historial de Formulaciones --
        group_form = QGroupBox("Historial de Fórmulas Guardadas")
        lay_f = QVBoxLayout(group_form)

        # Barra herramientas formulaciones
        toolbar_f = QHBoxLayout()
        self.btn_abrir_f = QPushButton("Abrir en Formulador")
        self.btn_abrir_f.setStyleSheet("background-color:#5BC0DE; color:white; font-weight:bold; padding:6px 12px; border-radius:4px;")
        self.btn_abrir_f.clicked.connect(self.abrir_formulacion_sel)

        self.btn_dup_f = QPushButton("⧉ Duplicar")
        self.btn_dup_f.setStyleSheet(BTN_EDIT)
        self.btn_dup_f.clicked.connect(self.duplicar_formulacion_sel)

        self.btn_del_f = QPushButton("🗑️ Eliminar")
        self.btn_del_f.setStyleSheet(BTN_DEL)
        self.btn_del_f.clicked.connect(self.eliminar_formulacion_sel)
        
        toolbar_f.addWidget(self.btn_abrir_f)
        toolbar_f.addWidget(self.btn_dup_f)
        toolbar_f.addWidget(self.btn_del_f)
        toolbar_f.addStretch()
        
        btn_refresh = QPushButton("🔄 Actualizar")
        btn_refresh.clicked.connect(self.load_formulaciones)
        toolbar_f.addWidget(btn_refresh)
        
        lay_f.addLayout(toolbar_f)

        self.table_form = QTableWidget()
        form_headers = ["ID", "Nombre", "Animal", "Tipo", "Costo/kg", "Total kg", "Fecha"]
        self.table_form.setColumnCount(len(form_headers))
        self.table_form.setHorizontalHeaderLabels(form_headers)
        self.table_form.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table_form.setAlternatingRowColors(True)
        self.table_form.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_form.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table_form.doubleClicked.connect(self.abrir_formulacion_sel)
        lay_f.addWidget(self.table_form)

        lay_der.addWidget(group_form, 1)
        splitter.addWidget(panel_der)

        splitter.setSizes([200, 900])

    # =================================================================
    # Lógica de Animales
    # =================================================================
    def load_animales(self):
        self.animales = get_all_animales()
        self.list_animales.clear()
        for a in self.animales:
            item = QListWidgetItem(a['nombre'])
            item.setData(Qt.ItemDataRole.UserRole, a['id'])
            self.list_animales.addItem(item)
        if self.animales:
            self.list_animales.setCurrentRow(0)

    def _on_animal_changed(self, row):
        if row < 0 or row >= len(self.animales):
            self._animal_id = None
            self.load_formulaciones()
            return
        
        self._animal_id = self.animales[row]['id']
        # Filtrar formulaciones por animal seleccionado
        self.load_formulaciones(self._animal_id)

    def agregar_animal(self):
        dlg = AnimalDialog(self)
        if dlg.exec():
            if insert_animal(dlg.get_data()): self.load_animales()

    def editar_animal(self):
        row = self.list_animales.currentRow()
        if row < 0: return
        animal = self.animales[row]
        dlg = AnimalDialog(self, animal_data=animal)
        if dlg.exec():
            if update_animal(animal['id'], dlg.get_data()): self.load_animales()

    def eliminar_animal(self):
        row = self.list_animales.currentRow()
        if row < 0: return
        animal = self.animales[row]
        res = QMessageBox.question(self, "Confirmar", f"¿Eliminar {animal['nombre']} y todo su historial?")
        if res == QMessageBox.StandardButton.Yes:
            if delete_animal(animal['id']): self.load_animales()

    # =================================================================
    # Lógica de Formulaciones
    # =================================================================
    def load_formulaciones(self, animal_id=None):
        formulaciones = self.gestor_bd.listar_formulaciones(animal_id=animal_id)
        self.table_form.setRowCount(0)
        for f in formulaciones:
            r = self.table_form.rowCount()
            self.table_form.insertRow(r)
            
            # ["ID", "Nombre", "Animal", "Tipo", "Costo/kg", "Total kg", "Fecha"]
            vals = [
                str(f['id']),
                f['nombre'],
                f['animal_nombre'] or '-',
                "⚡ Auto" if f['tipo'] == 'optimizada' else "✍️ Manual",
                f"${f['costo_por_kg']:.4f}",
                f"{f['total_kg']:.2f}",
                f['fecha_modificacion'][:16].replace('T', ' ')
            ]
            
            for c, v in enumerate(vals):
                cell = QTableWidgetItem(v)
                cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter if c != 1 else Qt.AlignmentFlag.AlignLeft)
                if c == 0: cell.setData(Qt.ItemDataRole.UserRole, f['id'])
                self.table_form.setItem(r, c, cell)

    def _get_form_id_sel(self):
        row = self.table_form.currentRow()
        if row < 0: return None
        return self.table_form.item(row, 0).data(Qt.ItemDataRole.UserRole)

    def abrir_formulacion_sel(self):
        fid = self._get_form_id_sel()
        if not fid:
            QMessageBox.warning(self, "Selección", "Selecciona una formulación de la tabla.")
            return
        form_data = self.gestor_bd.cargar_formulacion(fid)
        if form_data:
            self.abrir_formulacion.emit(form_data)

    def duplicar_formulacion_sel(self):
        fid = self._get_form_id_sel()
        if not fid: return
        row = self.table_form.currentRow()
        nombre_actual = self.table_form.item(row, 1).text()
        nuevo, ok = QInputDialog.getText(self, "Duplicar", "Nuevo nombre:", text=f"Copia de {nombre_actual}")
        if ok and nuevo.strip():
            self.gestor_bd.duplicar_formulacion(fid, nuevo.strip())
            self.load_formulaciones(self._animal_id)

    def eliminar_formulacion_sel(self):
        fid = self._get_form_id_sel()
        if not fid: return
        res = QMessageBox.question(self, "Confirmar", "¿Eliminar la formulación seleccionada de forma permanente?")
        if res == QMessageBox.StandardButton.Yes:
            self.gestor_bd.eliminar_formulacion(fid)
            self.load_formulaciones(self._animal_id)
