@echo off
chcp 65001 >nul
echo ============================================
echo    VITAL - Instalador para Windows
echo ============================================
echo.

:: Verificar Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python no esta instalado.
    echo Descargalo desde https://www.python.org/downloads/
    echo IMPORTANTE: Marca la opcion "Add Python to PATH" durante la instalacion.
    pause
    exit /b 1
)

echo [1/3] Creando entorno virtual...
python -m venv venv
if %errorlevel% neq 0 (
    echo ERROR: No se pudo crear el entorno virtual.
    pause
    exit /b 1
)

echo.
echo [2/3] Instalando dependencias...
call venv\Scripts\activate.bat
pip install --upgrade pip
pip install PyQt6 pandas matplotlib numpy scipy openpyxl reportlab qdarkstyle darkdetect

echo.
echo [3/3] Iniciando VITAL...
python main.py

echo.
echo ============================================
echo    Para ejecutar VITAL en el futuro:
echo ============================================
echo    1. Abre una terminal en esta carpeta
echo    2. Ejecuta: run.bat
echo ============================================
pause
