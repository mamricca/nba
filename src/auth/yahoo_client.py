"""
Módulo de cliente y autenticación para la API de Yahoo Fantasy Sports.
Soporta autenticación OAuth2 real y modo Demo/Simulado para desarrollo y pruebas.
"""

import json
import os
from typing import Dict, List, Optional, Any
import pandas as pd


class YahooFantasyClient:
    def __init__(self, oauth_file: str = "config/oauth2.json", use_mock: bool = False):
        self.oauth_file = oauth_file
        self.use_mock = use_mock
        self.sc = None
        self.gm = None
        self.league = None
        self.is_authenticated = False
        
        # Intentar autenticar si no se fuerza modo mock
        if not use_mock and os.path.exists(self.oauth_file):
            try:
                self._authenticate()
            except Exception as e:
                print(f"[YahooClient] Error al autenticar con Yahoo API ({e}). Usando modo Demo.")
                self.use_mock = True
        else:
            self.use_mock = True

    def _authenticate(self):
        """Inicializa la sesión OAuth2 con Yahoo Fantasy API"""
        try:
            from yahoo_oauth import OAuth2
            import yahoo_fantasy_api as yfa
            
            # yahoo_oauth lee directamente el archivo json
            self.sc = OAuth2(None, None, from_file=self.oauth_file)
            if self.sc.is_logged_in():
                self.gm = yfa.Game(self.sc, 'nba')
                self.is_authenticated = True
            else:
                self.use_mock = True
        except Exception as e:
            self.is_authenticated = False
            self.use_mock = True
            raise e

    def set_league(self, league_id: str):
        """Establece la liga activa"""
        if not self.use_mock and self.is_authenticated:
            try:
                import yahoo_fantasy_api as yfa
                self.league = self.gm.to_league(league_id)
                return True
            except Exception as e:
                print(f"[YahooClient] Error conectando a liga {league_id}: {e}")
        return False

    def get_user_leagues(self) -> List[Dict[str, Any]]:
        """Retorna las ligas de NBA Fantasy del usuario"""
        if not self.use_mock and self.is_authenticated:
            try:
                league_ids = self.gm.league_ids()
                leagues = []
                for lid in league_ids:
                    l = self.gm.to_league(lid)
                    meta = l.settings()
                    leagues.append({
                        "league_id": lid,
                        "name": meta.get("name", f"Liga {lid}"),
                        "num_teams": meta.get("num_teams", 12),
                        "scoring_type": meta.get("scoring_type", "head")
                    })
                return leagues
            except Exception as e:
                print(f"[YahooClient] Error obteniendo ligas: {e}")

        # Datos Simulados de Ejemplo (Modo Demo)
        return [
            {
                "league_id": "nba.l.123456",
                "name": "NBA Fantasy Amigos 2024-2025",
                "num_teams": 12,
                "scoring_type": "head"
            }
        ]

    def get_teams(self) -> List[Dict[str, Any]]:
        """Retorna todos los equipos de la liga activa"""
        if not self.use_mock and self.league:
            try:
                teams_data = self.league.teams()
                teams = []
                for team_key, details in teams_data.items():
                    teams.append({
                        "team_key": team_key,
                        "team_id": details.get("team_id"),
                        "name": details.get("name"),
                        "manager": details.get("managers", [{}])[0].get("nickname", "Manager"),
                        "is_current_user": details.get("is_current_login", 0) == 1
                    })
                return teams
            except Exception as e:
                print(f"[YahooClient] Error obteniendo equipos: {e}")

        # Equipos Mock
        return [
            {"team_key": "nba.l.123456.t.1", "team_id": "1", "name": "Mi Equipo (Dream Team)", "manager": "Tú", "is_current_user": True},
            {"team_key": "nba.l.123456.t.2", "team_id": "2", "name": "Los Pistoleros", "manager": "Carlos", "is_current_user": False},
            {"team_key": "nba.l.123456.t.3", "team_id": "3", "name": "Rim Protectors", "manager": "Mateo", "is_current_user": False},
            {"team_key": "nba.l.123456.t.4", "team_id": "4", "name": "Triple Threat", "manager": "Lucas", "is_current_user": False},
            {"team_key": "nba.l.123456.t.5", "team_id": "5", "name": "Fast Break Express", "manager": "Santi", "is_current_user": False},
            {"team_key": "nba.l.123456.t.6", "team_id": "6", "name": "Ankle Breakers", "manager": "Joaquín", "is_current_user": False},
            {"team_key": "nba.l.123456.t.7", "team_id": "7", "name": "Alley Oops", "manager": "Diego", "is_current_user": False},
            {"team_key": "nba.l.123456.t.8", "team_id": "8", "name": "Dime Droppers", "manager": "Andrés", "is_current_user": False},
            {"team_key": "nba.l.123456.t.9", "team_id": "9", "name": "Zone Defense", "manager": "Martín", "is_current_user": False},
            {"team_key": "nba.l.123456.t.10", "team_id": "10", "name": "Clutch City", "manager": "Nico", "is_current_user": False},
            {"team_key": "nba.l.123456.t.11", "team_id": "11", "name": "Post Up Masters", "manager": "Facu", "is_current_user": False},
            {"team_key": "nba.l.123456.t.12", "team_id": "12", "name": "Buzzer Beaters", "manager": "Bruno", "is_current_user": False}
        ]

    def get_roster(self, team_key: str = "nba.l.123456.t.1") -> List[Dict[str, Any]]:
        """Retorna el roster de un equipo específico leyendo draft_state.json o league_rosters.json"""
        if not self.use_mock and self.league:
            try:
                team = self.league.to_team(team_key)
                return team.roster()
            except Exception as e:
                print(f"[YahooClient] Error obteniendo roster {team_key} de Yahoo: {e}")

        # Extraer índice de equipo si el formato es nba.l.123456.t.X
        team_idx = 1
        try:
            if ".t." in team_key:
                team_idx = int(team_key.split(".t.")[-1])
        except Exception:
            team_idx = 1

        # 1. Intentar cargar desde data/league_rosters.json
        league_rosters_file = "data/league_rosters.json"
        if os.path.exists(league_rosters_file):
            try:
                with open(league_rosters_file, "r", encoding="utf-8") as f:
                    lr_data = json.load(f)
                    if team_key in lr_data and lr_data[team_key]:
                        return [{"name": name, "selected_position": "BN", "eligible_positions": ["PG", "SG", "SF", "PF", "C"]} for name in lr_data[team_key]]
                    if str(team_idx) in lr_data and lr_data[str(team_idx)]:
                        return [{"name": name, "selected_position": "BN", "eligible_positions": ["PG", "SG", "SF", "PF", "C"]} for name in lr_data[str(team_idx)]]
            except Exception:
                pass

        # 2. Intentar cargar desde draft_state.json
        state_file = "data/draft_state.json"
        if os.path.exists(state_file):
            try:
                with open(state_file, "r", encoding="utf-8") as f:
                    state = json.load(f)
                    if team_idx == state.get("my_team_index", 1):
                        my_roster = state.get("my_roster", [])
                        if my_roster:
                            return [{"name": name, "selected_position": "BN", "eligible_positions": ["PG", "SG", "SF", "PF", "C"]} for name in my_roster]
                    
                    # Buscar jugadores asignados a este team_idx en drafted_players
                    drafted = state.get("drafted_players", {})
                    team_players = [p for p, t_id in drafted.items() if t_id == team_idx]
                    if team_players:
                        return [{"name": name, "selected_position": "BN", "eligible_positions": ["PG", "SG", "SF", "PF", "C"]} for name in team_players]
            except Exception:
                pass

        # Fallback predeterminado para pruebas iniciales
        default_rosters = {
            1: ["Nikola Jokic", "Tyrese Haliburton", "Derrick White", "Evan Mobley", "Brook Lopez", "Alex Caruso", "Mike Conley", "Trey Murphy III", "Naz Reid", "Jalen Duren", "Al Horford", "Dennis Schroder", "Grayson Allen"],
            2: ["Luka Doncic", "Stephen Curry", "Karl-Anthony Towns", "Dejounte Murray", "Mikal Bridges", "Tobias Harris", "Malcolm Brogdon", "Bogdan Bogdanovic", "Norman Powell", "Bobby Portis", "Cole Anthony", "Gary Trent Jr.", "Wendell Carter Jr."],
            3: ["Giannis Antetokounmpo", "Anthony Davis", "Bam Adebayo", "Rudy Gobert", "Jarrett Allen", "Clint Capela", "Walker Kessler", "Ivica Zubac", "Jakob Poeltl", "Daniel Gafford", "Steven Adams", "Mark Williams", "Mitchell Robinson"],
        }
        player_names = default_rosters.get(team_idx, default_rosters[1])
        return [{"name": name, "selected_position": "BN", "eligible_positions": ["PG", "SG", "SF", "PF", "C"]} for name in player_names]

    def add_player_to_team(self, team_key: str, player_name: str) -> bool:
        """Añade un agente libre a un equipo y lo remueve del pool de FA"""
        state_file = "data/draft_state.json"
        team_idx = 1
        try:
            if ".t." in team_key:
                team_idx = int(team_key.split(".t.")[-1])
        except Exception:
            team_idx = 1

        state = {}
        if os.path.exists(state_file):
            try:
                with open(state_file, "r", encoding="utf-8") as f:
                    state = json.load(f)
            except Exception:
                state = {}

        if "drafted_players" not in state:
            state["drafted_players"] = {}
        if "my_roster" not in state:
            state["my_roster"] = []

        state["drafted_players"][player_name] = team_idx
        if team_idx == state.get("my_team_index", 1):
            if player_name not in state["my_roster"]:
                state["my_roster"].append(player_name)

        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
        return True

    def drop_player_from_team(self, team_key: str, player_name: str) -> bool:
        """Corta un jugador de un equipo y lo devuelve a la agencia libre"""
        state_file = "data/draft_state.json"
        team_idx = 1
        try:
            if ".t." in team_key:
                team_idx = int(team_key.split(".t.")[-1])
        except Exception:
            team_idx = 1

        if os.path.exists(state_file):
            try:
                with open(state_file, "r", encoding="utf-8") as f:
                    state = json.load(f)

                if player_name in state.get("drafted_players", {}):
                    del state["drafted_players"][player_name]

                if team_idx == state.get("my_team_index", 1) and player_name in state.get("my_roster", []):
                    state["my_roster"].remove(player_name)

                with open(state_file, "w", encoding="utf-8") as f:
                    json.dump(state, f, indent=2, ensure_ascii=False)
                return True
            except Exception as e:
                print(f"[YahooClient] Error al cortar jugador: {e}")
        return False

    def trade_players(self, team_a_key: str, team_b_key: str, players_from_a: List[str], players_from_b: List[str]) -> bool:
        """Registra un intercambio de jugadores entre dos equipos"""
        team_a_idx = int(team_a_key.split(".t.")[-1]) if ".t." in team_a_key else 1
        team_b_idx = int(team_b_key.split(".t.")[-1]) if ".t." in team_b_key else 2

        state_file = "data/draft_state.json"
        state = {}
        if os.path.exists(state_file):
            try:
                with open(state_file, "r", encoding="utf-8") as f:
                    state = json.load(f)
            except Exception:
                pass

        if "drafted_players" not in state:
            state["drafted_players"] = {}
        if "my_roster" not in state:
            state["my_roster"] = []

        my_idx = state.get("my_team_index", 1)

        # Mover jugadores de A hacia B
        for p in players_from_a:
            state["drafted_players"][p] = team_b_idx
            if team_a_idx == my_idx and p in state["my_roster"]:
                state["my_roster"].remove(p)
            if team_b_idx == my_idx and p not in state["my_roster"]:
                state["my_roster"].append(p)

        # Mover jugadores de B hacia A
        for p in players_from_b:
            state["drafted_players"][p] = team_a_idx
            if team_b_idx == my_idx and p in state["my_roster"]:
                state["my_roster"].remove(p)
            if team_a_idx == my_idx and p not in state["my_roster"]:
                state["my_roster"].append(p)

        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
        return True

    def get_matchups(self, week: int = 1) -> List[Dict[str, Any]]:
        """Retorna los resultados y estadísticas de la semana solicitada"""
        if not self.use_mock and self.league:
            try:
                return self.league.matchups(week)
            except Exception as e:
                print(f"[YahooClient] Error obteniendo matchups de semana {week}: {e}")

        # Intentar cargar desde data/weekly_scores.json
        scores_file = "data/weekly_scores.json"
        if os.path.exists(scores_file):
            try:
                with open(scores_file, "r", encoding="utf-8") as f:
                    weekly_data = json.load(f)
                    week_key = f"Week {week}"
                    if week_key in weekly_data:
                        return weekly_data[week_key]
            except Exception:
                pass

        # Box scores simulados por defecto
        return [
            {
                "week": week,
                "team1": {
                    "name": "Mi Equipo (Dream Team)",
                    "team_key": "nba.l.123456.t.1",
                    "stats": {
                        "PTS": 645, "REB": 235, "AST": 172, "STL": 45, "BLK": 38,
                        "3PM": 72, "FG%": 0.488, "FT%": 0.812, "TO": 68
                    }
                },
                "team2": {
                    "name": "Los Pistoleros",
                    "team_key": "nba.l.123456.t.2",
                    "stats": {
                        "PTS": 680, "REB": 190, "AST": 160, "STL": 38, "BLK": 15,
                        "3PM": 95, "FG%": 0.442, "FT%": 0.865, "TO": 85
                    }
                }
            },
            {
                "week": week,
                "team1": {
                    "name": "Rim Protectors",
                    "team_key": "nba.l.123456.t.3",
                    "stats": {
                        "PTS": 580, "REB": 310, "AST": 115, "STL": 48, "BLK": 65,
                        "3PM": 32, "FG%": 0.545, "FT%": 0.675, "TO": 78
                    }
                },
                "team2": {
                    "name": "Triple Threat",
                    "team_key": "nba.l.123456.t.4",
                    "stats": {
                        "PTS": 620, "REB": 215, "AST": 155, "STL": 40, "BLK": 24,
                        "3PM": 82, "FG%": 0.465, "FT%": 0.800, "TO": 65
                    }
                }
            }
        ]

    def save_weekly_scores(self, week: int, matchups_data: List[Dict[str, Any]]):
        """Guarda marcadores personalizados para una semana específica"""
        scores_file = "data/weekly_scores.json"
        weekly_data = {}
        if os.path.exists(scores_file):
            try:
                with open(scores_file, "r", encoding="utf-8") as f:
                    weekly_data = json.load(f)
            except Exception:
                weekly_data = {}

        weekly_data[f"Week {week}"] = matchups_data
        try:
            with open(scores_file, "w", encoding="utf-8") as f:
                json.dump(weekly_data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"[YahooClient] Error guardando marcadores semanales: {e}")
            return False

    def get_free_agents(self, position: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retorna todos los jugadores no drafteados/no asignados directamente desde el dataset de proyecciones"""
        if not self.use_mock and self.league:
            try:
                return self.league.free_agents(position)
            except Exception as e:
                print(f"[YahooClient] Error obteniendo agentes libres de Yahoo: {e}")

        # Cargar proyecciones y filtrar los que ya están drafteados o en plantillas
        csv_path = "data/projections_sample.csv"
        state_path = "data/draft_state.json"
        
        drafted = set()
        if os.path.exists(state_path):
            try:
                with open(state_path, "r", encoding="utf-8") as f:
                    st_data = json.load(f)
                    drafted.update(st_data.get("drafted_players", {}).keys())
                    drafted.update(st_data.get("my_roster", []))
            except Exception:
                pass

        if os.path.exists(csv_path):
            try:
                df = pd.read_csv(csv_path)
                if drafted:
                    df = df[~df["Player"].isin(drafted)]
                
                # Convertir a formato de agentes libres con FPPG calculado
                fa_list = []
                for _, row in df.iterrows():
                    pts = float(row.get("PTS", 0.0))
                    reb = float(row.get("REB", 0.0))
                    ast = float(row.get("AST", 0.0))
                    stl = float(row.get("STL", 0.0))
                    blk = float(row.get("BLK", 0.0))
                    tpm = float(row.get("3PM", 0.0))
                    to = float(row.get("TO", 0.0))
                    
                    # Yahoo Points formula: PTS*1 + REB*1.2 + AST*1.5 + STL*3 + BLK*3 + 3PM*1 - TO*1
                    fppg = round(pts * 1.0 + reb * 1.2 + ast * 1.5 + stl * 3.0 + blk * 3.0 + tpm * 1.0 - to * 1.0, 1)

                    fa_list.append({
                        "name": row["Player"],
                        "team": row["Team"],
                        "position": row["Positions"],
                        "FPPG": fppg,
                        "PTS": pts,
                        "3PM": tpm,
                        "FG%": float(row.get("FG%", 0.450)),
                        "FT%": float(row.get("FT%", 0.750)),
                        "REB": reb,
                        "AST": ast,
                        "STL": stl,
                        "BLK": blk,
                        "TO": to
                    })
                return fa_list
            except Exception as e:
                print(f"[YahooClient] Error cargando FA desde CSV: {e}")

        return []


