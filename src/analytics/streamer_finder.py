"""
Buscador y Optimizador de Jugadores 'Streamers' y Agentes Libres (Waivers).
Cruza el calendario de partidos NBA con las necesidades de puntos fantasy y estadísticas de la plantilla.
"""

import json
import os
from typing import Dict, List, Optional, Any, Union
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

    def _normalize_week_key(self, week_input: Union[int, str]) -> str:
        """Normaliza cualquier formato de semana a 'Week X'"""
        w_str = str(week_input).strip()
        if w_str.isdigit():
            return f"Week {w_str}"
        if w_str.lower().startswith("semana "):
            num = w_str.lower().replace("semana ", "").strip()
            return f"Week {num}"
        if w_str.lower().startswith("week "):
            num = w_str.lower().replace("week ", "").strip()
            return f"Week {num}"
        return f"Week {w_str}"

    def get_available_weeks(self) -> List[str]:
        """Retorna la lista de semanas disponibles en el calendario"""
        weeks = list(self.schedule_data.get("weeks", {}).keys())
        if not weeks:
            return [f"Week {i}" for i in range(1, 25)]
        # Ordenar numéricamente si es posible
        try:
            return sorted(weeks, key=lambda w: int(w.replace("Week ", "")))
        except Exception:
            return weeks

    def get_team_schedule_summary(self, week_str: Union[int, str] = "Week 1") -> pd.DataFrame:
        """Genera una tabla con la cantidad total de partidos y partidos en días de bajo volumen (Off-days)"""
        w_key = self._normalize_week_key(week_str)
        week_info = self.schedule_data.get("weeks", {}).get(w_key, {})
        
        # Si la semana no está definida, intentar fallback con Week 1
        if not week_info and "Week 1" in self.schedule_data.get("weeks", {}):
            week_info = self.schedule_data["weeks"]["Week 1"]

        rows = []
        for team, data in week_info.items():
            total = data.get("total", 0)
            days = data.get("days", {})
            off_days_count = sum(days.get(d, 0) for d in self.OFF_DAYS_DEFAULT)
            b2b = 1 if (days.get("Tue", 0) and days.get("Wed", 0)) or (days.get("Sat", 0) and days.get("Sun", 0)) else 0

            rows.append({
                "Team": team,
                "Total_Games": total,
                "Off_Day_Games (Mar/Jue/Sab/Dom)": off_days_count,
                "Lun": days.get("Mon", 0),
                "Mar": days.get("Tue", 0),
                "Mie": days.get("Wed", 0),
                "Jue": days.get("Thu", 0),
                "Vie": days.get("Fri", 0),
                "Sab": days.get("Sat", 0),
                "Dom": days.get("Sun", 0),
                "Back_to_Back": b2b
            })

        df = pd.DataFrame(rows)
        if not df.empty:
            df = df.sort_values(by=["Off_Day_Games (Mar/Jue/Sab/Dom)", "Total_Games"], ascending=False).reset_index(drop=True)
        return df

    def find_best_streamers(
        self,
        free_agents_df: pd.DataFrame,
        target_categories: Optional[List[str]] = None,
        week_str: Union[int, str] = "Week 1",
        top_n: int = 10,
        league_mode: str = "points"
    ) -> pd.DataFrame:
        """
        Calcula un puntaje de streaming cruzando:
        - Cantidad de partidos en la semana y en off-days (días de bajo volumen)
        - Rendimiento en FPPG (liga de puntos) o categorías clave
        """
        if free_agents_df.empty:
            return pd.DataFrame()

        df_sched = self.get_team_schedule_summary(week_str)
        if df_sched.empty:
            return free_agents_df.head(top_n)

        sched_map = dict(zip(df_sched["Team"], df_sched["Total_Games"]))
        off_col = "Off_Day_Games (Mar/Jue/Sab/Dom)"
        off_map = dict(zip(df_sched["Team"], df_sched[off_col]))

        df = free_agents_df.copy()
        df["Week_Games"] = df["team"].map(sched_map).fillna(3).astype(int)
        df["Off_Day_Games"] = df["team"].map(off_map).fillna(1).astype(int)

        def calc_stream_score(row):
            # 1. Modo Puntos Fantasy
            if league_mode == "points" or "FPPG" in row:
                fppg = float(row.get("FPPG", 0.0))
                if fppg <= 0:
                    # calcular FPPG sobre la marcha si falta
                    pts = float(row.get("PTS", 0.0))
                    reb = float(row.get("REB", 0.0))
                    ast = float(row.get("AST", 0.0))
                    stl = float(row.get("STL", 0.0))
                    blk = float(row.get("BLK", 0.0))
                    tpm = float(row.get("3PM", 0.0))
                    to = float(row.get("TO", 0.0))
                    fppg = pts * 1.0 + reb * 1.2 + ast * 1.5 + stl * 3.0 + blk * 3.0 + tpm * 1.0 - to * 1.0

                # Score semanal = Puntos proyectados por partidos de la semana + bonus táctico por Off-Days
                # En off-days es donde realmente vas a poder alinear al jugador sin mandarlo a la banca
                projected_weekly_pts = fppg * row["Week_Games"]
                tactical_bonus = (fppg * 0.25) * row["Off_Day_Games"]
                return round(projected_weekly_pts + tactical_bonus, 1)

            # 2. Modo Categorías
            cats = target_categories if target_categories else ["PTS", "REB", "AST", "3PM", "STL", "BLK"]
            stat_sum = 0.0
            for cat in cats:
                if cat in row and pd.notnull(row[cat]):
                    val = float(row[cat])
                    if cat in ["FG%", "FT%"]:
                        stat_sum += val * 10
                    elif cat == "TO":
                        stat_sum -= val
                    else:
                        stat_sum += val

            multiplier = (row["Week_Games"] * 0.7) + (row["Off_Day_Games"] * 0.9)
            return round(stat_sum * multiplier, 1)

        df["Streamer_Score"] = df.apply(calc_stream_score, axis=1)
        df = df.sort_values(by="Streamer_Score", ascending=False).reset_index(drop=True)
        df["Rank"] = df.index + 1

        return df.head(top_n)
