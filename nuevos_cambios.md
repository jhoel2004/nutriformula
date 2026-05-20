# PROMPT MAESTRO — VITAL v2.0
## Evolución completa del sistema de formulación nutricional animal
## Base: arquitectura MVC existente Python/PyQt6/SQLite — Windows + Linux

---

## CONTEXTO DEL SISTEMA ACTUAL

VITAL ya existe con esta estructura:
```
nutriformula/
├── main.py, VITAL.spec, build_windows.bat, install.sh
├── data/nutriformula.db
├── app/
│   ├── calculator.py, database.py, exporter.py
│   ├── main_window.py, utils.py, config.py
└── ui/
    ├── tab_ingredientes.py, tab_calcular.py
    ├── tab_formulacion.py, tab_formulacion_inversa.py
    ├── tab_formulaciones.py, tab_graficas.py, dialogs.py
```

Funciona con: PyQt6, Pandas, SciPy, Matplotlib, QDarkStyle, SQLite3, PyInstaller

**Aplicar TODOS los cambios descritos abajo sobre el código existente.**

---

## BLOQUE 1 — CORRECCIONES CRÍTICAS (hacer primero)

### 1.1 — Compatibilidad multiplataforma real

```python
# app/utils.py — REEMPLAZAR COMPLETO

import sys, os
from pathlib import Path

def get_base_path() -> Path:
    """Ruta base: funciona en desarrollo Y en PyInstaller (.exe / binario Linux)."""
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS)
    return Path(__file__).parent.parent

def get_data_dir() -> Path:
    """
    Directorio de datos persistentes del usuario.
    Windows: C:/Users/<user>/AppData/Local/VITAL/
    Linux:   /home/<user>/.local/share/VITAL/
    """
    if sys.platform == 'win32':
        base = Path(os.environ.get('LOCALAPPDATA', Path.home()))
    else:
        base = Path.home() / '.local' / 'share'
    d = base / 'VITAL'
    d.mkdir(parents=True, exist_ok=True)
    return d

def get_db_path() -> Path:
    return get_data_dir() / 'vital.db'

def get_exports_dir() -> Path:
    d = get_data_dir() / 'Exportaciones'
    d.mkdir(exist_ok=True)
    return d

def get_logo_path() -> Path:
    return get_base_path() / 'logo.png'

def force_utf8():
    """Acentos correctos en Windows — llamar al inicio de main.py."""
    if sys.platform == 'win32':
        import ctypes
        ctypes.windll.kernel32.SetConsoleOutputCP(65001)
        os.environ['PYTHONIOENCODING'] = 'utf-8'

def get_system_font() -> str:
    return 'Segoe UI' if sys.platform == 'win32' else 'Ubuntu'
```

### 1.2 — Esquema de base de datos expandido (migración automática)

```python
# app/database.py — agregar al método inicializar()

SCHEMA_NUEVAS_TABLAS = """
PRAGMA foreign_keys = ON;
PRAGMA encoding = 'UTF-8';

-- Tabla de perfiles de empresa/granja
CREATE TABLE IF NOT EXISTS config_empresa (
    clave  TEXT PRIMARY KEY,
    valor  TEXT
);

-- Tabla de lotes de producción
CREATE TABLE IF NOT EXISTS lotes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    formulacion_id  INTEGER REFERENCES formulaciones(id) ON DELETE SET NULL,
    nombre          TEXT NOT NULL,
    fecha           TEXT NOT NULL,
    cantidad_kg     REAL DEFAULT 0,
    costo_total     REAL DEFAULT 0,
    notas           TEXT DEFAULT '',
    estado          TEXT DEFAULT 'producido'  -- producido | en_uso | agotado
);

-- Tabla de historial de precios de insumos
CREATE TABLE IF NOT EXISTS historial_precios (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    insumo_id   INTEGER NOT NULL REFERENCES insumos(id) ON DELETE CASCADE,
    precio_kg   REAL NOT NULL,
    fecha       TEXT NOT NULL,
    proveedor   TEXT DEFAULT ''
);

-- Tabla de alertas y notificaciones
CREATE TABLE IF NOT EXISTS alertas_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo            TEXT NOT NULL,  -- 'salud' | 'precio' | 'stock'
    mensaje         TEXT NOT NULL,
    formulacion_id  INTEGER,
    fecha           TEXT NOT NULL,
    leida           INTEGER DEFAULT 0
);
"""

def migrar_bd_v2(conn):
    """
    Agregar columnas nuevas a tablas existentes sin perder datos.
    Ejecutar al iniciar la app — seguro de correr múltiples veces.
    """
    migraciones = [
        # Insumos: nuevos campos
        "ALTER TABLE insumos ADD COLUMN precio_kg_anterior REAL DEFAULT 0",
        "ALTER TABLE insumos ADD COLUMN stock_kg REAL DEFAULT 0",
        "ALTER TABLE insumos ADD COLUMN proveedor TEXT DEFAULT ''",
        "ALTER TABLE insumos ADD COLUMN notas TEXT DEFAULT ''",
        "ALTER TABLE insumos ADD COLUMN tms REAL DEFAULT 0",   # Toxicidad máxima segura
        # Formulaciones: nuevos campos
        "ALTER TABLE formulaciones ADD COLUMN version INTEGER DEFAULT 1",
        "ALTER TABLE formulaciones ADD COLUMN etiqueta TEXT DEFAULT ''",
        "ALTER TABLE formulaciones ADD COLUMN aprobada INTEGER DEFAULT 0",
    ]
    cursor = conn.cursor()
    for sql in migraciones:
        try:
            cursor.execute(sql)
        except Exception:
            pass  # columna ya existe — ignorar
    conn.commit()
```

### 1.3 — Datos precargados ampliados (insumos)

```python
# Agregar a los insumos default en database.py
# Insumos que faltan en el sistema actual:

INSUMOS_ADICIONALES = [
    # Minerales y vitaminas
    ('carbonato de calcio',   0.0,  0,    0.0, 0.0,  38.0, 0.0,  0.0, 0.0,   0,   0.0, 'Minerales'),
    ('fosfato bicálcico',     0.0,  0,    0.0, 0.0,  22.0, 18.0, 0.0, 0.0,   0,   0.0, 'Minerales'),
    ('sal común (NaCl)',      0.0,  0,    0.0, 0.0,  0.0,  0.0,  0.0, 0.0,   0,   0.0, 'Minerales'),
    ('bicarbonato de sodio',  0.0,  0,    0.0, 0.0,  0.0,  0.0,  0.0, 0.0,   0,   0.0, 'Minerales'),
    ('óxido de zinc',         0.0,  0,    0.0, 0.0,  0.0,  0.0,  0.0, 0.0,   0,   0.0, 'Minerales'),
    ('premezcla vitamínica aves', 12.0, 0, 0.0, 0.0, 3.5, 2.0,  0.5, 0.3, 2500, 0.0, 'Premezclas'),
    ('premezcla vitamínica porcinos',10.0,0,0.0,0.0, 2.0, 1.5,  0.4, 0.2, 2000, 0.0, 'Premezclas'),
    ('lisina sintética L-Lys', 78.0, 0,  0.0, 0.0,  0.0,  0.0,  78.0,0.0,   0,   0.0, 'Aminoácidos'),
    ('DL-metionina',           58.0, 0,  0.0, 0.0,  0.0,  0.0,  0.0, 99.0,  0,   0.0, 'Aminoácidos'),
    ('treonina sintética',     98.0, 0,  0.0, 0.0,  0.0,  0.0,  0.0, 0.0,   0,   0.0, 'Aminoácidos'),
    ('triptófano sintético',   98.0, 0,  0.0, 0.0,  0.0,  0.0,  0.0, 0.0,   0,   0.0, 'Aminoácidos'),
    ('aceite de palma',         0.0, 8000,0.0,80.0, 0.0,  0.0,  0.0, 0.0,   0,   0.0, 'Grasas'),
    ('aceite de soya',          0.0, 8000,0.0,80.0, 0.0,  0.0,  0.0, 0.0,   0,   0.0, 'Grasas'),
    ('glicerina cruda',         0.0, 3300,0.0, 0.0, 0.0,  0.0,  0.0, 0.0,   0,   0.0, 'Energéticos'),
    ('harina de sangre',       80.0, 2900,1.0, 1.5, 0.3,  0.25, 7.0, 1.2,  800,  0.0, 'Proteínas'),
    ('harina de plumas',       85.0, 2850,2.0, 3.5, 0.4,  0.50, 1.8, 0.6,  500,  0.0, 'Proteínas'),
    ('gluten de maíz',         60.0, 3600,2.0, 4.5, 0.05, 0.5,  1.2, 2.0,  600,  0.0, 'Proteínas'),
    ('cebada grano',           11.5, 2650,5.5, 2.1, 0.06, 0.38, 0.43,0.18, 1050, 0.0, 'Cereales'),
    ('trigo grano',            12.5, 3200,3.0, 1.9, 0.07, 0.38, 0.35,0.22,  950, 0.0, 'Cereales'),
    ('maíz alto en aceite',     8.5, 3500,1.5, 6.5, 0.03, 0.27, 0.22,0.19,  510, 0.0, 'Cereales'),
]
```

---

## BLOQUE 2 — NUEVOS MÓDULOS A CREAR

### 2.1 — NUEVO TAB: "📦 Inventario / Stock"

Crear archivo `ui/tab_inventario.py`:

```python
"""
MÓDULO DE INVENTARIO DE MATERIAS PRIMAS

Tabla principal con columnas:
  Ingrediente | Stock actual (kg) | Precio/kg actual | Proveedor |
  Último precio | Variación % | Estado

Estado visual por colores:
  🟢 Verde   → stock > 50 kg
  🟡 Amarillo → stock entre 10 y 50 kg  (advertencia)
  🔴 Rojo    → stock ≤ 10 kg  (stock crítico)

FUNCIONES:
  - Actualizar stock: al hacer doble clic en un ingrediente →
    diálogo con campos: "Cantidad entrada (kg)" + "Precio pagado/kg" + "Proveedor"
    → actualiza stock_kg en insumos
    → inserta registro en historial_precios

  - Ver historial de precios: botón → gráfica matplotlib de línea
    mostrando la evolución del precio del insumo seleccionado en el tiempo
    X: fechas de compra | Y: precio/kg

  - Calcular costo de formulación con stock actual:
    Botón "¿Tengo suficiente para X kg?" → seleccionar formulación guardada
    → calcular si el stock actual alcanza para producir N kg
    → mostrar semáforo por ingrediente: ✅ suficiente | ❌ faltan X kg

  - Exportar lista de compras: botón → genera PDF/Excel con:
    qué ingredientes están bajo mínimo y cuánto hay que comprar

ALERTAS AUTOMÁTICAS:
  Al abrir la app: revisar stock de todos los ingredientes activos
  Si alguno tiene stock_kg ≤ 10 → mostrar badge rojo en el tab de Inventario
  Registrar en tabla alertas_log
"""
```

### 2.2 — NUEVO TAB: "📈 Análisis Económico"

Crear archivo `ui/tab_economia.py`:

```python
"""
MÓDULO DE ANÁLISIS ECONÓMICO DE RACIONES

SECCIÓN 1 — Costo histórico por animal:
  Gráfica de barras o línea mostrando cómo ha evolucionado el costo/kg
  de las formulaciones guardadas de cada animal.
  X: fecha de guardado | Y: costo por kg
  Útil para detectar inflación de costos en el tiempo.

SECCIÓN 2 — Comparador de costos entre formulaciones:
  Seleccionar 2-5 formulaciones del historial
  → Tabla comparativa de costo/kg y costo/tonelada
  → Gráfica de barras agrupadas mostrando costo por nutriente

SECCIÓN 3 — Simulador de variación de precios:
  Slider o campo: "¿Qué pasa si el precio del Maíz sube 20%?"
  → Recalcular el costo de todas las formulaciones guardadas con ese insumo
  → Mostrar impacto en tabla: formulación | costo actual | costo simulado | diferencia

SECCIÓN 4 — Resumen mensual:
  Tabla: mes | lotes producidos | kg totales | costo total | costo promedio/kg
  Datos tomados de la tabla 'lotes'
  Gráfica de barras por mes

WIDGETS DE RESUMEN (cards en la parte superior):
  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐
  │ Fórmula    │ │ Fórmula    │ │ Insumo más │ │ Ahorro vs  │
  │ más barata │ │ más cara   │ │ costoso    │ │ mes pasado │
  │ $0.45/kg  │ │ $1.20/kg   │ │ H. Pescado │ │   -8.3%    │
  └────────────┘ └────────────┘ └────────────┘ └────────────┘
"""
```

### 2.3 — NUEVO TAB: "🏭 Lotes de Producción"

Crear archivo `ui/tab_lotes.py`:

```python
"""
MÓDULO DE TRAZABILIDAD DE PRODUCCIÓN

Registra cada vez que se produce una ración real en campo.

TABLA PRINCIPAL:
  # | Nombre del Lote | Formulación usada | Animal | Fecha | Kg producidos |
  Costo total | Estado (producido/en_uso/agotado) | Notas

CREAR NUEVO LOTE:
  Diálogo con campos:
  - Nombre del lote (ej: "Lote 001 Ponedoras Mayo")
  - Formulación base (seleccionar del historial)
  - Cantidad a producir (kg) → calcular automáticamente los kg de cada ingrediente
  - Fecha de producción
  - Notas / observaciones
  → Al guardar: verificar si el stock alcanza (cruzar con inventario)
  → Si alcanza: descontar automáticamente del stock de cada ingrediente
  → Si no alcanza: mostrar qué ingredientes faltan antes de confirmar

DETALLE DE LOTE (al hacer clic):
  - Resumen de ingredientes usados con cantidades reales
  - Costo total del lote
  - Botón "Exportar etiqueta del lote" → PDF simple con: nombre, fecha,
    animal, kg, ingredientes principales, instrucciones de preparación

CAMBIAR ESTADO:
  Botones: [En uso] [Agotado]
  Para trazabilidad y seguimiento

HISTORIAL DE PRODUCCIÓN:
  Filtros por: animal | mes | estado
  Total producido en el período seleccionado
"""
```

### 2.4 — NUEVO PANEL: "🔔 Centro de Alertas"

Crear `ui/panel_alertas.py` como widget integrado en `main_window.py`:

```python
"""
PANEL DE ALERTAS EN TIEMPO REAL

Badge numérico en el ícono del sidebar mostrando alertas no leídas.

TIPOS DE ALERTAS:
  🔴 Stock crítico:     "[Ingrediente] tiene solo X kg en stock"
  🟡 Precio inusual:   "[Ingrediente] subió más del 15% desde la última compra"
  🔴 Ca:P fuera rango: "La ración [nombre] tiene Ca:P = X.X (fuera de 1.2-2.0)"
  🟡 Ingrediente limitado: "[Ingrediente] supera el % máximo recomendado"
  🔵 Info:             "Formulación [nombre] guardada exitosamente"

COMPORTAMIENTO:
  - Al iniciar la app: revisar stock y generar alertas automáticas
  - Al guardar formulación: revisar Ca:P y límites de inclusión
  - Al actualizar precio de un insumo: comparar con precio anterior
  - Clic en alerta → navegar al módulo relacionado

IMPLEMENTACIÓN en main_window.py:
  def verificar_alertas_al_iniciar(self):
      alertas = self.db.obtener_alertas_no_leidas()
      if alertas:
          # Mostrar badge rojo con el número
          self.actualizar_badge_alertas(len(alertas))
          # Si hay alertas críticas: mostrar popup no invasivo (QSystemTrayIcon)
"""
```

---

## BLOQUE 3 — MEJORAS A MÓDULOS EXISTENTES

### 3.1 — tab_ingredientes.py: agregar columnas y funciones

```python
"""
MEJORAS AL MÓDULO DE INGREDIENTES

NUEVAS COLUMNAS en la tabla:
  Stock (kg) | Proveedor | TMS% (toxicidad máxima segura) | Notas

NUEVAS FUNCIONES:
  1. Importar desde Excel:
     Botón "📥 Importar Excel" → QFileDialog → leer .xlsx con openpyxl
     Columnas esperadas: Nombre | Proteína% | EM Kcal | Fibra% | ...
     Mostrar preview antes de confirmar importación
     Manejar duplicados: preguntar si sobrescribir o saltar

  2. Exportar catálogo:
     Botón "📤 Exportar" → .xlsx con todos los ingredientes + valores nutricionales
     Útil para compartir con otros usuarios o hacer respaldo

  3. Campo TMS (Toxicidad Máxima Segura):
     Cada ingrediente puede tener un % máximo recomendado por la literatura
     Al usarse en formulación y superar ese %, disparar alerta automática

  4. Duplicar ingrediente:
     Clic derecho → "Duplicar" → crear copia con nombre "Copia de [X]"
     Útil para variantes del mismo insumo (ej: Maíz nacional / Maíz importado)

  5. Historial de uso:
     Al hacer clic derecho → "Ver en qué formulaciones se usa"
     → Lista de formulaciones que contienen ese ingrediente
"""
```

### 3.2 — tab_formulacion.py: mejorar la comparativa

```python
"""
MEJORAS AL FORMULADOR MANUAL

1. SELECTOR DE REFERENCIA MEJORADO:
   Combo "Comparar con:" con opciones:
   - [Sin referencia]
   - [Mejor fórmula del historial] (la de menor costo que cumpla nutrientes)
   - [Última fórmula guardada del animal]
   - [Seleccionar del historial...] → abrir diálogo con lista

2. PANEL DE SEMÁFOROS DETALLADO:
   Para cada nutriente:
   ┌─────────────────────────────────────────────────────┐
   │ Proteína%  [████████░░] 18.5% / ref: 20.0%  ⚠️ -7.5% │
   │ EM Kcal    [██████████] 3100  / ref: 2900   ✅ +6.8%  │
   │ Ca:P       [██████████] 1.8:1 / rango: 1.2-2.0 ✅    │
   └─────────────────────────────────────────────────────┘
   Barras de progreso coloreadas: verde/amarillo/rojo
   Porcentaje de diferencia vs referencia

3. MODO "AJUSTE RÁPIDO":
   Si un nutriente está en rojo → botón "💡 Sugerencia"
   → El sistema sugiere qué ingrediente aumentar/disminuir
   para acercar ese nutriente al objetivo sin subir mucho el costo

4. GUARDAR CON VERSIÓN:
   Si ya existe una formulación con ese nombre para ese animal:
   → Preguntar: "¿Crear versión nueva (v2) o sobrescribir?"
   → Si versión nueva: guardar como v2 y mantener v1 en historial

5. CAMPO ETIQUETA:
   Input de texto libre: "Etiqueta / Temporada" (ej: "Verano 2025", "Post-destete")
   Se guarda en formulaciones.etiqueta
   Sirve para filtrar en el historial

6. INSTRUCCIONES DE PREPARACIÓN:
   QPlainTextEdit expandible al pie del panel derecho
   Con botones: [Plantilla básica] [Limpiar]
   La plantilla básica autorrellena pasos estándar de mezclado
"""
```

### 3.3 — tab_formulaciones.py: historial enriquecido

```python
"""
MEJORAS AL HISTORIAL DE FORMULACIONES

1. FILTROS AVANZADOS en la barra superior:
   [Animal ▼] [Etiqueta ▼] [Tipo: Manual/Auto ▼] [Fecha desde] [Fecha hasta]
   [Buscar por nombre...] [☑ Solo aprobadas]

2. COLUMNAS ADICIONALES en la tabla:
   Nombre | Animal | Tipo | Etiqueta | Versión | Fecha | Costo/kg | Proteína% |
   EM Kcal | ✅ Aprobada

3. BOTÓN "APROBAR" FORMULACIÓN:
   Marcar una formulación como "aprobada" (formulaciones.aprobada = 1)
   Las aprobadas aparecen con un ícono especial ✅
   Solo las aprobadas pueden usarse como referencia en el comparador

4. PANEL PREVIEW (lateral derecho):
   Al seleccionar una formulación → mostrar preview instantáneo sin abrir:
   - Ingredientes y % en tabla compacta
   - Mini radar nutricional
   - Costo/kg y costo/tonelada
   - Instrucciones de preparación (resumen)

5. COMPARAR DOS FORMULACIONES LADO A LADO:
   Seleccionar dos formulaciones con Ctrl+click
   → Botón "⚖️ Comparar" → abrir diálogo con tabla comparativa
   Columnas: Nutriente | Form. A | Form. B | Diferencia
   Resaltado en verde la que sea mejor en cada nutriente

6. EXPORTAR HISTORIAL COMPLETO:
   Botón "📤 Exportar historial" → Excel con todas las formulaciones del animal
   Una hoja por formulación + hoja resumen
"""
```

### 3.4 — tab_graficas.py: dashboard completo

```python
"""
MEJORAS AL MÓDULO DE GRÁFICAS

NUEVAS GRÁFICAS (agregar a las existentes):

1. RADAR NUTRICIONAL (ya implementado — mejorar):
   - 8 ejes: Proteína, EM, Fibra, Grasa, Calcio, Fósforo, Lisina, Metionina
   - Normalización 1kg × 1kg vs formulación de referencia
   - Área sombreada roja = referencia | Línea azul = actual
   - Puntos coloreados: verde ≥0.95 | amarillo ≥0.80 | rojo <0.80
   - Tabla de ratios debajo del radar
   - Tooltip al hover con valor exacto

2. EVOLUCIÓN DE COSTOS (gráfica de línea):
   X: fechas de guardado de formulaciones
   Y: costo/kg de cada formulación del animal seleccionado
   Múltiples líneas = múltiples animales
   Mostrar tendencia (línea punteada de regresión lineal)

3. MAPA DE CALOR NUTRICIONAL:
   Tabla coloreada con todos los ingredientes × todos los nutrientes
   Color de celda: intensidad según el valor nutricional
   Verde oscuro = valor alto | Blanco = valor bajo
   Permite identificar visualmente qué ingrediente aporta qué

4. GRÁFICA DE CONTRIBUCIÓN APILADA:
   Barras 100% apiladas
   X: cada nutriente | Colores: cada ingrediente
   Muestra visualmente qué ingrediente aporta qué % de cada nutriente
   Interactivo: hover muestra el valor exacto

5. DASHBOARD GENERAL (pantalla de inicio del tab):
   Cards de resumen:
   ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
   │ Total fórmulas │ │ Animales  │ │ Costo prom. │ │ Insumos     │
   │     47         │ │     8     │ │  $0.72/kg   │ │  con stock  │
   │  guardadas     │ │ activos   │ │   general   │ │    crítico  │
   └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘

CONTROLES DE GRÁFICAS:
  - Selector de animal (filtra todas las gráficas)
  - Selector de rango de fechas
  - Botón exportar PNG/PDF para cada gráfica individual
  - Botón "Exportar dashboard completo" → PDF con todas las gráficas
"""
```

### 3.5 — app/exporter.py: PDF más completo

```python
"""
MEJORAS AL EXPORTADOR

PDF COMPLETO (mejorar el existente):
  Página 1: Encabezado empresa + logo + datos generales
  Página 2: Composición detallada (tabla con todos los aportes por ingrediente)
  Página 3: Perfil nutricional vs requerimientos (tabla semáforo)
  Página 4: Gráficas (radar + torta composición + costos)
  Página 5: Instrucciones de preparación (tipografía grande, legible en planta)
  Pie de página: nombre formulación | fecha | página N

NUEVOS TIPOS DE EXPORTACIÓN:
  1. "Etiqueta de lote" (A6 o media carta):
     - Nombre del lote
     - Animal y etapa
     - Ingredientes principales (top 5 por %)
     - Fecha de producción
     - Kg totales
     - Código QR con ID de formulación (usar qrcode library)

  2. "Lista de compras":
     - Ingredientes con stock crítico
     - Cantidad sugerida a comprar (para producir X toneladas)
     - Último precio registrado
     - Proveedor habitual

  3. "Ficha técnica":
     - Una página por ingrediente
     - Valores nutricionales completos
     - Gráfica de evolución de precios
     - Notas y restricciones de uso

CONFIGURACIÓN DE EMPRESA (en dialogs.py):
  Diálogo "Configuración":
    - Nombre de empresa/granja
    - Logo (subir PNG/JPG)
    - Responsable técnico
    - Moneda (Bs. / $ / S/. / €)
    - Pie de página personalizado
  Se guarda en tabla config_empresa
  Los PDFs usan estos datos automáticamente
"""
```

---

## BLOQUE 4 — MEJORAS VISUALES Y UX

### 4.1 — main_window.py: sidebar mejorado

```python
"""
MEJORAS A LA VENTANA PRINCIPAL

SIDEBAR:
  Iconos + texto para cada tab:
    🧪 Ingredientes
    🧮 Calcular
    📊 Gráficas
    📁 Formulaciones
    📦 Inventario      ← NUEVO con badge de alertas
    📈 Economía        ← NUEVO
    🏭 Lotes           ← NUEVO
  
  Botón "☰" para colapsar el sidebar (solo iconos, sin texto)
  Al colapsar: el contenido principal se expande
  
  En la parte inferior del sidebar:
    [🔔 N alertas]  ← badge rojo si hay alertas
    [⚙️ Configuración]
    [❓ Ayuda]

TOOLBAR SUPERIOR:
  Mostrar el nombre de la formulación activa:
  "VITAL | 🐄 Bovinos — Ración Cría Lote 3 *"
  El asterisco indica cambios sin guardar

ATAJOS DE TECLADO:
  Ctrl+S → Guardar formulación actual
  Ctrl+N → Nueva formulación
  Ctrl+E → Exportar PDF
  Ctrl+1-7 → Cambiar de tab
  F5 → Actualizar/Recalcular

DIÁLOGO DE INICIO:
  Si no hay formulaciones guardadas (primera vez):
    Mostrar wizard de 3 pasos:
    1. "Bienvenido — configura tu empresa"
    2. "Agrega tu primer animal"
    3. "Crea tu primera ración"
"""
```

### 4.2 — config.py: constantes de estilo actualizadas

```python
# app/config.py — REEMPLAZAR COMPLETO

from app.utils import get_system_font

FONT = get_system_font()

# Paleta de colores
COLORS = {
    'bg_dark':      '#1E1E2E',
    'bg_surface':   '#252538',
    'bg_deeper':    '#0F0F1E',
    'bg_border':    '#2A2A4A',
    'primary':      '#2D7D46',
    'primary_light':'#5CB85C',
    'primary_dark': '#1B4F2E',
    'accent':       '#5BC0DE',
    'warning':      '#F0AD4E',
    'danger':       '#D9534F',
    'muted':        '#6060A0',
    'text':         '#E0E0F0',
    'text_dim':     '#A0A0C0',
    'text_faint':   '#505070',
    'gold':         '#F0D060',
    # Semáforo
    'semaforo_ok':  '#1A3A2A',
    'semaforo_warn':'#3A2A0A',
    'semaforo_bad': '#3A1A1A',
}

ESTILO_TABLA = f"""
    QTableWidget {{
        background-color: {COLORS['bg_dark']};
        alternate-background-color: {COLORS['bg_surface']};
        color: {COLORS['text']};
        gridline-color: {COLORS['bg_border']};
        border: 1px solid {COLORS['bg_border']};
        font-family: "{FONT}";
        font-size: 11px;
    }}
    QTableWidget::item {{
        background-color: {COLORS['bg_dark']};
        color: {COLORS['text']};
        padding: 4px 6px;
        border: none;
    }}
    QTableWidget::item:selected {{
        background-color: {COLORS['primary']};
        color: white;
    }}
    QTableWidget::item:hover {{
        background-color: {COLORS['bg_border']};
    }}
    QHeaderView::section {{
        background-color: {COLORS['bg_deeper']};
        color: {COLORS['muted']};
        padding: 6px 8px;
        border: none;
        border-right: 1px solid {COLORS['bg_border']};
        border-bottom: 2px solid {COLORS['primary']};
        font-weight: bold;
        font-size: 10px;
        font-family: "{FONT}";
    }}
    QScrollBar:vertical {{
        background: {COLORS['bg_dark']}; width: 8px;
    }}
    QScrollBar::handle:vertical {{
        background: {COLORS['bg_border']}; border-radius: 4px; min-height: 20px;
    }}
    QScrollBar::handle:vertical:hover {{ background: {COLORS['primary']}; }}
"""

# Límites de inclusión por insumo (% máximo recomendado en la ración)
LIMITES_INCLUSION = {
    'melaza':                15.0,
    'harina de pescado':      8.0,
    'gallinaza aves':        10.0,
    'aceite vegetal':        10.0,
    'aceite de palma':       10.0,
    'aceite de soya':        10.0,
    'bagazo de caña azúcar': 20.0,
    'harina de sangre':       5.0,
    'harina de plumas':       5.0,
    'glicerina cruda':        5.0,
    'sal común (nacl)':       0.5,
    'bicarbonato de sodio':   0.5,
    'dl-metionina':           0.5,
    'lisina sintética l-lys': 1.0,
}

# Rango saludable Ca:P
CA_P_MIN = 1.2
CA_P_MAX = 2.0
```

---

## BLOQUE 5 — SCRIPTS Y EMPAQUETADO

### build_windows.bat (actualizado):
```batch
@echo off
chcp 65001 > nul
echo ========================================
echo   VITAL v2.0 - Build Windows
echo ========================================

pip install -r requirements.txt --quiet

pyinstaller ^
    --onefile ^
    --windowed ^
    --icon=logo.ico ^
    --name="VITAL" ^
    --add-data "logo.png;." ^
    --add-data "assets;assets" ^
    --hidden-import=scipy.optimize ^
    --hidden-import=scipy.optimize._linprog ^
    --hidden-import=pandas ^
    --hidden-import=numpy ^
    --hidden-import=matplotlib.backends.backend_qtagg ^
    --hidden-import=qdarkstyle ^
    --hidden-import=openpyxl ^
    --hidden-import=reportlab ^
    VITAL.spec

echo.
echo Build completado: dist/VITAL.exe
pause
```

### install.sh (Linux — actualizado):
```bash
#!/bin/bash
set -e
echo "========================================"
echo "  VITAL v2.0 - Instalación Linux"
echo "========================================"

# Verificar Python 3.11+
python3 --version

# Instalar dependencias del sistema (Ubuntu/Debian)
if command -v apt-get &> /dev/null; then
    sudo apt-get install -y python3-pip python3-venv \
        libxcb-xinerama0 libxcb-cursor0 \
        libglib2.0-0 libgl1-mesa-glx
fi

# Entorno virtual
python3 -m venv .venv
source .venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt

# Crear acceso directo en el escritorio
DESKTOP_FILE="$HOME/Desktop/VITAL.desktop"
cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Name=VITAL
Comment=Formulación Nutricional Animal
Exec=$(pwd)/.venv/bin/python $(pwd)/main.py
Icon=$(pwd)/logo.png
Terminal=false
Type=Application
Categories=Science;
EOF
chmod +x "$DESKTOP_FILE"

echo ""
echo "✅ Instalación completada."
echo "   Ejecuta: source .venv/bin/activate && python main.py"
echo "   O usa el acceso directo en tu escritorio."
```

### requirements.txt (actualizado):
```
PyQt6>=6.6.0
pandas>=2.0.0
numpy>=1.26.0
scipy>=1.11.0
matplotlib>=3.8.0
reportlab>=4.0.0
openpyxl>=3.1.0
qdarkstyle>=3.2.0
pyinstaller>=6.0.0
qrcode[pil]>=7.4.0
Pillow>=10.0.0
```

---

## ORDEN DE IMPLEMENTACIÓN

```
FASE 1 — Correcciones base (no rompe nada existente):
  1. app/utils.py          → compatibilidad multiplataforma real
  2. app/config.py         → constantes centralizadas + LIMITES_INCLUSION
  3. app/database.py       → migrar_bd_v2() + INSUMOS_ADICIONALES + nuevas tablas

FASE 2 — Mejoras a módulos existentes:
  4. ui/tab_ingredientes.py → importar/exportar Excel, duplicar, TMS, historial uso
  5. ui/tab_formulacion.py  → semáforos mejorados, versiones, etiquetas, instrucciones
  6. ui/tab_formulaciones.py → filtros avanzados, aprobar, comparar lado a lado, preview
  7. ui/tab_graficas.py      → dashboard, evolución costos, mapa de calor, barras apiladas
  8. app/exporter.py         → PDF completo, etiqueta lote, lista compras, QR code

FASE 3 — Nuevos módulos:
  9. ui/tab_inventario.py   → stock, historial precios, alerta crítico
  10. ui/tab_economia.py    → análisis económico, simulador precios
  11. ui/tab_lotes.py       → trazabilidad de producción
  12. ui/panel_alertas.py   → centro de alertas con badge

FASE 4 — UI/UX general:
  13. app/main_window.py    → sidebar mejorado, badges, atajos, wizard inicio
  14. ui/dialogs.py         → configuración empresa, logo, moneda
  15. build_windows.bat + install.sh → actualizados
```

---

## REGLAS OBLIGATORIAS

```
1. force_utf8() debe llamarse al inicio de main.py SIEMPRE
2. NUNCA hardcodear rutas — usar get_db_path() y get_exports_dir()
3. Todas las migraciones de BD usan try/except para ser idempotentes
4. ESTILO_TABLA de config.py se aplica a TODAS las tablas — sin colores crema
5. LIMITES_INCLUSION se verifica en calculator.py al calcular cualquier ración
6. Los PDFs usan datos de config_empresa de la BD (nombre, logo, moneda)
7. Todo texto en la UI en ESPAÑOL con acentos (UTF-8)
8. Los nuevos tabs se agregan al QStackedWidget en main_window.py en el orden del sidebar
9. Cada tab nuevo recibe self.db como parámetro en su constructor
10. El campo 'moneda' de config_empresa se usa en todos los costos mostrados
```

---

*VITAL v2.0 — Prompt de evolución completa*
*Sistema base: MVC Python/PyQt6/SQLite — Windows 10/11 + Ubuntu 20.04+ / Debian 11+*