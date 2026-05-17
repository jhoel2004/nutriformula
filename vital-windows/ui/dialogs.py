# ui/dialogs.py
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLineEdit,
                              QComboBox, QPushButton, QHBoxLayout, QMessageBox,
                              QLabel, QSizePolicy)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

# ══════════════════════════════════════════════════════════════════════
# InsumoDialog — Agregar / Editar un insumo
# ══════════════════════════════════════════════════════════════════════
class InsumoDialog(QDialog):
    def __init__(self, parent=None, insumo_data=None):
        super().__init__(parent)
        self.insumo_data = insumo_data
        self.setWindowTitle("Agregar Insumo" if not insumo_data else "Editar Insumo")
        self.setMinimumWidth(500)
        self.setup_ui()
        if self.insumo_data:
            self.load_data()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.inputs = {}
        fields = [
            ("nombre",    "Nombre",         ""),
            ("proteina",  "Proteína %",     "0-100"),
            ("em_kcal",   "EM Kcal/kg",     "0-9000"),
            ("fibra",     "Fibra %",        "0-90"),
            ("grasa",     "Grasa %",        "0-100"),
            ("calcio",    "Calcio %",       "0-20"),
            ("fosforo",   "Fósforo %",      "0-20"),
            ("lisina",    "Lisina %",       "0-20"),
            ("metionina", "Metionina %",    "0-20"),
            ("colina_mgr","Colina mg/kg",   "0-5000"),
            ("precio_kg", "Precio/kg",      "0.00"),
        ]
        for key, label, placeholder in fields:
            inp = QLineEdit()
            inp.setPlaceholderText(placeholder)
            form.addRow(label, inp)
            self.inputs[key] = inp

        self.combo_categoria = QComboBox()
        self.combo_categoria.addItems([
            "Cereales", "Proteínas", "Grasas", "Subproductos",
            "Minerales", "Fibras", "Aditivos", "General"
        ])
        form.addRow("Categoría", self.combo_categoria)
        layout.addLayout(form)

        # ── Botones ───────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_guardar = QPushButton("💾 Guardar")
        btn_guardar.setStyleSheet(
            "background-color:#2D7D46;color:white;font-weight:bold;padding:8px 16px;border-radius:4px;")
        btn_guardar.clicked.connect(self.validate_and_save)
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.clicked.connect(self.reject)
        btn_row.addWidget(btn_guardar)
        btn_row.addWidget(btn_cancelar)
        layout.addLayout(btn_row)

    def load_data(self):
        for key, inp in self.inputs.items():
            inp.setText(str(self.insumo_data.get(key, "")))
        self.combo_categoria.setCurrentText(self.insumo_data.get('categoria', 'General'))

    def validate_and_save(self):
        try:
            nombre = self.inputs['nombre'].text().strip()
            if not nombre:
                raise ValueError("El nombre no puede estar vacío.")
            prot = float(self.inputs['proteina'].text() or 0)
            if not (0 <= prot <= 100):
                raise ValueError("La proteína debe estar entre 0 y 100%")
            em = float(self.inputs['em_kcal'].text() or 0)
            if not (0 <= em <= 9000):
                raise ValueError("La EM debe estar entre 0 y 9000 Kcal/kg")
            fibra = float(self.inputs['fibra'].text() or 0)
            if not (0 <= fibra <= 90):
                raise ValueError("La fibra debe estar entre 0 y 90%")
            self.accept()
        except ValueError as e:
            QMessageBox.warning(self, "Error de validación", str(e))

    def get_data(self):
        data = {}
        for key, inp in self.inputs.items():
            raw = inp.text().strip()
            if key == 'nombre':
                data[key] = raw
            else:
                try:
                    data[key] = float(raw) if raw else 0.0
                except ValueError:
                    data[key] = 0.0
        data['categoria'] = self.combo_categoria.currentText()
        return data



# ══════════════════════════════════════════════════════════════════════
# AnimalDialog — Agregar / Editar un animal
# ══════════════════════════════════════════════════════════════════════
class AnimalDialog(QDialog):

    def __init__(self, parent=None, animal_data=None):
        super().__init__(parent)
        self.animal_data = animal_data
        self.setWindowTitle("Agregar Animal" if not animal_data else "Editar Animal")
        self.setFixedSize(380, 200)
        self.setup_ui()
        if self.animal_data:
            self.load_data()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.inp_nombre = QLineEdit()
        self.inp_nombre.setPlaceholderText("Ej: Conejos, Patos, Tilapias...")

        form.addRow("Nombre del animal:", self.inp_nombre)
        layout.addLayout(form)

        btn_row = QHBoxLayout()
        btn_ok = QPushButton("💾 Guardar")
        btn_ok.setStyleSheet(
            "background-color:#2D7D46;color:white;font-weight:bold;padding:8px 16px;border-radius:4px;")
        btn_ok.clicked.connect(self.validate_and_save)
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_ok)
        btn_row.addWidget(btn_cancel)
        layout.addLayout(btn_row)

    def load_data(self):
        self.inp_nombre.setText(self.animal_data.get('nombre', ''))

    def validate_and_save(self):
        if not self.inp_nombre.text().strip():
            QMessageBox.warning(self, "Campo requerido", "El nombre no puede estar vacío.")
            return
        self.accept()

    def get_data(self):
        return {
            'nombre': self.inp_nombre.text().strip()
        }


# ══════════════════════════════════════════════════════════════════════
# ConfigDialog
# ══════════════════════════════════════════════════════════════════════
class ConfigDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configuración de Empresa")
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.empresa = QLineEdit("Mi Granja S.A.")
        self.tecnico = QLineEdit("Técnico Principal")
        self.moneda = QComboBox()
        self.moneda.addItems(["$", "Bs.", "S/.", "€"])

        form.addRow("Nombre de la empresa:", self.empresa)
        form.addRow("Técnico Responsable:", self.tecnico)
        form.addRow("Moneda:", self.moneda)
        layout.addLayout(form)

        btn_box = QHBoxLayout()
        btn_guardar = QPushButton("Guardar")
        btn_guardar.clicked.connect(self.accept)
        btn_box.addWidget(btn_guardar)
        layout.addLayout(btn_box)
