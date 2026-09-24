"""
Módulo para gestión y cálculo dinámico de estrategias "Punt" (descarte de categorías).
Permite identificar jugadores infravalorados o robos específicos para cada tipo de alineación.
"""

from typing import Dict, List, Optional, Set
import pandas as pd
from .zscore import ZScoreEngine


class PuntStrategyManager:
    # Estrategias Punt populares predefinidas en NBA Fantasy
    PRESET_STRATEGIES = {
        "Punt FT% + TO (Big Man Dominance)": ["FT%", "TO"],
        "Punt FT% (Giannis / Gobert Build)": ["FT%"],
        "Punt FG% + TO (Guard Heavy / Triples)": ["FG%", "TO"],
        "Punt AST (Wings & Bigs)": ["AST"],
        "Punt PTS + 3PM (Efficiency & Defense)": ["PTS", "3PM"],
        "Punt BLK (Guard Dominant)": ["BLK"],
        "Punt TO Only (High Usage Playmakers)": ["TO"],
    }

    def __init__(self, z_engine: ZScoreEngine):
        self.z_engine = z_engine

    def apply_punt(
        self,
        df_base: pd.DataFrame,
        punt_categories: List[str]
    ) -> pd.DataFrame:
        """
        Recalcula los rankings y el valor de cada jugador excluyendo las categorías a 'puntear'.
        Añade columnas de delta de ranking (Punt_Rank_Shift) para detectar 'steals' o 'traps'.
        """
        all_cats = self.z_engine.DEFAULT_CATEGORIES
        active_cats = [c for c in all_cats if c not in punt_categories]

        # 1. Ranking sin Punt (Original)
        df_original = self.z_engine.transform(df_base, active_categories=all_cats)
        original_ranks = dict(zip(df_original["Player"], df_original["Rank"]))
        original_vals = dict(zip(df_original["Player"], df_original["Total_Value"]))

        # 2. Ranking con Punt
        df_punt = self.z_engine.transform(df_base, active_categories=active_cats)
        
        # 3. Calcular diferencias
        df_punt["Orig_Rank"] = df_punt["Player"].map(original_ranks)
        df_punt["Orig_Value"] = df_punt["Player"].map(original_vals)
        df_punt["Punt_Rank"] = df_punt["Rank"]
        df_punt["Rank_Shift"] = df_punt["Orig_Rank"] - df_punt["Punt_Rank"]  # Positivo = Sube posiciones en el draft
        df_punt["Value_Diff"] = df_punt["Total_Value"] - df_punt["Orig_Value"]
        df_punt["Punted_Categories"] = ", ".join(punt_categories) if punt_categories else "Ninguna"

        return df_punt

    def get_top_punt_boosters(self, df_punt: pd.DataFrame, top_n: int = 15) -> pd.DataFrame:
        """Devuelve los jugadores que más se benefician de la estrategia Punt actual (mayores subidas)"""
        # Excluir jugadores con ranking original muy bajo para evitar ruido de fondo
        viable_players = df_punt[df_punt["Orig_Rank"] <= 120].copy()
        return viable_players.sort_values(by="Rank_Shift", ascending=False).head(top_n)

    def get_top_punt_traps(self, df_punt: pd.DataFrame, top_n: int = 15) -> pd.DataFrame:
        """Devuelve los jugadores que más pierden valor con esta estrategia (evitar elegir temprano)"""
        viable_players = df_punt[df_punt["Orig_Rank"] <= 80].copy()
        return viable_players.sort_values(by="Rank_Shift", ascending=True).head(top_n)

