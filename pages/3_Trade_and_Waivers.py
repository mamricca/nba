"""
Página: Evaluador de Traspasos (Trade Machine), Asesor de Agentes Libres (Waivers) y Gestión de Plantillas
"""

import streamlit as st
import pandas as pd
import os
import sys

sys.path.append(os.path.abspath(os.path.dirname(__file__) + "/.."))

from src.auth.yahoo_client import YahooFantasyClient
from src.core.zscore import ZScoreEngine
from src.core.trade_evaluator import TradeEvaluator
from src.core.points_engine import PointsLeagueEngine

st.title("🔄 Mercado Fantasy: Traspasos, Waivers y Plantillas")
st.caption("Evalúa traspasos, asesora agentes libres y gestiona las altas, bajas y cambios de plantilla sin depender de Yahoo.")

# Cargar proyecciones base
@st.cache_data
def load_projections():
    csv_path = "data/projections_sample.csv"
    if os.path.exists(csv_path):
        return pd.read_csv(csv_path)
    return pd.DataFrame()

df_projections = load_projections()
z_engine = ZScoreEngine().fit(df_projections)
points_engine = PointsLeagueEngine()
trade_evaluator = TradeEvaluator(z_engine)

client: YahooFantasyClient = st.session_state.get("yahoo_client", YahooFantasyClient(use_mock=True))
all_teams = client.get_teams()

# Identificar mi equipo y rivales
my_team_info = next((t for t in all_teams if t.get("is_current_user")), all_teams[0])
rival_teams = [t for t in all_teams if t["team_key"] != my_team_info["team_key"]]

def get_team_dataframe(team_key: str) -> pd.DataFrame:
    raw_roster = client.get_roster(team_key)
    names = [p["name"] for p in raw_roster]
    df_match = df_projections[df_projections["Player"].isin(names)].copy()
    if df_match.empty:
        df_match = df_projections.head(13).copy()
    
    # Agregar FPPG
    df_match = points_engine.transform(df_match)
    return z_engine.transform(df_match)

df_my_roster = get_team_dataframe(my_team_info["team_key"])

# 3 Pestañas Principales
tab_trade, tab_waivers, tab_rosters = st.tabs([
    "🤝 Simulador de Traspasos (Trade Machine)", 
    "🔍 Asesor de Agentes Libres (Waivers)",
    "✍️ Gestión de Mercado & Plantillas (Altas, Bajas y Trades)"
])

# -------------------------------------------------------------
# TAB 1: TRADE MACHINE
# -------------------------------------------------------------
with tab_trade:
    st.subheader("Simulador de Traspasos (Trade Machine)")
    st.markdown("Analiza cómo cambiaría el rendimiento de tu equipo antes de aceptar un traspaso.")
    
    col_t1, col_t2 = st.columns(2)
    
    with col_t1:
        st.markdown(f"### 🛡️ {my_team_info['name']} (Tú)")
        giving_players = st.multiselect(
            "Jugadores que entregas:",
            options=df_my_roster["Player"].tolist()
        )
        if giving_players:
            df_giving = df_my_roster[df_my_roster["Player"].isin(giving_players)]
            st.caption(f"FPPG Total entregado: **{df_giving['FPPG'].sum():.1f} pts/partido**")
    
    with col_t2:
        selected_rival_name = st.selectbox("Selecciona Equipo Rival:", [r["name"] for r in rival_teams])
        rival_info = next(r for r in rival_teams if r["name"] == selected_rival_name)
        df_rival_roster = get_team_dataframe(rival_info["team_key"])
        
        st.markdown(f"### 🎯 {rival_info['name']} (Rival)")
        receiving_players = st.multiselect(
            "Jugadores que recibes a cambio:",
            options=df_rival_roster["Player"].tolist()
        )
        if receiving_players:
            df_rec = df_rival_roster[df_rival_roster["Player"].isin(receiving_players)]
            st.caption(f"FPPG Total recibido: **{df_rec['FPPG'].sum():.1f} pts/partido**")

    st.write("")
    if st.button("🚀 Evaluar Impacto del Traspaso", type="primary", use_container_width=True):
        if not giving_players or not receiving_players:
            st.warning("Selecciona al menos un jugador de cada equipo para simular el trade.")
        else:
            result = trade_evaluator.evaluate_trade(
                team_a_roster=df_my_roster,
                team_b_roster=df_rival_roster,
                giving_players_a=giving_players,
                receiving_players_a=receiving_players
            )
            
            # Calcular delta FPPG para ligas de puntos
            fppg_giving = df_my_roster[df_my_roster["Player"].isin(giving_players)]["FPPG"].sum()
            fppg_rec = df_rival_roster[df_rival_roster["Player"].isin(receiving_players)]["FPPG"].sum()
            fppg_delta = round(fppg_rec - fppg_giving, 1)

            st.divider()
            
            # Mostrar Veredicto
            v_col1, v_col2, v_col3 = st.columns([1.5, 1.2, 1.3])
            with v_col1:
                st.markdown(f"## {result['verdict']}")
                st.markdown(f"**Impacto Neto Z-Score:** `{result['total_z_delta_team_a']:+.3f}`")
            
            with v_col2:
                st.metric(
                    "Impacto Puntos Fantasy (FPPG)", 
                    f"{fppg_delta:+.1f} pts/partido",
                    delta=f"{'🟢 Ganas FPPG' if fppg_delta > 0 else '🔴 Pierdes FPPG'}"
                )

            with v_col3:
                st.markdown(f"**🟢 Categorías que Mejoras ({len(result['categories_improved'])}):** {', '.join(result['categories_improved']) or 'Ninguna'}")
                st.markdown(f"**🔴 Categorías que Empeoras ({len(result['categories_worsened'])}):** {', '.join(result['categories_worsened']) or 'Ninguna'}")
            
            # Tabla de cambios categoría por categoría
            st.subheader("📊 Variación Proyectada por Categoría para tu Equipo")
            diff_rows = []
            for cat, z_delta in result["category_z_deltas_team_a"].items():
                raw_diff = result["raw_stats_deltas_team_a"].get(cat, 0.0)
                unit = "%" if "%" in cat else " /partido"
                diff_rows.append({
                    "Categoría": cat,
                    "Cambio Estadístico": f"{raw_diff:+.2f}{unit}",
                    "Impacto Z-Score": z_delta,
                    "Efecto": "🟢 Mejora" if z_delta > 0.1 else ("🔴 Pérdida" if z_delta < -0.1 else "⚪ Neutro")
                })
            
            df_diffs = pd.DataFrame(diff_rows)
            st.dataframe(
                df_diffs,
                use_container_width=True,
                hide_index=True
            )

# -------------------------------------------------------------
# TAB 2: WAIVERS & AGENTES LIBRES
# -------------------------------------------------------------
with tab_waivers:
    st.subheader("🔍 Recomendaciones de Agentes Libres (Waivers)")
    st.markdown("Encuentra jugadores disponibles en tu liga ordenados por puntos fantasy o estadísticas específicas:")

    fa_list = client.get_free_agents()
    df_fa = pd.DataFrame(fa_list)

    filter_col1, filter_col2, filter_col3 = st.columns([2, 1, 1])
    with filter_col1:
        sort_mode = st.radio("Ordenar por:", ["🏆 Puntos Fantasy (FPPG)", "🎯 Categorías Específicas"], horizontal=True)
    with filter_col2:
        pos_filter_waiver = st.selectbox("Posición:", ["TODAS", "PG", "SG", "SF", "PF", "C"])
    with filter_col3:
        top_fa_count = st.slider("Mostrar:", 10, 50, 20)

    if not df_fa.empty:
        if pos_filter_waiver != "TODAS":
            df_fa = df_fa[df_fa["position"].str.contains(pos_filter_waiver, na=False)]
        
        if "Categorías" in sort_mode:
            target_cats = st.multiselect(
                "Categorías a reforzar prioritariamente:",
                ["PTS", "REB", "AST", "STL", "BLK", "3PM", "FG%", "FT%"],
                default=["STL", "BLK", "3PM"]
            )
            def rank_waiver(row):
                score = 0.0
                for c in target_cats:
                    if c in row:
                        val = float(row[c])
                        if "%" in c:
                            score += val * 20
                        else:
                            score += val * 1.5
                return score
            df_fa["Fit_Score"] = df_fa.apply(rank_waiver, axis=1)
            df_fa = df_fa.sort_values(by="Fit_Score", ascending=False).reset_index(drop=True)
        else:
            df_fa = df_fa.sort_values(by="FPPG", ascending=False).reset_index(drop=True)

        disp_fa_cols = ["name", "team", "position", "FPPG", "PTS", "REB", "AST", "STL", "BLK", "3PM", "FG%", "FT%", "TO"]
        if "Fit_Score" in df_fa.columns:
            disp_fa_cols.insert(3, "Fit_Score")

        col_fa_cfg = {
            "FPPG": st.column_config.ProgressColumn("FPPG", format="%.1f pts", min_value=10.0, max_value=60.0),
            "Fit_Score": st.column_config.ProgressColumn("Fit Score", format="%.1f", min_value=0.0, max_value=50.0),
            "FG%": st.column_config.NumberColumn("FG%", format="%.3f"),
            "FT%": st.column_config.NumberColumn("FT%", format="%.3f"),
            "PTS": st.column_config.NumberColumn("PTS", format="%.1f"),
            "REB": st.column_config.NumberColumn("REB", format="%.1f"),
            "AST": st.column_config.NumberColumn("AST", format="%.1f"),
            "STL": st.column_config.NumberColumn("STL", format="%.1f"),
            "BLK": st.column_config.NumberColumn("BLK", format="%.1f"),
            "3PM": st.column_config.NumberColumn("3PM", format="%.1f"),
            "TO": st.column_config.NumberColumn("TO", format="%.1f"),
        }
        st.dataframe(
            df_fa[[c for c in disp_fa_cols if c in df_fa.columns]].head(top_fa_count),
            column_config=col_fa_cfg,
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No hay agentes libres registrados.")

# -------------------------------------------------------------
# TAB 3: GESTIÓN DE PLANTILLAS Y MERCADO (ALTAS, BAJAS, TRADES)
# -------------------------------------------------------------
with tab_rosters:
    st.subheader("✍️ Registro y Gestión Manual de Movimientos de Mercado")
    st.markdown("Realiza fichajes, despidos y confirma traspasos entre equipos. Los cambios se guardan y actualizan automáticamente todas las pantallas de la app.")

    col_m1, col_m2 = st.columns(2)

    # 1. FICHAJES Y DESPIDOS
    with col_m1:
        with st.container(border=True):
            st.markdown("### 🟢 Fichar Agente Libre (Add)")
            dest_team_name = st.selectbox("Equipo que ficha:", [t["name"] for t in all_teams], key="add_dest_team")
            dest_team_info = next(t for t in all_teams if t["name"] == dest_team_name)
            
            avail_fa = client.get_free_agents()
            fa_names = [p["name"] for p in avail_fa]
            
            if fa_names:
                player_to_add = st.selectbox("Jugador disponible para fichar:", fa_names, key="add_player_sel")
                if st.button("➕ Confirmar Fichaje", type="primary", use_container_width=True):
                    client.add_player_to_team(dest_team_info["team_key"], player_to_add)
                    st.success(f"✅ ¡{player_to_add} ha sido fichado por {dest_team_name}!")
                    st.rerun()
            else:
                st.info("No hay agentes libres disponibles.")

        with st.container(border=True):
            st.markdown("### 🔴 Cortar Jugador (Drop a Free Agency)")
            drop_team_name = st.selectbox("Equipo que despide:", [t["name"] for t in all_teams], key="drop_team_sel")
            drop_team_info = next(t for t in all_teams if t["name"] == drop_team_name)
            
            curr_roster = client.get_roster(drop_team_info["team_key"])
            curr_roster_names = [p["name"] for p in curr_roster]
            
            if curr_roster_names:
                player_to_drop = st.selectbox("Jugador a cortar:", curr_roster_names, key="drop_player_sel")
                if st.button("🗑️ Confirmar Corte", type="secondary", use_container_width=True):
                    client.drop_player_from_team(drop_team_info["team_key"], player_to_drop)
                    st.warning(f"⚠️ {player_to_drop} fue enviado a la agencia libre.")
                    st.rerun()
            else:
                st.info(f"{drop_team_name} no tiene jugadores en su plantilla.")

    # 2. EJECUTAR TRASPASO DIRECTO
    with col_m2:
        with st.container(border=True):
            st.markdown("### 🔄 Ejecutar Traspaso Realizado")
            st.caption("Intercambia jugadores definitivamente entre dos equipos de la liga.")
            
            tr_team_a_name = st.selectbox("Equipo A:", [t["name"] for t in all_teams], index=0, key="tr_t_a")
            tr_team_b_name = st.selectbox("Equipo B:", [t["name"] for t in all_teams if t["name"] != tr_team_a_name], index=0, key="tr_t_b")
            
            tr_team_a_info = next(t for t in all_teams if t["name"] == tr_team_a_name)
            tr_team_b_info = next(t for t in all_teams if t["name"] == tr_team_b_name)
            
            roster_a = [p["name"] for p in client.get_roster(tr_team_a_info["team_key"])]
            roster_b = [p["name"] for p in client.get_roster(tr_team_b_info["team_key"])]
            
            tr_giving_a = st.multiselect(f"Jugadores que salen de {tr_team_a_name}:", roster_a, key="tr_give_a")
            tr_giving_b = st.multiselect(f"Jugadores que salen de {tr_team_b_name}:", roster_b, key="tr_give_b")
            
            if st.button("🤝 Confirmar e Intercambiar", type="primary", use_container_width=True):
                if not tr_giving_a or not tr_giving_b:
                    st.error("Debes seleccionar al menos un jugador de cada equipo para el traspaso.")
                else:
                    client.trade_players(tr_team_a_info["team_key"], tr_team_b_info["team_key"], tr_giving_a, tr_giving_b)
                    st.success(f"🎉 ¡Traspaso completado exitosamente entre {tr_team_a_name} y {tr_team_b_name}!")
                    st.rerun()

    st.divider()

    # 3. INSPECTOR DE PLANTILLAS
    st.subheader("📋 Visualizador de Plantillas de la Liga")
    inspect_team_name = st.selectbox("Selecciona equipo para ver su plantilla completa:", [t["name"] for t in all_teams])
    inspect_team_info = next(t for t in all_teams if t["name"] == inspect_team_name)
    df_inspect = get_team_dataframe(inspect_team_info["team_key"])

    if not df_inspect.empty:
        col_ins1, col_ins2 = st.columns([1, 2])
        with col_ins1:
            st.metric("Total Jugadores", f"{len(df_inspect)} jugadores")
            st.metric("Puntos Fantasy Proyectados (FPPG Total)", f"{df_inspect['FPPG'].sum():.1f} pts")
        
        with col_ins2:
            disp_ins_cols = ["Player", "Team", "Positions", "FPPG", "PTS", "REB", "AST", "STL", "BLK", "3PM"]
            st.dataframe(
                df_inspect[[c for c in disp_ins_cols if c in df_inspect.columns]],
                use_container_width=True,
                hide_index=True
            )
    else:
        st.info("Plantilla vacía.")
