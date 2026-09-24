"""
Página: Calendario Semanal y Optimizador de Jugadores Streamers
"""

import streamlit as st
import pandas as pd
import json
import os
import sys

sys.path.append(os.path.abspath(os.path.dirname(__file__) + "/.."))

from src.auth.yahoo_client import YahooFantasyClient
from src.analytics.streamer_finder import StreamerFinder

st.title("📅 Calendario NBA & Optimizador de Streamers")
st.caption("Planifica tus fichajes semanales maximizando partidos en días de bajo volumen (Off-Days: Mar/Jue/Sáb/Dom) para no dejar huecos en tu quinteto.")

finder = StreamerFinder(schedule_file="data/nba_schedule_sample.json")
client: YahooFantasyClient = st.session_state.get("yahoo_client", YahooFantasyClient(use_mock=True))

available_weeks = finder.get_available_weeks()
week_options = [f"Semana {w.replace('Week ', '')}" for w in available_weeks]

col_w1, col_w2, col_w3 = st.columns([1.5, 1.5, 2])
with col_w1:
    selected_week_label = st.selectbox("📅 Selecciona la Semana a Analizar:", week_options, index=0)
    selected_week_key = selected_week_label.replace("Semana ", "Week ")

with col_w2:
    league_mode = st.radio("🏆 Modo de Liga:", ["Puntos Fantasy (FPPG)", "Categorías (9-Cat)"], horizontal=True)

with col_w3:
    st.write("")
    with st.popover("⚙️ Importar / Editar Calendario"):
        st.markdown("**Personalizar Calendario Semanal**")
        pasted_sched = st.text_area("Pega aquí un JSON de calendario personalizado:", height=150, help="Estructura: {'weeks': {'Week 1': {'ATL': {'total': 4, 'days': {...}}}}}")
        if st.button("💾 Guardar Calendario"):
            try:
                parsed_json = json.loads(pasted_sched)
                with open("data/nba_schedule_sample.json", "w", encoding="utf-8") as f:
                    json.dump(parsed_json, f, indent=2)
                st.success("✅ Calendario actualizado exitosamente!")
                st.rerun()
            except Exception as e:
                st.error(f"Error en formato JSON: {e}")

# 1. Resumen de Calendario de la Semana
st.subheader(f"🗓️ Densidad de Partidos por Equipo ({selected_week_label})")

df_schedule = finder.get_team_schedule_summary(selected_week_key)

if not df_schedule.empty:
    teams_4_games = df_schedule[df_schedule["Total_Games"] >= 4]["Team"].tolist()
    teams_2_games = df_schedule[df_schedule["Total_Games"] <= 2]["Team"].tolist()
    top_off_day_teams = df_schedule[df_schedule["Off_Day_Games (Mar/Jue/Sab/Dom)"] >= 3]["Team"].tolist()

    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric("🔥 Equipos con 4 Partidos", f"{len(teams_4_games)} equipos", delta=f"{', '.join(teams_4_games[:5])}...")
    with m2:
        st.metric("⭐ Reyes de Off-Days (Mar/Jue/Sáb/Dom)", f"{len(top_off_day_teams)} equipos", delta=f"{', '.join(top_off_day_teams[:4])}...")
    with m3:
        st.metric("⚠️ Equipos con 2 Partidos (Evitar)", f"{len(teams_2_games)} equipos", delta=f"{', '.join(teams_2_games) if teams_2_games else 'Ninguno'}")

    st.markdown("**Matriz de Partidos por Día:**")
    st.dataframe(
        df_schedule,
        use_container_width=True,
        height=320,
        hide_index=True
    )
else:
    st.warning("No se encontraron datos de calendario para esta semana.")

st.divider()

# 2. Recomendador de Streamers de Agencia Libre
st.subheader(f"🎯 Mejores Streamers en la Agencia Libre ({selected_week_label})")
st.markdown("Calcula automáticamente qué agentes libres te darán **la mayor cantidad de puntos netos** jugando en los días donde tienes huecos en tu quinteto:")

fa_list = client.get_free_agents()
df_fa = pd.DataFrame(fa_list)

col_f1, col_f2, col_f3 = st.columns([2, 1, 1])
with col_f1:
    if league_mode == "Categorías (9-Cat)":
        stream_cats = st.multiselect(
            "Categorías a reforzar esta semana:",
            ["PTS", "REB", "AST", "STL", "BLK", "3PM", "FG%", "FT%"],
            default=["3PM", "STL", "PTS"]
        )
    else:
        st.info("💡 **Modo Puntos**: Pondera automáticamente por FPPG proyectado, partidos totales y bonus en Off-Days.")
        stream_cats = None

with col_f2:
    pos_stream_filter = st.selectbox("Filtrar por Posición:", ["TODAS", "PG", "SG", "SF", "PF", "C"])

with col_f3:
    top_n_streamers = st.slider("Cantidad de recomendaciones:", 5, 25, 12)

if not df_fa.empty:
    if pos_stream_filter != "TODAS":
        df_fa = df_fa[df_fa["position"].str.contains(pos_stream_filter, na=False)]

    mode_param = "points" if "Puntos" in league_mode else "categories"
    df_streamers = finder.find_best_streamers(
        free_agents_df=df_fa,
        target_categories=stream_cats,
        week_str=selected_week_key,
        top_n=top_n_streamers,
        league_mode=mode_param
    )

    if not df_streamers.empty:
        disp_cols = ["Rank", "name", "team", "position", "Streamer_Score", "Week_Games", "Off_Day_Games", "FPPG", "PTS", "REB", "AST", "STL", "BLK", "3PM"]
        
        col_st_cfg = {
            "Streamer_Score": st.column_config.ProgressColumn("Streamer Score", format="%.1f", min_value=0.0, max_value=180.0),
            "FPPG": st.column_config.NumberColumn("FPPG Proy", format="%.1f"),
            "Week_Games": st.column_config.NumberColumn("Partidos Sem.", format="%d 🏀"),
            "Off_Day_Games": st.column_config.NumberColumn("Off-Days", format="%d ⭐"),
            "PTS": st.column_config.NumberColumn("PTS", format="%.1f"),
            "REB": st.column_config.NumberColumn("REB", format="%.1f"),
            "AST": st.column_config.NumberColumn("AST", format="%.1f"),
            "STL": st.column_config.NumberColumn("STL", format="%.1f"),
            "BLK": st.column_config.NumberColumn("BLK", format="%.1f"),
            "3PM": st.column_config.NumberColumn("3PM", format="%.1f"),
        }

        st.dataframe(
            df_streamers[[c for c in disp_cols if c in df_streamers.columns]],
            column_config=col_st_cfg,
            use_container_width=True,
            hide_index=True
        )

        st.write("")
        # Acción rápida de fichaje directo
        with st.expander("⚡ Fichaje Rápido de Streamer (Añadir a mi plantilla)"):
            c_fich1, c_fich2 = st.columns([3, 1])
            with c_fich1:
                streamer_to_add = st.selectbox("Selecciona jugador para fichar:", df_streamers["name"].tolist())
            with c_fich2:
                st.write("")
                if st.button("➕ Fichar Ahora", type="primary", use_container_width=True):
                    client.add_player_to_team("nba.l.123456.t.1", streamer_to_add)
                    st.success(f"🎉 ¡{streamer_to_add} añadido a tu equipo!")
                    st.rerun()
    else:
        st.info("No hay jugadores que coincidan con los filtros seleccionados.")
else:
    st.info("No hay agentes libres disponibles para calcular streaming.")
