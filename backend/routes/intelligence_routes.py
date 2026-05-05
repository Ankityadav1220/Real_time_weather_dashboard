"""
Intelligence Routes — lat/lon-first API endpoints
All endpoints now accept: lat + lon (primary) OR city (fallback)
"""
from flask import Blueprint, request, jsonify, current_app
import logging
from datetime import datetime

from database.db_manager import DatabaseManager
from backend.utils.weather_api import WeatherAPIService
from backend.utils.risk_engine import compute_all_risks
from backend.utils.nowcaster import NowcastEngine
from backend.utils.productivity_ai import analyse_productivity
from backend.utils.urban_intelligence import compute_urban_risk, analyse_route, predict_energy

logger = logging.getLogger(__name__)
intel_bp = Blueprint('intelligence', __name__)
db = DatabaseManager()
nowcaster = NowcastEngine()


def _svc():
    api_key = current_app.config.get('OPENWEATHER_API_KEY', '')
    return WeatherAPIService(api_key)


def _parse_location(args):
    """
    STRICT PRIORITY: Agar search bar mein city hai, toh coordinates ko 
    ignore karo taaki Satrikh ki jagah Delhi ka data aaye.
    """
    city = args.get('city', '').strip()
    # Check agar user ne koi real shehar search kiya hai
    is_manual = city and city.lower() not in ['', 'my location', 'your location', 'null']

    try:
        # Agar manual search hai, toh lat/lon ko raddi mein phenko (None kar do)
        lat = float(args['lat']) if ('lat' in args and not is_manual) else None
        lon = float(args['lon']) if ('lon' in args and not is_manual) else None
    except (ValueError, TypeError):
        lat, lon = None, None
        
    if not city and (lat is None or lon is None):
        city = 'Delhi'
    return city, lat, lon

def _get_weather(city: str = None, lat: float = None, lon: float = None) -> dict:
    svc = _svc()
    # Manual City ko pehli priority
    if city and city.lower() not in ['', 'my location', 'your location']:
        data = svc.get_current_weather(city)
        if data: return data
    
    # GPS ko dusri priority
    if lat is not None and lon is not None:
        return svc.get_weather_by_coords(lat, lon) or {}
        
    return svc.get_current_weather(city or 'Delhi') or {}


def _parse_profile(args) -> dict:
    raw_conds = args.get('conditions', '')
    conds = [c.strip() for c in raw_conds.split(',') if c.strip()] if raw_conds else []
    return {
        'age_group':  args.get('age_group', 'adult'),
        'conditions': conds,
        'name':       args.get('name', 'User'),
    }


# ─── Safety Radar ─────────────────────────────────────────────────────────────
@intel_bp.route('/api/intelligence/safety-radar')
def safety_radar():
    city, lat, lon = _parse_location(request.args)
    profile = _parse_profile(request.args)
    try:
        w = _get_weather(city, lat, lon)
        result = compute_all_risks(w, profile)
        result['city'] = w.get('city', city)
        result['weather'] = {k: w.get(k) for k in ('temperature','humidity','wind_speed','weather_main','rain_1h')}
        logger.info(f"Safety radar: city={result['city']} lat={lat} lon={lon}")
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        logger.error(f'Safety radar error: {e}', exc_info=True)
        return jsonify({'error': str(e)}), 500


# ─── Nowcasting ───────────────────────────────────────────────────────────────
@intel_bp.route('/api/intelligence/nowcast')
def nowcast():
    city, lat, lon = _parse_location(request.args)
    try:
        obs = db.get_observations(city or 'Delhi', limit=48)
        result = nowcaster.analyse(obs)
        w = _get_weather(city, lat, lon)
        result['current_weather'] = w
        result['anomaly_score']   = nowcaster.anomaly_score(obs)
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        logger.error(f'Nowcast error: {e}', exc_info=True)
        return jsonify({'error': str(e)}), 500


# ─── Productivity ─────────────────────────────────────────────────────────────
@intel_bp.route('/api/intelligence/productivity')
def productivity():
    city, lat, lon = _parse_location(request.args)
    profile = _parse_profile(request.args)
    try:
        w = _get_weather(city, lat, lon)
        result = analyse_productivity(w, profile)
        result['city']    = w.get('city', city)
        result['weather'] = {k: w.get(k) for k in ('temperature','humidity','weather_main','weather_description')}
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        logger.error(f'Productivity error: {e}', exc_info=True)
        return jsonify({'error': str(e)}), 500


# ─── Urban Risk ───────────────────────────────────────────────────────────────
@intel_bp.route('/api/intelligence/urban-risk')
def urban_risk():
    city, lat, lon = _parse_location(request.args)
    try:
        w = _get_weather(city, lat, lon)
        result = compute_urban_risk(w)
        result['city']    = w.get('city', city)
        result['weather'] = {k: w.get(k) for k in ('temperature','rain_1h','wind_speed','weather_main')}
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        logger.error(f'Urban risk error: {e}', exc_info=True)
        return jsonify({'error': str(e)}), 500


# ─── Route Planner (ORS-powered) ─────────────────────────────────────────────
@intel_bp.route('/api/intelligence/route')
def route_weather():
    origin = request.args.get('origin', '').strip()
    dest   = request.args.get('dest',   '').strip()
    if not origin or not dest:
        return jsonify({'error': 'origin and dest are required'}), 400
    try:
        svc = _svc()
        ors_key = current_app.config.get('OPENROUTESERVICE_KEY', '')
        from backend.utils.route_planner import build_route
        result = build_route(
            origin, dest,
            lambda la, lo: svc.get_weather_by_coords(la, lo) or {},
            ors_api_key=ors_key
        )
        logger.info(f"Route: {origin} → {dest} | {result.get('distance_km')} km")
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        logger.error(f'Route error: {e}', exc_info=True)
        return jsonify({'error': str(e)}), 500


# ─── Energy ───────────────────────────────────────────────────────────────────
@intel_bp.route('/api/intelligence/energy')
def energy():
    city, lat, lon = _parse_location(request.args)
    try:
        w = _get_weather(city, lat, lon)
        result = predict_energy(w)
        result['city']    = w.get('city', city)
        result['weather'] = {k: w.get(k) for k in ('temperature','humidity','weather_main')}
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        logger.error(f'Energy error: {e}', exc_info=True)
        return jsonify({'error': str(e)}), 500


# ─── Health Impact ────────────────────────────────────────────────────────────
@intel_bp.route('/api/intelligence/health-impact')
def health_impact():
    city, lat, lon = _parse_location(request.args)
    profile = _parse_profile(request.args)
    try:
        w = _get_weather(city, lat, lon)
        temp  = w.get('temperature', 25)
        hum   = w.get('humidity', 55)
        aqi   = (w.get('aqi_info') or {}).get('value', 2)
        cond  = w.get('weather_main', 'Clear')
        wind  = w.get('wind_speed', 10)
        rain  = w.get('rain_1h', 0)
        conditions = profile.get('conditions', [])

        def hi_score(base, mults):
            s = base
            for c in conditions:
                s *= mults.get(c, 1.0)
            return min(100, round(s))

        impacts = {
            'respiratory': {
                'score':  hi_score(aqi * 18, {'asthma': 2.0, 'copd': 2.2}),
                'icon': '🫁', 'title': 'Respiratory Health',
                'detail': f'AQI {aqi}, humidity {hum}% — {"High risk for asthma patients." if "asthma" in conditions else "Monitor air quality."}',
            },
            'cardiovascular': {
                'score':  hi_score(max(0, (temp - 25) * 2.5), {'heart_disease': 2.0, 'hypertension': 1.6}),
                'icon': '❤️', 'title': 'Cardiovascular',
                'detail': f'Heat stress: {temp}°C. {"High alert — monitor pulse." if "heart_disease" in conditions else "Stay cool and hydrated."}',
            },
            'dehydration': {
                'score':  hi_score(max(0, (temp - 20) * 3 + (hum - 50) * 0.3), {'diabetes': 1.4}),
                'icon': '💧', 'title': 'Dehydration Risk',
                'detail': f'{temp}°C with {hum}% humidity. {"Increased risk with diabetes." if "diabetes" in conditions else "Drink regularly."}',
            },
            'skin': {
                'score':  hi_score(max(0, 45 if hum < 30 else (30 if hum < 45 else 10)), {}),
                'icon': '🧴', 'title': 'Skin Dryness / UV',
                'detail': f'Humidity {hum}%. {"Very dry — apply moisturiser frequently." if hum < 35 else "Skin conditions manageable."}',
            },
            'mental': {
                'score':  hi_score(max(0, 40 if cond in ("Thunderstorm","Rain","Fog") else 10), {}),
                'icon': '🧠', 'title': 'Mental Wellbeing',
                'detail': f'{cond} weather can affect mood. {"Practice mindfulness." if cond in ("Thunderstorm","Rain","Fog") else "Good conditions for positive mood."}',
            },
            'injury': {
                'score':  hi_score(min(100, int(rain * 3 + (max(0, wind - 30) * 0.8))), {}),
                'icon': '🦴', 'title': 'Slip / Injury Risk',
                'detail': f'Rain {rain} mm, wind {wind} km/h. {"Slippery surfaces likely." if rain >= 3 else "Normal conditions."}',
            },
        }

        for k, v in impacts.items():
            v['level'] = 'Critical' if v['score'] >= 75 else ('High' if v['score'] >= 50 else ('Moderate' if v['score'] >= 25 else 'Low'))
            v['color'] = '#f43f5e' if v['score'] >= 75 else ('#f97316' if v['score'] >= 50 else ('#f59e0b' if v['score'] >= 25 else '#10b981'))

        overall = round(sum(v['score'] for v in impacts.values()) / len(impacts))

        return jsonify({'success': True, 'data': {
            'city': w.get('city', city), 'profile': profile,
            'impacts': impacts, 'overall_score': overall,
            'weather': {k: w.get(k) for k in ('temperature','humidity','weather_main','aqi_info')},
        }})
    except Exception as e:
        logger.error(f'Health impact error: {e}', exc_info=True)
        return jsonify({'error': str(e)}), 500


# ─── Community Reports ────────────────────────────────────────────────────────
@intel_bp.route('/api/intelligence/community-report', methods=['POST'])
def community_report():
    data = request.get_json() or {}
    city     = data.get('city', 'Delhi')
    obs_type = data.get('type', 'rain')
    severity = data.get('severity', 'moderate')
    note     = data.get('note', '')
    try:
        with db.get_connection() as conn:
            conn.execute('''
                INSERT OR IGNORE INTO community_reports (city, report_type, severity, note, reported_at)
                VALUES (?,?,?,?,?)
            ''', (city, obs_type, severity, note, datetime.utcnow().isoformat()))
        return jsonify({'success': True, 'message': 'Report submitted. Thank you!'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@intel_bp.route('/api/intelligence/community-reports')
def community_reports():
    city = request.args.get('city', 'Delhi')
    try:
        with db.get_connection() as conn:
            rows = conn.execute('''
                SELECT * FROM community_reports
                WHERE LOWER(city)=LOWER(?) ORDER BY reported_at DESC LIMIT 20
            ''', (city,)).fetchall()
        return jsonify({'success': True, 'reports': [dict(r) for r in rows]})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ─── AI Chat ──────────────────────────────────────────────────────────────────
@intel_bp.route('/api/intelligence/chat', methods=['POST'])
def ai_chat():
    data    = request.get_json() or {}
    message = data.get('message', '').lower()
    city, lat, lon = _parse_location(data)
    try:
        w    = _get_weather(city, lat, lon)
        temp = w.get('temperature', 25)
        cond = w.get('weather_main', 'Clear')
        hum  = w.get('humidity', 55)
        rain = w.get('rain_1h', 0)
        wind = w.get('wind_speed', 10)
        display_city = w.get('city', city or 'your location')
        reply = _chat_reply(message, display_city, temp, cond, hum, rain, wind, w)
        return jsonify({'success': True, 'reply': reply, 'city': display_city})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def _chat_reply(msg, city, temp, cond, hum, rain, wind, w):
    if any(x in msg for x in ['umbrella', 'rain', 'wet']):
        if rain > 0 or cond in ('Rain', 'Drizzle', 'Thunderstorm'):
            return f'Yes, carry an umbrella! It\'s currently {cond.lower()} in {city} with {rain} mm rain in the last hour. 🌧️'
        return f'No umbrella needed right now — it\'s {cond} in {city}. ☀️'
    if any(x in msg for x in ['jog', 'run', 'exercise', 'walk', 'outdoor']):
        if temp < 32 and cond in ('Clear', 'Clouds') and wind < 30:
            return f'Great conditions for outdoor exercise in {city}! {temp}°C, {cond.lower()}, wind {wind} km/h. 🏃'
        elif temp >= 36:
            return f'Too hot right now ({temp}°C in {city}). Try early morning or after 7pm. 🌡️'
        elif cond in ('Rain', 'Thunderstorm'):
            return f'Not ideal for outdoor exercise due to {cond.lower()}. Try indoor alternatives. 🏋️'
        return f'Conditions in {city} are acceptable — {temp}°C, {cond.lower()}. 👍'
    if any(x in msg for x in ['drive', 'travel', 'road']):
        if cond == 'Thunderstorm' or rain > 10 or wind > 60:
            return f'Travel caution for {city}! Severe weather: {cond}, rain {rain} mm/hr, wind {wind} km/h. ⚠️'
        return f'Roads manageable in {city} — {cond}, {temp}°C. Drive safely. 🚗'
    if any(x in msg for x in ['hot', 'heat', 'warm', 'temperature']):
        return f'Current temp in {city}: {temp}°C, feels like {round(temp+2)}°C with {hum}% humidity. {"Stay hydrated!" if temp > 32 else "Comfortable."} 🌡️'
    if any(x in msg for x in ['cold', 'cool', 'jacket']):
        if temp < 15:
            return f'Wear a jacket — it\'s {temp}°C in {city}! 🧥'
        return f'At {temp}°C in {city}, a light layer in the evening might help. 👕'
    if any(x in msg for x in ['aqi', 'air', 'pollution', 'mask']):
        aqi_val = (w.get('aqi_info') or {}).get('value', 2)
        aqi_labels = {1: 'Good', 2: 'Fair', 3: 'Moderate', 4: 'Poor', 5: 'Very Poor'}
        return f'Air quality in {city}: {aqi_labels.get(aqi_val, "Fair")} (Level {aqi_val}). {"Wear a mask!" if aqi_val >= 4 else "Safe for most people."} 🌿'
    return f'Current conditions in {city}: {cond}, {temp}°C, humidity {hum}%, wind {wind} km/h. Ask me anything about weather, travel, or safety! 🤖'


# ─── Hyperlocal ───────────────────────────────────────────────────────────────
@intel_bp.route('/api/intelligence/hyperlocal')
def hyperlocal_intel():
    try:
        lat = float(request.args.get('lat', 28.6139))
        lon = float(request.args.get('lon', 77.2090))
    except (ValueError, TypeError):
        return jsonify({'error': 'lat and lon must be valid numbers'}), 400
    try:
        svc  = _svc()
        data = svc.get_hyperlocal(lat, lon)
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ─── Rural / Agricultural Risk ────────────────────────────────────────────────
@intel_bp.route('/api/intelligence/rural-risk')
def rural_risk_api():
    city, lat, lon = _parse_location(request.args)
    crop = request.args.get('crop', 'general').strip()
    
    if request.args.get('city'):
        lat, lon = None, None 

    try:
        from backend.utils.rural_risk import compute_rural_risk
        svc  = _svc()
        w    = _get_weather(city, lat, lon)
        
        obs_city = w.get('city') or city or 'Unknown Location'
        
        # =====================================================================
        # 🌍 GLOBAL AUTO-SEEDER LOGIC START
        # =====================================================================
        try:
            obs = db.get_observations(obs_city, limit=72)
            
            if len(obs) < 5:
                from backend.utils.data_seeder import seed_city, CITY_CLIMATES
                logger.info(f"Generating dynamic 30-day history for new global location: {obs_city}")
                
                CITY_CLIMATES[obs_city] = {
                    'base_temp': w.get('temperature', 25), 
                    'temp_amplitude': 6, 'temp_noise': 2,
                    'base_hum': w.get('humidity', 60),  'hum_noise': 10,
                    'base_wind': w.get('wind_speed', 10), 'wind_noise': 5,
                    'base_pressure': w.get('pressure', 1010), 'pressure_noise': 5,
                    'country': w.get('country', 'Unknown'), 
                    'lat': w.get('latitude', lat or 0), 
                    'lon': w.get('longitude', lon or 0)
                }
                
                seed_city(db, obs_city, days=30)
                obs = db.get_observations(obs_city, limit=72)
                
        except Exception as e:
            logger.error(f"Global Seeder Error: {e}")
            obs = []
        # =====================================================================

        real_risk = compute_rural_risk(w, crop=crop, observations=obs)

        # 1. FIX FONT SIZES
        mapped_risks = {}
        
        r_mm = w.get('rain_1h', 0)
        mapped_risks['flood'] = mapped_risks['flood_risk'] = {
            'score': 'High' if r_mm > 15 else ('Mod' if r_mm > 5 else 'Low'),
            'detail': f"{r_mm} mm/hr rain",
            'color': '#f43f5e' if r_mm > 15 else ('#f59e0b' if r_mm > 5 else '#10b981')
        }

        d_data = real_risk['risks'].get('drought', {})
        is_insuf = 'Insufficient' in d_data.get('level', '')
        mapped_risks['drought'] = mapped_risks['drought_risk'] = {
            'score': 'N/A' if is_insuf else d_data.get('level', 'Mod').replace(' Drought', ''),
            'detail': 'Need more data' if is_insuf else f"SPI: {d_data.get('spi', 0)}",
            'color': '#94a3b8' if is_insuf else d_data.get('color', '#f59e0b')
        }

        f_data = real_risk['risks'].get('frost', {})
        mapped_risks['frost'] = mapped_risks['frost_risk'] = {
            'score': f_data.get('level', 'Safe'),
            'detail': f"{f_data.get('temp', '--')}°C",
            'color': f_data.get('color', '#10b981')
        }

        h_data = real_risk['risks'].get('livestock', {})
        mapped_risks['heat_stress'] = mapped_risks['heat'] = {
            'score': h_data.get('level', 'Safe'),
            'detail': f"THI: {h_data.get('thi', '--')}",
            'color': h_data.get('color', '#10b981')
        }

        # =====================================================================
        # 🗣️ HINDI TRANSLATOR FOR VOICE SYSTEM
        # =====================================================================
        def to_hindi(text):
            t = text.lower()
            if 'irrigation' in t and 'urgent' in t: return "सिंचाई की तुरंत आवश्यकता है, मिट्टी सूख रही है।"
            if 'irrigation' in t or 'water' in t: return "फसल को पानी देने का सही समय है।"
            if 'frost' in t: return "पाला पड़ने की संभावना है, कृपया अपनी फसल को ढकें।"
            if 'rain' in t: return "बारिश की संभावना है, कृपया खुले में रखी फसल को सुरक्षित करें।"
            if 'drought' in t: return "सूखे की स्थिति है, पानी का बचाव करें और खेत में नमी बनाए रखें।"
            if 'heat' in t: return "तापमान बहुत ज्यादा है, कृपया फसल और जानवरों को तेज धूप से बचाएं।"
            if 'pest' in t or 'fungal' in t: return "फसल में कीड़े या बीमारी लगने का खतरा है, कृपया दवा का छिड़काव करें।"
            if 'wind' in t: return "तेज हवाएं चल सकती हैं, लंबी फसलों का ध्यान रखें।"
            if 'stable' in t or 'favourable' in t: return "अभी खेती के लिए मौसम की स्थिति बहुत बढ़िया है।"
            return "अभी खेती के लिए मौसम की स्थिति सामान्य है।"

        # 2. FIX CROP UPDATES & ATTACH HINDI
        mapped_advisories = []
        c_risk = real_risk['risks'].get('crop_damage', {})
        p_risk = real_risk['risks'].get('pest', {})
        
        c_msg = c_risk.get('reasons', ['Stable conditions for this crop.'])[0]
        mapped_advisories.append({
            'icon': '🌾',
            'title': f"{crop.title()} Health",
            'message': c_msg,
            'hindi_msg': to_hindi(c_msg)
        })
        
        p_msg = p_risk.get('pests', ['No major pest threat right now.'])[0]
        mapped_advisories.append({
            'icon': '🐛',
            'title': f"Pest Risk ({crop.title()})",
            'message': p_msg,
            'hindi_msg': to_hindi(p_msg)
        })

        for adv in real_risk.get('farming_advisory', []):
            adv_text = adv.get('text', '')
            mapped_advisories.append({
                'icon': adv.get('icon', '⚠️'),
                'title': adv.get('type', 'Advisory'),
                'message': adv_text,
                'hindi_msg': to_hindi(adv_text)
            })

        final_data = {
            'city': obs_city,
            'overall_risk_label': real_risk.get('overall_level', 'Moderate'),
            'risks': mapped_risks,
            'advisories': mapped_advisories
        }
        
        return jsonify({'success': True, 'data': final_data})

    except Exception as e:
        logger.error(f'Rural risk error: {e}', exc_info=True)
        return jsonify({'success': True, 'data': {
            'city': city or 'Error', 'overall_risk_label': 'Error',
            'risks': {}, 'advisories': []
        }}), 200