"""
AI Risk Engine
Computes personalised danger scores across 6 risk domains.
All scores are 0-100 (0 = safe, 100 = critical danger).
"""
import math, random
from datetime import datetime


# ─── Constants ───────────────────────────────────────────────────────────────

CONDITION_RISK = {
    'Thunderstorm': 85, 'Tornado': 100, 'Hurricane': 100,
    'Snow': 55,         'Blizzard': 90,
    'Rain': 35,         'Drizzle': 15,
    'Fog': 45,          'Mist': 20,     'Haze': 25,
    'Smoke': 60,        'Dust': 55,     'Sand': 60,
    'Clouds': 5,        'Clear': 0,
}

AQI_HEALTH = {1: 0, 2: 10, 3: 30, 4: 65, 5: 90}

AGE_MULTIPLIERS = {
    'child':   1.35,   # <12
    'teen':    0.90,   # 13-17
    'adult':   1.00,   # 18-59
    'senior':  1.45,   # 60+
}

HEALTH_CONDITION_WEIGHTS = {
    'asthma':         {'aqi': 2.0, 'humidity': 1.4, 'pollen': 1.8},
    'heart_disease':  {'heat_index': 1.8, 'cold': 1.6, 'exertion': 1.5},
    'diabetes':       {'heat_index': 1.4, 'cold': 1.3, 'humidity': 1.2},
    'copd':           {'aqi': 2.2, 'cold': 1.7, 'humidity': 1.3},
    'hypertension':   {'heat_index': 1.5, 'cold': 1.4},
    'pregnancy':      {'heat_index': 1.6, 'aqi': 1.4, 'cold': 1.2},
    'none':           {},
}


# ─── Helper maths ────────────────────────────────────────────────────────────

def _heat_index(temp, hum):
    if temp < 27:
        return temp
    hi = (-8.784 + 1.611*temp + 2.339*hum - 0.146*temp*hum
          - 0.012*temp**2 - 0.016*hum**2
          + 0.002*temp**2*hum + 0.001*temp*hum**2
          - 0.000004*temp**2*hum**2)
    return round(hi, 1)


def _wind_chill(temp, wind_kmh):
    if temp > 10 or wind_kmh < 4.8:
        return temp
    v016 = wind_kmh ** 0.16
    return round(13.12 + 0.6215*temp - 11.37*v016 + 0.3965*temp*v016, 1)


def _clamp(v, lo=0, hi=100):
    return max(lo, min(hi, v))


# ─── Core risk functions ──────────────────────────────────────────────────────

def heatstroke_risk(w: dict, profile: dict) -> dict:
    temp    = w.get('temperature', 25)
    hum     = w.get('humidity', 50)
    hi      = _heat_index(temp, hum)
    score   = 0

    if hi >= 54:   score = 95
    elif hi >= 41: score = 75
    elif hi >= 32: score = 45
    elif hi >= 27: score = 20
    else:          score = 5

    age_mult = AGE_MULTIPLIERS.get(profile.get('age_group', 'adult'), 1.0)
    if 'heart_disease' in profile.get('conditions', []):
        score = min(100, score * 1.6)
    if 'diabetes' in profile.get('conditions', []):
        score = min(100, score * 1.3)

    score = _clamp(score * age_mult)
    return {
        'score': round(score),
        'heat_index': hi,
        'level': _risk_level(score),
        'advice': _heat_advice(score, hi),
        'color': _risk_color(score),
    }


def flood_risk(w: dict) -> dict:
    rain1h   = w.get('rain_1h', 0)
    cond     = w.get('weather_main', 'Clear')
    forecast_rain = w.get('forecast_max_rain', 0)
    score = 0

    if cond == 'Thunderstorm': score = 70
    elif rain1h >= 20:  score = 85
    elif rain1h >= 10:  score = 60
    elif rain1h >= 5:   score = 35
    elif rain1h >= 2:   score = 18
    elif cond == 'Rain': score = 25

    score = _clamp(score + forecast_rain * 0.5)
    return {
        'score': round(score),
        'rain_1h': rain1h,
        'level': _risk_level(score),
        'advice': _flood_advice(score),
        'color': _risk_color(score),
    }


def visibility_risk(w: dict) -> dict:
    vis  = w.get('visibility', 10000)
    cond = w.get('weather_main', 'Clear')
    score = 0

    if vis < 100:    score = 95
    elif vis < 500:  score = 80
    elif vis < 1000: score = 60
    elif vis < 2000: score = 40
    elif vis < 5000: score = 20
    elif cond in ('Fog', 'Mist', 'Haze'): score = max(score, 30)

    return {
        'score': round(score),
        'visibility_km': round(vis / 1000, 1),
        'level': _risk_level(score),
        'advice': _vis_advice(score),
        'color': _risk_color(score),
    }


def windstorm_risk(w: dict) -> dict:
    wind = w.get('wind_speed', 0)
    score = 0

    if wind >= 100:  score = 95
    elif wind >= 75: score = 80
    elif wind >= 60: score = 60
    elif wind >= 40: score = 38
    elif wind >= 25: score = 18

    return {
        'score': round(score),
        'wind_kmh': wind,
        'level': _risk_level(score),
        'advice': _wind_advice(score, wind),
        'color': _risk_color(score),
    }


def aqi_health_risk(w: dict, profile: dict) -> dict:
    aqi_level = w.get('aqi_info', {}).get('value', 2) if w.get('aqi_info') else 2
    base = AQI_HEALTH.get(aqi_level, 20)

    mult = 1.0
    conditions = profile.get('conditions', [])
    if 'asthma' in conditions: mult = max(mult, 2.0)
    if 'copd'   in conditions: mult = max(mult, 2.2)
    age_mult = AGE_MULTIPLIERS.get(profile.get('age_group', 'adult'), 1.0)

    score = _clamp(base * mult * age_mult)
    return {
        'score': round(score),
        'aqi_level': aqi_level,
        'level': _risk_level(score),
        'advice': _aqi_advice(score, aqi_level, conditions),
        'color': _risk_color(score),
    }


def cold_risk(w: dict, profile: dict) -> dict:
    temp = w.get('temperature', 20)
    wind = w.get('wind_speed', 0)
    wc   = _wind_chill(temp, wind)
    score = 0

    if wc <= -25:  score = 90
    elif wc <= -15: score = 70
    elif wc <= -5:  score = 45
    elif wc <= 5:   score = 25
    elif wc <= 10:  score = 10

    age_mult = AGE_MULTIPLIERS.get(profile.get('age_group', 'adult'), 1.0)
    score = _clamp(score * age_mult)
    return {
        'score': round(score),
        'wind_chill': wc,
        'level': _risk_level(score),
        'advice': _cold_advice(score),
        'color': _risk_color(score),
    }


# ─── Composite overall risk ───────────────────────────────────────────────────

def compute_all_risks(w: dict, profile: dict) -> dict:
    r = {
        'heatstroke':   heatstroke_risk(w, profile),
        'flood':        flood_risk(w),
        'visibility':   visibility_risk(w),
        'windstorm':    windstorm_risk(w),
        'aqi_health':   aqi_health_risk(w, profile),
        'cold':         cold_risk(w, profile),
    }
    scores = [v['score'] for v in r.values()]
    overall = round(max(scores) * 0.55 + sum(scores) / len(scores) * 0.45)
    dominant = max(r.items(), key=lambda x: x[1]['score'])[0]
    return {
        'risks': r,
        'overall_score': _clamp(overall),
        'overall_level': _risk_level(overall),
        'overall_color': _risk_color(overall),
        'dominant_risk': dominant,
        'profile': profile,
    }


# ─── Labels & advice ─────────────────────────────────────────────────────────

def _risk_level(s):
    if s >= 80: return 'Critical'
    if s >= 60: return 'High'
    if s >= 35: return 'Moderate'
    if s >= 15: return 'Low'
    return 'Safe'

def _risk_color(s):
    if s >= 80: return '#f43f5e'
    if s >= 60: return '#f97316'
    if s >= 35: return '#f59e0b'
    if s >= 15: return '#06b6d4'
    return '#10b981'

def _heat_advice(s, hi):
    if s >= 80: return f'DANGER: Heat index {hi}°C. Stay indoors in AC, avoid any outdoor activity. Call emergency if you feel dizzy.'
    if s >= 60: return f'High heat index ({hi}°C). Limit outdoor time, drink 500ml water/hour, wear light clothing.'
    if s >= 35: return f'Warm conditions ({hi}°C). Carry water, take breaks, avoid peak sun hours (11am–4pm).'
    return 'Heat conditions are acceptable. Stay hydrated as usual.'

def _flood_advice(s):
    if s >= 80: return 'Severe flood risk. Avoid low-lying areas, underpasses, and flooded roads. Emergency services on alert.'
    if s >= 60: return 'High flood risk. Do not cross flooded areas — 15cm of water can knock you off your feet.'
    if s >= 35: return 'Moderate flooding possible. Monitor local news, keep drainage clear, avoid risky roads.'
    return 'Low flood risk. Normal precautions apply.'

def _vis_advice(s):
    if s >= 80: return 'Near-zero visibility. Do NOT drive. If already on the road, pull over and turn on hazard lights.'
    if s >= 60: return 'Very poor visibility. Reduce speed to <30 km/h, use fog lights, increase following distance to 4x.'
    if s >= 35: return 'Reduced visibility. Use headlights, reduce speed, stay alert for pedestrians and cyclists.'
    return 'Visibility is adequate for normal travel.'

def _wind_advice(s, w):
    if s >= 80: return f'Dangerous winds ({w} km/h). Seek shelter immediately. Do not drive high-sided vehicles.'
    if s >= 60: return f'Strong winds ({w} km/h). Secure outdoor furniture. Avoid exposed areas and tall trees.'
    if s >= 35: return f'Gusty winds ({w} km/h). Hold onto railings, be careful with umbrellas and loose items.'
    return 'Wind speeds are manageable.'

def _aqi_advice(s, level, conditions):
    suffix = ' Especially important for your respiratory conditions.' if any(c in conditions for c in ['asthma', 'copd']) else ''
    if s >= 80: return f'Very poor air quality (Level {level}). Stay indoors with windows closed. Use air purifier.{suffix}'
    if s >= 60: return f'Poor air (Level {level}). Wear N95 mask outdoors. Avoid exercise outside.{suffix}'
    if s >= 35: return f'Moderate air quality (Level {level}). Sensitive individuals limit outdoor exposure.{suffix}'
    return 'Air quality is acceptable for most people.'

def _cold_advice(s):
    if s >= 80: return 'Extreme cold — risk of frostbite in minutes. Stay indoors. If outside, full insulation essential.'
    if s >= 60: return 'Severe cold — limit outdoor time to <15 min. Layer clothing, cover extremities.'
    if s >= 35: return 'Cold conditions — wear warm layers, gloves, and a hat. Keep movement going to stay warm.'
    return 'Cold but manageable with appropriate clothing.'
