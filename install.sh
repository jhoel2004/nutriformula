#!/bin/bash
echo "Creando entorno virtual (venv)..."
python3 -m venv venv
echo "Activando entorno virtual..."
source venv/bin/activate
echo "Instalando dependencias de VITAL..."
pip install -r requirements.txt
echo "Iniciando VITAL..."
python main.py
