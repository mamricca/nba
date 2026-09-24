"""
Entrypoint para Streamlit Cloud
"""
import os
import sys

# Redirigir a app/app.py
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# Ejecutar app.py
from app.app import *
