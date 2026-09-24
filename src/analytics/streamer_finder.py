"""
Buscador y Optimizador de Jugadores 'Streamers' y Agentes Libres (Waivers).
Cruza el calendario de partidos NBA con las necesidades estadísticas de la plantilla.
"""

import json
import os
from typing import Dict, List, Optional, Any
import pandas as pd


class StreamerFinder:
    OFF_DAYS_DEFAULT = ["Tue", "Thu", "Sat", "Sun"]

    def __init__(self, schedule_file: str = "data/nba_schedule_sample.json"):
        self.schedule_file = schedule_file
        self.schedule_data = self._load_schedule()

    def _load_schedule(self) -> Dict[str, Any]:
        if os.path.exists(self.schedule_file):
            try:
                with open(self.schedule_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"[StreamerFinder] Error cargando calendario: {e}")
        return {"weeks": {}, "day_game_counts_week_1": {}}

    def get_team_schedule_summary(self, week_str: str = "Week 1") -> pd.DataFrame:
        """Genera una tabla con la cantidad total de partidos y partidos en días de bajo volumen (Off-days)"""
        week_info = self.schedule_data.get("weeks", {}).get(week_str, {})
        rows = []

        for team, data in week_info.items():
            total = data.get("total", 0)
            days = data.get("days", {})
            off_days_count = sum(days.get(d, 0) for d in self.OFF_DAYS_DEFAULT)
            b2b = 1 if (days.get("Tue", 0) and days.get("Wed", 0)) or (days.get("Sat", 0) and days.get("Sun", 0)) else 0

            rows.append({
                "Team": team,
                "Total_Games": total,
                "Off_Day_Games (Tue/Thu/Sat/Sun)": off_days_count,
                "Mon": days.get("Mon", 0),
                "Tue": days.get("Tue", 0),
                "Wed": days.get("Wed", 0),
                "Thu": days.get("Thu", 0),
                "Fri": days.get("Fri", 0),
                "Sat": days.get("Sat", 0),
                "Sun": days.get("Sun", 0),
                "Back_to_Back": b2b
            })

        df = pd.DataFrame(rows)
        if not df.empty:
            df = df.sort_values(by=["Off_Day_Games (Tue/Thu/Sat/Sun)", "Total_Games"], ascending=False).reset_index(drop=True)
        return df

    def find_best_streamers(
        self,
        free_agents_df: pd.DataFrame,
        target_categories: Optional[List[str]] = None,
        week_str: str = "Week 1",
        top_n: int = 10
    ) -> pd.DataFrame:
        """
        Calcula un puntaje de streaming cruzando:
        - Cantidad de partidos en la semana y en off-days
        - Contribución en las categorías objetivo seleccionadas
        """
        if free_agents_df.empty:
            return pd.DataFrame()

        df_sched = self.get_team_schedule_summary(week_str)
        if df_sched.empty:
            return free_agents_df.head(top_n)

        sched_map = dict(zip(df_sched["Team"], df_sched["Total_Games"]))
        off_map = dict(zip(df_sched["Team"], df_sched["Off_Day_Games (Tue/Thu/Sat/Sun)"]))

        df = free_agents_df.copy()
        df["Week_Games"] = df["team"].map(sched_map).fillna(3)
        df["Off_Day_Games"] = df["team"].map(off_map).fillna(1)

        # Calcular score de valor de streaming
        if not target_categories:
            target_categories = ["PTS", "REB", "AST", "3PM", "STL", "BLK"]

        def calc_stream_score(row):
            stat_sum = 0.0
            for cat in target_categories:
                if cat in row and pd.notnull(row[cat]):
                    val = float(row[cat])
                    if cat in ["FG%", "FT%"]:
                        stat_sum += val * 10
                    elif cat == "TO":
                        stat_sum -= val
                    else:
                        stat_sum += val

            # Ponderar fuertemente por partidos totales y en off-days
            multiplier = (row["Week_Games"] * 0.7) + (row["Off_Day_Games"] * 0.9)
            return stat_sum * multiplier

        df["Streamer_Score"] = df.apply(calc_stream_score, axis=1)
        df = df.sort_values(by="Streamer_Score", ascending=False).reset_index(drop=True)
        df["Rank"] = df.index + 1

        return df.head(top_n)

