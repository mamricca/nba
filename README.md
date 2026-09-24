# 🏀 Asistente de NBA Fantasy Yahoo (Draft & Temporada Regular)

Herramienta profesional desarrollada en Python y Streamlit para dominar tu liga de **Yahoo Fantasy Basketball** (formato 9-Categorías Head-to-Head o Puntos).

---

## 🌟 Características Principales

### 1. 🎯 Live Draft Assistant (Asistente de Draft en Tiempo Real)
- **Motor de Z-Scores Ponderados:** Evalúa objetivamente el valor estadístico de cada jugador en las 9 categorías estándar (PTS, REB, AST, STL, BLK, 3PM, FG%, FT%, TO), ponderando los porcentajes por volumen de tiro.
- **Estrategias "Punt" Dinámicas:** Descarta categorías (ej. *Punt FT% + TO* para builds de Giannis/Gobert, o *Punt AST* para wings/tiradores) y visualiza instantáneamente a los jugadores que más suben de valor (*Punt Boosters / Steals*).
- **Ajuste por Necesidades Posicionales:** Bonificación inteligente en recomendaciones según las posiciones que aún no has cubierto (PG, SG, SF, PF, C).
- **Persistencia en Vivo:** Guarda el progreso del draft en `data/draft_state.json` para evitar pérdidas si se recarga el navegador, con función de "Deshacer Último Pick".

### 2. 📊 Resumen Semanal & "All-Play" Power Rankings
- **Conexión con Yahoo Fantasy:** Descarga automáticamente los marcadores y estadísticas de cada semana.
- **All-Play True Record:** Simula tus estadísticas contra **todos los equipos de la liga** esa semana para saber si ganaste/perdiste por suerte del calendario o por rendimiento real.
- **Radar de Categorías & Diagnóstico:** Identifica qué categorías son fortalezas élite (Top 3), cuáles están en la media y cuáles son debilidades críticas a corregir.

### 3. 🔄 Trade Machine & Asesor de Waivers
- **Simulador de Traspasos:** Compara plantillas antes y después de un traspaso, proyectando la ganancia o pérdida neta categoría por categoría y generando un veredicto algorítmico.
- **Filtro de Agentes Libres:** Encuentra jugadores disponibles en la agencia libre que aporten exactamente en las categorías que necesitas potenciar.

### 4. 📅 Calendario & Optimizador de Streamers
- **Detección de Off-Days:** Detecta qué franquicias juegan en días de bajo volumen de partidos (Martes, Jueves, Sábados y Domingos), donde tienes puestos libres en el quinteto inicial.
- **Puntaje de Streaming:** Clasifica a los agentes libres según su calendario semanal favorable y su producción por partido.

---

## 🚀 Instalación y Puesta en Marcha

### Requisitos Previos
Tener instalado Python 3.10 o superior.

### 1. Instalar dependencias
Abre una terminal en esta carpeta y ejecuta:
```bash
pip install -r requirements.txt
```

### 2. Iniciar la aplicación
Puedes hacer doble clic en `run_app.bat` o ejecutar:
```bash
streamlit run app/app.py
```
La aplicación se abrirá automáticamente en tu navegador en `http://localhost:8501`.

---

## 🔑 Conectar con tu Liga Real de Yahoo (Opcional)

Por defecto, la aplicación incluye un **Modo Demo / Simulado** completo que te permite usar todas las funciones y el Draft Assistant sin configurar nada.

Para sincronizar tu liga real de Yahoo:
1. Entra en [Yahoo Developer Apps](https://developer.yahoo.com/apps/create/).
2. Crea una aplicación:
   - **Application Name:** `NBA Fantasy Assistant`
   - **Application Type:** `Installed Application`
   - **Redirect URI:** `https://localhost` o `oob`
   - **API Permissions:** Marca **Fantasy Sports** (Read).
3. Copia tu `Client ID` y `Client Secret`.
4. Crea un archivo `config/oauth2.json` (puedes guiarte con `config/oauth2_sample.json`):
```json
{
  "consumer_key": "TU_CLIENT_ID_AQUI",
  "consumer_secret": "TU_CLIENT_SECRET_AQUI"
}
```
5. En la barra lateral de la app, selecciona **Modo: Yahoo Fantasy API (OAuth2)**. Se abrirá una ventana para iniciar sesión en Yahoo una única vez.

---

## 📁 Estructura del Proyecto

```
nba-fantasy/
├── app/
│   ├── app.py                         # Página principal / Dashboard
│   └── pages/
│       ├── 1_🎯_Draft_Assistant.py     # Tablero en vivo y recomendaciones de draft
│       ├── 2_📊_Resumen_Semanal.py     # Power rankings y diagnóstico semanal
│       ├── 3_🔄_Trade_&_Waivers.py     # Simulador de traspasos y agentes libres
│       └── 4_📅_Calendario_Streamers.py# Calendario NBA y optimizador de streaming
├── config/
│   ├── settings.yaml                  # Configuración de categorías y liga
│   └── oauth2_sample.json             # Plantilla de credenciales Yahoo
├── data/
│   ├── projections_sample.csv         # Proyecciones estadísticas para >100 jugadores
│   └── nba_schedule_sample.json       # Calendario de partidos por equipo
├── src/
│   ├── auth/yahoo_client.py           # Cliente API Yahoo / OAuth2
│   ├── core/zscore.py                 # Motor matemático de Z-Scores
│   ├── core/punt_strategy.py          # Lógica de estrategias Punt
│   ├── core/trade_evaluator.py        # Evaluador de traspasos
│   ├── draft/draft_manager.py         # Gestor del draft en vivo
│   └── analytics/matchup_analyzer.py  # Analizador H2H y All-Play
├── tests/
│   └── test_assistant.py              # Suite de pruebas unitarias
├── requirements.txt
├── run_app.bat
└── README.md
```

---

## 🧪 Ejecutar Pruebas
Para verificar la integridad matemática y el funcionamiento de todos los módulos:
```bash
python tests/test_assistant.py
```

