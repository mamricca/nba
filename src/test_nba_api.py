"""
Prueba de conexión con la API oficial de la NBA (stats.nba.com vía nba_api).
"""

from nba_api.stats.endpoints import leaguedashplayerstats

def test_nba_api():
    print("Consultando la API oficial de NBA.com (stats.nba.com)...")
    try:
        stats = leaguedashplayerstats.LeagueDashPlayerStats(
            season='2023-24',
            per_mode_detailed='PerGame',
            timeout=10
        )
        df = stats.get_data_frames()[0]
        print(f"✅ Conexión exitosa con NBA.com! {len(df)} jugadores obtenidos.")
        print(df[["PLAYER_NAME", "TEAM_ABBREVIATION", "PTS", "REB", "AST", "STL", "BLK", "FG_PCT"]].head(5))
        return df
    except Exception as e:
        print(f"Nota de conexión API NBA: {e}")
        return None

if __name__ == "__main__":
    test_nba_api()
