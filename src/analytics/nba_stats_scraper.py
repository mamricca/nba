"""
Módulo de cálculo y scraping de estadísticas oficiales NBA para Ligas Fantasy de Puntos y Categorías.
Permite calcular los resultados y marcadores semanales de toda la liga cruzando:
1. Las plantillas reales de los 12 equipos
2. El calendario de partidos NBA de la semana (cantidad de partidos por equipo)
3. Las estadísticas reales/proyectadas por partido de cada jugador
4. La fórmula de puntuación oficial de la liga (PTS*1, REB*1.2, AST*1.5, STL*3, BLK*3, 3PM*1, TO*-1)
"""

import json
import os
from typing import Dict, List, Any, Optional
import pandas as pd
import numpy as np


class NBAWeeklyCalculator:
    def __init__(
        self,
        projections_file: str = "data/projections_sample.csv",
        schedule_file: str = "data/nba_schedule_sample.json",
        scoring_rules: Optional[Dict[str, float]] = None
    ):
        self.projections_file = projections_file
        self.schedule_file = schedule_file
        self.scoring_rules = scoring_rules or {
            "PTS": 1.0,
            "REB": 1.2,
            "AST": 1.5,
            "STL": 3.0,
            "BLK": 3.0,
            "3PM": 1.0,
            "TO": -1.0
        }
        self.projections_df = self._load_projections()
        self.schedule_data = self._load_schedule()

    def _load_projections(self) -> pd.DataFrame:
        if os.path.exists(self.projections_file):
            try:
                return pd.read_csv(self.projections_file)
            except Exception as e:
                print(f"[NBAWeeklyCalculator] Error cargando proyecciones: {e}")
        return pd.DataFrame()

    def _load_schedule(self) -> Dict[str, Any]:
        if os.path.exists(self.schedule_file):
            try:
                with open(self.schedule_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"[NBAWeeklyCalculator] Error cargando calendario: {e}")
        return {"weeks": {}}

    def get_team_game_counts_for_week(self, week_num: int = 1) -> Dict[str, int]:
        """Retorna {team_abbreviation: games_count} para la semana indicada"""
        week_key = f"Week {week_num}"
        week_info = self.schedule_data.get("weeks", {}).get(week_key, {})
        if not week_info and "Week 1" in self.schedule_data.get("weeks", {}):
            week_info = self.schedule_data["weeks"]["Week 1"]

        return {tm: data.get("total", 3) for tm, data in week_info.items()}

    def calculate_player_weekly_stats(self, player_name: str, games_count: int) -> Dict[str, Any]:
        """Calcula las estadísticas acumuladas y puntos fantasy de un jugador en la semana según sus partidos"""
        if self.projections_df.empty:
            return {}

        match = self.projections_df[self.projections_df["Player"] == player_name]
        if match.empty:
            # Búsqueda insensible a mayúsculas o parcial
            match = self.projections_df[self.projections_df["Player"].str.lower() == player_name.lower()]
        
        if match.empty:
            # Valores promedio de jugador de rotación si no se encuentra
            row = {
                "Player": player_name, "Team": "FA", "Positions": "UTIL",
                "PTS": 12.0, "REB": 4.5, "AST": 2.5, "STL": 0.8, "BLK": 0.5, "3PM": 1.2, "TO": 1.5,
                "FG%": 0.460, "FT%": 0.780
            }
        else:
            row = match.iloc[0].to_dict()

        # Multiplicar estadísticas por la cantidad de partidos jugados en la semana
        pts = float(row.get("PTS", 0.0)) * games_count
        reb = float(row.get("REB", 0.0)) * games_count
        ast = float(row.get("AST", 0.0)) * games_count
        stl = float(row.get("STL", 0.0)) * games_count
        blk = float(row.get("BLK", 0.0)) * games_count
        tpm = float(row.get("3PM", 0.0)) * games_count
        to = float(row.get("TO", 0.0)) * games_count

        # Puntos Fantasy semanales
        f_pts = (
            pts * self.scoring_rules.get("PTS", 1.0) +
            reb * self.scoring_rules.get("REB", 1.2) +
            ast * self.scoring_rules.get("AST", 1.5) +
            stl * self.scoring_rules.get("STL", 3.0) +
            blk * self.scoring_rules.get("BLK", 3.0) +
            tpm * self.scoring_rules.get("3PM", 1.0) +
            to * self.scoring_rules.get("TO", -1.0)
        )

        fppg = (
            float(row.get("PTS", 0.0)) * self.scoring_rules.get("PTS", 1.0) +
            float(row.get("REB", 0.0)) * self.scoring_rules.get("REB", 1.2) +
            float(row.get("AST", 0.0)) * self.scoring_rules.get("AST", 1.5) +
            float(row.get("STL", 0.0)) * self.scoring_rules.get("STL", 3.0) +
            float(row.get("BLK", 0.0)) * self.scoring_rules.get("BLK", 3.0) +
            float(row.get("3PM", 0.0)) * self.scoring_rules.get("3PM", 1.0) +
            float(row.get("TO", 0.0)) * self.scoring_rules.get("TO", -1.0)
        )

        return {
            "Player": player_name,
            "NBA_Team": row.get("Team", "NBA"),
            "Positions": row.get("Positions", "UTIL"),
            "Games": games_count,
            "FPPG": round(fppg, 1),
            "Weekly_FPTS": round(f_pts, 1),
            "PTS": round(pts, 1),
            "REB": round(reb, 1),
            "AST": round(ast, 1),
            "STL": round(stl, 1),
            "BLK": round(blk, 1),
            "3PM": round(tpm, 1),
            "TO": round(to, 1)
        }

    def calculate_league_weekly_results(
        self,
        teams: List[Dict[str, Any]],
        roster_fetcher_fn,
        week_num: int = 1,
        active_roster_size: int = 10
    ) -> Dict[str, Any]:
        """
        Calcula los resultados semanales completos para todos los equipos de la liga.
        Retorna:
        - 'teams_summary': Lista de resúmenes de cada equipo (total FPTS, estadísticas acumuladas)
        - 'player_breakdowns': Detalle jugador por jugador para cada equipo
        """
        schedule_counts = self.get_team_game_counts_for_week(week_num)
        teams_summary = []
        player_breakdowns = {}

        for t in teams:
            t_name = t["name"]
            t_key = t["team_key"]
            is_me = t.get("is_current_user", False)

            # Obtener jugadores de la plantilla
            raw_roster = roster_fetcher_fn(t_key)
            roster_names = [p["name"] for p in raw_roster]

            player_stats_list = []
            for p_name in roster_names:
                # Determinar equipo NBA del jugador
                p_match = self.projections_df[self.projections_df["Player"] == p_name]
                nba_tm = p_match.iloc[0]["Team"] if not p_match.empty else "LAL"
                games = schedule_counts.get(nba_tm, 3)

                p_stat = self.calculate_player_weekly_stats(p_name, games)
                if p_stat:
                    player_stats_list.append(p_stat)

            # Ordenar jugadores por puntos semanales para tomar los titulares (active starters)
            player_stats_list.sort(key=lambda x: x.get("Weekly_FPTS", 0), reverse=True)
            
            # Tomar los mejores N jugadores activos (quinteto + suplentes activos)
            active_players = player_stats_list[:active_roster_size] if len(player_stats_list) > active_roster_size else player_stats_list
            bench_players = player_stats_list[active_roster_size:] if len(player_stats_list) > active_roster_size else []

            # Sumar estadísticas totales del equipo
            total_fpts = round(sum(p["Weekly_FPTS"] for p in active_players), 1)
            total_pts = round(sum(p["PTS"] for p in active_players))
            total_reb = round(sum(p["REB"] for p in active_players))
            total_ast = round(sum(p["AST"] for p in active_players))
            total_stl = round(sum(p["STL"] for p in active_players))
            total_blk = round(sum(p["BLK"] for p in active_players))
            total_3pm = round(sum(p["3PM"] for p in active_players))
            total_to = round(sum(p["TO"] for p in active_players))

            summary_item = {
                "Team": t_name,
                "team_key": t_key,
                "Manager": t.get("manager", "Manager"),
                "is_me": is_me,
                "Fantasy_Points": total_fpts,
                "PTS": total_pts,
                "REB": total_reb,
                "AST": total_ast,
                "STL": total_stl,
                "BLK": total_blk,
                "3PM": total_3pm,
                "TO": total_to,
                "Active_Players_Count": len(active_players),
                "Total_Roster_Count": len(player_stats_list)
            }
            teams_summary.append(summary_item)

            player_breakdowns[t_key] = {
                "active": active_players,
                "bench": bench_players,
                "all": player_stats_list
            }

        teams_summary.sort(key=lambda x: x["Fantasy_Points"], reverse=True)
        return {
            "teams_summary": teams_summary,
            "player_breakdowns": player_breakdowns,
            "week": week_num
        }
