"""
Main Page Routes — no auth, global location state
"""
from flask import Blueprint, render_template, request, jsonify, current_app
import logging

logger = logging.getLogger(__name__)
main_bp = Blueprint('main', __name__)


CITY_LIST = [
    'Delhi', 'Mumbai', 'Bangalore', 'Bengaluru', 'Chennai', 'Kolkata', 'Hyderabad',
    'Pune', 'Ahmedabad', 'Jaipur', 'Lucknow', 'Kanpur', 'Surat', 'Nagpur',
    'Varanasi', 'Agra', 'Patna', 'Bhopal', 'Amritsar', 'Kochi', 'Goa',
    'London', 'Manchester', 'Birmingham', 'Edinburgh', 'Glasgow',
    'New York', 'Los Angeles', 'Chicago', 'Houston', 'Phoenix', 'Dallas',
    'San Francisco', 'Miami', 'Seattle', 'Boston', 'Las Vegas',
    'Tokyo', 'Osaka', 'Dubai', 'Abu Dhabi',
    'Sydney', 'Melbourne', 'Brisbane', 'Perth',
    'Paris', 'Berlin', 'Madrid', 'Rome', 'Amsterdam', 'Vienna',
    'Stockholm', 'Oslo', 'Copenhagen', 'Prague', 'Warsaw', 'Budapest',
    'Singapore', 'Bangkok', 'Kuala Lumpur', 'Jakarta', 'Manila',
    'Beijing', 'Shanghai', 'Guangzhou', 'Hong Kong',
    'Toronto', 'Vancouver', 'Montreal',
    'São Paulo', 'Rio de Janeiro', 'Buenos Aires',
    'Cairo', 'Lagos', 'Nairobi', 'Cape Town', 'Johannesburg',
    'Moscow', 'Istanbul', 'Seoul', 'Karachi', 'Dhaka', 'Kathmandu',
]


@main_bp.route('/')
def dashboard():
    return render_template('index.html', page='dashboard')


@main_bp.route('/forecast')
def forecast():
    return render_template('forecast.html', page='forecast')


@main_bp.route('/alerts')
def alerts():
    return render_template('alerts.html', page='alerts')


@main_bp.route('/cities')
def cities():
    return render_template('cities.html', page='cities')


@main_bp.route('/ml-models')
def ml_models():
    return render_template('ml_models.html', page='ml')


@main_bp.route('/safety-radar')
def safety_radar():
    return render_template('safety_radar.html', page='safety')


@main_bp.route('/nowcasting')
def nowcasting():
    return render_template('nowcasting.html', page='nowcast')


@main_bp.route('/productivity')
def productivity():
    return render_template('productivity.html', page='productivity')


@main_bp.route('/urban-risk')
def urban_risk():
    return render_template('urban_risk.html', page='urban')


@main_bp.route('/route-planner')
def route_planner():
    return render_template('route_planner.html', page='route')


@main_bp.route('/energy')
def energy():
    return render_template('energy.html', page='energy')


@main_bp.route('/health-impact')
def health_impact():
    return render_template('health_impact.html', page='health')


@main_bp.route('/community')
def community():
    return render_template('community.html', page='community')


@main_bp.route('/ai-assistant')
def ai_assistant():
    return render_template('ai_assistant.html', page='assistant')


@main_bp.route('/rural-risk')
def rural_risk():
    return render_template('rural_risk.html', page='rural')


@main_bp.route('/hyperlocal')
def hyperlocal_page():
    return render_template('hyperlocal.html', page='hyperlocal')


# ─── Autocomplete ─────────────────────────────────────────────────────────────
@main_bp.route('/api/autocomplete')
def autocomplete():
    q = request.args.get('q', '').strip().lower()
    if len(q) < 1:
        return jsonify([])
    matches = [c for c in CITY_LIST if q in c.lower()][:10]
    return jsonify(matches)


# ─── Geo-weather: lat/lon → weather + city name ───────────────────────────────
@main_bp.route('/api/geo-weather')
def geo_weather():
    """
    GET /api/geo-weather?lat=28.61&lon=77.21
    Returns weather + resolved city name for browser geolocation.
    """
    try:
        lat = float(request.args.get('lat', 0))
        lon = float(request.args.get('lon', 0))
    except (ValueError, TypeError):
        return jsonify({'error': 'lat and lon must be numbers'}), 400

    if lat == 0 and lon == 0:
        return jsonify({'error': 'lat and lon required'}), 400

    try:
        api_key = current_app.config.get('OPENWEATHER_API_KEY', '')
        from backend.utils.weather_api import WeatherAPIService
        svc = WeatherAPIService(api_key)

        # Get weather by coordinates
        data = svc.get_weather_by_coords(lat, lon)
        if not data:
            data = {}

        # Reverse geocode to get proper display name
        city_name = svc.reverse_geocode(lat, lon)
        display_name = data.get('city', city_name)

        logger.info(f"Geo-weather: ({lat},{lon}) → {display_name}")

        return jsonify({
            'success': True,
            'city': display_name,
            'lat': lat,
            'lon': lon,
            'data': data
        })
    except Exception as e:
        logger.error(f"geo-weather error: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500
