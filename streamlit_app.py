"""
Página Principal / Entrypoint de Navegación Streamlit
"""
import streamlit as st

st.set_page_config(
    page_title="Yahoo NBA Fantasy Assistant",
    page_icon="🏀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Definición de páginas usando st.navigation nativo
pg_dashboard = st.Page("pages/0_Dashboard.py", title="Inicio / Dashboard", icon="🏠", default=True)
pg_draft = st.Page("pages/1_Draft_Assistant.py", title="Snake Draft Assistant", icon="🎯")
pg_weekly = st.Page("pages/2_Resumen_Semanal.py", title="Resumen Semanal", icon="📊")
pg_trades = st.Page("pages/3_Trade_and_Waivers.py", title="Traspasos & Waivers", icon="🔄")
pg_streamers = st.Page("pages/4_Calendario_Streamers.py", title="Calendario Streamers", icon="📅")

pg = st.navigation({
    "Menú Principal": [pg_dashboard],
    "Herramientas en Vivo": [pg_draft, pg_weekly, pg_trades, pg_streamers]
})

pg.run()
