"""
Evaluador y Simulador de Traspasos (Trades) para Fantasy NBA.
Compara plantillas antes y después del intercambio para calcular el impacto categoría por categoría.
"""

from typing import Dict, List, Tuple, Any, Optional
import numpy as np
import pandas as pd
from .zscore import ZScoreEngine


class TradeEvaluator:
    def __init__(self, z_engine: ZScoreEngine):
        self.z_engine = z_engine

    def evaluate_trade(
        self,
        team_a_roster: pd.DataFrame,
        team_b_roster: pd.DataFrame,
        giving_players_a: List[str],  # Jugadores que salen de A hacia B
        receiving_players_a: List[str], # Jugadores que llegan a A desde B
        active_categories: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Calcula el impacto detallado de un traspaso para ambos equipos.
        """
        if active_categories is None:
            active_categories = self.z_engine.DEFAULT_CATEGORIES

        # 1. Separar datos de jugadores
        df_giving_a = team_a_roster[team_a_roster["Player"].isin(giving_players_a)].copy()
        df_receiving_a = team_b_roster[team_b_roster["Player"].isin(receiving_players_a)].copy()

        # 2. Nuevos Rosters Proyectados
        new_roster_a = pd.concat([
            team_a_roster[~team_a_roster["Player"].isin(giving_players_a)],
            df_receiving_a
        ]).reset_index(drop=True)

        new_roster_b = pd.concat([
            team_b_roster[~team_b_roster["Player"].isin(receiving_players_a)],
            df_giving_a
        ]).reset_index(drop=True)

        # 3. Calcular Z-Scores antes y después para Team A
        z_before_a = self.z_engine.compute_team_balance(team_a_roster, active_categories)
        z_after_a = self.z_engine.compute_team_balance(new_roster_a, active_categories)

        z_diff_a = {cat: round(z_after_a.get(cat, 0.0) - z_before_a.get(cat, 0.0), 3) for cat in active_categories}
        total_z_diff_a = round(sum(z_diff_a.values()), 3)

        # 4. Deltas en estadísticas brutas / promedio por partido
        stats_diff_a = {}
        for cat in ["PTS", "REB", "AST", "STL", "BLK", "3PM", "TO"]:
            if cat in team_a_roster.columns:
                before_sum = team_a_roster[cat].sum()
                after_sum = new_roster_a[cat].sum()
                stats_diff_a[cat] = round(after_sum - before_sum, 2)

        # Porcentajes de tiro del equipo (ponderados por intentos)
        if "FGM" in team_a_roster.columns and "FGA" in team_a_roster.columns:
            fg_before = team_a_roster["FGM"].sum() / max(team_a_roster["FGA"].sum(), 1.0)
            fg_after = new_roster_a["FGM"].sum() / max(new_roster_a["FGA"].sum(), 1.0)
            stats_diff_a["FG%"] = round((fg_after - fg_before) * 100, 2)  # en puntos porcentuales

        if "FTM" in team_a_roster.columns and "FTA" in team_a_roster.columns:
            ft_before = team_a_roster["FTM"].sum() / max(team_a_roster["FTA"].sum(), 1.0)
            ft_after = new_roster_a["FTM"].sum() / max(new_roster_a["FTA"].sum(), 1.0)
            stats_diff_a["FT%"] = round((ft_after - ft_before) * 100, 2)

        # 5. Conteo de categorías ganadas vs perdidas
        cats_improved = [cat for cat, delta in z_diff_a.items() if delta > 0.1]
        cats_worsened = [cat for cat, delta in z_diff_a.items() if delta < -0.1]
        cats_neutral = [cat for cat, delta in z_diff_a.items() if abs(delta) <= 0.1]

        # Veredicto
        if total_z_diff_a > 1.0 and len(cats_improved) >= len(cats_worsened):
            verdict = "🔥 Gran Mejora (Trade Altamente Recomendado)"
        elif total_z_diff_a > 0.2:
            verdict = "✅ Favorable (Ganas valor neto)"
        elif abs(total_z_diff_a) <= 0.2:
            verdict = "⚖️ Equilibrado (Ajuste de necesidades de categorías)"
        elif total_z_diff_a > -1.0:
            verdict = "⚠️ Desfavorable (Pérdida moderada de valor)"
        else:
            verdict = "❌ Muy Desfavorable (No recomendado)"

        return {
            "verdict": verdict,
            "total_z_delta_team_a": total_z_diff_a,
            "category_z_deltas_team_a": z_diff_a,
            "raw_stats_deltas_team_a": stats_diff_a,
            "categories_improved": cats_improved,
            "categories_worsened": cats_worsened,
            "categories_neutral": cats_neutral,
            "team_a_giving": giving_players_a,
            "team_a_receiving": receiving_players_a,
            "new_roster_a": new_roster_a,
            "new_roster_b": new_roster_b
        }
