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

    def get_roster(self, team_key: str) -> List[Dict[str, Any]]:
        """Retorna la lista de jugadores de un equipo específico"""
        if not self.use_mock and self.league:
            try:
                team = self.league.to_team(team_key)
                return team.roster()
            except Exception as e:
                print(f"[YahooClient] Error obteniendo roster {team_key}: {e}")

        # Rosters Simulados de ejemplo basados en el dataset de proyecciones
        rosters_map = {
            "nba.l.123456.t.1": [  # Tu equipo
                "Nikola Jokic", "Tyrese Haliburton", "Derrick White", "Evan Mobley",
                "Brook Lopez", "Alex Caruso", "Mike Conley", "Trey Murphy III",
                "Naz Reid", "Jalen Duren", "Al Horford", "Dennis Schroder", "Grayson Allen"
            ],
            "nba.l.123456.t.2": [  # Rival 1 (Pistoleros)
                "Luka Doncic", "Trae Young", "Damian Lillard", "Jordan Poole",
                "Anfernee Simons", "Bogdan Bogdanovic", "Norman Powell", "Tyler Herro",
                "Miles Bridges", "Tobias Harris", "Jonas Valanciunas", "Bobby Portis", "Klay Thompson"
            ],
            "nba.l.123456.t.3": [  # Rival 2 (Rim Protectors)
                "Victor Wembanyama", "Giannis Antetokounmpo", "Anthony Davis", "Rudy Gobert",
                "Walker Kessler", "Nic Claxton", "Jarrett Allen", "Daniel Gafford",
                "Ivica Zubac", "Ausar Thompson", "Amen Thompson", "Herbert Jones", "Alex Sarr"
            ]
        }
        
        player_names = rosters_map.get(team_key, [
            "Shai Gilgeous-Alexander", "Jayson Tatum", "Donovan Mitchell", "Chet Holmgren",
            "Jalen Williams", "Kristaps Porzingis", "Fred VanVleet", "Immanuel Quickley",
            "Myles Turner", "Marcus Smart", "Keegan Murray", "De'Anthony Melton", "Jonathan Kuminga"
        ])
        
        return [{"name": name, "selected_position": "BN", "eligible_positions": ["PG", "SG", "SF", "PF", "C"]} for name in player_names]

    def get_matchups(self, week: int = 1) -> List[Dict[str, Any]]:
        """Retorna los resultados y estadísticas de la semana solicitada"""
        if not self.use_mock and self.league:
            try:
                return self.league.matchups(week)
            except Exception as e:
                print(f"[YahooClient] Error obteniendo matchups de semana {week}: {e}")

        # Box scores simulados para semana 1
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

    def get_free_agents(self, position: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retorna jugadores en la agencia libre / waiver wire"""
        if not self.use_mock and self.league:
            try:
                return self.league.free_agents(position)
            except Exception as e:
                print(f"[YahooClient] Error obteniendo agentes libres: {e}")

        # Agentes libres simulados
        fa_players = [
            {"name": "Norman Powell", "team": "LAC", "position": "SG/SF", "PTS": 14.3, "3PM": 2.2, "FG%": 0.486, "FT%": 0.864, "REB": 2.6, "AST": 1.1, "STL": 0.6, "BLK": 0.3, "TO": 1.1},
            {"name": "Tre Jones", "team": "SAS", "position": "PG", "PTS": 10.0, "3PM": 0.8, "FG%": 0.505, "FT%": 0.856, "REB": 3.8, "AST": 6.2, "STL": 1.0, "BLK": 0.1, "TO": 1.5},
            {"name": "Max Strus", "team": "CLE", "position": "SG/SF", "PTS": 12.2, "3PM": 2.4, "FG%": 0.418, "FT%": 0.794, "REB": 4.8, "AST": 4.0, "STL": 0.9, "BLK": 0.4, "TO": 1.4},
            {"name": "T.J. McConnell", "team": "IND", "position": "PG", "PTS": 10.2, "3PM": 0.2, "FG%": 0.556, "FT%": 0.790, "REB": 2.7, "AST": 5.5, "STL": 1.0, "BLK": 0.1, "TO": 1.3},
            {"name": "Al Horford", "team": "BOS", "position": "C", "PTS": 8.6, "3PM": 1.5, "FG%": 0.511, "FT%": 0.867, "REB": 6.4, "AST": 2.6, "STL": 0.6, "BLK": 1.0, "TO": 0.9},
            {"name": "Cole Anthony", "team": "ORL", "position": "PG/SG", "PTS": 11.6, "3PM": 1.1, "FG%": 0.435, "FT%": 0.826, "REB": 3.8, "AST": 2.9, "STL": 0.8, "BLK": 0.5, "TO": 1.5},
            {"name": "Harrison Barnes", "team": "SAS", "position": "SF/PF", "PTS": 12.0, "3PM": 1.5, "FG%": 0.474, "FT%": 0.801, "REB": 3.0, "AST": 1.2, "STL": 0.7, "BLK": 0.1, "TO": 0.8},
            {"name": "Royce O'Neale", "team": "PHX", "position": "SG/SF", "PTS": 7.7, "3PM": 1.8, "FG%": 0.397, "FT%": 0.692, "REB": 4.8, "AST": 2.8, "STL": 0.7, "BLK": 0.6, "TO": 1.1}
        ]
        return fa_players

