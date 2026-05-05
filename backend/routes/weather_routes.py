"""
Weather Routes — /api/current-weather, /api/forecast, /api/history,
                 /api/alerts, /api/geo-weather, /api/hyperlocal
Fixed: City search priority logic to prevent "Satrikh" coordinates from overriding city names.
"""
from flask import Blueprint, request, jsonify, current_app
import logging, time
from database.db_manager import DatabaseManager
from backend.utils.weather_api import WeatherAPIService
from backend.utils.alert_system import AlertSystem

logger    = logging.getLogger(__name__)
weather_bp = Blueprint('weather', __name__)
db         = DatabaseManager()
alert_sys  = AlertSystem()


def _svc():
    return WeatherAPIService(api_key=current_app.config.get('OPENWEATHER_API_KEY', ''))


def _log(endpoint, method, status, city=None, elapsed=None, error=None):
    try:
        db.log_request(endpoint, method, status, city, elapsed, error)
    except Exception:
        pass


# ─── Current Weather by city name ────────────────────────────────────────────
@weather_bp.route('/current-weather', methods=['GET'])
def current_weather():
    city = request.args.get('city', 'Delhi').strip()
    if not city:
        return jsonify({'error': 'city parameter required'}), 400
    t0 = time.time()
    try:
        svc  = _svc()
        data = svc.get_current_weather(city)
        if not data:
            return jsonify({'error': f'Could not fetch weather for {city}'}), 503

        # AQI
        if data.get('latitude') and data.get('longitude'):
            if not data.get('aqi'):
                aqi = svc.get_aqi(data['latitude'], data['longitude'])
                if aqi:
                    from backend.utils.weather_api import AQI_LABELS
                    data['aqi']      = aqi
                    data['aqi_info'] = {'value': aqi, 'label': AQI_LABELS.get(aqi,('N/A','#94a3b8'))[0],
                                        'color': AQI_LABELS.get(aqi,('N/A','#94a3b8'))[1]}

        alerts = alert_sys.check_alerts(data)
        data['alerts']                   = alerts
        data['activity_recommendations'] = alert_sys.get_activity_recommendations(data)
        data['uv_advice']               = alert_sys.get_uv_advice(
            data.get('temperature', 20), data.get('cloud_coverage', 0)
        )

        db.save_observation(data)
        for a in alerts:
            db.save_alert(city, a['type'], a['severity'], a['message'])

        _log('/api/current-weather', 'GET', 200, city, (time.time()-t0)*1000)
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        logger.error(f'/current-weather error: {e}', exc_info=True)
        _log('/api/current-weather', 'GET', 500, city, None, str(e))
        return jsonify({'error': 'Failed to fetch weather', 'detail': str(e)}), 500


# ─── Geolocation Weather (lat/lon from browser) ───────────────────────────────
@weather_bp.route('/geo-weather', methods=['GET'])
def geo_weather():
    try:
        lat = float(request.args.get('lat', 0))
        lon = float(request.args.get('lon', 0))
    except (ValueError, TypeError):
        return jsonify({'error': 'lat and lon must be valid numbers'}), 400

    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return jsonify({'error': 'lat/lon out of valid range'}), 400

    try:
        svc  = _svc()
        data = svc.get_weather_by_coords(lat, lon)
        if not data:
            return jsonify({'error': 'Could not fetch weather for these coordinates'}), 503

        alerts = alert_sys.check_alerts(data)
        data['alerts']                   = alerts
        data['activity_recommendations'] = alert_sys.get_activity_recommendations(data)
        data['detected_lat']             = lat
        data['detected_lon']             = lon

        db.save_observation(data)
        return jsonify({'success': True, 'data': data, 'city': data.get('city', 'Your Location')})
    except Exception as e:
        logger.error(f'/geo-weather error: {e}', exc_info=True)
        return jsonify({'error': str(e)}), 500


# ─── Hyperlocal Weather ───────────────────────────────────────────────────────
@weather_bp.route('/hyperlocal', methods=['GET'])
def hyperlocal():
    try:
        lat = float(request.args.get('lat', 28.6139))
        lon = float(request.args.get('lon', 77.2090))
    except (ValueError, TypeError):
        return jsonify({'error': 'lat and lon must be valid numbers'}), 400

    try:
        svc    = _svc()
        data   = svc.get_hyperlocal(lat, lon)
        alerts = alert_sys.check_alerts(data)
        data['alerts'] = alerts
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        logger.error(f'/hyperlocal error: {e}', exc_info=True)
        return jsonify({'error': str(e)}), 500


# ─── Forecast (FIXED FOR CITY PRIORITY) ───────────────────────────────────────
@weather_bp.route('/forecast', methods=['GET'])
def forecast():
    city = request.args.get('city', '').strip()
    
    # 🎯 PRIORITY LOGIC: Agar city typed hai, toh GPS coordinates ko ignore karein
    is_manual = city and city.lower() not in ['', 'my location', 'your location']

    try:
        # Agar manual city hai, toh lat/lon ko bypass (None) kar do
        lat = float(request.args.get('lat')) if (request.args.get('lat') and not is_manual) else None
        lon = float(request.args.get('lon')) if (request.args.get('lon') and not is_manual) else None
    except (ValueError, TypeError):
        lat = lon = None

    if not city and (lat is None or lon is None):
        city = 'Delhi'

    try:
        svc       = _svc()
        # API call with priority aware parameters
        forecasts = svc.get_forecast(city=city or None, lat=lat, lon=lon)
        
        if not forecasts:
            return jsonify({'error': 'Could not fetch forecast'}), 503
        
        # Save to DB if city name resolved
        resolved_city = city or (forecasts.get('city', {}).get('name') if isinstance(forecasts, dict) else city)
        if resolved_city:
            db.save_forecasts(resolved_city, forecasts)
        
        _log('/api/forecast', 'GET', 200, resolved_city)
        
        # frontend format compatibility fix
        return jsonify({
            'success': True, 
            'city': resolved_city or f'{lat},{lon}',
            'data': forecasts # Ye forecasts poora object hona chahiye jisme 'list' ya 'hourly' ho
        })
    except Exception as e:
        logger.error(f'/forecast error: {e}', exc_info=True)
        return jsonify({'error': str(e)}), 500


# ─── History ──────────────────────────────────────────────────────────────────
@weather_bp.route('/history', methods=['GET'])
def history():
    city  = request.args.get('city', 'Delhi').strip()
    limit = min(int(request.args.get('limit', 48)), 200)
    try:
        records = db.get_observations(city, limit=limit)
        return jsonify({'success': True, 'city': city, 'count': len(records), 'data': records})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ─── Alerts ───────────────────────────────────────────────────────────────────
@weather_bp.route('/alerts', methods=['GET'])
def alerts():
    city = request.args.get('city', 'Delhi').strip()
    try:
        active = db.get_alerts(city, limit=10)
        if not active:
            active = []
        return jsonify({'success': True, 'city': city, 'alerts': active}), 200
    except Exception as e:
        logger.error(f"/alerts error: {e}")
        return jsonify({'success': False, 'error': str(e), 'alerts': []}), 500