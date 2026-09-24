"""
Página: Resumen Semanal para Ligas de Puntos (Points League) y Categorías
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

st.title("📊 Resumen Semanal de Puntos Fantasy")
st.caption("Marcadores semanales, rendimiento frente a tu rival, líderes de puntos y 'All-Play' Power Rankings sin necesidad de API de Yahoo.")

client: YahooFantasyClient = st.session_state.get("yahoo_client", YahooFantasyClient(use_mock=True))

col_s1, col_s2 = st.columns([2, 1])
with col_s1:
    leagues = client.get_user_leagues()
    league_names = [l["name"] for l in leagues]
    selected_league_name = st.selectbox("Liga Activa:", league_names)
    selected_league = next((l for l in leagues if l["name"] == selected_league_name), leagues[0])
    client.set_league(selected_league["league_id"])

with col_s2:
    selected_week = st.number_input("Semana a Analizar (Week):", min_value=1, max_value=24, value=1)

# Pestañas principales
tab_summary, tab_manual, tab_import = st.tabs([
    "📊 Marcadores & Power Rankings",
    "✍️ Cargar / Editar Puntos Semanales",
    "📥 Pegar Datos de Yahoo / Web"
])

all_teams = client.get_teams()

# Función de cálculo de puntos fantasy con fórmula oficial
def calc_weekly_fantasy_pts(stats: dict) -> float:
    pts = (
        float(stats.get("PTS", 0)) * 1.0 +
        float(stats.get("REB", 0)) * 1.2 +
        float(stats.get("AST", 0)) * 1.5 +
        float(stats.get("STL", 0)) * 3.0 +
        float(stats.get("BLK", 0)) * 3.0 +
        float(stats.get("3PM", 0)) * 1.0 -
        float(stats.get("TO", 0)) * 1.0
    )
    return round(pts, 1)

# Cargar marcadores guardados o generados
weekly_scores_file = "data/weekly_scores.json"
saved_weekly = {}
if os.path.exists(weekly_scores_file):
    try:
        with open(weekly_scores_file, "r", encoding="utf-8") as f:
            saved_weekly = json.load(f)
    except Exception:
        saved_weekly = {}

week_key = f"Week {selected_week}"
custom_scores_for_week = saved_weekly.get(week_key, None)
custom_imported = st.session_state.get(f"custom_matchups_w{selected_week}", None)

# Procesar equipos
teams_summary = []

if custom_scores_for_week:
    teams_summary = custom_scores_for_week
elif custom_imported:
    for idx, item in enumerate(custom_imported):
        t_name = item.get("team_name", f"Equipo {idx+1}")
        f_pts = float(item.get("points", 1000.0))
        teams_summary.append({
            "Team": t_name,
            "Manager": f"Manager {idx+1}",
            "is_me": (idx == 0),
            "Fantasy_Points": f_pts,
            "PTS": round(f_pts * 0.45),
            "REB": round(f_pts * 0.18),
            "AST": round(f_pts * 0.12),
            "STL": round(f_pts * 0.03),
            "BLK": round(f_pts * 0.02),
            "3PM": round(f_pts * 0.05),
            "TO": round(f_pts * 0.05)
        })
else:
    matchups = client.get_matchups(week=selected_week)
    for t in all_teams:
        found_stats = None
        for m in matchups:
            if m["team1"]["name"] == t["name"]:
                found_stats = m["team1"]["stats"]
                break
            elif m["team2"]["name"] == t["name"]:
                found_stats = m["team2"]["stats"]
                break

        if not found_stats:
            noise = (hash(t["name"] + str(selected_week)) % 25 - 12) / 100.0
            found_stats = {
                "PTS": round(620 * (1 + noise)),
                "REB": round(230 * (1 + noise)),
                "AST": round(150 * (1 + noise)),
                "STL": round(42 * (1 + noise)),
                "BLK": round(30 * (1 + noise)),
                "3PM": round(65 * (1 + noise)),
                "TO": round(70 * (1 - noise * 0.5))
            }

        f_pts = calc_weekly_fantasy_pts(found_stats)
        teams_summary.append({
            "Team": t["name"],
            "Manager": t["manager"],
            "is_me": t.get("is_current_user", False),
            "Fantasy_Points": f_pts,
            **found_stats
        })

df_teams_week = pd.DataFrame(teams_summary).sort_values(by="Fantasy_Points", ascending=False).reset_index(drop=True)
df_teams_week["Rank"] = df_teams_week.index + 1

# -------------------------------------------------------------
# TAB 1: MARCADORES & POWER RANKINGS
# -------------------------------------------------------------
with tab_summary:
    # Identificar mi equipo y rival
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
        st.metric("Tus Puntos Fantasy", f"{my_pts} pts")

    with m_col2:
        st.write("")
        if is_win:
            st.success(f"🏆 **VICTORIA**\n\n**{pts_diff:+.1f} pts**", icon="🔥")
        else:
            st.error(f"❌ **DERROTA**\n\n**{pts_diff:+.1f} pts**", icon="⚠️")

    with m_col3:
        st.markdown(f"### 🎯 {opp_row['Team']}")
        st.metric("Puntos del Rival", f"{opp_pts} pts")

    st.divider()

    # All-Play Power Rankings
    st.subheader("🏆 'All-Play' Power Rankings (Simulación Todos contra Todos)")
    st.markdown("¿Cómo le hubiera ido a tu equipo si hubiera jugado contra TODOS los 11 equipos de la liga con los puntos de esta semana?")

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
        "Fantasy_Points": st.column_config.ProgressColumn("Puntos Fantasy", format="%.1f", min_value=800.0, max_value=1600.0),
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
# TAB 2: CARGA / EDICIÓN MANUAL DE PUNTOS
# -------------------------------------------------------------
with tab_manual:
    st.subheader(f"✍️ Editor Manual de Resultados (Semana {selected_week})")
    st.markdown("Ingresa los puntos finales de cada equipo o sus estadísticas. Se guardarán en el historial de la liga automáticamente.")

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

    c_btn1, c_btn2 = st.columns([2, 1])
    with c_btn1:
        if st.button("💾 Guardar Resultados de la Semana", type="primary", use_container_width=True):
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
            
            saved_weekly[week_key] = updated_list
            with open(weekly_scores_file, "w", encoding="utf-8") as f:
                json.dump(saved_weekly, f, indent=2, ensure_ascii=False)
            st.success(f"✅ ¡Puntuaciones de la Semana {selected_week} guardadas correctamente!")
            st.rerun()

    with c_btn2:
        if st.button("🔄 Recalcular Puntos desde Estadísticas", use_container_width=True):
            for idx, row in edited_df.iterrows():
                stats = {
                    "PTS": row["PTS"], "REB": row["REB"], "AST": row["AST"],
                    "STL": row["STL"], "BLK": row["BLK"], "3PM": row["3PM"], "TO": row["TO"]
                }
                edited_df.at[idx, "Fantasy_Points"] = calc_weekly_fantasy_pts(stats)
            st.info("Puntos recalculados. Haz clic en Guardar para confirmar.")

# -------------------------------------------------------------
# TAB 3: IMPORTAR TEXTO DE YAHOO / WEB
# -------------------------------------------------------------
with tab_import:
    st.subheader(f"📥 Importar Marcadores Reales Pegando Texto (Semana {selected_week})")
    st.markdown("""
    **¿Cómo traer los datos reales en segundos?**
    1. Abre tu liga en [Yahoo Fantasy Basketball](https://basketball.fantasysports.yahoo.com/) o cualquier web.
    2. Ve a la sección **Matchups** de la semana.
    3. Selecciona la tabla de resultados, cópiala (`Ctrl + C`) y pégala aquí abajo.
    """)
    pasted_yahoo_text = st.text_area("Pega aquí el texto o tabla copiada:", height=150, key="pasted_text_input")
    
    if st.button("🚀 Extraer y Cargar Marcadores", type="primary", use_container_width=True):
        if pasted_yahoo_text:
            scraper = YahooWebScraper()
            parsed_data = scraper.parse_matchup_text_or_html(pasted_yahoo_text)
            if parsed_data:
                st.session_state[f"custom_matchups_w{selected_week}"] = parsed_data
                
                # Guardar directamente a archivo de la semana
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
                saved_weekly[week_key] = formatted_list
                with open(weekly_scores_file, "w", encoding="utf-8") as f:
                    json.dump(saved_weekly, f, indent=2, ensure_ascii=False)
                
                st.success(f"✅ ¡Se importaron exitosamente {len(parsed_data)} equipos para la Semana {selected_week}!")
                st.rerun()
            else:
                st.warning("No se detectaron puntuaciones en el texto pegado.")
