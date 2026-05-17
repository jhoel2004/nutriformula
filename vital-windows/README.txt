# VITAL - Formulacion de Raciones
## Version para Windows

Aplicacion de escritorio para la formulacion nutricional de raciones animales.

---

## Requisitos del Sistema

- Windows 10/11 (64 bits)
- Python 3.10 o superior (https://www.python.org/downloads/)

---

## Opcion 1: Ejecutar sin compilar (recomendado para desarrollo)

1. Abre una terminal (cmd o PowerShell) en esta carpeta
2. Ejecuta:
   ```
   install_windows.bat
   ```
3. Se instalara todo automaticamente y se abrira VITAL

**Para ejecutar en el futuro:**
```
run.bat
```

---

## Opcion 2: Generar VITAL.EXE (para distribucion)

1. Abre una terminal en esta carpeta
2. Ejecuta:
   ```
   build_windows.bat
   ```
3. Espera a que termine la compilacion
4. El ejecutable estara en: `dist\VITAL\VITAL.exe`

**Para distribuir:** Copia toda la carpeta `dist\VITAL\` a otra computadora.
No requiere Python instalado.

---

## Estructura del Proyecto

```
vital-windows/
├── main.py                 # Punto de entrada
├── app/                    # Logica de negocio
│   ├── database.py         # Base de datos SQLite
│   ├── calculator.py       # Calculos nutricionales
│   ├── exporter.py         # Exportar PDF/Excel
│   ├── config.py           # Configuracion
│   └── utils.py            # Utilidades
├── ui/                     # Interfaz grafica
│   ├── dialogs.py          # Dialogos
│   ├── tab_ingredientes.py # Tab de insumos
│   ├── tab_calcular.py     # Tab de calculo
│   ├── tab_formulacion.py  # Formulacion manual
│   ├── tab_formulacion_inversa.py  # Autoformular
│   ├── tab_formulaciones.py        # Historial
│   └── tab_graficas.py     # Graficas
├── data/
│   └── nutriformula.db     # Base de datos
├── logo.png                # Icono
├── VITAL.spec              # Configuracion PyInstaller
├── build_windows.bat       # Script de compilacion
├── install_windows.bat     # Script de instalacion
├── run.bat                 # Script de ejecucion
└── requirements.txt        # Dependencias
```

---

## Funcionalidades

- **Insumos**: CRUD completo con import/export Excel
- **Formulacion manual**: Tanteo por kg/%, calculo automatico
- **Autoformular**: Optimizacion automatica por programacion lineal
- **Graficas**: Torta, barras, costos (matplotlib)
- **Historial**: Guardar/cargar/duplicar formulaciones
- **Animales**: 8 especies predefinidas
- **Exportar**: PDF y Excel

---

## Solucion de Problemas

### "Python no esta instalado"
Descarga Python desde https://www.python.org/downloads/
IMPORTANTE: Marca "Add Python to PATH" durante la instalacion.

### Error de dependencias
Ejecuta manualmente:
```
pip install -r requirements.txt
```

### El ejecutable no abre
Verifica que tengas todos los archivos de la carpeta `dist\VITAL\`
No muevas solo VITAL.exe, necesita las carpetas acompanantes.

---

(c) 2026 FAMVET - VITAL v1.0
