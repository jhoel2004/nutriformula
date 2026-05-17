# app/calculator.py
import pandas as pd

def calcular_resultados(insumos_seleccionados, tanteos, modo='kg'):
    """
    Calcula la composición nutricional de una ración.
    - insumos_seleccionados: lista de diccionarios con datos de insumos
    - tanteos: lista de cantidades (kg o %)
    - modo: 'kg' o 'porcentaje'
    
    Retorna un diccionario con:
    - resultados_por_insumo: lista de diccionarios
    - totales: diccionario con suma de nutrientes
    """
    total_tanteo = sum(tanteos)
    
    if total_tanteo == 0:
        # Evitar división por cero
        return {"resultados_por_insumo": [], "totales": {}}
        
    proporciones = []
    if modo == 'kg':
        proporciones = [t / total_tanteo for t in tanteos]
    else:
        # Modo porcentaje: la suma debería ser idealmente 100
        # Usamos t/100 para los cálculos. Si suma > 100 se alertará en la UI.
        proporciones = [t / 100.0 for t in tanteos]

    resultados = []
    totales = {
        'proteina': 0, 'em_kcal': 0, 'fibra': 0, 'grasa': 0,
        'calcio': 0, 'fosforo': 0, 'lisina': 0, 'metionina': 0,
        'colina_mgr': 0, 'costo_kg': 0
    }
    
    for insumo, prop in zip(insumos_seleccionados, proporciones):
        # Aportes del insumo
        aporte = {
            'nombre': insumo['nombre'],
            'porcentaje': prop * 100,
            'proteina': insumo.get('proteina', 0) * prop,
            'em_kcal': insumo.get('em_kcal', 0) * prop,
            'fibra': insumo.get('fibra', 0) * prop,
            'grasa': insumo.get('grasa', 0) * prop,
            'calcio': insumo.get('calcio', 0) * prop,
            'fosforo': insumo.get('fosforo', 0) * prop,
            'lisina': insumo.get('lisina', 0) * prop,
            'metionina': insumo.get('metionina', 0) * prop,
            'colina_mgr': insumo.get('colina_mgr', 0) * prop,
            'costo': insumo.get('precio_kg', 0) * prop
        }
        resultados.append(aporte)
        
        # Sumar a totales
        totales['proteina'] += aporte['proteina']
        totales['em_kcal'] += aporte['em_kcal']
        totales['fibra'] += aporte['fibra']
        totales['grasa'] += aporte['grasa']
        totales['calcio'] += aporte['calcio']
        totales['fosforo'] += aporte['fosforo']
        totales['lisina'] += aporte['lisina']
        totales['metionina'] += aporte['metionina']
        totales['colina_mgr'] += aporte['colina_mgr']
        totales['costo_kg'] += aporte['costo']
        
    return {
        "resultados_por_insumo": resultados,
        "totales": totales,
        "suma_tanteos": total_tanteo,
        "suma_porcentajes": sum(p['porcentaje'] for p in resultados)
    }

def evaluar_cumplimiento(valor_calculado, nutriente, requerimientos_especie):
    """
    Evalúa si un nutriente cumple con el requerimiento.
    Retorna: 'verde' (cumple), 'amarillo' (dentro del 10%), 'rojo' (no cumple)
    """
    req = requerimientos_especie
    if not req:
        return 'verde' # No hay restricciones (ej. Personalizado sin datos)
        
    min_key = f"{nutriente}_min"
    max_key = f"{nutriente}_max"
    
    estado = 'verde'
    
    val_min = req.get(min_key, None)
    val_max = req.get(max_key, None)
    
    # Evaluar mínimo
    if val_min is not None:
        if valor_calculado < val_min:
            if valor_calculado >= val_min * 0.9:
                estado = 'amarillo'
            else:
                return 'rojo'
                
    # Evaluar máximo
    if val_max is not None:
        if valor_calculado > val_max:
            if valor_calculado <= val_max * 1.1:
                if estado != 'rojo': # Si ya era rojo por el mínimo, se queda rojo
                    estado = 'amarillo'
            else:
                return 'rojo'
                
    return estado

# ══════════════════════════════════════════════════════════════════════
# Límites máximos de inclusión por insumo (% de la ración total)
# Basados en literatura zootécnica. Superarlos puede causar problemas
# de salud, sabor, textura o toxicidad.
# ══════════════════════════════════════════════════════════════════════
LIMITES_INCLUSION = {
    "harina de pescado": {"max_pct": 10.0, "razon": "Sabor y olor desagradable en carne/huevos"},
    "melaza": {"max_pct": 15.0, "razon": "Exceso de humedad y problemas digestivos"},
    "aceite vegetal": {"max_pct": 8.0, "razon": "Afecta textura del pellet y digestibilidad"},
    "gallinaza aves": {"max_pct": 10.0, "razon": "Riesgo sanitario (patógenos)"},
    "pasta de algodón": {"max_pct": 15.0, "razon": "Gossipol: tóxico en monogástricos"},
    "harina de carne": {"max_pct": 12.0, "razon": "Riesgo sanitario y regulación"},
    "achiote": {"max_pct": 5.0, "razon": "Pigmento concentrado, puede alterar color"},
    "bagazo de caña azúcar": {"max_pct": 10.0, "razon": "Alta fibra indigerible"},
    "heno de avena molida": {"max_pct": 15.0, "razon": "Muy fibroso, baja digestibilidad"},
    "heno de cebada molida": {"max_pct": 15.0, "razon": "Muy fibroso, baja digestibilidad"},
}


def calcular_ratio_ca_p(totales):
    """
    Calcula la relación Calcio:Fósforo.
    Retorna (ratio, estado, mensaje).
    - ratio: float (ej. 1.5)
    - estado: 'verde', 'amarillo', 'rojo'
    - mensaje: str descriptivo
    
    Rango saludable: 1.2:1 a 2.0:1 (para la mayoría de especies)
    """
    calcio = totales.get('calcio', 0)
    fosforo = totales.get('fosforo', 0)

    if fosforo <= 0:
        if calcio <= 0:
            return 0, 'verde', "Ca:P — Sin datos suficientes"
        return float('inf'), 'rojo', f"⚠️ Ca:P — Fósforo es 0. Relación indefinida (Ca={calcio:.3f}%)"

    ratio = calcio / fosforo

    if 1.2 <= ratio <= 2.0:
        return ratio, 'verde', f"✅ Ca:P = {ratio:.2f}:1 (Rango saludable: 1.2–2.0)"
    elif 1.0 <= ratio < 1.2 or 2.0 < ratio <= 2.5:
        return ratio, 'amarillo', f"⚠️ Ca:P = {ratio:.2f}:1 (Ligeramente fuera del rango 1.2–2.0)"
    else:
        if ratio < 1.0:
            return ratio, 'rojo', f"🔴 Ca:P = {ratio:.2f}:1 — Exceso de Fósforo relativo. Riesgo de descalcificación."
        else:
            return ratio, 'rojo', f"🔴 Ca:P = {ratio:.2f}:1 — Exceso de Calcio. Puede interferir con absorción de minerales."


def verificar_limites_inclusion(insumos_sel, tanteos, modo='kg'):
    """
    Verifica si algún insumo seleccionado supera su límite máximo de inclusión.
    Retorna lista de alertas: [{nombre, porcentaje_usado, max_permitido, razon}]
    """
    total = sum(tanteos)
    if total == 0:
        return []

    alertas = []
    for insumo, tanteo in zip(insumos_sel, tanteos):
        if modo == 'kg':
            pct = (tanteo / total) * 100
        else:
            pct = tanteo

        nombre_lower = insumo['nombre'].lower().strip()
        if nombre_lower in LIMITES_INCLUSION:
            limite = LIMITES_INCLUSION[nombre_lower]
            if pct > limite['max_pct']:
                alertas.append({
                    'nombre': insumo['nombre'],
                    'porcentaje_usado': pct,
                    'max_permitido': limite['max_pct'],
                    'razon': limite['razon']
                })
    return alertas


def auditar_insumo(insumo):
    """
    Verifica si un insumo tiene datos críticos incompletos.
    Retorna lista de advertencias (vacía si todo está bien).
    """
    advertencias = []
    nombre = insumo.get('nombre', '?')

    # Campos críticos: proteína y energía no pueden ser ambos 0
    if insumo.get('proteina', 0) == 0 and insumo.get('em_kcal', 0) == 0:
        advertencias.append(f"Proteína y Energía en 0")

    if insumo.get('precio_kg', 0) == 0:
        advertencias.append(f"Precio no definido")

    # Campos que deberían tener algún valor (al menos uno de estos)
    minerales = ['calcio', 'fosforo']
    if all(insumo.get(m, 0) == 0 for m in minerales):
        advertencias.append(f"Calcio y Fósforo en 0")

    return advertencias
