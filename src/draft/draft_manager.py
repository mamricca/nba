"""
Módulo del Administrador del Draft en Vivo con soporte para Snake Draft y Ligas de Puntos / 9-Cat.
Calcula automáticamente los turnos Snake, cuenta regresiva hacia tu próximo pick, nombres personalizados de equipos y sugerencias por FPPG.
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
        self.team_names: Dict[int, str] = {}

        # Cargar estado previo
        self.load_state()

    def _ensure_team_names_dict(self):
        if not hasattr(self, "team_names") or not isinstance(self.team_names, dict):
            self.team_names = {}

    def get_team_name(self, team_idx: int) -> str:
        """Retorna el nombre personalizado del equipo o su nombre por defecto"""
        self._ensure_team_names_dict()
        try:
            team_idx = int(team_idx)
        except Exception:
            pass

        if team_idx in self.team_names and str(self.team_names[team_idx]).strip():
            return str(self.team_names[team_idx]).strip()
        if team_idx == getattr(self, "my_team_index", 1):
            return "Mi Equipo (Tú)"
        return f"Equipo {team_idx}"

    def set_team_name(self, team_idx: int, name: str):
        """Asigna un nombre personalizado a un equipo y guarda el estado"""
        self._ensure_team_names_dict()
        if name and str(name).strip():
            self.team_names[int(team_idx)] = str(name).strip()
            self.save_state()

    def set_all_team_names(self, names_dict: Dict[int, str]):
        """Actualiza todos los nombres de los equipos de la liga"""
        self._ensure_team_names_dict()
        for idx, name in names_dict.items():
            if name and str(name).strip():
                self.team_names[int(idx)] = str(name).strip()
        self.save_state()

    def get_snake_team_on_clock(self, overall_pick: int) -> int:
        """
        Calcula el equipo al que le corresponde elegir según el orden Snake.
        Ronda 1 (impar): 1 -> N
        Ronda 2 (par):   N -> 1
        """
        num_t = getattr(self, "num_teams", 12)
        round_num = (overall_pick - 1) // num_t + 1
        pos_in_round = (overall_pick - 1) % num_t

        if round_num % 2 == 1:
            return pos_in_round + 1
        else:
            return num_t - pos_in_round

    def get_my_upcoming_picks(self, total_rounds: int = 13) -> List[int]:
        """Calcula todos los números de pick globales que le corresponden a tu equipo en el formato Snake"""
        my_picks = []
        num_t = getattr(self, "num_teams", 12)
        my_idx = getattr(self, "my_team_index", 1)
        for r in range(1, total_rounds + 1):
            if r % 2 == 1:
                pick_num = (r - 1) * num_t + my_idx
            else:
                pick_num = (r - 1) * num_t + (num_t - my_idx + 1)
            my_picks.append(pick_num)
        return my_picks

    def get_picks_until_my_turn(self) -> Tuple[int, Optional[int]]:
        """
        Retorna (cantidad_de_picks_restantes, proximo_pick_global).
        Si ya es tu turno, retorna (0, proximo_pick).
        """
        history = getattr(self, "pick_history", [])
        current_overall = len(history) + 1
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
        if not hasattr(self, "drafted_players"):
            self.drafted_players = {}
        if not hasattr(self, "my_roster"):
            self.my_roster = []
        if not hasattr(self, "pick_history"):
            self.pick_history = []

        if player_name in self.drafted_players:
            return False

        overall_pick = len(self.pick_history) + 1
        if team_index is None:
            team_index = self.get_snake_team_on_clock(overall_pick)

        num_t = getattr(self, "num_teams", 12)
        round_num = (overall_pick - 1) // num_t + 1
        t_name = self.get_team_name(team_index)
        my_idx = getattr(self, "my_team_index", 1)

        self.drafted_players[player_name] = team_index
        if team_index == my_idx:
            self.my_roster.append(player_name)

        self.pick_history.append({
            "overall_pick": overall_pick,
            "round": round_num,
            "team_index": team_index,
            "team_name": t_name,
            "player": player_name,
            "is_my_team": (team_index == my_idx)
        })

        self.save_state()
        return True

    def undo_last_pick(self) -> Optional[Dict[str, Any]]:
        """Deshace la última selección realizada"""
        if not hasattr(self, "pick_history") or not self.pick_history:
            return None

        last_pick = self.pick_history.pop()
        player = last_pick["player"]

        if hasattr(self, "drafted_players") and player in self.drafted_players:
            del self.drafted_players[player]

        if hasattr(self, "my_roster") and player in self.my_roster:
            self.my_roster.remove(player)

        self.save_state()
        return last_pick

    def reset_draft(self):
        """Reinicia el draft completo preservando los nombres de equipos"""
        self._ensure_team_names_dict()
        saved_names = dict(self.team_names)
        self.drafted_players = {}
        self.my_roster = []
        self.pick_history = []
        self.team_names = saved_names
        self.save_state()

    def get_available_players(self) -> pd.DataFrame:
        """Retorna jugadores disponibles ordenados según el formato activo (Puntos o 9-Cat)"""
        drafted = getattr(self, "drafted_players", {})
        avail = self.raw_df[~self.raw_df["Player"].isin(drafted.keys())].copy()

        fmt = getattr(self, "league_format", "points")
        if fmt == "points":
            return self.points_engine.transform(avail)
        else:
            punted = getattr(self, "punted_categories", [])
            return self.punt_manager.apply_punt(avail, punted)

    def get_my_roster_df(self) -> pd.DataFrame:
        """Retorna los datos de los jugadores en mi plantilla"""
        roster = getattr(self, "my_roster", [])
        if not roster:
            return pd.DataFrame()
        roster_df = self.raw_df[self.raw_df["Player"].isin(roster)].copy()
        fmt = getattr(self, "league_format", "points")
        if fmt == "points":
            return self.points_engine.transform(roster_df)
        else:
            return self.z_engine.transform(roster_df)

    def get_team_roster_df(self, team_idx: int) -> pd.DataFrame:
        """Retorna el DataFrame de los jugadores drafteados por un equipo específico"""
        drafted = getattr(self, "drafted_players", {})
        players = [p for p, t_id in drafted.items() if t_id == team_idx]
        if not players:
            return pd.DataFrame()
        roster_df = self.raw_df[self.raw_df["Player"].isin(players)].copy()
        fmt = getattr(self, "league_format", "points")
        if fmt == "points":
            return self.points_engine.transform(roster_df)
        else:
            return self.z_engine.transform(roster_df)

    def get_positional_coverage(self) -> Dict[str, int]:
        """Cuenta cuántos jugadores tiene mi equipo por posición"""
        counts = {"PG": 0, "SG": 0, "SF": 0, "PF": 0, "C": 0}
        roster = getattr(self, "my_roster", [])
        if not roster:
            return counts

        roster_df = self.raw_df[self.raw_df["Player"].isin(roster)]
        for _, row in roster_df.iterrows():
            pos_str = str(row.get("Positions", ""))
            for pos in counts.keys():
                if pos in pos_str:
                    counts[pos] += 1
        return counts

    def get_recommended_picks(self, top_n: int = 10, position_filter: Optional[str] = None) -> pd.DataFrame:
        """
        Recomendador inteligente para Snake Draft en Ligas de Puntos y 9-Cat.
        """
        avail = self.get_available_players()

        if position_filter and position_filter != "TODAS":
            avail = avail[avail["Positions"].str.contains(position_filter, na=False)]

        coverage = self.get_positional_coverage()
        roster = getattr(self, "my_roster", [])
        total_drafted = len(roster)
        fmt = getattr(self, "league_format", "points")

        def calc_rec(row):
            base_val = row["FPPG"] if fmt == "points" else row.get("Total_Value", 0.0)
            bonus = 0.0
            pos_str = str(row.get("Positions", ""))

            if total_drafted >= 1:
                unfilled_covered = [p for p, cnt in coverage.items() if cnt == 0 and p in pos_str]
                if unfilled_covered:
                    scarcity_multiplier = 1.0 + (total_drafted * 0.4)
                    bonus += (2.5 * scarcity_multiplier) if fmt == "points" else (0.5 * scarcity_multiplier)

                all_saturated = all(coverage.get(p, 0) >= 2 for p in pos_str.split("/") if p in coverage)
                if all_saturated and total_drafted >= 2:
                    bonus -= 3.0 if fmt == "points" else 0.6

            return base_val + bonus

        avail["Rec_Score"] = avail.apply(calc_rec, axis=1)
        avail = avail.sort_values(by="Rec_Score", ascending=False).reset_index(drop=True)
        return avail.head(top_n)

    def save_state(self):
        self._ensure_team_names_dict()
        state = {
            "drafted_players": getattr(self, "drafted_players", {}),
            "my_roster": getattr(self, "my_roster", []),
            "pick_history": getattr(self, "pick_history", []),
            "punted_categories": getattr(self, "punted_categories", []),
            "num_teams": getattr(self, "num_teams", 12),
            "my_team_index": getattr(self, "my_team_index", 1),
            "league_format": getattr(self, "league_format", "points"),
            "team_names": getattr(self, "team_names", {})
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
                    raw_names = state.get("team_names", {})
                    self.team_names = {int(k): v for k, v in raw_names.items()}
            except Exception as e:
                print(f"[DraftManager] Error cargando estado: {e}")
