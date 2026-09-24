"""
Pruebas Unitarias para el Motor de Z-Scores, Ligas de Puntos (FPPG), Snake Draft y Analítica.
"""

import unittest
import os
import sys
import pandas as pd
import numpy as np

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.core.zscore import ZScoreEngine
from src.core.punt_strategy import PuntStrategyManager
from src.core.points_engine import PointsLeagueEngine
from src.core.trade_evaluator import TradeEvaluator
from src.draft.draft_manager import DraftManager
from src.analytics.matchup_analyzer import MatchupAnalyzer
from src.analytics.streamer_finder import StreamerFinder


class TestNBAFantasyAssistant(unittest.TestCase):

    def setUp(self):
        self.df = pd.read_csv("data/projections_sample.csv")
        self.z_engine = ZScoreEngine().fit(self.df)
        self.points_engine = PointsLeagueEngine(num_teams=12)

    def test_points_league_fppg(self):
        """Verifica el cálculo de FPPG y VORP para ligas de puntos"""
        df_pts = self.points_engine.transform(self.df)
        self.assertIn("FPPG", df_pts.columns)
        self.assertIn("VORP", df_pts.columns)
        self.assertIn("Total_Points", df_pts.columns)

        # El mejor jugador debe tener más de 45 FPPG
        self.assertGreater(df_pts.iloc[0]["FPPG"], 45.0)

    def test_snake_draft_order_and_countdown(self):
        """Verifica la rotación exacta del Snake Draft y cuenta regresiva hacia el turno del usuario"""
        # Liga de 12 equipos, usuario es el Equipo #4
        draft_mgr = DraftManager(
            projections_df=self.df,
            num_teams=12,
            my_team_index=4,
            league_format="points",
            state_file="data/test_snake_draft.json"
        )
        draft_mgr.reset_draft()

        # Ronda 1 (impar): orden 1..12
        self.assertEqual(draft_mgr.get_snake_team_on_clock(1), 1)
        self.assertEqual(draft_mgr.get_snake_team_on_clock(4), 4)
        self.assertEqual(draft_mgr.get_snake_team_on_clock(12), 12)

        # Ronda 2 (par): orden 12..1 (Snake)
        self.assertEqual(draft_mgr.get_snake_team_on_clock(13), 12)
        # Equipo 4 en ronda 2 elige en el pick global: 12 + (12 - 4 + 1) = 21
        self.assertEqual(draft_mgr.get_snake_team_on_clock(21), 4)

        # Picks globales del equipo 4: #4, #21, #28, #45...
        my_picks = draft_mgr.get_my_upcoming_picks()
        self.assertEqual(my_picks[0], 4)
        self.assertEqual(my_picks[1], 21)
        self.assertEqual(my_picks[2], 28)

        # Al inicio, faltan 3 picks para el turno 4 (1, 2, 3 -> le toca en el 4)
        picks_left, next_pick = draft_mgr.get_picks_until_my_turn()
        self.assertEqual(picks_left, 3)
        self.assertEqual(next_pick, 4)

    def test_zscore_calculation(self):
        df_transformed = self.z_engine.transform(self.df)
        self.assertIn("Total_Value", df_transformed.columns)
        top_player = df_transformed.iloc[0]
        self.assertGreater(top_player["Total_Value"], 5.0)

    def test_trade_evaluator(self):
        roster_a = self.df.head(10).copy()
        roster_b = self.df.iloc[10:20].copy()
        evaluator = TradeEvaluator(self.z_engine)
        result = evaluator.evaluate_trade(
            team_a_roster=roster_a,
            team_b_roster=roster_b,
            giving_players_a=[roster_a.iloc[0]["Player"]],
            receiving_players_a=[roster_b.iloc[0]["Player"]]
        )
        self.assertIn("verdict", result)


if __name__ == "__main__":
    unittest.main()
