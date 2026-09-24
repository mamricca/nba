"""
Motor de Cálculo para Ligas de Puntos (Points League) de Fantasy Basketball.
Calcula Fantasy Points Per Game (FPPG), Puntos Totales Proyectados y VORP (Value Over Replacement Player).
"""

from typing import Dict, List, Optional
import pandas as pd


class PointsLeagueEngine:
    # Sistema de puntuación predeterminado de Yahoo Fantasy Points
    DEFAULT_SCORING = {
        "PTS": 1.0,
        "REB": 1.2,
        "AST": 1.5,
        "STL": 3.0,
        "BLK": 3.0,
        "3PM": 1.0,
        "TO": -1.0,
        "FGM": 0.0,
        "FGA": 0.0,
        "FTM": 0.0,
        "FTA": 0.0
    }

    def __init__(self, scoring_rules: Optional[Dict[str, float]] = None, num_teams: int = 12):
        self.scoring_rules = scoring_rules or self.DEFAULT_SCORING.copy()
        self.num_teams = num_teams

    def calculate_fppg(self, row: pd.Series) -> float:
        """Calcula los Fantasy Points por partido (FPPG) de un jugador"""
        points = 0.0
        for stat, weight in self.scoring_rules.items():
            if weight != 0.0 and stat in row and pd.notnull(row[stat]):
                points += float(row[stat]) * weight
        return round(points, 2)

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calcula FPPG, Total Points y Rankings para todos los jugadores del DataFrame.
        """
        df_res = df.copy()
        df_res["FPPG"] = df_res.apply(self.calculate_fppg, axis=1)

        # Si viene cantidad de partidos proyectados (GP), calcular Total Fantasy Points
        if "GP" in df_res.columns:
            df_res["Total_Points"] = round(df_res["FPPG"] * df_res["GP"], 1)
        else:
            df_res["Total_Points"] = round(df_res["FPPG"] * 75, 1)

        # Ordenar por FPPG y asignar ranking
        df_res = df_res.sort_values(by="FPPG", ascending=False).reset_index(drop=True)
        df_res["Rank"] = df_res.index + 1

        # Calcular VORP (Value Over Replacement Player) basado en el jugador #140 (línea de reemplazo para 12 equipos x 12 jugadores)
        replacement_idx = min(len(df_res) - 1, self.num_teams * 11)
        replacement_fppg = df_res.iloc[replacement_idx]["FPPG"] if len(df_res) > replacement_idx else 15.0
        df_res["VORP"] = round(df_res["FPPG"] - replacement_fppg, 2)

        return df_res

    def compute_team_points_total(self, team_df: pd.DataFrame) -> Dict[str, float]:
        """Calcula el total de puntos fantasy promedio y por semana para una plantilla"""
        if team_df.empty:
            return {"Total_FPPG": 0.0, "Projected_Weekly_Points": 0.0, "Starters_FPPG": 0.0}

        df_calc = self.transform(team_df) if "FPPG" not in team_df.columns else team_df
        total_fppg = df_calc["FPPG"].sum()
        # Top 10 titulares vs banca
        starters_fppg = df_calc.head(10)["FPPG"].sum()
        # Asumiendo ~3.3 partidos por jugador en la semana
        weekly_proj = round(starters_fppg * 3.3, 1)

        return {
            "Total_FPPG": round(total_fppg, 1),
            "Starters_FPPG": round(starters_fppg, 1),
            "Projected_Weekly_Points": weekly_proj
        }

