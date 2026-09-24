"""
Página: Evaluador de Traspasos (Trade Machine) y Asesor de Agentes Libres (Waivers)
"""

import streamlit as st
import pandas as pd
import os
import sys

sys.path.append(os.path.abspath(os.path.dirname(__file__) + "/.."))

from src.auth.yahoo_client import YahooFantasyClient
from src.core.zscore import ZScoreEngine
from src.core.trade_evaluator import TradeEvaluator

st.title("🔄 Simulador de Traspasos & Asesor de Waivers")
st.caption("Evalúa el impacto neto de traspasos propuestos y descubre los mejores jugadores en la agencia libre.")

# Cargar proyecciones base
@st.cache_data
def load_projections():
    csv_path = "data/projections_sample.csv"
    if os.path.exists(csv_path):
        return pd.read_csv(csv_path)
    return pd.DataFrame()

df_projections = load_projections()
z_engine = ZScoreEngine().fit(df_projections)
trade_evaluator = TradeEvaluator(z_engine)

client: YahooFantasyClient = st.session_state.get("yahoo_client", YahooFantasyClient(use_mock=True))
all_teams = client.get_teams()

# Identificar mi equipo y rivales
my_team_info = next((t for t in all_teams if t.get("is_current_user")), all_teams[0])
rival_teams = [t for t in all_teams if t["team_key"] != my_team_info["team_key"]]

# Funciones auxiliares para obtener DataFrame de roster
def get_team_dataframe(team_key: str) -> pd.DataFrame:
    raw_roster = client.get_roster(team_key)
    names = [p["name"] for p in raw_roster]
    df_match = df_projections[df_projections["Player"].isin(names)].copy()
    if df_match.empty:
        df_match = df_projections.head(13).copy()
    return z_engine.transform(df_match)

df_my_roster = get_team_dataframe(my_team_info["team_key"])

# Tabs: Trade Machine vs Agentes Libres
tab_trade, tab_waivers = st.tabs(["🤝 Simulador de Traspasos (Trade Machine)", "🔍 Asesor de Agentes Libres"])

with tab_trade:
    st.subheader("Simulador de Traspasos (Trade Machine)")
    
    col_t1, col_t2 = st.columns(2)
    
    with col_t1:
        st.markdown(f"### 🛡️ {my_team_info['name']} (Tú)")
        giving_players = st.multiselect(
            "Jugadores que entregas:",
            options=df_my_roster["Player"].tolist()
        )
    
    with col_t2:
        selected_rival_name = st.selectbox("Selecciona Equipo Rival:", [r["name"] for r in rival_teams])
        rival_info = next(r for r in rival_teams if r["name"] == selected_rival_name)
        df_rival_roster = get_team_dataframe(rival_info["team_key"])
        
        st.markdown(f"### 🎯 {rival_info['name']} (Rival)")
        receiving_players = st.multiselect(
            "Jugadores que recibes a cambio:",
            options=df_rival_roster["Player"].tolist()
        )

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
            
            st.divider()
            
            # Mostrar Veredicto
            v_col1, v_col2 = st.columns([2, 1])
            with v_col1:
                st.markdown(f"## {result['verdict']}")
                st.markdown(f"**Impacto Neto Z-Score:** `{result['total_z_delta_team_a']:+.3f}`")
            
            with v_col2:
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

with tab_waivers:
    st.subheader("🔍 Recomendaciones de Agentes Libres (Waivers)")
    st.markdown("Encuentra jugadores disponibles en tu liga que aporten exactamente en las estadísticas que necesitas:")

    fa_list = client.get_free_agents()
    df_fa = pd.DataFrame(fa_list)

    filter_col1, filter_col2 = st.columns([2, 1])
    with filter_col1:
        target_cats = st.multiselect(
            "Categorías a reforzar prioritariamente:",
            ["PTS", "REB", "AST", "STL", "BLK", "3PM", "FG%", "FT%"],
            default=["STL", "BLK", "3PM"]
        )
    with filter_col2:
        pos_filter_waiver = st.selectbox("Posición:", ["TODAS", "PG", "SG", "SF", "PF", "C"])

    if not df_fa.empty:
        if pos_filter_waiver != "TODAS":
            df_fa = df_fa[df_fa["position"].str.contains(pos_filter_waiver, na=False)]
        
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

        disp_fa_cols = ["name", "team", "position", "Fit_Score", "PTS", "REB", "AST", "STL", "BLK", "3PM", "FG%", "FT%", "TO"]
        col_fa_cfg = {
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
            df_fa[[c for c in disp_fa_cols if c in df_fa.columns]],
            column_config=col_fa_cfg,
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No hay agentes libres registrados.")
