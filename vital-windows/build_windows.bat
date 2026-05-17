@echo off
chcp 65001 >nul
echo ============================================
echo    VITAL - Compilador para Windows
echo ============================================
echo.

:: Verificar Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python no esta instalado.
    echo Descargalo desde https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [1/4] Instalando dependencias...
pip install --upgrade pip
pip install PyQt6 pandas matplotlib numpy scipy openpyxl reportlab qdarkstyle darkdetect pyinstaller

echo.
echo [2/4] Verificando archivos...
if not exist "data\nutriformula.db" (
    echo ERROR: No se encuentra data\nutriformula.db
    pause
    exit /b 1
)
if not exist "logo.png" (
    echo ADVERTENCIA: No se encuentra logo.png (el ejecutable no tendra icono)
)

echo.
echo [3/4] Compilando VITAL.exe...
pyinstaller --clean VITAL.spec

echo.
echo [4/4] Verificando resultado...
if exist "dist\VITAL\VITAL.exe" (
    echo.
    echo ============================================
    echo    COMPILACION EXITOSA!
    echo ============================================
    echo.
    echo El ejecutable se encuentra en:
    echo   dist\VITAL\VITAL.exe
    echo.
    echo Puedes distribuir toda la carpeta dist\VITAL\
    echo.
    echo Para abrir la carpeta, ejecuta:
    echo   explorer dist\VITAL
    echo ============================================
) else (
    echo.
    echo ERROR: No se encontro VITAL.exe en dist\VITAL\
    echo Revisa los mensajes de error anteriores.
)

echo.
pause
