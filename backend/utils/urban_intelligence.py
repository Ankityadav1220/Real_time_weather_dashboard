"""
Urban Risk, Route Weather & Energy Prediction
Covers:
  - Waterlogging probability
  - Traffic congestion risk
  - Infrastructure stress
  - Route weather safety (A→B)
  - Electricity demand prediction
"""
import numpy as np
from datetime import datetime, timedelta
import math


# ─── Urban Risk Engine ────────────────────────────────────────────────────────

def compute_urban_risk(w: dict) -> dict:
    rain    = w.get('rain_1h', 0)
    cond    = w.get('weather_main', 'Clear')
    temp    = w.get('temperature', 25)
    hum     = w.get('humidity', 55)
    wind    = w.get('wind_speed', 10)
    vis     = w.get('visibility', 10000)
    hour    = datetime.utcnow().hour

    # ── Waterlogging ─────────────────────────────────────────────────────
    if rain >= 25 or cond == 'Thunderstorm':
        wl_score = 85
    elif rain >= 10:
        wl_score = 65
    elif rain >= 5:
        wl_score = 40
    elif rain >= 2:
        wl_score = 22
    else:
        wl_score = max(0, 5)

    # ── Traffic congestion risk ──────────────────────────────────────────
    # Peak hours: 8-10am, 5-8pm
    is_peak = (8 <= hour <= 10) or (17 <= hour <= 20)
    traffic_base = 60 if is_peak else 30
    traffic_rain_add = min(35, rain * 3)
    fog_add = 25 if vis < 1000 else (10 if vis < 3000 else 0)
    traffic_score = min(100, traffic_base + traffic_rain_add + fog_add)

    # ── Power grid stress ────────────────────────────────────────────────
    power_base = 40
    if temp >= 38:    power_base += 40   # heavy AC use
    elif temp >= 32:  power_base += 25
    elif temp <= 5:   power_base += 30   # heating
    if is_peak:       power_base += 15
    power_score = min(100, power_base)

    # ── Infrastructure stress ────────────────────────────────────────────
    infra = 20
    if wind >= 60:    infra += 40
    elif wind >= 40:  infra += 20
    if rain >= 15:    infra += 25
    if cond == 'Thunderstorm': infra += 30
    infra_score = min(100, infra)

    # ── Air pollution spike ──────────────────────────────────────────────
    aqi_val = (w.get('aqi_info') or {}).get('value', 2)
    pollution_score = {1: 5, 2: 20, 3: 45, 4: 70, 5: 90}.get(aqi_val, 20)

    def lbl(s):
        if s >= 70: return 'Critical'
        if s >= 50: return 'High'
        if s >= 30: return 'Moderate'
        return 'Low'

    def col(s):
        if s >= 70: return '#f43f5e'
        if s >= 50: return '#f97316'
        if s >= 30: return '#f59e0b'
        return '#10b981'

    risks = {
        'waterlogging': {'score': wl_score,      'label': lbl(wl_score),      'color': col(wl_score),      'icon': '🌊', 'title': 'Waterlogging Risk'},
        'traffic':      {'score': traffic_score,  'label': lbl(traffic_score), 'color': col(traffic_score), 'icon': '🚗', 'title': 'Traffic Congestion Risk'},
        'power':        {'score': power_score,    'label': lbl(power_score),   'color': col(power_score),   'icon': '⚡', 'title': 'Power Grid Stress'},
        'infrastructure':{'score': infra_score,   'label': lbl(infra_score),   'color': col(infra_score),   'icon': '🏗️', 'title': 'Infrastructure Stress'},
        'pollution':    {'score': pollution_score,'label': lbl(pollution_score),'color': col(pollution_score),'icon': '🌫️','title': 'Air Pollution Risk'},
    }

    overall = round(max(v['score'] for v in risks.values()) * 0.5 +
                    sum(v['score'] for v in risks.values()) / len(risks) * 0.5)

    return {
        'risks': risks,
        'overall_score': overall,
        'overall_label': lbl(overall),
        'peak_hours': is_peak,
        'advisories': _urban_advisories(risks),
    }


def _urban_advisories(risks):
    adv = []
    if risks['waterlogging']['score'] >= 50:
        adv.append({'icon': '🌊', 'text': 'Avoid low-lying roads and underpasses — waterlogging likely.'})
    if risks['traffic']['score'] >= 60:
        adv.append({'icon': '🚗', 'text': 'Expect heavy congestion. Use public transport or delay travel.'})
    if risks['power']['score'] >= 60:
        adv.append({'icon': '⚡', 'text': 'High power demand — possible outages. Keep devices charged.'})
    if risks['infrastructure']['score'] >= 50:
        adv.append({'icon': '🏗️', 'text': 'Strong winds or rain may damage structures. Stay clear of construction sites.'})
    if not adv:
        adv.append({'icon': '✅', 'text': 'Urban conditions are normal. No special advisories.'})
    return adv


# ─── Route Weather Engine ─────────────────────────────────────────────────────

# Simulated waypoint offsets for cities
CITY_COORDS = {
    'Delhi':    (28.61, 77.21), 'Mumbai': (19.08, 72.88),
    'London':   (51.51, -0.13), 'New York': (40.71, -74.01),
    'Tokyo':    (35.68, 139.69),'Dubai': (25.20, 55.27),
}

def analyse_route(origin: str, dest: str, weather_func) -> dict:
    """
    Simulates weather conditions along 5 waypoints between origin and dest.
    Uses weather_func(city) to fetch weather for each waypoint.
    """
    o = CITY_COORDS.get(origin, (28.61, 77.21))
    d = CITY_COORDS.get(dest, (19.08, 72.88))

    distance_km = _haversine(o[0], o[1], d[0], d[1])
    waypoints = _interpolate(o, d, 5)

    segments = []
    worst_risk = 0
    risk_points = []

    for i, (lat, lon) in enumerate(waypoints):
        # Approximate: slightly vary weather per waypoint
        w = weather_func(origin)
        # Add route-position variation
        rain_add   = max(0, (i - 2) * 1.5) if i > 2 else 0
        temp_delta = (i - 2) * 0.5

        seg = {
            'index':    i,
            'lat':      round(lat, 3),
            'lon':      round(lon, 3),
            'label':    f'Waypoint {i+1}' if 0 < i < len(waypoints)-1 else ('Origin' if i == 0 else 'Destination'),
            'temp':     round(w.get('temperature', 25) + temp_delta, 1),
            'rain':     round(w.get('rain_1h', 0) + rain_add, 1),
            'wind':     w.get('wind_speed', 10),
            'vis':      w.get('visibility', 10000),
            'cond':     w.get('weather_main', 'Clear'),
            'risk':     0,
        }
        # Compute segment risk
        seg_risk = _segment_risk(seg)
        seg['risk']  = seg_risk
        seg['risk_label'] = 'Safe' if seg_risk < 25 else ('Caution' if seg_risk < 55 else 'Risky')
        seg['risk_color'] = '#10b981' if seg_risk < 25 else ('#f59e0b' if seg_risk < 55 else '#f43f5e')

        if seg_risk > worst_risk:
            worst_risk = seg_risk
        if seg_risk >= 50:
            risk_points.append(f"Waypoint {i+1}")
        segments.append(seg)

    eta_hours = distance_km / 80    # assume 80 km/h average
    weather_delay = (worst_risk / 100) * eta_hours * 0.5

    return {
        'origin':       origin,
        'destination':  dest,
        'distance_km':  round(distance_km),
        'eta_hours':    round(eta_hours, 1),
        'weather_delay_hr': round(weather_delay, 1),
        'segments':     segments,
        'worst_risk':   worst_risk,
        'risk_label':   'Safe' if worst_risk < 25 else ('Exercise Caution' if worst_risk < 55 else 'High Risk'),
        'risk_color':   '#10b981' if worst_risk < 25 else ('#f59e0b' if worst_risk < 55 else '#f43f5e'),
        'risk_points':  risk_points,
        'recommendation': _route_recommendation(worst_risk, weather_delay),
    }


def _segment_risk(seg):
    r = 0
    if seg['vis'] < 1000:   r += 35
    if seg['wind'] >= 60:   r += 30
    elif seg['wind'] >= 40: r += 15
    if seg['rain'] >= 10:   r += 30
    elif seg['rain'] >= 3:  r += 15
    if seg['cond'] == 'Thunderstorm': r += 25
    return min(100, r)


def _route_recommendation(risk, delay):
    if risk >= 70:
        return f'⚠️ Route has HIGH weather risk. Recommend delaying travel or choosing an alternate route. Expected weather delay: +{delay:.1f}h.'
    if risk >= 40:
        return f'⚡ Some weather hazards along this route. Drive carefully, reduce speed in risky sections. Allow extra +{delay:.1f}h.'
    return '✅ Route looks clear. Weather conditions are favourable for travel.'


def _haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat/2)**2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))


def _interpolate(o, d, n):
    return [(o[0] + (d[0]-o[0])*i/(n-1),
             o[1] + (d[1]-o[1])*i/(n-1)) for i in range(n)]


# ─── Energy Prediction ────────────────────────────────────────────────────────

def predict_energy(w: dict) -> dict:
    temp  = w.get('temperature', 25)
    hum   = w.get('humidity', 55)
    hour  = datetime.utcnow().hour
    cond  = w.get('weather_main', 'Clear')

    # Baseline consumption (kWh/hr for average household)
    base = 0.8

    # Temperature-driven HVAC
    if temp >= 36:   ac_demand = 3.2
    elif temp >= 32: ac_demand = 2.4
    elif temp >= 28: ac_demand = 1.6
    elif temp <= 5:  ac_demand = 2.8   # heating
    elif temp <= 10: ac_demand = 1.8
    else:            ac_demand = 0.2

    # Lighting (cloudy/night)
    light_demand = 0.6 if (cond in ('Clouds','Rain','Fog','Thunderstorm') or hour < 7 or hour > 19) else 0.1

    # Peak factor
    peak_factor = 1.3 if (8 <= hour <= 10 or 18 <= hour <= 22) else 1.0

    total = round((base + ac_demand + light_demand) * peak_factor, 2)
    daily_est = round(total * 24 * 0.65, 1)  # rough daily estimate

    # Cost (₹ per kWh ~ ₹8 in India)
    cost_per_hour = round(total * 8, 1)
    daily_cost    = round(daily_est * 8, 1)

    # Solar potential
    solar = 80 if cond == 'Clear' else (40 if cond == 'Clouds' else 10)

    tips = _energy_tips(temp, cond, total)

    # Hourly forecast (next 12h)
    hourly = []
    for i in range(12):
        h = (hour + i) % 24
        t_offset = 3 * math.sin(math.pi * (h - 5) / 14) if 5 <= h <= 19 else -1
        t_proj = max(10, temp + t_offset)
        ac_proj = max(0.1, ac_demand + (t_proj - temp) * 0.08)
        light_p = 0.5 if (h < 7 or h > 19) else 0.1
        pf = 1.25 if (8 <= h <= 10 or 18 <= h <= 22) else 1.0
        total_h = round((base + ac_proj + light_p) * pf, 2)
        hourly.append({'hour': f'{h:02d}:00', 'kwh': total_h, 'cost': round(total_h * 8, 1)})

    return {
        'current_kwh':  total,
        'daily_est_kwh': daily_est,
        'cost_per_hour': cost_per_hour,
        'daily_cost_inr': daily_cost,
        'breakdown': {
            'hvac':     round(ac_demand * peak_factor, 2),
            'lighting': round(light_demand * peak_factor, 2),
            'base':     round(base * peak_factor, 2),
        },
        'solar_potential_pct': solar,
        'tips': tips,
        'hourly_forecast': hourly,
        'peak_hours': (8 <= hour <= 10 or 18 <= hour <= 22),
    }


def _energy_tips(temp, cond, kwh):
    tips = []
    if temp >= 32:
        tips.append({'icon': '❄️', 'text': 'Set AC to 26°C (not lower) — each °C lower increases consumption by 6%.'})
    if temp <= 10:
        tips.append({'icon': '🔥', 'text': 'Use a programmable thermostat. Set heating to 20°C and lower at night.'})
    if cond == 'Clear':
        tips.append({'icon': '☀️', 'text': 'Great solar generation day! Shift heavy appliances to peak solar hours (10am–3pm).'})
    if kwh > 2.5:
        tips.append({'icon': '💡', 'text': 'High consumption period. Unplug standby appliances and switch to LED lighting.'})
    tips.append({'icon': '⏰', 'text': 'Run washing machines and dishwashers at off-peak hours (10pm–6am) to save 30%.'})
    return tips[:4]
