"""
Weather Mood & Productivity AI
Predicts energy, focus, mood, and recommends best activity windows
based on weather conditions, time of day, and user profile.
"""
import math
from datetime import datetime


# ─── Influence tables ─────────────────────────────────────────────────────────

TEMP_PRODUCTIVITY = {
    # (min, max): (cognitive_boost, physical_boost)
    (-99, 0):   (-35, -50),
    (0,   8):   (-15, -30),
    (8,  15):   ( 10,   5),
    (15, 22):   ( 25,  20),   # ideal cognitive range
    (22, 26):   ( 20,  30),   # ideal physical range
    (26, 32):   (  0,  10),
    (32, 38):   (-20, -15),
    (38, 99):   (-40, -30),
}

WEATHER_MOOD = {
    'Clear':       {'mood': 25, 'energy': 20, 'focus': 10},
    'Clouds':      {'mood':  5, 'energy':  0, 'focus':  5},
    'Rain':        {'mood':-15, 'energy':-10, 'focus': 15},   # rain boosts deep focus!
    'Drizzle':     {'mood': -5, 'energy': -5, 'focus': 10},
    'Thunderstorm':{'mood':-25, 'energy':-20, 'focus':-10},
    'Snow':        {'mood': 15, 'energy':-10, 'focus':  5},
    'Fog':         {'mood':-10, 'energy':-15, 'focus': -5},
    'Haze':        {'mood':-10, 'energy':-10, 'focus': -5},
    'Mist':        {'mood':  0, 'energy': -5, 'focus':  5},
}

HUMIDITY_EFFECT = {
    (0,  30): {'comfort': -20, 'label': 'Very dry'},
    (30, 45): {'comfort':  15, 'label': 'Comfortable'},
    (45, 60): {'comfort':  20, 'label': 'Ideal'},
    (60, 75): {'comfort':   5, 'label': 'Slightly humid'},
    (75, 85): {'comfort': -15, 'label': 'Humid'},
    (85,100): {'comfort': -30, 'label': 'Very humid'},
}

CIRCADIAN_CURVE = {
    # hour: (cognitive_peak, energy_peak)  — based on circadian rhythm research
     0: (-40, -45),  1: (-45, -50),  2: (-50, -55),  3: (-55, -60),
     4: (-45, -55),  5: (-20, -30),  6: ( 10, -10),  7: ( 25,  10),
     8: ( 35,  25),  9: ( 45,  35),  10: ( 50,  40), 11: ( 48,  38),
    12: ( 35,  30),  13: ( 15,  20), 14: ( 10,  15), 15: ( 30,  25),
    16: ( 45,  40),  17: ( 42,  45), 18: ( 30,  40), 19: ( 20,  25),
    20: (  5,  10),  21: (-10, -10), 22: (-25, -20), 23: (-35, -35),
}


def _temp_effect(temp):
    for (lo, hi), effect in TEMP_PRODUCTIVITY.items():
        if lo <= temp < hi:
            return effect
    return (0, 0)


def _humidity_comfort(hum):
    for (lo, hi), v in HUMIDITY_EFFECT.items():
        if lo <= hum <= hi:
            return v['comfort'], v['label']
    return 0, 'Normal'


def _clamp(v, lo=0, hi=100):
    return max(lo, min(hi, v))


def _normalise(raw, base=50):
    """Convert raw score (-100..+100 deltas) to 0-100 percentage."""
    return _clamp(base + raw)


# ─── Main analysis ────────────────────────────────────────────────────────────

def analyse_productivity(w: dict, profile: dict) -> dict:
    now  = datetime.utcnow()
    hour = now.hour

    temp  = w.get('temperature', 22)
    hum   = w.get('humidity', 55)
    cond  = w.get('weather_main', 'Clear')
    aqi   = (w.get('aqi_info') or {}).get('value', 2)
    wind  = w.get('wind_speed', 10)

    # Base from circadian
    circ_cog, circ_en = CIRCADIAN_CURVE.get(hour, (0, 0))

    # Temperature effect
    t_cog, t_phy = _temp_effect(temp)

    # Weather mood
    wm = WEATHER_MOOD.get(cond, {'mood': 0, 'energy': 0, 'focus': 0})

    # Humidity
    h_comfort, h_label = _humidity_comfort(hum)

    # AQI penalty
    aqi_pen = {1: 0, 2: -3, 3: -10, 4: -22, 5: -35}.get(aqi, 0)

    # Compute raw scores (delta from 50-baseline)
    cognitive_delta = circ_cog + t_cog * 0.3 + wm['focus'] * 0.5 + aqi_pen * 0.4
    energy_delta    = circ_en  + t_phy * 0.4 + wm['energy']* 0.6 + h_comfort * 0.2 + aqi_pen * 0.3
    mood_delta      = wm['mood'] * 0.7 + h_comfort * 0.2 + t_cog * 0.1

    cognitive  = _normalise(cognitive_delta)
    energy     = _normalise(energy_delta)
    mood       = _normalise(mood_delta)
    focus_wndw = cognitive > 60

    # Best windows forecast (next 12 hrs)
    windows = _forecast_windows(w, hour)

    # Recommendations
    recs = _build_recommendations(cognitive, energy, mood, cond, temp, hum, aqi, hour)

    return {
        'scores': {
            'cognitive': cognitive,
            'energy':    energy,
            'mood':      mood,
            'overall':   round((cognitive * 0.4 + energy * 0.35 + mood * 0.25)),
        },
        'context': {
            'temp_effect':      f'{t_cog:+d}% cognitive boost from temperature',
            'weather_effect':   f'{wm["mood"]:+d} mood, {wm["energy"]:+d} energy from {cond}',
            'humidity_label':   h_label,
            'circadian_phase':  _circadian_label(hour),
            'aqi_impact':       f'AQI Level {aqi} — {aqi_pen:+d} cognitive penalty',
        },
        'focus_window_now': focus_wndw,
        'windows': windows,
        'recommendations': recs,
        'hour': hour,
    }


def _circadian_label(hour):
    if 8  <= hour <= 11: return 'Morning Peak — optimal cognitive performance'
    if 12 <= hour <= 13: return 'Post-lunch dip — take a short break'
    if 15 <= hour <= 18: return 'Afternoon surge — second peak for focus'
    if 19 <= hour <= 21: return 'Evening wind-down — light tasks recommended'
    if 22 <= hour or hour < 6: return 'Night — rest and recovery phase'
    return 'Early morning — warming up'


def _forecast_windows(w, current_hour):
    """Generate 12-hour productivity forecast."""
    temp = w.get('temperature', 22)
    cond = w.get('weather_main', 'Clear')
    windows = []
    for offset in range(12):
        h = (current_hour + offset) % 24
        circ_cog, circ_en = CIRCADIAN_CURVE.get(h, (0, 0))
        wm = WEATHER_MOOD.get(cond, {'mood': 0, 'energy': 0, 'focus': 0})
        t_cog, _ = _temp_effect(temp)
        score = _normalise(circ_cog + t_cog * 0.25 + wm['focus'] * 0.4)
        windows.append({
            'hour': f'{h:02d}:00',
            'hour_int': h,
            'score': score,
            'label': 'Peak' if score >= 70 else ('Good' if score >= 50 else ('Low' if score >= 30 else 'Rest')),
        })
    return windows


def _build_recommendations(cog, energy, mood, cond, temp, hum, aqi, hour):
    recs = []

    # Study / deep work
    if cog >= 65:
        recs.append({'icon': '📚', 'type': 'study',    'title': 'Great time for deep work', 'desc': 'Cognitive performance is high. Tackle your most demanding tasks now — coding, studying, writing.', 'priority': 'high'})
    elif cog >= 45:
        recs.append({'icon': '📝', 'type': 'study',    'title': 'Moderate focus window',    'desc': 'Good for structured tasks, reviewing notes, emails, or creative work.', 'priority': 'medium'})
    else:
        recs.append({'icon': '😴', 'type': 'rest',     'title': 'Low focus period',         'desc': 'Cognitive capacity is diminished. Rest, light reading, or admin tasks are ideal.', 'priority': 'low'})

    # Physical activity
    if energy >= 65 and cond in ('Clear', 'Clouds') and 10 <= temp <= 28:
        recs.append({'icon': '🏃', 'type': 'physical', 'title': 'Ideal for outdoor exercise', 'desc': f'Weather ({cond}, {temp}°C) and energy levels are both optimal for a run, walk or cycle.', 'priority': 'high'})
    elif energy >= 50 and temp > 28:
        recs.append({'icon': '🏊', 'type': 'physical', 'title': 'Exercise indoors or in water', 'desc': f'It\'s {temp}°C — prefer indoor gym, yoga, or swimming to avoid heat exposure.', 'priority': 'medium'})
    elif energy < 40:
        recs.append({'icon': '🧘', 'type': 'physical', 'title': 'Light stretching recommended', 'desc': 'Energy is low. Gentle yoga, stretching, or a short walk are appropriate.', 'priority': 'low'})

    # Hydration
    if temp >= 32 or hum >= 75:
        recs.append({'icon': '💧', 'type': 'hydration','title': 'Hydration alert',           'desc': f'Hot or humid conditions ({temp}°C, {hum}% humidity). Drink at least 400ml/hr. Set reminders.', 'priority': 'high'})
    else:
        recs.append({'icon': '🥤', 'type': 'hydration','title': 'Standard hydration',        'desc': '2.5–3 litres of water through the day maintains optimal cognitive performance.', 'priority': 'low'})

    # Sleep / rest
    if 21 <= hour or hour < 7:
        recs.append({'icon': '🌙', 'type': 'sleep',    'title': 'Wind-down time',            'desc': f'{"Good sleep weather." if 15<=temp<=22 else f"Temp ({temp}°C) may affect sleep. Use AC/fan."} Avoid screens 1hr before bed.', 'priority': 'medium'})

    # Mood booster
    if mood < 40 and cond in ('Rain', 'Thunderstorm', 'Fog'):
        recs.append({'icon': '🎵', 'type': 'mood',     'title': 'Boost your mood',           'desc': 'Dark weather can affect mood. Try upbeat music, a hot drink, light therapy, or call a friend.', 'priority': 'medium'})

    # AQI
    if aqi >= 3:
        recs.append({'icon': '😷', 'type': 'health',   'title': 'Air quality affects focus', 'desc': 'Poor air quality reduces cognitive performance. Keep windows closed and use an air purifier.', 'priority': 'high'})

    return recs[:6]   # top 6
