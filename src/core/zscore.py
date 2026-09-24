"""
Motor de Cálculo de Z-Scores para Fantasy Basketball (9-Cat y Personalizado).
Incluye ponderación de volumen para porcentajes (FG% y FT%) y cálculo de valor sobre reemplazo.
"""

from typing import Dict, List, Optional, Set
import numpy as np
import pandas as pd


class ZScoreEngine:
    # 9 categorías estándar de Yahoo Fantasy Basketball
    DEFAULT_CATEGORIES = ["PTS", "REB", "AST", "STL", "BLK", "3PM", "FG%", "FT%", "TO"]
    NEGATIVE_CATEGORIES = {"TO"}

    def __init__(self, baseline_size: int = 150):
        """
        :param baseline_size: Número de jugadores del top a usar como línea base para media y desviación estándar
        """
        self.baseline_size = baseline_size
        self.means: Dict[str, float] = {}
        self.stds: Dict[str, float] = {}
        self.fg_mean: float = 0.460
        self.ft_mean: float = 0.780

    def fit(self, df: pd.DataFrame) -> "ZScoreEngine":
        """Calcula las medias y desviaciones estándar sobre el pool de jugadores base"""
        # Filtrar o tomar los primeros baseline_size jugadores
        df_base = df.head(min(len(df), self.baseline_size)).copy()

        # Medias globales para impacto de porcentajes
        if "FG%" in df_base.columns:
            self.fg_mean = df_base["FG%"].mean()
        if "FT%" in df_base.columns:
            self.ft_mean = df_base["FT%"].mean()

        # Calcular métricas de impacto de volumen
        # Impacto FG = (FG% - FG%_medio) * FGA
        if "FG%" in df_base.columns and "FGA" in df_base.columns:
            df_base["_fg_impact"] = (df_base["FG%"] - self.fg_mean) * df_base["FGA"]
            self.means["FG%"] = df_base["_fg_impact"].mean()
            self.stds["FG%"] = df_base["_fg_impact"].std() or 1.0

        # Impacto FT = (FT% - FT%_medio) * FTA
        if "FT%" in df_base.columns and "FTA" in df_base.columns:
            df_base["_ft_impact"] = (df_base["FT%"] - self.ft_mean) * df_base["FTA"]
            self.means["FT%"] = df_base["_ft_impact"].mean()
            self.stds["FT%"] = df_base["_ft_impact"].std() or 1.0

        # Categorías de conteo directo
        counting_cats = ["PTS", "REB", "AST", "STL", "BLK", "3PM", "TO"]
        for cat in counting_cats:
            if cat in df_base.columns:
                self.means[cat] = df_base[cat].mean()
                self.stds[cat] = df_base[cat].std() or 1.0

        return self

    def transform(
        self,
        df: pd.DataFrame,
        active_categories: Optional[List[str]] = None,
        weights: Optional[Dict[str, float]] = None
    ) -> pd.DataFrame:
        """
        Calcula los Z-scores individuales por categoría y el Z-score total (Value).
        """
        df_res = df.copy()

        if active_categories is None:
            active_categories = self.DEFAULT_CATEGORIES

        if weights is None:
            weights = {cat: 1.0 for cat in active_categories}

        z_cols = []

        # Calcular Z-score para cada categoría activa
        for cat in active_categories:
            z_col = f"z_{cat}"
            z_cols.append(z_col)

            if cat == "FG%" and "FG%" in df_res.columns and "FGA" in df_res.columns:
                impact = (df_res["FG%"] - self.fg_mean) * df_res["FGA"]
                z = (impact - self.means.get("FG%", 0.0)) / self.stds.get("FG%", 1.0)
            elif cat == "FT%" and "FT%" in df_res.columns and "FTA" in df_res.columns:
                impact = (df_res["FT%"] - self.ft_mean) * df_res["FTA"]
                z = (impact - self.means.get("FT%", 0.0)) / self.stds.get("FT%", 1.0)
            elif cat in self.means:
                raw = df_res[cat]
                z = (raw - self.means[cat]) / self.stds[cat]
                # Invertir para estadísticas negativas como Pérdidas (TO)
                if cat in self.NEGATIVE_CATEGORIES:
                    z = -z
            else:
                z = pd.Series(0.0, index=df_res.index)

            # Aplicar ponderación
            weight = weights.get(cat, 1.0)
            df_res[z_col] = z * weight

        # Z-score total acumulado
        df_res["Total_Value"] = df_res[z_cols].sum(axis=1)

        # Ranking general
        df_res = df_res.sort_values(by="Total_Value", ascending=False).reset_index(drop=True)
        df_res["Rank"] = df_res.index + 1

        return df_res

    def compute_team_balance(self, team_df: pd.DataFrame, active_categories: Optional[List[str]] = None) -> Dict[str, float]:
        """Calcula el balance acumulado del equipo por categoría en unidades Z-score"""
        if active_categories is None:
            active_categories = self.DEFAULT_CATEGORIES

        scores = {}
        for cat in active_categories:
            z_col = f"z_{cat}"
            if z_col in team_df.columns:
                scores[cat] = float(team_df[z_col].sum())
            else:
                scores[cat] = 0.0
        return scores

