"""
Página Principal / Dashboard de Inicio del Asistente de NBA Fantasy Yahoo.
"""

import streamlit as st
import pandas as pd
import json
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.auth.yahoo_client import YahooFantasyClient

st.set_page_config(
    page_title="Yahoo NBA Fantasy Assistant (Points & Snake)",
    page_icon="🏀",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🏀 Yahoo NBA Fantasy Assistant")
st.caption("Tu centro de mando para el Draft Snake por Puntos Fantasy (FPPG), análisis semanal y optimización de traspasos y waivers.")

# Sidebar: Conexión y Estado
st.sidebar.title("⚙️ Configuración & Conexión")

st.sidebar.subheader("📌 Navegación")
st.sidebar.page_link("app/app.py", label="🏠 Inicio / Dashboard", icon="🏠")
st.sidebar.page_link("app/pages/1_🎯_Draft_Assistant.py", label="🎯 1. Snake Draft Assistant", icon="🎯")
st.sidebar.page_link("app/pages/2_📊_Resumen_Semanal.py", label="📊 2. Resumen Semanal", icon="📊")
st.sidebar.page_link("app/pages/3_🔄_Trade_&_Waivers.py", label="🔄 3. Traspasos & Waivers", icon="🔄")
st.sidebar.page_link("app/pages/4_📅_Calendario_Streamers.py", label="📅 4. Calendario Streamers", icon="📅")

st.sidebar.divider()

league_type = st.sidebar.selectbox("Formato de tu Liga:", ["Points League (Ligas por Puntos / FPPG)", "9-Categories H2H (Categorías)"])
st.session_state["league_format_type"] = "points" if "Points" in league_type else "9-cat"

auth_mode = st.sidebar.radio("Fuente de Datos:", ["Modo Demo / Simulado", "Yahoo Fantasy API (Cuenta Personal)"])

oauth_path = "config/oauth2.json"
yahoo_client = None

if auth_mode == "Yahoo Fantasy API (Cuenta Personal)":
    if os.path.exists(oauth_path):
        yahoo_client = YahooFantasyClient(oauth_file=oauth_path, use_mock=False)
        if yahoo_client.is_authenticated:
            st.sidebar.success("✅ Conectado a tu cuenta de Yahoo Fantasy")
        else:
            st.sidebar.warning("⚠️ No se pudo autenticar. Usando datos Demo.")
            yahoo_client = YahooFantasyClient(use_mock=True)
    else:
        st.sidebar.info("ℹ️ Ingresa tus credenciales personales abajo para conectar.")
        yahoo_client = YahooFantasyClient(use_mock=True)
else:
    yahoo_client = YahooFantasyClient(use_mock=True)
    st.sidebar.success("🟢 Modo Demo Activo (Listo para usar sin configuración)")

st.session_state["yahoo_client"] = yahoo_client

st.divider()

# Menú Principal usando contenedores nativos (compatibles 100% con Dark y Light Mode)
col1, col2 = st.columns(2)

with col1:
    with st.container(border=True):
        st.subheader("🎯 1. Snake Draft Assistant en Vivo")
        st.markdown("""
        **Herramienta diseñada para usar durante el draft en vivo de tu liga de puntos:**
        - **Turnos Snake Automáticos:** Calcula quién elige en cada turno (1→N, N→1) y te avisa cuántos picks faltan para tu turno.
        - **Rankings por FPPG y VORP:** Ordena a los jugadores por Puntos Fantasy por Partido y Valor sobre Reemplazo.
        - **Detección de Necesidades:** Sugerencias ajustadas a las posiciones de tu quinteto.
        """)
        st.page_link("app/pages/1_🎯_Draft_Assistant.py", label="👉 Abrir Snake Draft Assistant", icon="🎯")

    with st.container(border=True):
        st.subheader("🔄 3. Evaluador de Traspasos & Waivers")
        st.markdown("""
        **Simulador inteligente para tomar decisiones en el mercado:**
        - **Trade Machine:** Compara la ganancia neta en Puntos Fantasy (FPPG) antes de aceptar un trade.
        - **Waiver Targets:** Filtra los mejores agentes libres disponibles ordenados por producción real.
        """)
        st.page_link("app/pages/3_🔄_Trade_&_Waivers.py", label="👉 Abrir Evaluador de Traspasos & Waivers", icon="🔄")

with col2:
    with st.container(border=True):
        st.subheader("📊 2. Resumen Semanal de Puntos")
        st.markdown("""
        **Diagnóstico profundo de tu rendimiento semana a semana:**
        - **Marcador H2H Semanal:** Puntos totales acumulados frente a tu rival (ej: 1240 pts vs 1180 pts).
        - **All-Play Power Rankings:** Simula tus puntos contra todos los rivales para saber si hubieras ganado esa semana contra el resto de la liga.
        - **Importación Directa:** Pega el texto de Matchups de Yahoo en 5 segundos.
        """)
        st.page_link("app/pages/2_📊_Resumen_Semanal.py", label="👉 Abrir Resumen Semanal", icon="📊")

    with st.container(border=True):
        st.subheader("📅 4. Calendario & Optimizador de Streamers")
        st.markdown("""
        **Maximiza tus puntos semanales con fichajes temporales:**
        - **Detección de Off-Days:** Equipos que juegan en días con pocos partidos (Mar, Jue, Sáb) para sumar partidos extra.
        - **Streaming Score:** Puntos fantasy proyectados = *(Partidos favorables × FPPG)*.
        """)
        st.page_link("app/pages/4_📅_Calendario_Streamers.py", label="👉 Abrir Calendario de Streamers", icon="📅")

st.divider()

# Sección de Configuración de Yahoo API para Uso Personal
st.subheader("🔑 Conectar tu Cuenta de Yahoo Fantasy (Opcional)")

with st.expander("📝 Guía Paso a Paso para obtener tus Claves de Yahoo (Solo 2 minutos)"):
    st.markdown("""
    **¿Se puede hacer para uso personal?** ¡Sí, absolutamente! Yahoo permite que cualquier usuario cree una clave privada para su propia cuenta:

    1. **Entra al portal de desarrolladores:** Ve a [Yahoo Developer Apps](https://developer.yahoo.com/apps/create/) e inicia sesión con la misma cuenta de Yahoo con la que juegas al Fantasy.
    2. **Completa los campos:**
       - **Application Name:** `Mi Fantasy Assistant`
       - **Application Type:** Selecciona **Installed Application**
       - **Redirect URI:** Escribe `https://localhost` o `oob`
       - **API Permissions:** Marca la casilla **Fantasy Sports** (con permiso *Read*).
    3. **Haz clic en "Create App"** y copia tu **Client ID** y **Client Secret**.
    4. Pégalos en el formulario de abajo y haz clic en **Guardar Credenciales**.
    """)

col_k1, col_k2 = st.columns(2)
with col_k1:
    input_client_id = st.text_input("Client ID (Consumer Key):", type="password")
with col_k2:
    input_client_secret = st.text_input("Client Secret (Consumer Secret):", type="password")

if st.button("💾 Guardar Credenciales y Conectar con Yahoo"):
    if input_client_id and input_client_secret:
        creds = {
            "consumer_key": input_client_id.strip(),
            "consumer_secret": input_client_secret.strip()
        }
        os.makedirs("config", exist_ok=True)
        with open("config/oauth2.json", "w", encoding="utf-8") as f:
            json.dump(creds, f, indent=2)
        st.success("✅ Credenciales guardadas exitosamente en config/oauth2.json. Ahora puedes seleccionar 'Yahoo Fantasy API' en el menú lateral.")
        st.rerun()
    else:
        st.warning("Por favor ingresa tanto el Client ID como el Client Secret.")
