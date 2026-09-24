"""
Extractor y Parser directo de Yahoo Fantasy Web (Scraper / HTML Parser).
Permite obtener datos reales de tu liga de Yahoo de 3 formas:
1. Copiar y pegar el texto/HTML de la página de Yahoo Matchup o Rosters.
2. Descarga directa por URL usando la cookie de sesión de tu navegador.
3. Importación de archivos exportados de Yahoo.
"""

import re
from typing import Dict, List, Any, Optional
from bs4 import BeautifulSoup
import pandas as pd
import requests


class YahooWebScraper:
    def __init__(self, league_id: Optional[str] = None, session_cookie: Optional[str] = None):
        self.league_id = league_id
        self.session_cookie = session_cookie

    def fetch_matchup_html(self, league_id: str, week: int = 1) -> Optional[str]:
        """Descarga el HTML de la página de matchups de Yahoo usando la cookie de sesión"""
        url = f"https://basketball.fantasysports.yahoo.com/nba/{league_id}/matchup?week={week}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        }
        if self.session_cookie:
            headers["Cookie"] = self.session_cookie

        try:
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                return resp.text
            else:
                print(f"[YahooScraper] Status code: {resp.status_code}")
                return None
        except Exception as e:
            print(f"[YahooScraper] Error descargando: {e}")
            return None

    def parse_matchup_text_or_html(self, content: str) -> List[Dict[str, Any]]:
        """
        Parsea tanto HTML de Yahoo Fantasy como texto plano copiado directamente de la pantalla de Matchups.
        Extrae nombres de equipos, puntos totales y estadísticas de la semana.
        """
        matchups = []

        # 1. Intentar parsear como HTML si contiene etiquetas
        if "<html" in content.lower() or "<table" in content.lower() or "class=" in content:
            try:
                soup = BeautifulSoup(content, "html.parser")
                
                # Buscar tablas de matchups o secciones de equipos
                tables = soup.find_all("table")
                for table in tables:
                    # Extraer cabeceras o filas de equipos
                    rows = table.find_all("tr")
                    for row in rows:
                        cells = [c.get_text(strip=True) for c in row.find_all(["td", "th"])]
                        if len(cells) >= 3 and any(char.isdigit() for char in cells[-1]):
                            # Posible fila de equipo con puntos
                            team_name = cells[0]
                            pts_str = re.findall(r"[-+]?\d*\.\d+|\d+", cells[-1])
                            if pts_str and len(team_name) > 2:
                                matchups.append({
                                    "team_name": team_name,
                                    "points": float(pts_str[0]),
                                    "raw_cells": cells
                                })
            except Exception as e:
                print(f"[YahooScraper] Error parseando HTML: {e}")

        # 2. Si es texto plano o no se detectó HTML estructurado, parsear por líneas
        if not matchups:
            lines = content.strip().split("\n")
            current_team = None
            
            for line in lines:
                line_clean = line.strip()
                if not line_clean:
                    continue

                # Detectar líneas con formato: 'Nombre Equipo ... 1245.5' o 'Equipo vs Equipo'
                nums = re.findall(r"\b\d{3,4}(?:\.\d+)?\b", line_clean)
                if nums and len(line_clean.split()) >= 2:
                    pts = float(nums[-1])
                    # Limpiar el nombre del equipo eliminando números
                    name_part = re.sub(r"\b\d+(?:\.\d+)?\b", "", line_clean).strip()
                    if len(name_part) >= 3 and not name_part.startswith("Week"):
                        matchups.append({
                            "team_name": name_part,
                            "points": pts
                        })

        return matchups

    def parse_pasted_roster(self, text: str) -> List[str]:
        """
        Extrae la lista de jugadores a partir del texto copiado de la pestaña 'My Team' o 'Roster' de Yahoo.
        """
        players = []
        lines = text.strip().split("\n")

        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue

            # Buscar patrones comunes de Yahoo: 'Nikola Jokic Den - C' o 'Luka Doncic Dal - PG,SG'
            # Extraer nombres que contengan palabras con mayúsculas
            match = re.search(r"^([A-Z][a-zA-Z'\.\-]+(?:\s+[A-Z][a-zA-Z'\.\-]+)+)", line_str)
            if match:
                p_name = match.group(1).strip()
                # Filtrar encabezados comunes de Yahoo
                if p_name not in ["Yahoo Sports", "Fantasy Basketball", "My Team", "Matchup", "Players", "League", "Stat Categories"]:
                    players.append(p_name)

        return list(dict.fromkeys(players))  # eliminar duplicados manteniendo orden

