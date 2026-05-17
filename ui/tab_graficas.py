# -*- coding: utf-8 -*-
# ui/tab_graficas.py
import os
import io
import numpy as np

import matplotlib
matplotlib.use('QtAgg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QComboBox, QLabel, QApplication, QFileDialog,
                             QSizePolicy)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage
from app.database import get_connection, GestorFormulacionesBD, get_all_animales

PALETA = [
    '#2D7D46', '#5CB85C', '#F0AD4E', '#D9534F', '#5BC0DE',
    '#9B59B6', '#E67E22', '#1ABC9C', '#3498DB', '#E74C3C',
    '#95A5A6', '#F39C12', '#16A085', '#8E44AD', '#2980B9'
]

BG = '#1E1E2E'
BG2 = '#2A2A3E'
BORDER = '#3A3A6A'


class TabGraficas(QWidget):
    """
    Tab de visualización gráfica interactiva de la formulación actual.
    Se sincroniza con el Tab de Formulación mediante update_datos().
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._datos = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # ── Barra superior ────────────────────────────────────────────
        barra_top = QHBoxLayout()

        lbl = QLabel("Visualización:")
        lbl.setStyleSheet("font-weight: bold; color: #AAAACC;")
        barra_top.addWidget(lbl)

        self.combo_grafica = QComboBox()
        self.combo_grafica.addItems([
            "🥧  Composición de la ración (Torta)",
            "📊  Perfil nutricional vs requerimientos (Barras)",
            "📚  Aporte por ingrediente por nutriente (Barras apiladas)",
            "💰  Análisis de costos por ingrediente",
            "⚖️  Comparación con formulaciones guardadas",
        ])
        self.combo_grafica.setMinimumWidth(360)
        self.combo_grafica.currentIndexChanged.connect(self._cambiar_grafica)
        barra_top.addWidget(self.combo_grafica)

        barra_top.addStretch()

        btn_png = QPushButton("📷 Exportar PNG")
        btn_png.clicked.connect(lambda: self._exportar('png'))
        btn_pdf = QPushButton("Exportar PDF")
        btn_pdf.clicked.connect(lambda: self._exportar('pdf'))
        btn_copiar = QPushButton("📋 Copiar")
        btn_copiar.clicked.connect(self._copiar_portapapeles)

        for btn in (btn_png, btn_pdf, btn_copiar):
            btn.setStyleSheet(
                "QPushButton{background:#2D7D46;color:white;font-weight:bold;"
                "padding:5px 10px;border-radius:4px;}"
                "QPushButton:hover{background:#5CB85C;}"
            )
            barra_top.addWidget(btn)

        layout.addLayout(barra_top)

        # ── Canvas matplotlib ─────────────────────────────────────────
        self.figura = Figure(figsize=(12, 6), facecolor=BG)
        self.canvas = FigureCanvas(self.figura)
        self.canvas.setSizePolicy(QSizePolicy.Policy.Expanding,
                                  QSizePolicy.Policy.Expanding)
        layout.addWidget(self.canvas)

        # ── Mensaje sin datos ─────────────────────────────────────────
        self._mostrar_placeholder()

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------
    def update_datos(self, ingredientes_activos, totales, reqs, nombre_etapa="", **kwargs):
        """
        Llamar desde TabFormulacion cada vez que cambie la formulación.
        """
        self._datos = {
            'ingredientes': ingredientes_activos,
            'totales': totales,
            'reqs': reqs,
            'etapa': nombre_etapa
        }
        self._cambiar_grafica(self.combo_grafica.currentIndex())



    # ------------------------------------------------------------------
    # Graficas
    # ------------------------------------------------------------------
    def _cambiar_grafica(self, idx):
        if not self._datos or not self._datos.get('ingredientes'):
            self._mostrar_placeholder()
            return

        {
            0: self._grafica_torta,
            1: self._grafica_barras_nutricionales,
            2: self._grafica_apilada,
            3: self._grafica_costos
        }.get(idx, self._mostrar_placeholder)()

    def _clear_fig(self):
        self.figura.clear()
        self.figura.patch.set_facecolor(BG)

    def _grafica_torta(self):
        self._clear_fig()
        ax = self.figura.add_subplot(111, facecolor=BG)
        ings = self._datos['ingredientes']

        nombres = [i['nombre'][:18] for i in ings]
        pcts = [i['porcentaje'] for i in ings]
        colores = PALETA[:len(nombres)]

        wedges, _, autotexts = ax.pie(
            pcts, labels=None, colors=colores,
            autopct='%1.1f%%', startangle=90, pctdistance=0.75,
            wedgeprops={'linewidth': 2, 'edgecolor': BG}
        )
        for at in autotexts:
            at.set_color('white')
            at.set_fontsize(9)
            at.set_fontweight('bold')

        leyenda = [mpatches.Patch(color=c, label=f"{n} ({p:.1f}%)")
                   for n, p, c in zip(nombres, pcts, colores)]
        ax.legend(handles=leyenda, loc='center left',
                  bbox_to_anchor=(1.0, 0.5),
                  facecolor=BG2, edgecolor=BORDER,
                  labelcolor='white', fontsize=9)

        ax.set_title('Composición de la Ración',
                     color='white', fontsize=13, fontweight='bold', pad=15)
        self.figura.tight_layout()
        self.canvas.draw()

    def _grafica_barras_nutricionales(self):
        self._clear_fig()
        ax = self.figura.add_subplot(111, facecolor=BG)

        totales = self._datos['totales']
        reqs = self._datos['reqs']
        etapa = self._datos['etapa']

        nutrientes = ['Proteína%', 'Fibra%', 'Grasa%', 'Calcio%',
                      'Fósforo%', 'Lisina%', 'Metionina%']
        keys_tot = ['proteina', 'fibra', 'grasa', 'calcio',
                    'fosforo', 'lisina', 'metionina']
        keys_req = ['proteina_min', 'fibra_max', 'grasa_max', 'calcio_min',
                    'fosforo_min', 'lisina_min', 'metionina_min']

        x = np.arange(len(nutrientes))
        ancho = 0.35

        vals_c = [totales.get(k, 0) for k in keys_tot]
        vals_r = [reqs.get(k, 0) for k in keys_req]

        colores_b = []
        for calc, req, key in zip(vals_c, vals_r, keys_req):
            if req == 0:
                colores_b.append('#5BC0DE')
            elif 'max' in key:
                colores_b.append('#D9534F' if calc > req else '#5CB85C')
            else:
                colores_b.append('#D9534F' if calc < req else '#5CB85C')

        bars_c = ax.bar(x - ancho/2, vals_c, ancho,
                        color=colores_b, alpha=0.85,
                        label='Calculado', edgecolor='white', linewidth=0.5)
        ax.bar(x + ancho/2, vals_r, ancho,
               color='#5BC0DE', alpha=0.55,
               label=f'Requerido ({etapa})',
               edgecolor='white', linewidth=0.5)

        for bar in bars_c:
            h = bar.get_height()
            if h > 0:
                ax.text(bar.get_x() + bar.get_width()/2, h * 1.02,
                        f'{h:.2f}', ha='center', va='bottom',
                        color='white', fontsize=8, fontweight='bold')

        ax.set_xticks(x)
        ax.set_xticklabels(nutrientes, color='white', fontsize=9)
        ax.set_title('Perfil Nutricional vs Requerimientos',
                     color='white', fontsize=13, fontweight='bold')
        ax.legend(facecolor=BG2, edgecolor=BORDER, labelcolor='white')
        ax.tick_params(colors='white')
        ax.spines['bottom'].set_color(BORDER)
        ax.spines['left'].set_color(BORDER)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.grid(axis='y', alpha=0.2, color='white')
        ax.yaxis.label.set_color('white')

        self.figura.tight_layout()
        self.canvas.draw()

    def _grafica_apilada(self):
        """Aporte de cada ingrediente por nutriente (barras apiladas)."""
        self._clear_fig()
        ax = self.figura.add_subplot(111, facecolor=BG)

        ings = self._datos['ingredientes']
        nutrientes = ['proteina', 'fibra', 'grasa', 'calcio', 'fosforo', 'lisina']
        nut_labels = ['Proteína%', 'Fibra%', 'Grasa%', 'Calcio%', 'Fósforo%', 'Lisina%']
        x = np.arange(len(nutrientes))

        bottom = np.zeros(len(nutrientes))
        for i, ing in enumerate(ings):
            vals = []
            for nut in nutrientes:
                # Aporte de este ingrediente = valor_nutriente * pct_en_racion / 100
                pct = ing.get('porcentaje', 0) / 100
                aporte = ing.get(nut, 0) * pct
                vals.append(aporte)
            color = PALETA[i % len(PALETA)]
            ax.bar(x, vals, bottom=bottom, color=color, alpha=0.85,
                   label=ing['nombre'][:16], edgecolor=BG, linewidth=0.5)
            bottom += np.array(vals)

        ax.set_xticks(x)
        ax.set_xticklabels(nut_labels, color='white', fontsize=9)
        ax.set_title('Aporte por Ingrediente por Nutriente',
                     color='white', fontsize=13, fontweight='bold')
        ax.legend(loc='upper right', facecolor=BG2, edgecolor=BORDER,
                  labelcolor='white', fontsize=7,
                  bbox_to_anchor=(1.18, 1.0))
        ax.tick_params(colors='white')
        ax.spines['bottom'].set_color(BORDER)
        ax.spines['left'].set_color(BORDER)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.grid(axis='y', alpha=0.2, color='white')

        self.figura.tight_layout()
        self.canvas.draw()

    def _grafica_costos(self):
        self._clear_fig()
        ax = self.figura.add_subplot(111, facecolor=BG)

        ings = sorted(
            [i for i in self._datos['ingredientes'] if i.get('costo', 0) > 0],
            key=lambda x: x['costo'], reverse=True
        )

        if not ings:
            ax.text(0.5, 0.5,
                    'No hay precios configurados.\n'
                    'Ve a Ingredientes y agrega el precio/kg.',
                    ha='center', va='center', color='#8080B0', fontsize=12,
                    transform=ax.transAxes)
            self.canvas.draw()
            return

        nombres = [i['nombre'][:22] for i in ings]
        costos = [i['costo'] for i in ings]
        max_c = max(costos)
        colores = ['#D9534F' if c == max_c else '#2D7D46' for c in costos]

        barras = ax.barh(nombres, costos, color=colores, alpha=0.85,
                         edgecolor='white', linewidth=0.5)

        for bar, costo in zip(barras, costos):
            ax.text(bar.get_width() * 1.01,
                    bar.get_y() + bar.get_height()/2,
                    f'${costo:.4f}', va='center',
                    color='white', fontsize=9)

        ax.set_title('Costo por Ingrediente en la Ración',
                     color='white', fontsize=13, fontweight='bold')
        ax.set_xlabel('Costo ($)', color='white')
        ax.tick_params(colors='white')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['bottom'].set_color(BORDER)
        ax.spines['left'].set_color(BORDER)
        ax.grid(axis='x', alpha=0.2, color='white')

        self.figura.tight_layout()
        self.canvas.draw()


        ax.legend(facecolor=BG2, edgecolor=BORDER, labelcolor='white',
                  fontsize=8, loc='upper left')
        ax.tick_params(colors='white')
        ax.spines['bottom'].set_color(BORDER)
        ax.spines['left'].set_color(BORDER)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.grid(axis='y', alpha=0.2, color='white')
        
        self.figura.tight_layout()
        self.canvas.draw()

    def _mostrar_placeholder(self):
        self._clear_fig()
        ax = self.figura.add_subplot(111, facecolor=BG)
        ax.text(0.5, 0.5,
                'Agrega ingredientes en el Tab de Formulacion\n'
                'para ver las graficas aqui.',
                ha='center', va='center',
                color='#5050A0', fontsize=14,
                transform=ax.transAxes,
                bbox=dict(boxstyle='round,pad=0.6',
                          facecolor=BG2, edgecolor=BORDER, alpha=0.8))
        ax.set_xticks([])
        ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_color(BORDER)
        self.canvas.draw()

    # ------------------------------------------------------------------
    # Exportación
    # ------------------------------------------------------------------
    def _exportar(self, fmt):
        ruta, _ = QFileDialog.getSaveFileName(
            self, f"Exportar gráfica como {fmt.upper()}",
            os.path.expanduser(f"~/grafica_vital.{fmt}"),
            f"Imagen {fmt.upper()} (*.{fmt})"
        )
        if ruta:
            self.figura.savefig(ruta, format=fmt, dpi=200,
                                bbox_inches='tight', facecolor=BG)

    def _copiar_portapapeles(self):
        buf = io.BytesIO()
        self.figura.savefig(buf, format='png', dpi=150,
                            bbox_inches='tight', facecolor=BG)
        buf.seek(0)
        imagen = QImage.fromData(buf.read())
        QApplication.clipboard().setImage(imagen)
