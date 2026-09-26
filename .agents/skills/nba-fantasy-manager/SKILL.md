---
name: nba-fantasy-manager
description: >-
  Estratega y gestor integral para ligas de Fantasy Basketball (Yahoo Points & Categories).
  Ejecuta rutinas semanales: extracción de estadísticas oficiales de NBA.com, optimización
  de alineaciones semanales (Weekly Locks), escáner de gemas ocultas (FP/MIN, Per-36, Stocks),
  gestión de agentes libres (Add/Drop) y cálculo de matchups y Power Rankings.
---

# 🏀 NBA Fantasy Basketball Strategic Skill

Este skill equipa al asistente con el protocolo experto para gestionar, optimizar y ganar ligas de Fantasy Basketball de Yahoo (especialmente ligas de puntos con bloqueo semanal o diario).

---

## 📅 1. Protocolo de los Lunes (Optimización de Alineación Semanal)

Cuando el usuario pida armar el quinteto, preparar la semana o alinear jugadores:

1. **Actualizar Estadísticas Oficiales**:
   ```bash
   python src/data_fetcher.py
   ```
2. **Consultar Calendario de la Semana**:
   - Leer `data/nba_schedule_sample.json` para la semana activa (Week 1 a 24).
   - Identificar cuántos partidos juega cada equipo (priorizar equipos con **4 partidos** y descartar los de **2 o 3 partidos** si hay mejores opciones).
3. **Chequeo de Lesiones**:
   - Verificar etiquetas de lesión: `[Q]` (Cuestionable), `[P]` (Probable), `[O]` (Out).
   - En ligas semanales (**Weekly-Monday**), **evitar colocar jugadores cuestionables [Q] en los 10 titulares** a menos que su potencial sea irreemplazable, ya que no se pueden sustituir una vez comenzada la semana.
4. **Calcular la Alineación Óptima de 10 Titulares**:
   - **PG, SG, G, SF, PF, F, C, C, Util, Util**.
   - Maximizar el producto: $\text{FPPG} \times \text{Partidos de la Semana}$.
   - Dejar a los 3 jugadores de menor volumen o mayor riesgo en la **Banca (BN)**.

---

## 🔍 2. Protocolo de Scouting de Agentes Libres y Gemas Ocultas

Cuando el usuario pida buscar refuerzos, analizar waivers o mejorar la plantilla:

1. **Ejecutar el Escáner de Métricas Avanzadas**:
   ```python
   from src.analytics.advanced_metrics import AdvancedMetricsEngine
   from src.auth.yahoo_client import YahooFantasyClient
   
   client = YahooFantasyClient(use_mock=True)
   engine = AdvancedMetricsEngine()
   fa_df = pd.DataFrame(client.get_free_agents())
   gems = engine.find_hidden_gems(fa_df, min_efficiency=1.05)
   ```
2. **Criterios de Detección de Gemas**:
   - **FP/MIN (Eficiencia por Minuto)**: Si $\text{FP/MIN} \ge 1.05$ en $\le 26$ minutos, es un *Sleeper* que explotará al recibir minutos de titular.
   - **Stocks (Robos + Bloqueos)**: Si $\text{STL} + \text{BLK} \ge 1.7$, aporta una base gigante de puntos ($+3.0\text{ pts}$ c/u).
   - **Usage Vacuum (Vacío de Uso)**: Monitorear lesiones recientes en la NBA real para identificar suplentes que heredarán 30+ minutos y tiros.
3. **Asesor de Cortes (Drop Advisor)**:
   - Identificar al peor jugador del roster con `engine.evaluate_drop_candidates(my_roster_df)`.
   - Calcular la ganancia neta semanal: $\Delta \text{FPTS} = (\text{FPPG}_{\text{FA}} \times \text{PJ}) - (\text{FPPG}_{\text{Roster}} \times \text{PJ})$.
   - Proponer la orden de Add/Drop directa.

---

## 📊 3. Protocolo de Cierre de Semana y Marcadores

Cuando el usuario pida revisar resultados, simular el matchup o calcular puntos:

1. **Calcular Resultados con el Motor Oficial**:
   ```python
   from src.analytics.nba_stats_scraper import NBAWeeklyCalculator
   calc = NBAWeeklyCalculator()
   res = calc.calculate_league_weekly_results(teams, client.get_roster, week_num=X)
   ```
2. **Generar el Resumen del Matchup**:
   - Puntos totales de tu equipo vs. Rival.
   - Desglose jugador por jugador (partidos jugados, FPPG y puntos semanales).
   - Tabla de **All-Play Power Rankings** (simulación de todos contra todos).

---

## 🚀 4. Sincronización y Despliegue en la Nube
Siempre que se actualicen plantillas, proyecciones o resultados:
```bash
git add . && git commit -m "update: Sync NBA Fantasy data" && git push origin main
```
Esto garantiza que la app en Streamlit Cloud permanezca en tiempo real y accesible desde el móvil.
