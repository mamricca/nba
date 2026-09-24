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
st.caption("Scouting de agentes libres, radar de especialistas, comparador de cortes y simulador de traspasos.")

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
tab_waivers, tab_trade, tab_rosters = st.tabs([
    "🔍 Scouting de Agentes Libres (Waivers)",
    "🤝 Simulador de Traspasos (Trade Machine)", 
    "✍️ Gestión de Plantillas (Altas, Bajas y Trades)"
])

# -------------------------------------------------------------
# TAB 1: WAIVERS & RADAR DE AGENTES LIBRES
# -------------------------------------------------------------
with tab_waivers:
    st.subheader("🔍 Radar y Scouting de Agentes Libres (Waiver Wire)")
    st.markdown("Identifica los mejores talentos disponibles en la agencia libre por puntos fantasy, arquetipos o especialistas de estadísticas clave.")

    fa_list = client.get_free_agents()
    df_fa = pd.DataFrame(fa_list)

    if not df_fa.empty:
        # Asignar etiquetas/arquetipos a cada agente libre
        def assign_archetype(row):
            badges = []
            fppg = float(row.get("FPPG", 0.0))
            tpm = float(row.get("3PM", 0.0))
            stl = float(row.get("STL", 0.0))
            blk = float(row.get("BLK", 0.0))
            reb = float(row.get("REB", 0.0))
            ast = float(row.get("AST", 0.0))

            if (stl + blk) >= 1.7:
                badges.append("🛡️ Defensor Elite")
            if tpm >= 2.1:
                badges.append("🎯 Triplero")
            if reb >= 6.8:
                badges.append("🚀 Reboteador")
            if ast >= 3.8:
                badges.append("🪄 Asistidor")
            if fppg >= 24.0:
                badges.append("🔥 Titular / High Floor")
            if not badges:
                badges.append("📈 Rotación / Sleeper")
            return " • ".join(badges)

        df_fa["Perfil"] = df_fa.apply(assign_archetype, axis=1)

        # Filtros Superiores
        f_col1, f_col2, f_col3, f_col4 = st.columns([1.8, 1.2, 1.2, 1])
        with f_col1:
            archetype_filter = st.selectbox(
                "Arquetipo / Rol Buscado:",
                [
                    "🌟 Todos los Agentes Libres",
                    "🔥 Mayor FPPG (Mejor Jugador Disponible)",
                    "🛡️ Especialistas Defensivos (Robos + Bloqueos)",
                    "🎯 Especialistas Tripleros (3PM)",
                    "🚀 Reboteadores y Pintura (REB)",
                    "🪄 Generadores de Juego (AST)",
                ]
            )
        with f_col2:
            pos_filter_waiver = st.selectbox("Posición:", ["TODAS", "PG", "SG", "SF", "PF", "C"])
        with f_col3:
            sort_metric = st.selectbox("Ordenar tabla por:", ["FPPG", "PTS", "REB", "AST", "STL", "BLK", "3PM"])
        with f_col4:
            top_fa_count = st.slider("Mostrar:", 10, 50, 25)

        # Aplicar filtros
        df_filtered_fa = df_fa.copy()
        if pos_filter_waiver != "TODAS":
            df_filtered_fa = df_filtered_fa[df_filtered_fa["position"].str.contains(pos_filter_waiver, na=False)]

        if "Defensivos" in archetype_filter:
            df_filtered_fa["Stocks"] = df_filtered_fa["STL"] + df_filtered_fa["BLK"]
            df_filtered_fa = df_filtered_fa[df_filtered_fa["Stocks"] >= 1.4].sort_values(by="Stocks", ascending=False)
        elif "Tripleros" in archetype_filter:
            df_filtered_fa = df_filtered_fa[df_filtered_fa["3PM"] >= 1.8].sort_values(by="3PM", ascending=False)
        elif "Reboteadores" in archetype_filter:
            df_filtered_fa = df_filtered_fa[df_filtered_fa["REB"] >= 5.5].sort_values(by="REB", ascending=False)
        elif "Generadores" in archetype_filter:
            df_filtered_fa = df_filtered_fa[df_filtered_fa["AST"] >= 3.0].sort_values(by="AST", ascending=False)
        elif "FPPG" in archetype_filter or sort_metric == "FPPG":
            df_filtered_fa = df_filtered_fa.sort_values(by="FPPG", ascending=False)
        else:
            df_filtered_fa = df_filtered_fa.sort_values(by=sort_metric, ascending=False)

        df_filtered_fa = df_filtered_fa.reset_index(drop=True)

        disp_fa_cols = ["name", "team", "position", "Perfil", "FPPG", "PTS", "REB", "AST", "STL", "BLK", "3PM", "FG%", "FT%", "TO"]
        col_fa_cfg = {
            "FPPG": st.column_config.ProgressColumn("FPPG Proy", format="%.1f pts", min_value=8.0, max_value=45.0),
            "Perfil": st.column_config.TextColumn("Perfil & Especialidad", width="medium"),
            "PTS": st.column_config.NumberColumn("PTS", format="%.1f"),
            "REB": st.column_config.NumberColumn("REB", format="%.1f"),
            "AST": st.column_config.NumberColumn("AST", format="%.1f"),
            "STL": st.column_config.NumberColumn("STL", format="%.1f"),
            "BLK": st.column_config.NumberColumn("BLK", format="%.1f"),
            "3PM": st.column_config.NumberColumn("3PM", format="%.1f"),
            "FG%": st.column_config.NumberColumn("FG%", format="%.3f"),
            "FT%": st.column_config.NumberColumn("FT%", format="%.3f"),
            "TO": st.column_config.NumberColumn("TO", format="%.1f"),
        }

        st.dataframe(
            df_filtered_fa[[c for c in disp_fa_cols if c in df_filtered_fa.columns]].head(top_fa_count),
            column_config=col_fa_cfg,
            use_container_width=True,
            hide_index=True
        )

        st.divider()

        # -------------------------------------------------------------
        # ASESOR DE CORTES (DROP ADVISOR & HEAD-TO-HEAD)
        # -------------------------------------------------------------
        st.subheader("⚖️ Comparador Head-to-Head & Asesor de Cortes (Drop Advisor)")
        st.markdown("Compara cualquier agente libre directamente contra tu plantilla para ver si vale la pena el cambio:")

        c_comp1, c_comp2 = st.columns(2)
        with c_comp1:
            selected_fa_name = st.selectbox(
                "Selecciona Agente Libre a incorporar:",
                df_filtered_fa["name"].tolist(),
                key="sel_fa_h2h"
            )
            fa_row = df_filtered_fa[df_filtered_fa["name"] == selected_fa_name].iloc[0]

        with c_comp2:
            # Identificar peor jugador de mi plantilla por FPPG como sugerencia predeterminada
            df_my_sorted = df_my_roster.sort_values(by="FPPG", ascending=True).reset_index(drop=True)
            default_drop_name = df_my_sorted.iloc[0]["Player"] if not df_my_sorted.empty else df_my_roster["Player"].iloc[0]
            
            selected_my_player = st.selectbox(
                "Jugador de tu plantilla a cortar (Drop):",
                df_my_roster["Player"].tolist(),
                index=df_my_roster["Player"].tolist().index(default_drop_name) if default_drop_name in df_my_roster["Player"].tolist() else 0,
                key="sel_my_drop_h2h"
            )
            my_p_row = df_my_roster[df_my_roster["Player"] == selected_my_player].iloc[0]

        # Calcular deltas head-to-head
        delta_fppg = round(float(fa_row["FPPG"]) - float(my_p_row["FPPG"]), 1)
        delta_pts = round(float(fa_row["PTS"]) - float(my_p_row["PTS"]), 1)
        delta_reb = round(float(fa_row["REB"]) - float(my_p_row["REB"]), 1)
        delta_ast = round(float(fa_row["AST"]) - float(my_p_row["AST"]), 1)
        delta_stl = round(float(fa_row["STL"]) - float(my_p_row["STL"]), 1)
        delta_blk = round(float(fa_row["BLK"]) - float(my_p_row["BLK"]), 1)
        delta_3pm = round(float(fa_row["3PM"]) - float(my_p_row["3PM"]), 1)

        with st.container(border=True):
            m_h1, m_h2, m_h3 = st.columns([1.5, 1.5, 2])
            with m_h1:
                st.markdown(f"**➕ Fichaje:** `{selected_fa_name}` ({fa_row['team']} - {fa_row['position']})")
                st.markdown(f"**FPPG:** `{fa_row['FPPG']:.1f} pts`")
            with m_h2:
                st.markdown(f"**➖ Corte:** `{selected_my_player}` ({my_p_row.get('Team', 'NBA')} - {my_p_row.get('Positions', 'UTIL')})")
                st.markdown(f"**FPPG:** `{my_p_row['FPPG']:.1f} pts`")
            with m_h3:
                st.metric(
                    "Impacto Neto por Partido (Δ FPPG)",
                    f"{delta_fppg:+.1f} pts/partido",
                    delta="🟢 Fichaje Recomendado" if delta_fppg >= 0 else "🔴 Pérdida de Puntos"
                )

            st.markdown(f"""
            **Variación por Categoría:** PTS: `{delta_pts:+.1f}` | REB: `{delta_reb:+.1f}` | AST: `{delta_ast:+.1f}` | STL: `{delta_stl:+.1f}` | BLK: `{delta_blk:+.1f}` | 3PM: `{delta_3pm:+.1f}`
            """)

            if st.button(f"🔄 Ejecutar Movimiento: Fichar a {selected_fa_name} y Cortar a {selected_my_player}", type="primary", use_container_width=True):
                client.drop_player_from_team("nba.l.123456.t.1", selected_my_player)
                client.add_player_to_team("nba.l.123456.t.1", selected_fa_name)
                st.success(f"🎉 ¡Movimiento completado! {selected_fa_name} ha ingresado a tu equipo y {selected_my_player} fue liberado.")
                st.rerun()
    else:
        st.info("No hay agentes libres registrados.")

# -------------------------------------------------------------
# TAB 2: TRADE MACHINE
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
            
            fppg_giving = df_my_roster[df_my_roster["Player"].isin(giving_players)]["FPPG"].sum()
            fppg_rec = df_rival_roster[df_rival_roster["Player"].isin(receiving_players)]["FPPG"].sum()
            fppg_delta = round(fppg_rec - fppg_giving, 1)

            st.divider()
            
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
