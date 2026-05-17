@echo off
echo ========================================
echo   Construyendo VITAL para Windows
echo ========================================

:: Instalar dependencias necesarias
pip install pyinstaller qdarkstyle pandas darkdetect openpyxl PyQt6

:: Ejecutar PyInstaller usando el archivo .spec
pyinstaller --clean VITAL.spec

echo.
echo ========================================
echo   Proceso completado. 
echo   Busca el ejecutable en la carpeta 'dist/VITAL'
echo ========================================
pause
