"""
Página: Calendario Semanal y Optimizador de Jugadores Streamers
"""

import streamlit as st
import pandas as pd
import os
import sys

sys.path.append(os.path.abspath(os.path.dirname(__file__) + "/.."))

from src.auth.yahoo_client import YahooFantasyClient
from src.analytics.streamer_finder import StreamerFinder

st.title("📅 Calendario NBA & Optimizador de Streamers")
st.caption("Planifica tus fichajes semanales maximizando partidos en días de bajo volumen (Off-Days) para no dejar huecos en tu quinteto.")

finder = StreamerFinder(schedule_file="data/nba_schedule_sample.json")
client: YahooFantasyClient = st.session_state.get("yahoo_client", YahooFantasyClient(use_mock=True))

# 1. Resumen de Calendario de la Semana
st.subheader("🗓️ Densidad de Partidos por Equipo (Semana 1)")

df_schedule = finder.get_team_schedule_summary("Week 1")

if not df_schedule.empty:
    col_sched1, col_sched2 = st.columns([3, 1])
    
    with col_sched1:
        st.markdown("**Matriz de Partidos por Día:**")
        st.dataframe(
            df_schedule.style.background_gradient(subset=["Off_Day_Games (Tue/Thu/Sat/Sun)", "Total_Games"], cmap="Blues"),
            use_container_width=True,
            height=350
        )

    with col_sched2:
        with st.container(border=True):
            st.subheader("💡 Estrategia de Streaming")
            st.markdown("""
            Los días con **pocos partidos (Mar, Jue, Sáb)** son clave porque es cuando tienes posiciones libres en tu alineación inicial.
            
            Prioriza equipos con **3 o 4 partidos** que jueguen en esos días clave (ej: **CLE, GSW, LAL, PHX, SAS**).
            """)
else:
    st.warning("No se encontraron datos de calendario.")

st.divider()

# 2. Recomendador de Streamers de Agencia Libre
st.subheader("🎯 Mejores Opciones de Streaming en la Agencia Libre")

# Cargar agentes libres
fa_list = client.get_free_agents()
df_fa = pd.DataFrame(fa_list)

col_f1, col_f2 = st.columns([2, 1])
with col_f1:
    stream_cats = st.multiselect(
        "Estadísticas que buscas sumar esta semana:",
        ["PTS", "REB", "AST", "STL", "BLK", "3PM", "FG%", "FT%"],
        default=["3PM", "STL", "PTS"]
    )
with col_f2:
    top_n_streamers = st.slider("Cantidad de recomendaciones:", 5, 20, 10)

if not df_fa.empty:
    df_streamers = finder.find_best_streamers(
        free_agents_df=df_fa,
        target_categories=stream_cats,
        week_str="Week 1",
        top_n=top_n_streamers
    )

    st.markdown("**Ranking de Streamers (Ponderado por partidos en Off-Days y rendimiento estadístico):**")
    
    disp_cols = ["Rank", "name", "team", "position", "Streamer_Score", "Week_Games", "Off_Day_Games", "PTS", "REB", "AST", "STL", "BLK", "3PM", "FG%", "FT%"]
    st.dataframe(
        df_streamers[[c for c in disp_cols if c in df_streamers.columns]],
        use_container_width=True
    )
else:
    st.info("No hay agentes libres disponibles para calcular streaming.")
