"""
Módulo de Métricas Avanzadas y Detección Automática de Gemas Ocultas para Fantasy Basketball.
Aplica la nomenclatura profesional: FP/MIN, Per-36, Stocks, Usage Vacuum, Floor/Ceiling y Drop Advisor.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional


class AdvancedMetricsEngine:
    def __init__(self, scoring_rules: Optional[Dict[str, float]] = None):
        self.scoring_rules = scoring_rules or {
            "PTS": 1.0,
            "REB": 1.2,
            "AST": 1.5,
            "STL": 3.0,
            "BLK": 3.0,
            "3PM": 1.0,
            "TO": -1.0
        }

    def compute_advanced_metrics(self, df: pd.DataFrame, week_game_counts: Optional[Dict[str, int]] = None) -> pd.DataFrame:
        """
        Calcula las métricas avanzadas sobre cualquier DataFrame de jugadores:
        - FPPG (Fantasy Points Per Game)
        - FP_per_MIN (Eficiencia por minuto)
        - Per_36_FPTS (Proyección si jugara 36 minutos)
        - Stocks (Steals + Blocks)
        - Floor y Ceiling proyectados
        - Weekly_FPTS (Puntos totales considerando partidos de la semana)
        - Etiquetas automáticas (Gemas, Sleepers, Especialistas)
        """
        if df.empty:
            return pd.DataFrame()

        res = df.copy()

        # 1. Asegurar cálculo de FPPG
        def calc_fppg(row):
            pts = float(row.get("PTS", 0.0))
            reb = float(row.get("REB", 0.0))
            ast = float(row.get("AST", 0.0))
            stl = float(row.get("STL", 0.0))
            blk = float(row.get("BLK", 0.0))
            tpm = float(row.get("3PM", 0.0))
            to = float(row.get("TO", 0.0))
            return round(
                pts * self.scoring_rules.get("PTS", 1.0) +
                reb * self.scoring_rules.get("REB", 1.2) +
                ast * self.scoring_rules.get("AST", 1.5) +
                stl * self.scoring_rules.get("STL", 3.0) +
                blk * self.scoring_rules.get("BLK", 3.0) +
                tpm * self.scoring_rules.get("3PM", 1.0) +
                to * self.scoring_rules.get("TO", -1.0),
                2
            )

        if "FPPG" not in res.columns:
            res["FPPG"] = res.apply(calc_fppg, axis=1)

        # 2. Minutos y Eficiencia por minuto (FP/MIN)
        if "MIN" in res.columns:
            res["MIN"] = pd.to_numeric(res["MIN"], errors="coerce").fillna(25.0)
        else:
            res["MIN"] = 25.0

        res["FP_per_MIN"] = (res["FPPG"] / res["MIN"].replace(0, 1.0)).round(2)

        # 3. Proyección Per-36 minutos
        res["Per_36_FPTS"] = (res["FP_per_MIN"] * 36.0).round(1)

        # 4. Stocks (Robos + Bloqueos)
        stl_col = pd.to_numeric(res.get("STL", 0), errors="coerce").fillna(0.0)
        blk_col = pd.to_numeric(res.get("BLK", 0), errors="coerce").fillna(0.0)
        res["Stocks"] = (stl_col + blk_col).round(1)

        # 5. Estimación de Floor (Suelo) y Ceiling (Techo)
        # Floor: ~75% del promedio (rendimiento base asegurado)
        # Ceiling: ~140% del promedio (noches explosivas)
        res["Floor_FPTS"] = (res["FPPG"] * 0.72).round(1)
        res["Ceiling_FPTS"] = (res["FPPG"] * 1.38).round(1)

        # 6. Puntos Semanales cruzando el Calendario
        if week_game_counts and "Team" in res.columns:
            res["Week_Games"] = res["Team"].map(week_game_counts).fillna(3).astype(int)
        elif "w1_games" in res.columns:
            res["Week_Games"] = res["w1_games"]
        else:
            res["Week_Games"] = 3

        res["Weekly_Total_FPTS"] = (res["FPPG"] * res["Week_Games"]).round(1)

        # 7. Generación de Etiquetas Inteligentes (Nomenclatura)
        def tag_player(row):
            tags = []
            fpm = float(row["FP_per_MIN"])
            min_val = float(row["MIN"])
            fppg = float(row["FPPG"])
            stocks = float(row["Stocks"])
            tpm = float(row.get("3PM", 0.0))
            reb = float(row.get("REB", 0.0))
            ast = float(row.get("AST", 0.0))

            # Detección de Gemas / Sleepers por alta eficiencia en pocos minutos
            if fpm >= 1.05 and min_val <= 26.0:
                tags.append("💎 Gema Oculta / Sleeper")
            elif fpm >= 1.15:
                tags.append("🔥 Superestrella / Per-Min Elite")

            if stocks >= 1.7:
                tags.append("🛡️ Monstruo Defensivo (Stocks)")
            if tpm >= 2.2:
                tags.append("🎯 Triplero Elite")
            if reb >= 8.0:
                tags.append("🚀 Reboteador Top")
            if ast >= 5.5:
                tags.append("🪄 Playmaker / Asistidor")

            if not tags:
                if fppg >= 30.0:
                    tags.append("⭐ Titular Consolidado")
                else:
                    tags.append("📈 Jugador de Rotación")

            return " | ".join(tags)

        res["Perfil_Avanzado"] = res.apply(tag_player, axis=1)
        return res

    def find_hidden_gems(self, free_agents_df: pd.DataFrame, min_efficiency: float = 1.00, top_n: int = 15) -> pd.DataFrame:
        """
        Escáner especializado en 'Gemas Ocultas':
        Filtra jugadores con alta producción por minuto (FP/MIN >= 1.00) que están listos para explotar
        si reciben 5-10 minutos más por una lesión o ajuste de rotación.
        """
        if free_agents_df.empty:
            return pd.DataFrame()

        df_metrics = self.compute_advanced_metrics(free_agents_df)
        gems = df_metrics[df_metrics["FP_per_MIN"] >= min_efficiency].sort_values(by=["FP_per_MIN", "Per_36_FPTS"], ascending=False)
        return gems.head(top_n)

    def evaluate_drop_candidates(self, roster_df: pd.DataFrame, top_n: int = 3) -> pd.DataFrame:
        """
        Identifica automáticamente los candidatos óptimos a ser cortados del roster
        ponderando bajo FPPG, baja eficiencia por minuto y bajo techo de puntos.
        """
        if roster_df.empty:
            return pd.DataFrame()

        df_metrics = self.compute_advanced_metrics(roster_df)
        
        def calc_drop_score(row):
            # Menor FPPG y menor FP/MIN = Mayor probabilidad de corte
            score = (50.0 - float(row["FPPG"])) * 1.5 + (1.5 - float(row["FP_per_MIN"])) * 20.0
            return round(score, 1)

        df_metrics["Drop_Priority_Score"] = df_metrics.apply(calc_drop_score, axis=1)
        return df_metrics.sort_values(by="Drop_Priority_Score", ascending=False).head(top_n)
