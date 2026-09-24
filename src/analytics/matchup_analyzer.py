"""
Analizador de Rendimiento Semanal y Matchups Head-to-Head.
Calcula la matriz de simulación 'Todos contra Todos' (All-Play Power Rankings),
diagnósticos de fortalezas y debilidades, y genera datos para gráficos de radar.
"""

from typing import Dict, List, Tuple, Any, Optional
import numpy as np
import pandas as pd


class MatchupAnalyzer:
    CATEGORIES_9CAT = ["PTS", "REB", "AST", "STL", "BLK", "3PM", "FG%", "FT%", "TO"]
    NEGATIVE_CATS = {"TO"}

    def __init__(self, categories: Optional[List[str]] = None):
        self.categories = categories or self.CATEGORIES_9CAT

    def compare_teams(self, stats_a: Dict[str, float], stats_b: Dict[str, float]) -> Dict[str, Any]:
        """Compara dos equipos en las categorías seleccionadas y determina el resultado 9-cat"""
        wins_a = 0
        wins_b = 0
        ties = 0
        cat_results = {}

        for cat in self.categories:
            val_a = stats_a.get(cat, 0.0)
            val_b = stats_b.get(cat, 0.0)

            if cat in self.NEGATIVE_CATS:
                # Para pérdidas, menor valor gana
                if val_a < val_b:
                    wins_a += 1
                    cat_results[cat] = ("WIN", val_a, val_b)
                elif val_b < val_a:
                    wins_b += 1
                    cat_results[cat] = ("LOSS", val_a, val_b)
                else:
                    ties += 1
                    cat_results[cat] = ("TIE", val_a, val_b)
            else:
                if val_a > val_b:
                    wins_a += 1
                    cat_results[cat] = ("WIN", val_a, val_b)
                elif val_b > val_a:
                    wins_b += 1
                    cat_results[cat] = ("LOSS", val_a, val_b)
                else:
                    ties += 1
                    cat_results[cat] = ("TIE", val_a, val_b)

        return {
            "score": f"{wins_a}-{wins_b}-{ties}",
            "wins_a": wins_a,
            "wins_b": wins_b,
            "ties": ties,
            "categories": cat_results
        }

    def compute_all_play_power_rankings(self, weekly_teams_data: List[Dict[str, Any]]) -> pd.DataFrame:
        """
        Simula los resultados de cada equipo contra TODOS los demás equipos de la liga esa semana.
        Esto elimina la suerte del calendario y revela el verdadero nivel del equipo (True Power).
        """
        results = []

        for i, team_a in enumerate(weekly_teams_data):
            total_wins = 0
            total_losses = 0
            total_ties = 0
            cat_totals = {cat: 0 for cat in self.categories}

            for j, team_b in enumerate(weekly_teams_data):
                if i == j:
                    continue
                match = self.compare_teams(team_a["stats"], team_b["stats"])
                total_wins += match["wins_a"]
                total_losses += match["wins_b"]
                total_ties += match["ties"]

                for cat, (res, _, _) in match["categories"].items():
                    if res == "WIN":
                        cat_totals[cat] += 1

            total_matchups = len(weekly_teams_data) - 1
            win_pct = (total_wins + 0.5 * total_ties) / max((total_wins + total_losses + total_ties), 1)

            entry = {
                "Team": team_a["name"],
                "Team_Key": team_a.get("team_key", ""),
                "True_Record": f"{total_wins}-{total_losses}-{total_ties}",
                "Win_Pct": round(win_pct, 3),
                "Category_Wins": total_wins,
                **team_a["stats"]
            }
            results.append(entry)

        df_rankings = pd.DataFrame(results)
        df_rankings = df_rankings.sort_values(by=["Win_Pct", "Category_Wins"], ascending=False).reset_index(drop=True)
        df_rankings["Power_Rank"] = df_rankings.index + 1
        return df_rankings

    def diagnose_weaknesses(self, my_stats: Dict[str, float], all_teams_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Identifica cuáles categorías son fortalezas élite, competitivas o debilidades críticas
        comparando los valores con los percentiles de la liga.
        """
        df_all = pd.DataFrame([t["stats"] for t in all_teams_data])
        
        diagnostics = {}
        for cat in self.categories:
            if cat not in df_all.columns:
                continue

            my_val = my_stats.get(cat, 0.0)
            col_vals = df_all[cat]

            # Calcular ranking en la categoría dentro de la liga
            if cat in self.NEGATIVE_CATS:
                rank_in_league = (col_vals < my_val).sum() + 1
            else:
                rank_in_league = (col_vals > my_val).sum() + 1

            league_median = col_vals.median()
            
            # Clasificación de estado
            total_teams = len(all_teams_data)
            if rank_in_league <= 3:
                status = "🟢 Fortaleza Élite (Top 3)"
            elif rank_in_league <= (total_teams // 2):
                status = "🟡 Competitiva (Mitad Superior)"
            elif rank_in_league <= total_teams - 3:
                status = "🟠 En Riesgo (Mitad Inferior)"
            else:
                status = "🔴 Debilidad Crítica (Fondo de Liga)"

            diagnostics[cat] = {
                "my_value": my_val,
                "league_median": round(league_median, 3 if "%" in cat else 1),
                "rank_in_league": int(rank_in_league),
                "total_teams": total_teams,
                "status": status
            }

        return diagnostics

