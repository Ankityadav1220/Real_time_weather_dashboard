"""
Rural & Agricultural Risk Intelligence
Weather-based risk assessment specifically for farmers and rural communities.
Covers: crop damage, irrigation need, pest risk, livestock risk, harvest windows,
        soil moisture, frost alerts, drought prediction.
"""
import math
from datetime import datetime, timedelta


# ─── Crop sensitivity profiles ────────────────────────────────────────────────
CROP_PROFILES = {
    'wheat':   {'temp_ideal': (10, 25), 'rain_min': 2,  'rain_max': 20, 'humidity_max': 80, 'frost_risk': True},
    'rice':    {'temp_ideal': (22, 35), 'rain_min': 10, 'rain_max': 60, 'humidity_max': 95, 'frost_risk': False},
    'cotton':  {'temp_ideal': (21, 37), 'rain_min': 3,  'rain_max': 25, 'humidity_max': 70, 'frost_risk': True},
    'sugarcane':{'temp_ideal': (20, 40),'rain_min': 5,  'rain_max': 50, 'humidity_max': 90, 'frost_risk': True},
    'maize':   {'temp_ideal': (18, 32), 'rain_min': 4,  'rain_max': 30, 'humidity_max': 85, 'frost_risk': True},
    'soybean': {'temp_ideal': (20, 30), 'rain_min': 3,  'rain_max': 25, 'humidity_max': 80, 'frost_risk': True},
    'potato':  {'temp_ideal': (10, 20), 'rain_min': 3,  'rain_max': 20, 'humidity_max': 75, 'frost_risk': True},
    'tomato':  {'temp_ideal': (18, 30), 'rain_min': 2,  'rain_max': 15, 'humidity_max': 80, 'frost_risk': True},
    'onion':   {'temp_ideal': (13, 25), 'rain_min': 2,  'rain_max': 15, 'humidity_max': 70, 'frost_risk': False},
    'mango':   {'temp_ideal': (24, 38), 'rain_min': 1,  'rain_max': 20, 'humidity_max': 80, 'frost_risk': True},
    'general': {'temp_ideal': (15, 35), 'rain_min': 2,  'rain_max': 30, 'humidity_max': 85, 'frost_risk': False},
}


def _clamp(v, lo=0, hi=100):
    return max(lo, min(hi, int(v)))


def _risk_level(s):
    if s >= 75: return ('Critical', '#f43f5e')
    if s >= 55: return ('High',     '#f97316')
    if s >= 35: return ('Moderate', '#f59e0b')
    if s >= 15: return ('Low',      '#06b6d4')
    return ('Safe', '#10b981')


# ─── Individual risk assessors ────────────────────────────────────────────────

def crop_damage_risk(w: dict, crop: str = 'general') -> dict:
    profile = CROP_PROFILES.get(crop.lower(), CROP_PROFILES['general'])
    temp    = w.get('temperature', 25)
    rain    = w.get('rain_1h', 0)
    hum     = w.get('humidity', 55)
    cond    = w.get('weather_main', 'Clear')
    wind    = w.get('wind_speed', 10)

    score = 0
    reasons = []

    # Temperature stress
    tmin, tmax = profile['temp_ideal']
    if temp < tmin - 5:
        score += 40; reasons.append(f'Temperature {temp}°C well below {crop} minimum {tmin}°C')
    elif temp < tmin:
        score += 20; reasons.append(f'Temperature {temp}°C slightly below optimal for {crop}')
    elif temp > tmax + 8:
        score += 45; reasons.append(f'Heat stress: {temp}°C far above {crop} maximum {tmax}°C')
    elif temp > tmax:
        score += 22; reasons.append(f'Temperature {temp}°C above optimal for {crop}')

    # Rain stress
    if rain > profile['rain_max']:
        score += 35; reasons.append(f'Excess rainfall ({rain} mm/hr) — waterlogging risk')
    elif rain < profile['rain_min'] and cond == 'Clear':
        score += 20; reasons.append(f'Low rainfall — irrigation likely needed for {crop}')

    # Humidity
    if hum > profile['humidity_max']:
        score += 20; reasons.append(f'High humidity ({hum}%) — fungal disease risk')

    # Wind damage
    if wind >= 50:
        score += 30; reasons.append(f'Strong winds ({wind} km/h) — lodging and mechanical damage risk')
    elif wind >= 35:
        score += 15; reasons.append(f'Moderate winds ({wind} km/h) — some crop movement')

    # Storm
    if cond == 'Thunderstorm':
        score += 25; reasons.append('Active thunderstorm — severe crop damage possible')

    score = _clamp(score)
    level, color = _risk_level(score)
    return {
        'score':   score, 'level': level, 'color': color,
        'crop':    crop,  'reasons': reasons or ['Conditions are suitable for this crop'],
        'icon':    '🌾',  'title': f'{crop.title()} Crop Risk',
    }


def irrigation_need(w: dict) -> dict:
    temp   = w.get('temperature', 25)
    hum    = w.get('humidity', 55)
    rain   = w.get('rain_1h', 0)
    cond   = w.get('weather_main', 'Clear')
    wind   = w.get('wind_speed', 10)

    # ETo simplified Hargreaves-like formula (Penman-Monteith approximation)
    eto = max(0, (0.0023 * (temp + 17.8) * (temp - 0) * 0.5 * 0.408 *
                  (1 + wind * 0.01) * (1 - hum / 200)))
    eto = round(eto, 2)

    deficit = max(0, eto - rain * 0.8)
    if deficit < 0.5:   score = 5
    elif deficit < 1.5: score = 30
    elif deficit < 3.0: score = 60
    else:               score = 85

    if cond in ('Rain', 'Drizzle', 'Thunderstorm') and rain > 3:
        score = max(0, score - 40)

    level, color = _risk_level(score)
    return {
        'score': _clamp(score), 'level': level, 'color': color,
        'eto_mm_day': eto, 'deficit_mm': round(deficit, 2),
        'icon': '💧', 'title': 'Irrigation Need',
        'advice': _irrigation_advice(score, deficit, cond),
    }


def pest_disease_risk(w: dict, crop: str = 'general') -> dict:
    temp = w.get('temperature', 25)
    hum  = w.get('humidity', 55)
    rain = w.get('rain_1h', 0)
    cond = w.get('weather_main', 'Clear')

    score = 0
    pests = []

    # High humidity → fungal diseases
    if hum >= 85 and temp >= 20:
        score += 45; pests.append('High fungal disease risk (blight, rust, mildew)')
    elif hum >= 70 and temp >= 22:
        score += 25; pests.append('Moderate fungal risk — monitor leaves for spots')

    # Warm & humid → insects
    if 25 <= temp <= 35 and hum >= 60:
        score += 20; pests.append('Favourable for aphids, whiteflies, and thrips')

    # Post-rain → slug/snail, root disease
    if rain > 5:
        score += 15; pests.append('Post-rain: watch for slugs, snails, and root rot')

    # Dry & hot → spider mites
    if temp > 32 and hum < 40:
        score += 20; pests.append('Dry hot conditions favour spider mites')

    level, color = _risk_level(_clamp(score))
    return {
        'score': _clamp(score), 'level': level, 'color': color,
        'pests': pests or ['No significant pest conditions detected'],
        'icon': '🐛', 'title': 'Pest & Disease Risk',
    }


def frost_risk(w: dict) -> dict:
    temp   = w.get('temperature', 20)
    dew    = _dew_point(temp, w.get('humidity', 55))
    wind   = w.get('wind_speed', 10)
    cond   = w.get('weather_main', 'Clear')
    hour   = datetime.utcnow().hour

    score = 0
    # Frost most likely 2–6am with clear skies and calm winds
    if temp <= 0:
        score = 90
    elif temp <= 3:
        score = 70
    elif temp <= 5 and cond == 'Clear' and wind < 10:
        score = 50
    elif temp <= 8:
        score = 25

    # Dew point near freezing increases frost risk
    if dew <= 2 and temp <= 8:
        score = min(100, score + 15)

    level, color = _risk_level(score)
    return {
        'score':     _clamp(score), 'level': level, 'color': color,
        'temp':      temp,  'dew_point': dew,
        'icon':      '❄️', 'title': 'Frost Risk',
        'advice':    _frost_advice(score, temp),
    }


def harvest_window(w: dict) -> dict:
    temp    = w.get('temperature', 25)
    rain    = w.get('rain_1h', 0)
    hum     = w.get('humidity', 55)
    wind    = w.get('wind_speed', 10)
    cond    = w.get('weather_main', 'Clear')

    # Ideal harvest: dry, moderate temp, low wind
    score = 0   # 0 = worst, 100 = best
    if cond == 'Clear' and rain == 0 and hum < 65 and 15 <= temp <= 32 and wind < 25:
        score = 90
    elif rain < 1 and hum < 75 and temp < 35 and wind < 35:
        score = 65
    elif rain < 3:
        score = 40
    elif rain < 8:
        score = 20
    else:
        score = 5

    advice = ('✅ Excellent harvesting conditions!' if score >= 80
              else '🟡 Acceptable — complete harvest before conditions worsen' if score >= 50
              else '🔴 Poor harvesting conditions — wait for dry weather')

    return {
        'score':  score, 'level': '✅ Excellent' if score >= 80 else ('🟡 Fair' if score >= 50 else '🔴 Poor'),
        'color':  '#10b981' if score >= 80 else ('#f59e0b' if score >= 50 else '#f43f5e'),
        'icon':   '🌾', 'title': 'Harvest Window', 'advice': advice,
    }


def livestock_risk(w: dict) -> dict:
    temp  = w.get('temperature', 25)
    hum   = w.get('humidity', 55)
    wind  = w.get('wind_speed', 10)
    rain  = w.get('rain_1h', 0)
    cond  = w.get('weather_main', 'Clear')

    # THI (Temperature-Humidity Index) for cattle
    thi = round(0.8 * temp + (hum / 100) * (temp - 14.4) + 46.4, 1)

    score = 0
    conditions = []

    if thi >= 79:
        score += 50; conditions.append(f'Severe heat stress (THI={thi}) — cattle productivity drops significantly')
    elif thi >= 72:
        score += 30; conditions.append(f'Moderate heat stress (THI={thi}) — reduce stocking density')

    if temp <= 0:
        score += 40; conditions.append('Freezing temperatures — shelter and extra feed needed for livestock')
    elif temp <= 5:
        score += 20; conditions.append('Cold stress — ensure shelter and adequate nutrition')

    if rain >= 10 or cond == 'Thunderstorm':
        score += 20; conditions.append('Heavy rain/storm — ensure livestock are under shelter')

    if wind >= 60:
        score += 15; conditions.append('Strong winds — check fencing and provide windbreaks')

    level, color = _risk_level(_clamp(score))
    return {
        'score':      _clamp(score), 'level': level, 'color': color,
        'thi':        thi, 'conditions': conditions or ['Livestock conditions are comfortable'],
        'icon':       '🐄', 'title': 'Livestock Risk',
    }


def drought_index(observations: list) -> dict:
    if len(observations) < 5:
        return {'spi': 0, 'level': 'Insufficient data', 'color': '#94a3b8', 'score': 0}

    recent_rain = sum(o.get('rain_1h', 0) for o in observations[-24:])
    avg_rain    = sum(o.get('rain_1h', 0) for o in observations) / len(observations)
    avg_temp    = sum(o.get('temperature', 25) for o in observations[-24:]) / min(24, len(observations))

    if avg_rain < 0.01:
        spi = -2.0
    else:
        spi = round((recent_rain - avg_rain * 24) / max(0.1, avg_rain * 5), 2)

    if spi <= -2.0:   level, color, score = 'Extreme Drought', '#9C27B0', 90
    elif spi <= -1.5: level, color, score = 'Severe Drought',  '#f43f5e', 75
    elif spi <= -1.0: level, color, score = 'Moderate Drought','#f97316', 55
    elif spi <= -0.5: level, color, score = 'Mild Drought',    '#f59e0b', 35
    else:             level, color, score = 'Normal',          '#10b981', 10

    return {
        'spi':         spi,
        'level':       level,
        'color':       color,
        'score':       score,
        'recent_rain_mm': round(recent_rain, 1),
        'avg_rain_mm': round(avg_rain, 3),
        'avg_temp':    round(avg_temp, 1),
        'icon':        '☀️',
        'title':       'Drought Index (SPI)',
        'advice':      _drought_advice(spi),
    }


# ─── Full rural risk composite ────────────────────────────────────────────────

def compute_rural_risk(w: dict, crop: str = 'general', observations: list = None) -> dict:
    risks = {
        'crop_damage': crop_damage_risk(w, crop),
        'irrigation':  irrigation_need(w),
        'pest':        pest_disease_risk(w, crop),
        'frost':       frost_risk(w),
        'harvest':     harvest_window(w),
        'livestock':   livestock_risk(w),
    }
    if observations:
        risks['drought'] = drought_index(observations)

    scores  = [v['score'] for v in risks.values() if 'score' in v]
    overall = _clamp(max(scores) * 0.5 + sum(scores) / len(scores) * 0.5) if scores else 0
    dom_key = max(risks.items(), key=lambda x: x[1].get('score', 0))[0]

    return {
        'risks':           risks,
        'overall_score':   overall,
        'overall_level':   _risk_level(overall)[0],
        'overall_color':   _risk_level(overall)[1],
        'dominant_risk':   dom_key,
        'crop':            crop,
        'weather_summary': {k: w.get(k) for k in ('temperature','humidity','wind_speed','rain_1h','weather_main')},
        'farming_advisory': _farming_advisory(risks, crop),
    }


# ─── Advisory generators ──────────────────────────────────────────────────────

def _irrigation_advice(score, deficit, cond):
    if score >= 70: return f'Urgent irrigation needed — soil moisture deficit {deficit:.1f} mm'
    if score >= 40: return f'Irrigation recommended within 24 hours — deficit {deficit:.1f} mm'
    if cond in ('Rain', 'Drizzle'): return 'No irrigation — rainfall is sufficient'
    return 'Soil moisture is adequate — monitor over next 48 hours'


def _frost_advice(score, temp):
    if score >= 75: return f'Frost occurring now ({temp}°C). Cover sensitive crops immediately.'
    if score >= 50: return f'High frost risk tonight. Cover crops, run sprinkler systems, move potted plants indoors.'
    if score >= 25: return f'Possible frost below 5°C. Monitor overnight temperatures.'
    return 'No frost risk in current conditions.'


def _drought_advice(spi):
    if spi <= -2.0: return 'Extreme drought — emergency water conservation measures. Prioritise livestock water supply.'
    if spi <= -1.5: return 'Severe drought — implement deficit irrigation. Consider drought-resistant varieties.'
    if spi <= -1.0: return 'Moderate drought — reduce irrigation frequency, mulch fields to conserve moisture.'
    if spi <= -0.5: return 'Mild dryness — monitor soil moisture. Consider water conservation.'
    return 'Precipitation levels are normal for the season.'


def _farming_advisory(risks, crop):
    advisories = []
    for key, risk in risks.items():
        score = risk.get('score', 0)
        if score >= 60:
            advisories.append({
                'icon':     risk.get('icon', '⚠️'),
                'type':     key.replace('_', ' ').title(),
                'severity': risk.get('level', 'High'),
                'text':     (risk.get('advice') or
                             (risk.get('reasons', [''])[0] if risk.get('reasons') else '') or
                             (risk.get('conditions', [''])[0] if risk.get('conditions') else '')),
                'color':    risk.get('color', '#f59e0b'),
            })
    if not advisories:
        advisories.append({
            'icon': '✅', 'type': 'General',
            'severity': 'Safe', 'color': '#10b981',
            'text': f'Weather conditions are generally favourable for {crop} farming today.',
        })
    return advisories


def _dew_point(temp, hum):
    a, b = 17.27, 237.3
    alpha = (a * temp / (b + temp)) + math.log(max(hum, 1) / 100.0)
    return round((b * alpha) / (a - alpha), 1)
