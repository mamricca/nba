"""
Página: Resumen Semanal para Ligas de Puntos (Points League) y Categorías
Cálculo automático de marcadores desde estadísticas oficiales NBA y gestión de resultados sin Yahoo API.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import os
import json
import sys

sys.path.append(os.path.abspath(os.path.dirname(__file__) + "/.."))

from src.auth.yahoo_client import YahooFantasyClient
from src.auth.yahoo_scraper import YahooWebScraper
from src.analytics.nba_stats_scraper import NBAWeeklyCalculator

st.title("📊 Resumen Semanal de Puntos Fantasy")
st.caption("Marcadores semanales, cálculo automático desde partidos y estadísticas NBA, detalle jugador por jugador y 'All-Play' Power Rankings.")

client: YahooFantasyClient = st.session_state.get("yahoo_client", YahooFantasyClient(use_mock=True))
calculator = NBAWeeklyCalculator()

col_s1, col_s2, col_s3 = st.columns([1.5, 1, 1.5])
with col_s1:
    leagues = client.get_user_leagues()
    league_names = [l["name"] for l in leagues]
    selected_league_name = st.selectbox("Liga Activa:", league_names)
    selected_league = next((l for l in leagues if l["name"] == selected_league_name), leagues[0])
    client.set_league(selected_league["league_id"])

with col_s2:
    selected_week = st.number_input("Semana (Week):", min_value=1, max_value=24, value=1)

with col_s3:
    st.write("")
    if st.button("🏀 Recalcular desde Estadísticas NBA", type="primary", use_container_width=True):
        all_teams_list = client.get_teams()
        calc_result = calculator.calculate_league_weekly_results(
            teams=all_teams_list,
            roster_fetcher_fn=client.get_roster,
            week_num=selected_week
        )
        
        # Guardar en archivo semanal
        weekly_scores_file = "data/weekly_scores.json"
        saved_weekly = {}
        if os.path.exists(weekly_scores_file):
            try:
                with open(weekly_scores_file, "r", encoding="utf-8") as f:
                    saved_weekly = json.load(f)
            except Exception:
                saved_weekly = {}

        saved_weekly[f"Week {selected_week}"] = {
            "teams_summary": calc_result["teams_summary"],
            "player_breakdowns": calc_result["player_breakdowns"]
        }
        with open(weekly_scores_file, "w", encoding="utf-8") as f:
            json.dump(saved_weekly, f, indent=2, ensure_ascii=False)

        st.session_state[f"breakdown_w{selected_week}"] = calc_result["player_breakdowns"]
        st.success(f"✅ ¡Marcadores de la Semana {selected_week} calculados con éxito desde partidos NBA!")
        st.rerun()

# Pestañas principales
tab_summary, tab_breakdown, tab_manual, tab_import = st.tabs([
    "📊 Marcadores & Power Rankings",
    "📋 Detalle Jugador por Jugador",
    "✍️ Cargar / Editar Manualmente",
    "📥 Pegar de Yahoo / Web"
])

all_teams = client.get_teams()

# Cargar marcadores guardados o calcular al vuelo
weekly_scores_file = "data/weekly_scores.json"
saved_weekly = {}
if os.path.exists(weekly_scores_file):
    try:
        with open(weekly_scores_file, "r", encoding="utf-8") as f:
            saved_weekly = json.load(f)
    except Exception:
        saved_weekly = {}

week_key = f"Week {selected_week}"
stored_week_data = saved_weekly.get(week_key, None)

player_breakdowns_data = {}

if stored_week_data:
    if isinstance(stored_week_data, dict) and "teams_summary" in stored_week_data:
        teams_summary = stored_week_data["teams_summary"]
        player_breakdowns_data = stored_week_data.get("player_breakdowns", {})
    elif isinstance(stored_week_data, list):
        teams_summary = stored_week_data
    else:
        teams_summary = []
else:
    # Calcular automáticamente con NBAWeeklyCalculator
    calc_res = calculator.calculate_league_weekly_results(
        teams=all_teams,
        roster_fetcher_fn=client.get_roster,
        week_num=selected_week
    )
    teams_summary = calc_res["teams_summary"]
    player_breakdowns_data = calc_res["player_breakdowns"]

df_teams_week = pd.DataFrame(teams_summary).sort_values(by="Fantasy_Points", ascending=False).reset_index(drop=True)
df_teams_week["Rank"] = df_teams_week.index + 1

# -------------------------------------------------------------
# TAB 1: MARCADORES & POWER RANKINGS
# -------------------------------------------------------------
with tab_summary:
    my_row = next((t for t in teams_summary if t.get("is_me")), teams_summary[0])
    opp_candidates = [t for t in teams_summary if not t.get("is_me")]
    opp_row = opp_candidates[0] if opp_candidates else teams_summary[0]

    st.subheader(f"⚔️ Matchup Semana {selected_week}: {my_row['Team']} vs {opp_row['Team']}")

    my_pts = float(my_row["Fantasy_Points"])
    opp_pts = float(opp_row["Fantasy_Points"])
    pts_diff = round(my_pts - opp_pts, 1)
    is_win = my_pts > opp_pts

    m_col1, m_col2, m_col3 = st.columns([2, 1, 2])
    with m_col1:
        st.markdown(f"### 🛡️ {my_row['Team']}")
        st.metric("Tus Puntos Fantasy", f"{my_pts:.1f} pts")

    with m_col2:
        st.write("")
        if is_win:
            st.success(f"🏆 **VICTORIA**\n\n**{pts_diff:+.1f} pts**", icon="🔥")
        else:
            st.error(f"❌ **DERROTA**\n\n**{pts_diff:+.1f} pts**", icon="⚠️")

    with m_col3:
        st.markdown(f"### 🎯 {opp_row['Team']}")
        st.metric("Puntos del Rival", f"{opp_pts:.1f} pts")

    st.divider()

    # All-Play Power Rankings
    st.subheader("🏆 'All-Play' Power Rankings (Simulación Todos contra Todos)")
    st.markdown("¿Cómo le hubiera ido a tu equipo si hubiera jugado contra TODOS los 11 rivales de la liga con los puntos de esta semana?")

    all_play_records = []
    total_t = len(df_teams_week)

    for i, row_a in df_teams_week.iterrows():
        wins = 0
        losses = 0
        ties = 0
        for j, row_b in df_teams_week.iterrows():
            if i == j:
                continue
            if row_a["Fantasy_Points"] > row_b["Fantasy_Points"]:
                wins += 1
            elif row_a["Fantasy_Points"] < row_b["Fantasy_Points"]:
                losses += 1
            else:
                ties += 1

        win_pct = round((wins + 0.5 * ties) / max(total_t - 1, 1), 3)
        all_play_records.append({
            "Power_Rank": i + 1,
            "Team": row_a["Team"],
            "Fantasy_Points": row_a["Fantasy_Points"],
            "All_Play_Record": f"{wins} - {losses}",
            "Win_Pct": win_pct,
            "PTS": row_a.get("PTS", 0),
            "REB": row_a.get("REB", 0),
            "AST": row_a.get("AST", 0),
            "STL": row_a.get("STL", 0),
            "BLK": row_a.get("BLK", 0),
            "3PM": row_a.get("3PM", 0),
            "TO": row_a.get("TO", 0)
        })

    df_all_play = pd.DataFrame(all_play_records)

    col_ap_cfg = {
        "Fantasy_Points": st.column_config.ProgressColumn("Puntos Fantasy", format="%.1f", min_value=800.0, max_value=1700.0),
        "Win_Pct": st.column_config.NumberColumn("Win %", format="%.3f"),
    }

    st.dataframe(
        df_all_play,
        column_config=col_ap_cfg,
        use_container_width=True,
        hide_index=True
    )

    st.divider()

    st.subheader("📊 Distribución de Puntos Fantasy en la Liga")
    fig_bar = px.bar(
        df_all_play,
        x="Team",
        y="Fantasy_Points",
        color="Fantasy_Points",
        color_continuous_scale="Viridis",
        labels={"Fantasy_Points": "Puntos Fantasy Semanales", "Team": "Equipo"},
        title=f"Tabla de Rendimiento en Puntos - Semana {selected_week}"
    )
    fig_bar.update_layout(xaxis_tickangle=-45, height=400)
    st.plotly_chart(fig_bar, use_container_width=True)

# -------------------------------------------------------------
# TAB 2: DETALLE JUGADOR POR JUGADOR
# -------------------------------------------------------------
with tab_breakdown:
    st.subheader(f"📋 Desglose Individual de Jugadores (Semana {selected_week})")
    st.markdown("Revisa cuántos partidos jugó cada jugador de tu plantilla en la semana y cuántos puntos fantasy aportó al equipo:")

    team_inspect_sel = st.selectbox("Selecciona Equipo para ver su alineación:", [t["name"] for t in all_teams])
    selected_team_obj = next(t for t in all_teams if t["name"] == team_inspect_sel)
    sel_t_key = selected_team_obj["team_key"]

    t_breakdown = player_breakdowns_data.get(sel_t_key, {})
    if not t_breakdown:
        # Calcular si no está en caché
        t_roster = client.get_roster(sel_t_key)
        sched_counts = calculator.get_team_game_counts_for_week(selected_week)
        p_list = []
        for p in t_roster:
            p_name = p["name"]
            p_m = calculator.projections_df[calculator.projections_df["Player"] == p_name]
            nba_tm = p_m.iloc[0]["Team"] if not p_m.empty else "NBA"
            g_cnt = sched_counts.get(nba_tm, 3)
            p_stat = calculator.calculate_player_weekly_stats(p_name, g_cnt)
            if p_stat:
                p_list.append(p_stat)
        p_list.sort(key=lambda x: x.get("Weekly_FPTS", 0), reverse=True)
        t_breakdown = {"active": p_list[:10], "bench": p_list[10:]}

    active_p = t_breakdown.get("active", [])
    bench_p = t_breakdown.get("bench", [])

    if active_p:
        st.markdown(f"### 🏀 Titulares Activos ({len(active_p)} jugadores)")
        df_active = pd.DataFrame(active_p)
        col_p_cfg = {
            "Weekly_FPTS": st.column_config.ProgressColumn("Puntos Semanales", format="%.1f pts", min_value=0.0, max_value=250.0),
            "FPPG": st.column_config.NumberColumn("FPPG", format="%.1f"),
            "Games": st.column_config.NumberColumn("Partidos", format="%d 🏀"),
            "PTS": st.column_config.NumberColumn("PTS", format="%.1f"),
            "REB": st.column_config.NumberColumn("REB", format="%.1f"),
            "AST": st.column_config.NumberColumn("AST", format="%.1f"),
            "STL": st.column_config.NumberColumn("STL", format="%.1f"),
            "BLK": st.column_config.NumberColumn("BLK", format="%.1f"),
            "3PM": st.column_config.NumberColumn("3PM", format="%.1f"),
            "TO": st.column_config.NumberColumn("TO", format="%.1f"),
        }
        disp_p_cols = ["Player", "NBA_Team", "Positions", "Games", "FPPG", "Weekly_FPTS", "PTS", "REB", "AST", "STL", "BLK", "3PM", "TO"]
        st.dataframe(
            df_active[[c for c in disp_p_cols if c in df_active.columns]],
            column_config=col_p_cfg,
            use_container_width=True,
            hide_index=True
        )

    if bench_p:
        st.markdown(f"### 🪑 Suplentes / Banca ({len(bench_p)} jugadores)")
        df_bench = pd.DataFrame(bench_p)
        st.dataframe(
            df_bench[[c for c in disp_p_cols if c in df_bench.columns]],
            column_config=col_p_cfg,
            use_container_width=True,
            hide_index=True
        )

# -------------------------------------------------------------
# TAB 3: CARGA / EDICIÓN MANUAL
# -------------------------------------------------------------
with tab_manual:
    st.subheader(f"✍️ Editor Manual de Resultados (Semana {selected_week})")
    st.markdown("Puedes ajustar o sobreescribir manualmente los marcadores de la semana:")

    edit_df = pd.DataFrame([
        {
            "Team": t.get("Team", ""),
            "Fantasy_Points": float(t.get("Fantasy_Points", 1000.0)),
            "PTS": int(t.get("PTS", 600)),
            "REB": int(t.get("REB", 200)),
            "AST": int(t.get("AST", 140)),
            "STL": int(t.get("STL", 40)),
            "BLK": int(t.get("BLK", 25)),
            "3PM": int(t.get("3PM", 60)),
            "TO": int(t.get("TO", 65)),
        }
        for t in teams_summary
    ])

    edited_df = st.data_editor(
        edit_df,
        num_rows="dynamic",
        use_container_width=True,
        key="weekly_score_editor"
    )

    if st.button("💾 Guardar Cambios Manuales", type="primary", use_container_width=True):
        updated_list = []
        for idx, row in edited_df.iterrows():
            updated_list.append({
                "Team": row["Team"],
                "Manager": f"Manager {idx+1}",
                "is_me": (idx == 0),
                "Fantasy_Points": float(row["Fantasy_Points"]),
                "PTS": int(row["PTS"]),
                "REB": int(row["REB"]),
                "AST": int(row["AST"]),
                "STL": int(row["STL"]),
                "BLK": int(row["BLK"]),
                "3PM": int(row["3PM"]),
                "TO": int(row["TO"]),
            })
        
        saved_weekly[week_key] = {"teams_summary": updated_list, "player_breakdowns": player_breakdowns_data}
        with open(weekly_scores_file, "w", encoding="utf-8") as f:
            json.dump(saved_weekly, f, indent=2, ensure_ascii=False)
        st.success(f"✅ ¡Puntuaciones de la Semana {selected_week} guardadas!")
        st.rerun()

# -------------------------------------------------------------
# TAB 4: IMPORTAR TEXTO DE YAHOO / WEB
# -------------------------------------------------------------
with tab_import:
    st.subheader(f"📥 Importar Marcadores Pegando Texto (Semana {selected_week})")
    pasted_yahoo_text = st.text_area("Pega aquí el texto o tabla copiada de Yahoo/Web:", height=150, key="pasted_text_input")
    
    if st.button("🚀 Extraer y Cargar Marcadores", type="primary", use_container_width=True):
        if pasted_yahoo_text:
            scraper = YahooWebScraper()
            parsed_data = scraper.parse_matchup_text_or_html(pasted_yahoo_text)
            if parsed_data:
                formatted_list = []
                for idx, item in enumerate(parsed_data):
                    t_name = item.get("team_name", f"Equipo {idx+1}")
                    pts = float(item.get("points", 1000.0))
                    formatted_list.append({
                        "Team": t_name,
                        "Manager": f"Manager {idx+1}",
                        "is_me": (idx == 0),
                        "Fantasy_Points": pts,
                        "PTS": round(pts * 0.45),
                        "REB": round(pts * 0.18),
                        "AST": round(pts * 0.12),
                        "STL": round(pts * 0.03),
                        "BLK": round(pts * 0.02),
                        "3PM": round(pts * 0.05),
                        "TO": round(pts * 0.05)
                    })
                saved_weekly[week_key] = {"teams_summary": formatted_list, "player_breakdowns": {}}
                with open(weekly_scores_file, "w", encoding="utf-8") as f:
                    json.dump(saved_weekly, f, indent=2, ensure_ascii=False)
                
                st.success(f"✅ ¡Se importaron exitosamente {len(parsed_data)} equipos para la Semana {selected_week}!")
                st.rerun()
            else:
                st.warning("No se detectaron puntuaciones en el texto pegado.")
