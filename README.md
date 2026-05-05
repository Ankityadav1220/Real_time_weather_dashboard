# ⛅ WeatherIQ AI Dashboard — v6

**AI-powered Smart Weather Intelligence Dashboard**
Location-first architecture · Real road routing · Dynamic animations · Zero auth

---

## 🚀 Quick Start (VS Code)

### Step 1 — Prerequisites
```bash
python --version   # Requires Python 3.9+
pip --version
```

### Step 2 — Install dependencies
```bash
cd weather_dashboard
pip install -r requirements.txt
```

### Step 3 — Configure API keys
```bash
# Copy the example and fill in your keys
cp .env.example .env
```
Open `.env` and add:
```env
OPENWEATHER_API_KEY=your_key_here          # Required for live weather
OPENROUTESERVICE_KEY=your_key_here         # Optional: real road routing
```

**Get free API keys:**
- OpenWeatherMap: https://openweathermap.org/api (free tier: 1000 calls/day)
- OpenRouteService: https://openrouteservice.org/dev/#/signup (free tier: 2000 calls/day)

> ⚠️ The app works WITHOUT API keys using realistic simulated data.

### Step 4 — Run
```bash
python run.py
```
Open browser: **http://localhost:5000**

---

## 🗂️ Project Structure

```
weather_dashboard/
├── app.py                          ← Flask app factory (no auth)
├── run.py                          ← Entry point
├── requirements.txt
├── .env.example
├── backend/
│   ├── routes/
│   │   ├── weather_routes.py       ← /api/current-weather, /api/forecast
│   │   ├── intelligence_routes.py  ← All AI endpoints (lat/lon-first)
│   │   ├── prediction_routes.py    ← ML prediction endpoints
│   │   └── main_routes.py          ← Page routes + autocomplete + geo-weather
│   ├── utils/
│   │   ├── weather_api.py          ← OpenWeatherMap service
│   │   ├── route_planner.py        ← ORS real routing + great-circle fallback
│   │   ├── rural_risk.py           ← Agricultural risk engine
│   │   ├── urban_intelligence.py   ← Urban risk & energy
│   │   ├── risk_engine.py          ← Safety radar
│   │   ├── productivity_ai.py      ← Productivity/mood analysis
│   │   ├── alert_system.py         ← Weather alerts
│   │   └── nowcaster.py            ← Nowcasting engine
│   └── models/
│       └── ml_models.py            ← Linear Regression, RF, LSTM
├── database/
│   └── db_manager.py               ← SQLite + WAL mode, thread-safe
└── frontend/
    ├── templates/
    │   ├── base.html               ← Navigation + global search + location pill
    │   ├── index.html              ← Dashboard
    │   ├── route_planner.html      ← Real road route planner
    │   ├── rural_risk.html         ← Farm intelligence (auto location)
    │   ├── hyperlocal.html         ← GPS-based hyperlocal
    │   └── ...
    └── static/
        ├── css/
        │   ├── base.css            ← Main stylesheet
        │   └── weather-bg.css      ← Animated weather backgrounds
        └── js/
            ├── base.js             ← 🌟 Global location state (window.WIQ)
            ├── dashboard.js        ← Auto-syncs with location
            ├── route_planner.js    ← ORS route planner
            ├── rural_risk.js       ← Auto-syncs with location
            ├── hyperlocal.js       ← GPS-aware
            └── ...
```

---

## 🌍 Global Location State

The core of v6 is `window.WIQ` — a single source of truth for location:

```javascript
// Change location — ALL modules refresh automatically
window.setLocation({ city: 'Mumbai', lat: 19.07, lon: 72.87, displayName: 'Mumbai' });

// Build API query string (lat/lon preferred, city fallback)
const params = window.locationParams();
// → "lat=19.07&lon=72.87&city=Mumbai"

// Listen to location changes in any JS module
window.addEventListener('wiq:location', (e) => {
  // e.detail: { city, lat, lon, displayName }
  fetchMyData(window.locationParams());
});
```

---

## 🛣️ Route Planner

**With ORS key** (real road routing):
- Actual road geometry via OpenRouteService Directions API
- Real distance and ETA
- Polyline decoded + sampled for weather waypoints

**Without ORS key** (fallback):
- Great-circle (straight-line) interpolation
- Estimated distance and ETA
- Marked as "Estimated Route" in UI

Both modes: weather data fetched at 8 waypoints, risk scoring, transport advice.

---

## 🔑 API Endpoints Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/current-weather` | GET | Current weather (`city` or `lat`+`lon`) |
| `/api/forecast` | GET | 48h forecast |
| `/api/alerts` | GET | Active weather alerts |
| `/api/geo-weather` | GET | Reverse geocode + weather for GPS coords |
| `/api/autocomplete` | GET | City name autocomplete |
| `/api/intelligence/route` | GET | Route planner (ORS or fallback) |
| `/api/intelligence/rural-risk` | GET | Agricultural risk |
| `/api/intelligence/urban-risk` | GET | Urban infrastructure risk |
| `/api/intelligence/health-impact` | GET | Health effects |
| `/api/intelligence/productivity` | GET | Productivity analysis |
| `/api/intelligence/hyperlocal` | GET | 1.5 km precision weather |
| `/api/intelligence/safety-radar` | GET | Overall safety score |
| `/api/intelligence/nowcast` | GET | Nowcasting AI |
| `/api/intelligence/energy` | GET | Energy demand prediction |
| `/api/intelligence/chat` | POST | AI weather chatbot |

All AI endpoints accept `city` OR `lat`+`lon` parameters.

---

## ⚙️ Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENWEATHER_API_KEY` | Optional* | OpenWeatherMap API key |
| `OPENROUTESERVICE_KEY` | Optional | ORS key for real road routing |
| `FLASK_DEBUG` | No | Set `True` for development |
| `SECRET_KEY` | No | Flask session secret |
| `PORT` | No | Server port (default: 5000) |

*Without API keys, realistic simulated data is used.

---

## 🐛 Common Issues & Fixes

**`ModuleNotFoundError: No module named 'flask'`**
```bash
pip install -r requirements.txt
```

**`Address already in use`**
```bash
# Kill existing process or change port:
PORT=5001 python run.py
```

**"Simulated Data" badge showing**
→ Add your `OPENWEATHER_API_KEY` to `.env`

**Route shows "Estimated Route" instead of real roads**
→ Add your `OPENROUTESERVICE_KEY` to `.env`

**GPS not working**
→ Browser requires HTTPS for geolocation (except `localhost`)
→ On localhost it works fine; on deployed server use HTTPS

**SQLite locked errors**
→ Fixed in v6 with WAL mode. If persists: delete `database/weather.db` and restart.

---

## 🌦️ Weather Animations

Animations trigger automatically based on weather condition:

| Weather | Animation |
|---------|-----------|
| ☀️ Clear | Warm glow, subtle rays |
| 🌧️ Rain | Falling rain drops |
| ⛈️ Thunderstorm | Heavy rain + lightning flash |
| ☁️ Cloudy | Drifting cloud shapes |
| 🌫️ Fog/Mist/Haze | Slow fog layers |
| ❄️ Snow | Falling snowflakes |

All animations are CSS/JS only — no canvas performance overhead.

---

## 📦 Deployment (Production)

```bash
# Using gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 "app:create_app()"

# Or with Docker
docker build -t weatheriq .
docker run -p 5000:5000 --env-file .env weatheriq
```
