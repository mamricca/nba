"""
Script para descargar/actualizar estadísticas oficiales directamente desde Basketball-Reference o NBA API.
"""

import os
import sys
import pandas as pd
import requests

def fetch_basketball_reference_stats(season_year: int = 2024) -> pd.DataFrame:
    """
    Descarga la tabla oficial de promedios por partido desde Basketball-Reference.
    Fuente: https://www.basketball-reference.com/leagues/NBA_{season_year}_per_game.html
    """
    url = f"https://www.basketball-reference.com/leagues/NBA_{season_year}_per_game.html"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    print(f"Descargando estadísticas oficiales desde: {url}...")
    resp = requests.get(url, headers=headers, timeout=15)
    
    if resp.status_code == 200:
        dfs = pd.read_html(resp.text)
        if dfs:
            df = dfs[0]
            # Filtrar filas de encabezado repetidas
            df = df[df["Player"] != "Player"].copy()
            print(f"✅ Se obtuvieron {len(df)} registros de jugadores desde Basketball-Reference.")
            return df
    else:
        print(f"Error descargando datos (Status {resp.status_code})")
        return pd.DataFrame()

if __name__ == "__main__":
    df = fetch_basketball_reference_stats(2024)
    if not df.empty:
        print("\nPrimeros 5 jugadores descargados directamente de la fuente:")
        print(df[["Player", "Pos", "Tm", "PTS", "TRB", "AST", "STL", "BLK", "FG%"]].head())
