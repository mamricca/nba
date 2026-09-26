"""
Módulo oficial de Extracción y Actualización de Estadísticas NBA.
Descarga datos en vivo desde la API oficial de la NBA (stats.nba.com) y Basketball-Reference,
normaliza el dataset y actualiza data/projections_sample.csv automáticamente.
"""

import os
import sys
import json
import time
from typing import Optional, Dict, Any
import pandas as pd
import requests


class NBADataUpdater:
    def __init__(self, target_csv: str = "data/projections_sample.csv"):
        self.target_csv = target_csv

    def fetch_from_nba_api(self, season: str = "2024-25") -> Optional[pd.DataFrame]:
        """Extrae estadísticas oficiales por partido desde la API de NBA.com"""
        try:
            from nba_api.stats.endpoints import leaguedashplayerstats
            print(f"[NBADataUpdater] Consultando stats.nba.com para la temporada {season}...")
            stats_endpoint = leaguedashplayerstats.LeagueDashPlayerStats(
                season=season,
                per_mode_detailed="PerGame",
                timeout=15
            )
            df_raw = stats_endpoint.get_data_frames()[0]
            if not df_raw.empty:
                print(f"[NBADataUpdater] ✅ Se obtuvieron {len(df_raw)} jugadores desde NBA.com.")
                
                # Mapear columnas a nuestro formato
                df_clean = pd.DataFrame({
                    "Player": df_raw["PLAYER_NAME"],
                    "Team": df_raw["TEAM_ABBREVIATION"],
                    "Positions": "G/F",  # NBA API base no siempre incluye posición detallada en este endpoint
                    "GP": df_raw["GP"],
                    "MIN": df_raw["MIN"],
                    "FGM": df_raw["FGM"],
                    "FGA": df_raw["FGA"],
                    "FG%": df_raw["FG_PCT"],
                    "FTM": df_raw["FTM"],
                    "FTA": df_raw["FTA"],
                    "FT%": df_raw["FT_PCT"],
                    "3PM": df_raw["FG3M"],
                    "PTS": df_raw["PTS"],
                    "REB": df_raw["REB"],
                    "AST": df_raw["AST"],
                    "STL": df_raw["STL"],
                    "BLK": df_raw["BLK"],
                    "TO": df_raw["TOV"]
                })
                return df_clean
        except Exception as e:
            print(f"[NBADataUpdater] Nota NBA API: {e}")
        return None

    def fetch_from_basketball_reference(self, year: int = 2024) -> Optional[pd.DataFrame]:
        """Descarga la tabla de promedios por partido desde Basketball-Reference como respaldo"""
        url = f"https://www.basketball-reference.com/leagues/NBA_{year}_per_game.html"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        try:
            print(f"[NBADataUpdater] Descargando desde Basketball-Reference: {url}...")
            resp = requests.get(url, headers=headers, timeout=15)
            if resp.status_code == 200:
                dfs = pd.read_html(resp.text)
                if dfs:
                    df = dfs[0]
                    df = df[df["Player"] != "Player"].copy()
                    
                    # Limpiar y mapear
                    df_clean = pd.DataFrame({
                        "Player": df["Player"].apply(lambda x: str(x).split("\\")[0]),
                        "Team": df["Tm"],
                        "Positions": df["Pos"],
                        "GP": pd.to_numeric(df["G"], errors="coerce").fillna(0),
                        "MIN": pd.to_numeric(df["MP"], errors="coerce").fillna(20.0),
                        "FGM": pd.to_numeric(df["FG"], errors="coerce").fillna(0.0),
                        "FGA": pd.to_numeric(df["FGA"], errors="coerce").fillna(0.0),
                        "FG%": pd.to_numeric(df["FG%"], errors="coerce").fillna(0.450),
                        "FTM": pd.to_numeric(df["FT"], errors="coerce").fillna(0.0),
                        "FTA": pd.to_numeric(df["FTA"], errors="coerce").fillna(0.0),
                        "FT%": pd.to_numeric(df["FT%"], errors="coerce").fillna(0.750),
                        "3PM": pd.to_numeric(df["3P"], errors="coerce").fillna(0.0),
                        "PTS": pd.to_numeric(df["PTS"], errors="coerce").fillna(0.0),
                        "REB": pd.to_numeric(df["TRB"], errors="coerce").fillna(0.0),
                        "AST": pd.to_numeric(df["AST"], errors="coerce").fillna(0.0),
                        "STL": pd.to_numeric(df["STL"], errors="coerce").fillna(0.0),
                        "BLK": pd.to_numeric(df["BLK"], errors="coerce").fillna(0.0),
                        "TO": pd.to_numeric(df["TOV"], errors="coerce").fillna(0.0)
                    })
                    print(f"[NBADataUpdater] ✅ Se obtuvieron {len(df_clean)} jugadores de Basketball-Reference.")
                    return df_clean
        except Exception as e:
            print(f"[NBADataUpdater] Error Basketball-Reference: {e}")
        return None

    def update_dataset(self, season_year: int = 2024) -> bool:
        """Descarga los datos oficiales y actualiza data/projections_sample.csv preservando jugadores clave"""
        df_new = self.fetch_from_nba_api()
        if df_new is None or df_new.empty:
            df_new = self.fetch_from_basketball_reference(season_year)

        if df_new is not None and not df_new.empty:
            # Cargar archivo existente para preservar posiciones multi-elegibles
            if os.path.exists(self.target_csv):
                try:
                    df_existing = pd.read_csv(self.target_csv)
                    pos_map = dict(zip(df_existing["Player"], df_existing["Positions"]))
                    df_new["Positions"] = df_new["Player"].map(pos_map).fillna(df_new["Positions"])
                except Exception:
                    pass

            df_new.to_csv(self.target_csv, index=False)
            print(f"[NBADataUpdater] 🎉 Archivo {self.target_csv} actualizado con {len(df_new)} jugadores oficiales!")
            return True
        else:
            print("[NBADataUpdater] ⚠️ No se pudieron obtener datos frescos. Se conserva el archivo local actual.")
            return False


if __name__ == "__main__":
    updater = NBADataUpdater()
    updater.update_dataset()
