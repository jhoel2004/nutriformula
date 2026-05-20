# ui/tab_inventario.py — Módulo de Inventario VITAL v2.0
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QTableWidget, QTableWidgetItem, QLineEdit,
                             QLabel, QHeaderView, QMessageBox, QComboBox,
                             QAbstractItemView, QDialog, QFormLayout,
                             QDoubleSpinBox, QDialogButtonBox, QSpinBox)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

from app.database import (get_all_insumos, actualizar_stock, get_historial_precios,
                           get_insumos_stock_critico, insertar_alerta)
from app.config import ESTILO_TABLA, COLORS, BTN_PRIMARY, BTN_DANGER, BTN_WARNING, BTN_ACCENT


class DialogoEntradaStock(QDialog):
    """Diálogo para registrar entrada de stock."""
    def __init__(self, insumo_nombre, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Entrada de Stock — {insumo_nombre}")
        self.setMinimumWidth(350)
        layout = QFormLayout(self)

        self.spin_cantidad = QDoubleSpinBox()
        self.spin_cantidad.setRange(0.01, 99999)
        self.spin_cantidad.setSuffix(" kg")
        self.spin_cantidad.setDecimals(2)

        self.spin_precio = QDoubleSpinBox()
        self.spin_precio.setRange(0, 99999)
        self.spin_precio.setDecimals(2)

        self.txt_proveedor = QLineEdit()
        self.txt_proveedor.setPlaceholderText("Nombre del proveedor (opcional)")

        layout.addRow("Cantidad:", self.spin_cantidad)
        layout.addRow("Precio/kg:", self.spin_precio)
        layout.addRow("Proveedor:", self.txt_proveedor)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addRow(btns)

    def get_data(self):
        return {
            'cantidad': self.spin_cantidad.value(),
            'precio_kg': self.spin_precio.value(),
            'proveedor': self.txt_proveedor.text().strip()
        }


class TabInventario(QWidget):
    def __init__(self, db=None):
        super().__init__()
        self.insumos = []
        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 10)

        # ── Título ───────────────────────────────────────────────────
        titulo = QLabel("📦 Inventario de Insumos")
        titulo.setStyleSheet(f"font-size:18px;font-weight:bold;color:{COLORS['text']};padding:5px 0;")
        layout.addWidget(titulo)

        # ── Barra de controles ───────────────────────────────────────
        top = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Buscar insumo...")
        self.search_input.textChanged.connect(self.filter_table)

        self.combo_estado = QComboBox()
        self.combo_estado.addItems(["Todos", "Con stock", "Stock crítico", "Sin stock"])
        self.combo_estado.currentTextChanged.connect(self.filter_table)

        self.btn_entrada = QPushButton("📥 Entrada Stock")
        self.btn_entrada.setStyleSheet(BTN_PRIMARY)
        self.btn_entrada.clicked.connect(self.registrar_entrada)

        self.btn_historial = QPushButton("📊 Historial Precios")
        self.btn_historial.setStyleSheet(BTN_ACCENT)
        self.btn_historial.clicked.connect(self.ver_historial)

        top.addWidget(self.search_input, 2)
        top.addWidget(self.combo_estado)
        top.addWidget(self.btn_entrada)
        top.addWidget(self.btn_historial)
        layout.addLayout(top)

        # ── Tabla ────────────────────────────────────────────────────
        self.table = QTableWidget()
        headers = ["Insumo", "Stock (kg)", "Precio/kg", "Precio Ant.", "Proveedor", "Categoría"]
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setStyleSheet(ESTILO_TABLA)
        layout.addWidget(self.table)

        # ── Panel de alertas ─────────────────────────────────────────
        self.lbl_alertas = QLabel()
        self.lbl_alertas.setStyleSheet(f"padding:8px;background:{COLORS['semaforo_warn']};border-radius:6px;color:{COLORS['warning']};")
        layout.addWidget(self.lbl_alertas)

        self.lbl_count = QLabel()
        self.lbl_count.setStyleSheet(f"color:{COLORS['text_dim']};")
        layout.addWidget(self.lbl_count)

    def load_data(self):
        self.insumos = get_all_insumos()
        self.filter_table()
        # Verificar alertas de stock crítico
        criticos = get_insumos_stock_critico()
        if criticos:
            nombres = ', '.join(i['nombre'] for i in criticos[:5])
            extra = f" (+{len(criticos)-5} más)" if len(criticos) > 5 else ""
            self.lbl_alertas.setText(f"⚠️ Stock crítico: {nombres}{extra}")
            self.lbl_alertas.show()
        else:
            self.lbl_alertas.hide()

    def filter_table(self):
        text = self.search_input.text().lower()
        estado = self.combo_estado.currentText()
        filtered = []
        for ins in self.insumos:
            if text and text not in ins['nombre'].lower():
                continue
            stock = ins.get('stock_kg', 0) or 0
            if estado == "Con stock" and stock <= 0:
                continue
            elif estado == "Stock crítico" and not (0 < stock <= 10):
                continue
            elif estado == "Sin stock" and stock > 0:
                continue
            filtered.append(ins)
        self._update_table(filtered)

    def _update_table(self, data):
        self.table.setRowCount(0)
        for ins in data:
            row = self.table.rowCount()
            self.table.insertRow(row)
            stock = ins.get('stock_kg', 0) or 0
            precio = ins.get('precio_kg', 0) or 0
            precio_ant = ins.get('precio_kg_anterior', 0) or 0
            proveedor = ins.get('proveedor', '') or ''

            items = [
                ins['nombre'],
                f"{stock:.1f}",
                f"{precio:.2f}",
                f"{precio_ant:.2f}",
                proveedor,
                ins.get('categoria', 'General')
            ]
            for col, val in enumerate(items):
                item = QTableWidgetItem(str(val))
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if col == 0:
                    item.setData(Qt.ItemDataRole.UserRole, ins['id'])
                # Colorear stock crítico
                if col == 1 and stock <= 10 and stock > 0:
                    item.setBackground(QColor(COLORS['semaforo_warn']))
                elif col == 1 and stock <= 0:
                    item.setBackground(QColor(COLORS['semaforo_bad']))
                # Indicar cambio de precio
                if col == 2 and precio_ant > 0:
                    if precio > precio_ant:
                        item.setForeground(QColor(COLORS['danger']))
                    elif precio < precio_ant:
                        item.setForeground(QColor(COLORS['primary_light']))
                self.table.setItem(row, col, item)
        self.lbl_count.setText(f"  {len(data)} insumo(s) mostrado(s)")

    def _get_selected(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Sin selección", "Selecciona un insumo primero.")
            return None, None
        id_insumo = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        insumo = next((i for i in self.insumos if i.get('id') == id_insumo), None)
        return id_insumo, insumo

    def registrar_entrada(self):
        id_insumo, insumo = self._get_selected()
        if not insumo:
            return
        dlg = DialogoEntradaStock(insumo['nombre'], self)
        if dlg.exec():
            data = dlg.get_data()
            if actualizar_stock(id_insumo, data['cantidad'], data['precio_kg'], data['proveedor']):
                QMessageBox.information(self, "✅ Stock actualizado",
                    f"Se registraron {data['cantidad']:.1f} kg de «{insumo['nombre']}».")
                self.load_data()
            else:
                QMessageBox.critical(self, "Error", "No se pudo registrar la entrada.")

    def ver_historial(self):
        id_insumo, insumo = self._get_selected()
        if not insumo:
            return
        historial = get_historial_precios(id_insumo)
        if not historial:
            QMessageBox.information(self, "Sin historial",
                f"No hay registros de precios para «{insumo['nombre']}».")
            return
        msg = f"Historial de precios — {insumo['nombre']}:\n\n"
        for h in historial[-15:]:
            fecha = h['fecha'][:10]
            msg += f"  {fecha} → ${h['precio_kg']:.2f}/kg"
            if h.get('proveedor'):
                msg += f"  ({h['proveedor']})"
            msg += "\n"
        QMessageBox.information(self, "📊 Historial de Precios", msg)
