"""
Módulo del Administrador del Draft en Vivo con soporte para Snake Draft y Ligas de Puntos / 9-Cat.
Calcula automáticamente los turnos Snake, cuenta regresiva hacia tu próximo pick y sugerencias por FPPG y necesidades de plantilla.
"""

import json
import os
from typing import Dict, List, Optional, Any, Tuple
import pandas as pd
from src.core.zscore import ZScoreEngine
from src.core.punt_strategy import PuntStrategyManager
from src.core.points_engine import PointsLeagueEngine


class DraftManager:
    def __init__(
        self,
        projections_df: pd.DataFrame,
        num_teams: int = 12,
        my_team_index: int = 1,
        league_format: str = "points",  # 'points' o '9-cat'
        scoring_rules: Optional[Dict[str, float]] = None,
        state_file: str = "data/draft_state.json"
    ):
        self.raw_df = projections_df.copy()
        self.num_teams = num_teams
        self.my_team_index = my_team_index
        self.league_format = league_format
        self.state_file = state_file

        # Motores
        self.points_engine = PointsLeagueEngine(scoring_rules=scoring_rules, num_teams=num_teams)
        self.z_engine = ZScoreEngine().fit(self.raw_df)
        self.punt_manager = PuntStrategyManager(self.z_engine)

        # Estado del draft
        self.drafted_players: Dict[str, int] = {}  # {player_name: team_index}
        self.my_roster: List[str] = []
        self.pick_history: List[Dict[str, Any]] = []
        self.punted_categories: List[str] = []

        # Cargar estado previo
        self.load_state()

    def get_snake_team_on_clock(self, overall_pick: int) -> int:
        """
        Calcula el equipo al que le corresponde elegir según el orden Snake.
        Ronda 1 (impar): 1 -> N
        Ronda 2 (par):   N -> 1
        """
        round_num = (overall_pick - 1) // self.num_teams + 1
        pos_in_round = (overall_pick - 1) % self.num_teams

        if round_num % 2 == 1:
            # Ronda impar: orden normal 1 a N
            return pos_in_round + 1
        else:
            # Ronda par: orden inverso N a 1
            return self.num_teams - pos_in_round

    def get_my_upcoming_picks(self, total_rounds: int = 13) -> List[int]:
        """Calcula todos los números de pick globales que le corresponden a tu equipo en el formato Snake"""
        my_picks = []
        for r in range(1, total_rounds + 1):
            if r % 2 == 1:
                pick_num = (r - 1) * self.num_teams + self.my_team_index
            else:
                pick_num = (r - 1) * self.num_teams + (self.num_teams - self.my_team_index + 1)
            my_picks.append(pick_num)
        return my_picks

    def get_picks_until_my_turn(self) -> Tuple[int, Optional[int]]:
        """
        Retorna (cantidad_de_picks_restantes, proximo_pick_global).
        Si ya es tu turno, retorna (0, proximo_pick).
        """
        current_overall = len(self.pick_history) + 1
        all_my_picks = self.get_my_upcoming_picks()

        future_picks = [p for p in all_my_picks if p >= current_overall]
        if not future_picks:
            return (999, None)

        next_pick = future_picks[0]
        picks_remaining = next_pick - current_overall
        return (picks_remaining, next_pick)

    def set_league_format(self, league_format: str):
        self.league_format = league_format
        self.save_state()

    def set_punt_categories(self, categories: List[str]):
        self.punted_categories = list(set(categories))

    def make_pick(self, player_name: str, team_index: Optional[int] = None) -> bool:
        """Registra un pick. Si no se pasa team_index, lo calcula automáticamente con el orden Snake"""
        if player_name in self.drafted_players:
            return False

        overall_pick = len(self.pick_history) + 1
        if team_index is None:
            team_index = self.get_snake_team_on_clock(overall_pick)

        round_num = (overall_pick - 1) // self.num_teams + 1

        self.drafted_players[player_name] = team_index
        if team_index == self.my_team_index:
            self.my_roster.append(player_name)

        self.pick_history.append({
            "overall_pick": overall_pick,
            "round": round_num,
            "team_index": team_index,
            "player": player_name,
            "is_my_team": (team_index == self.my_team_index)
        })

        self.save_state()
        return True

    def undo_last_pick(self) -> Optional[Dict[str, Any]]:
        """Deshace la última selección realizada"""
        if not self.pick_history:
            return None

        last_pick = self.pick_history.pop()
        player = last_pick["player"]

        if player in self.drafted_players:
            del self.drafted_players[player]

        if player in self.my_roster:
            self.my_roster.remove(player)

        self.save_state()
        return last_pick

    def reset_draft(self):
        """Reinicia el draft completo"""
        self.drafted_players.clear()
        self.my_roster.clear()
        self.pick_history.clear()
        if os.path.exists(self.state_file):
            try:
                os.remove(self.state_file)
            except Exception:
                pass

    def get_available_players(self) -> pd.DataFrame:
        """Retorna jugadores disponibles ordenados según el formato activo (Puntos o 9-Cat)"""
        avail = self.raw_df[~self.raw_df["Player"].isin(self.drafted_players.keys())].copy()

        if self.league_format == "points":
            return self.points_engine.transform(avail)
        else:
            return self.punt_manager.apply_punt(avail, self.punted_categories)

    def get_my_roster_df(self) -> pd.DataFrame:
        """Retorna los datos de los jugadores en mi plantilla"""
        if not self.my_roster:
            return pd.DataFrame()
        roster_df = self.raw_df[self.raw_df["Player"].isin(self.my_roster)].copy()
        if self.league_format == "points":
            return self.points_engine.transform(roster_df)
        else:
            return self.z_engine.transform(roster_df)

    def get_positional_coverage(self) -> Dict[str, int]:
        """Cuenta cuántos jugadores tiene mi equipo por posición"""
        counts = {"PG": 0, "SG": 0, "SF": 0, "PF": 0, "C": 0}
        if not self.my_roster:
            return counts

        roster_df = self.raw_df[self.raw_df["Player"].isin(self.my_roster)]
        for _, row in roster_df.iterrows():
            pos_str = str(row.get("Positions", ""))
            for pos in counts.keys():
                if pos in pos_str:
                    counts[pos] += 1
        return counts

    def get_recommended_picks(self, top_n: int = 10, position_filter: Optional[str] = None) -> pd.DataFrame:
        """
        Recomendador inteligente para Snake Draft en Ligas de Puntos y 9-Cat:
        Considera FPPG / VORP y escasez en posiciones no cubiertas.
        """
        avail = self.get_available_players()

        if position_filter and position_filter != "TODAS":
            avail = avail[avail["Positions"].str.contains(position_filter, na=False)]

        coverage = self.get_positional_coverage()
        total_drafted = len(self.my_roster)

        # Score de recomendación
        def calc_rec(row):
            val = row["FPPG"] if self.league_format == "points" else row.get("Total_Value", 0.0)
            bonus = 0.0
            if total_drafted >= 3:
                pos = str(row.get("Positions", ""))
                for p, cnt in coverage.items():
                    if p in pos and cnt == 0:
                        bonus += 2.0 if self.league_format == "points" else 0.4
            return val + bonus

        avail["Rec_Score"] = avail.apply(calc_rec, axis=1)
        avail = avail.sort_values(by="Rec_Score", ascending=False).reset_index(drop=True)
        return avail.head(top_n)

    def save_state(self):
        state = {
            "drafted_players": self.drafted_players,
            "my_roster": self.my_roster,
            "pick_history": self.pick_history,
            "punted_categories": self.punted_categories,
            "num_teams": self.num_teams,
            "my_team_index": self.my_team_index,
            "league_format": self.league_format
        }
        try:
            os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[DraftManager] Error guardando estado: {e}")

    def load_state(self):
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    state = json.load(f)
                    self.drafted_players = state.get("drafted_players", {})
                    self.my_roster = state.get("my_roster", [])
                    self.pick_history = state.get("pick_history", [])
                    self.punted_categories = state.get("punted_categories", [])
                    self.num_teams = state.get("num_teams", self.num_teams)
                    self.my_team_index = state.get("my_team_index", self.my_team_index)
                    self.league_format = state.get("league_format", self.league_format)
            except Exception as e:
                print(f"[DraftManager] Error cargando estado: {e}")
