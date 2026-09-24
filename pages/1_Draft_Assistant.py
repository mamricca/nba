"""
Página: Live Snake Draft Assistant (Ligas de Puntos & Categorías)
"""

import streamlit as st
import pandas as pd
import os
import sys

sys.path.append(os.path.abspath(os.path.dirname(__file__) + "/.."))

from src.core.points_engine import PointsLeagueEngine
from src.draft.draft_manager import DraftManager

# Cargar formato elegido en sesión o por defecto puntos
league_format = st.session_state.get("league_format_type", "points")

st.title("🎯 Live Snake Draft Assistant")
st.caption(f"Tablero en tiempo real con orden Snake y rankings por {'Puntos Fantasy (FPPG) y VORP' if league_format == 'points' else 'Z-Scores de Categorías'}.")

@st.cache_data
def load_base_projections():
    csv_path = "data/projections_sample.csv"
    if os.path.exists(csv_path):
        return pd.read_csv(csv_path)
    return pd.DataFrame()

df_projections = load_base_projections()

if df_projections.empty:
    st.error("No se encontró el archivo data/projections_sample.csv")
    st.stop()

# Inicializar o recuperar DraftManager
if "draft_manager" not in st.session_state:
    st.session_state["draft_manager"] = DraftManager(
        projections_df=df_projections,
        num_teams=12,
        my_team_index=1,
        league_format=league_format,
        state_file="data/draft_state.json"
    )

draft_mgr: DraftManager = st.session_state["draft_manager"]
draft_mgr.set_league_format(league_format)

# Sidebar: Configuración del Draft Snake
st.sidebar.header("🐍 Configuración del Snake Draft")
num_teams = st.sidebar.number_input("Número de Equipos en la Liga:", min_value=4, max_value=20, value=draft_mgr.num_teams)
my_team_index = st.sidebar.number_input("Tu Posición / Turno en el Draft (1 a N):", min_value=1, max_value=num_teams, value=draft_mgr.my_team_index)
draft_mgr.num_teams = num_teams
draft_mgr.my_team_index = my_team_index

st.sidebar.divider()
st.sidebar.subheader("🎯 Sistema de Puntos Fantasy (FPPG)")
with st.sidebar.expander("Modificar valores de puntuación"):
    st.caption("Puntos por cada acción estadística:")
    pts_val = st.number_input("Puntos (PTS):", value=1.0, step=0.1)
    reb_val = st.number_input("Rebotes (REB):", value=1.2, step=0.1)
    ast_val = st.number_input("Asistencias (AST):", value=1.5, step=0.1)
    stl_val = st.number_input("Robos (STL):", value=3.0, step=0.1)
    blk_val = st.number_input("Tapones (BLK):", value=3.0, step=0.1)
    tpm_val = st.number_input("Triples (3PM):", value=1.0, step=0.1)
    to_val = st.number_input("Pérdidas (TO):", value=-1.0, step=0.1)
    
    # Actualizar reglas si cambian
    new_rules = {"PTS": pts_val, "REB": reb_val, "AST": ast_val, "STL": stl_val, "BLK": blk_val, "3PM": tpm_val, "TO": to_val}
    draft_mgr.points_engine.scoring_rules = new_rules

st.sidebar.divider()
if st.sidebar.button("↩️ Deshacer Último Pick"):
    undone = draft_mgr.undo_last_pick()
    if undone:
        st.sidebar.success(f"Se canceló la selección de {undone['player']}")
        st.rerun()
    else:
        st.sidebar.info("No hay selecciones para deshacer.")

if st.sidebar.button("🗑️ Reiniciar Draft"):
    draft_mgr.reset_draft()
    st.sidebar.warning("Draft reiniciado.")
    st.rerun()

# 1. Estado del Snake Draft y Turnos
total_picks = len(draft_mgr.pick_history)
current_overall_pick = total_picks + 1
current_round = (total_picks // num_teams) + 1
team_on_clock = draft_mgr.get_snake_team_on_clock(current_overall_pick)
is_my_turn = (team_on_clock == my_team_index)
picks_until_my_turn, next_my_pick = draft_mgr.get_picks_until_my_turn()

# Banner de Turno Snake
if is_my_turn:
    st.success(f"🚨 **¡ES TU TURNO DE ELEGIR!** — Pick global #{current_overall_pick} (Ronda {current_round})", icon="🔥")
else:
    st.info(f"🐍 **Turno actual (Snake):** Eligiendo **Equipo {team_on_clock}** (Pick #{current_overall_pick} - Ronda {current_round}) | ⏳ Faltan **{picks_until_my_turn} picks** para tu próximo turno (Tu Pick #{next_my_pick}).", icon="ℹ️")

# Métricas Superiores
col_m1, col_m2, col_m3, col_m4 = st.columns(4)
with col_m1:
    st.metric("Pick Actual / Ronda", f"Pick #{current_overall_pick} (R{current_round})")
with col_m2:
    st.metric("Tus Picks Próximos (Snake)", ", ".join([f"#{p}" for p in draft_mgr.get_my_upcoming_picks()[:5]]))
with col_m3:
    st.metric("Tu Plantilla", f"{len(draft_mgr.my_roster)} / 13 Jugadores")
with col_m4:
    coverage = draft_mgr.get_positional_coverage()
    coverage_str = " | ".join([f"{k}:{v}" for k, v in coverage.items()])
    st.metric("Posiciones Cubiertas", coverage_str)

st.divider()

# 2. Registro de Pick Rápido con Autoselección Snake
st.subheader("⚡ Registrar Selección en el Draft")
p_col1, p_col2, p_col3 = st.columns([3, 2, 2])

df_avail = draft_mgr.get_available_players()
avail_list = df_avail["Player"].tolist()

with p_col1:
    selected_player = st.selectbox("Jugador Seleccionado:", options=[""] + avail_list, index=0)

with p_col2:
    # Automáticamente sugiere el equipo en turno según la regla Snake
    teams_options = [f"Equipo {i} (Tú)" if i == my_team_index else f"Equipo {i} (Rival)" for i in range(1, num_teams + 1)]
    default_team_idx = team_on_clock - 1
    selected_team_str = st.selectbox("Equipo que lo draftea:", options=teams_options, index=default_team_idx)
    chosen_team_idx = int(selected_team_str.split()[1])

with p_col3:
    st.write("")
    st.write("")
    if st.button("➕ Confirmar Pick", use_container_width=True, type="primary"):
        if selected_player:
            draft_mgr.make_pick(player_name=selected_player, team_index=chosen_team_idx)
            st.success(f"✅ {selected_player} seleccionado por {selected_team_str}!")
            st.rerun()
        else:
            st.warning("Selecciona un jugador primero.")

# 3. Tablero de Jugadores y Recomendaciones
tab1, tab2, tab3 = st.tabs(["🔥 Top Recomendados para tu Turno", "📋 Jugadores Disponibles", "🛡️ Mi Plantilla & Proyecciones"])

with tab1:
    st.markdown("**Mejores opciones disponibles según Puntos Fantasy por Partido (FPPG) y necesidades:**")
    pos_filter = st.radio("Filtrar por posición:", ["TODAS", "PG", "SG", "SF", "PF", "C"], horizontal=True)
    df_recs = draft_mgr.get_recommended_picks(top_n=15, position_filter=pos_filter)
    
    if not df_recs.empty:
        disp_cols = ["Rank", "Player", "Team", "Positions", "FPPG", "VORP", "Total_Points", "PTS", "REB", "AST", "STL", "BLK", "3PM", "TO"]
        col_cfg = {
            "FPPG": st.column_config.ProgressColumn("FPPG", format="%.1f", min_value=15.0, max_value=65.0),
            "VORP": st.column_config.NumberColumn("VORP", format="%+.1f"),
            "Total_Points": st.column_config.NumberColumn("Total Pts", format="%d"),
            "PTS": st.column_config.NumberColumn("PTS", format="%.1f"),
            "REB": st.column_config.NumberColumn("REB", format="%.1f"),
            "AST": st.column_config.NumberColumn("AST", format="%.1f"),
            "STL": st.column_config.NumberColumn("STL", format="%.1f"),
            "BLK": st.column_config.NumberColumn("BLK", format="%.1f"),
            "3PM": st.column_config.NumberColumn("3PM", format="%.1f"),
            "TO": st.column_config.NumberColumn("TO", format="%.1f"),
        }
        st.dataframe(
            df_recs[[c for c in disp_cols if c in df_recs.columns]],
            column_config=col_cfg,
            use_container_width=True,
            height=450,
            hide_index=True
        )
    else:
        st.info("No hay jugadores disponibles con ese filtro.")

with tab2:
    search_txt = st.text_input("🔍 Buscar jugador disponible:", "")
    df_all_avail = draft_mgr.get_available_players()
    if search_txt:
        df_all_avail = df_all_avail[df_all_avail["Player"].str.contains(search_txt, case=False, na=False)]
    
    disp_all_cols = ["Rank", "Player", "Team", "Positions", "FPPG", "VORP", "Total_Points", "PTS", "REB", "AST", "STL", "BLK", "3PM", "TO"]
    col_cfg_all = {
        "FPPG": st.column_config.NumberColumn("FPPG", format="%.1f"),
        "VORP": st.column_config.NumberColumn("VORP", format="%+.1f"),
        "Total_Points": st.column_config.NumberColumn("Total Pts", format="%d"),
        "PTS": st.column_config.NumberColumn("PTS", format="%.1f"),
        "REB": st.column_config.NumberColumn("REB", format="%.1f"),
        "AST": st.column_config.NumberColumn("AST", format="%.1f"),
        "STL": st.column_config.NumberColumn("STL", format="%.1f"),
        "BLK": st.column_config.NumberColumn("BLK", format="%.1f"),
        "3PM": st.column_config.NumberColumn("3PM", format="%.1f"),
        "TO": st.column_config.NumberColumn("TO", format="%.1f"),
    }
    st.dataframe(
        df_all_avail[[c for c in disp_all_cols if c in df_all_avail.columns]],
        column_config=col_cfg_all,
        use_container_width=True,
        height=500,
        hide_index=True
    )

with tab3:
    df_my_roster = draft_mgr.get_my_roster_df()
    if not df_my_roster.empty:
        disp_my_cols = ["Rank", "Player", "Team", "Positions", "FPPG", "Total_Points", "PTS", "REB", "AST", "STL", "BLK", "3PM", "TO"]
        st.dataframe(
            df_my_roster[[c for c in disp_my_cols if c in df_my_roster.columns]],
            column_config=col_cfg_all,
            use_container_width=True,
            hide_index=True
        )

        team_pts = draft_mgr.points_engine.compute_team_points_total(df_my_roster)
        st.subheader("📈 Proyección de Puntos de tu Equipo")
        tp_c1, tp_c2, tp_c3 = st.columns(3)
        with tp_c1:
            st.metric("Total FPPG de la Plantilla", f"{team_pts['Total_FPPG']} pts/partido")
        with tp_c2:
            st.metric("FPPG Quinteto Titular (Top 10)", f"{team_pts['Starters_FPPG']} pts/partido")
        with tp_c3:
            st.metric("Puntos Proyectados por Semana (~3.3 pj)", f"{team_pts['Projected_Weekly_Points']} pts")
    else:
        st.info("Aún no has drafteado jugadores para tu equipo. ¡Comienza arriba!")
