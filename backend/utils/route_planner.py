"""
Route Planner — OpenRouteService (ORS) + Great-Circle fallback
Uses real road routing when ORS API key is provided.
Falls back to great-circle interpolation otherwise.
"""
import math
import logging
import requests
import json
from typing import Optional, Callable

logger = logging.getLogger(__name__)

ORS_BASE = "https://api.openrouteservice.org"

# Comprehensive city coordinates database
WORLD_CITIES = {
    "delhi": (28.6139, 77.2090, "IN"), "new delhi": (28.6139, 77.2090, "IN"),
    "mumbai": (19.0760, 72.8777, "IN"), "bangalore": (12.9716, 77.5946, "IN"),
    "bengaluru": (12.9716, 77.5946, "IN"), "hyderabad": (17.3850, 78.4867, "IN"),
    "chennai": (13.0827, 80.2707, "IN"), "kolkata": (22.5726, 88.3639, "IN"),
    "pune": (18.5204, 73.8567, "IN"), "ahmedabad": (23.0225, 72.5714, "IN"),
    "jaipur": (26.9124, 75.7873, "IN"), "lucknow": (26.8467, 80.9462, "IN"),
    "surat": (21.1702, 72.8311, "IN"), "kanpur": (26.4499, 80.3319, "IN"),
    "nagpur": (21.1458, 79.0882, "IN"), "patna": (25.5941, 85.1376, "IN"),
    "bhopal": (23.2599, 77.4126, "IN"), "agra": (27.1767, 78.0081, "IN"),
    "varanasi": (25.3176, 82.9739, "IN"), "amritsar": (31.6340, 74.8723, "IN"),
    "goa": (15.2993, 74.1240, "IN"), "kochi": (9.9312, 76.2673, "IN"),
    "indore": (22.7196, 75.8577, "IN"), "bhubaneswar": (20.2961, 85.8245, "IN"),
    "coimbatore": (11.0168, 76.9558, "IN"), "chandigarh": (30.7333, 76.7794, "IN"),
    "visakhapatnam": (17.6868, 83.2185, "IN"), "guwahati": (26.1445, 91.7362, "IN"),
    "satrikh": (26.8867, 81.0167, "IN"),  # small town support
    # USA
    "new york": (40.7128, -74.0060, "US"), "los angeles": (34.0522, -118.2437, "US"),
    "chicago": (41.8781, -87.6298, "US"), "houston": (29.7604, -95.3698, "US"),
    "phoenix": (33.4484, -112.0740, "US"), "san francisco": (37.7749, -122.4194, "US"),
    "miami": (25.7617, -80.1918, "US"), "seattle": (47.6062, -122.3321, "US"),
    "dallas": (32.7767, -96.7970, "US"), "boston": (42.3601, -71.0589, "US"),
    "las vegas": (36.1699, -115.1398, "US"), "washington": (38.9072, -77.0369, "US"),
    # UK & Europe
    "london": (51.5074, -0.1278, "GB"), "manchester": (53.4808, -2.2426, "GB"),
    "birmingham": (52.4862, -1.8904, "GB"), "glasgow": (55.8642, -4.2518, "GB"),
    "edinburgh": (55.9533, -3.1883, "GB"), "paris": (48.8566, 2.3522, "FR"),
    "berlin": (52.5200, 13.4050, "DE"), "madrid": (40.4168, -3.7038, "ES"),
    "rome": (41.9028, 12.4964, "IT"), "amsterdam": (52.3676, 4.9041, "NL"),
    "vienna": (48.2082, 16.3738, "AT"), "zurich": (47.3769, 8.5417, "CH"),
    "stockholm": (59.3293, 18.0686, "SE"), "oslo": (59.9139, 10.7522, "NO"),
    "copenhagen": (55.6761, 12.5683, "DK"), "prague": (50.0755, 14.4378, "CZ"),
    "warsaw": (52.2297, 21.0122, "PL"), "budapest": (47.4979, 19.0402, "HU"),
    "barcelona": (41.3851, 2.1734, "ES"), "munich": (48.1351, 11.5820, "DE"),
    "milan": (45.4654, 9.1859, "IT"), "frankfurt": (50.1109, 8.6821, "DE"),
    "lisbon": (38.7169, -9.1395, "PT"),
    # Asia
    "tokyo": (35.6762, 139.6503, "JP"), "osaka": (34.6937, 135.5023, "JP"),
    "beijing": (39.9042, 116.4074, "CN"), "shanghai": (31.2304, 121.4737, "CN"),
    "hong kong": (22.3193, 114.1694, "HK"), "seoul": (37.5665, 126.9780, "KR"),
    "singapore": (1.3521, 103.8198, "SG"), "bangkok": (13.7563, 100.5018, "TH"),
    "kuala lumpur": (3.1390, 101.6869, "MY"), "jakarta": (-6.2088, 106.8456, "ID"),
    "manila": (14.5995, 120.9842, "PH"), "dubai": (25.2048, 55.2708, "AE"),
    "abu dhabi": (24.4539, 54.3773, "AE"), "riyadh": (24.7136, 46.6753, "SA"),
    "istanbul": (41.0082, 28.9784, "TR"), "karachi": (24.8607, 67.0011, "PK"),
    "lahore": (31.5204, 74.3587, "PK"), "dhaka": (23.8103, 90.4125, "BD"),
    "kathmandu": (27.7172, 85.3240, "NP"), "colombo": (6.9271, 79.8612, "LK"),
    # Middle East & Africa
    "cairo": (30.0444, 31.2357, "EG"), "nairobi": (-1.2921, 36.8219, "KE"),
    "lagos": (6.5244, 3.3792, "NG"), "johannesburg": (-26.2041, 28.0473, "ZA"),
    "cape town": (-33.9249, 18.4241, "ZA"), "tel aviv": (32.0853, 34.7818, "IL"),
    # Americas
    "toronto": (43.6532, -79.3832, "CA"), "vancouver": (49.2827, -123.1207, "CA"),
    "montreal": (45.5017, -73.5673, "CA"), "mexico city": (19.4326, -99.1332, "MX"),
    "sao paulo": (-23.5505, -46.6333, "BR"), "rio de janeiro": (-22.9068, -43.1729, "BR"),
    "buenos aires": (-34.6037, -58.3816, "AR"), "lima": (-12.0464, -77.0428, "PE"),
    # Oceania
    "sydney": (-33.8688, 151.2093, "AU"), "melbourne": (-37.8136, 144.9631, "AU"),
    "brisbane": (-27.4698, 153.0251, "AU"), "perth": (-31.9505, 115.8605, "AU"),
    "auckland": (-36.8509, 174.7645, "NZ"),
    # Russia
    "moscow": (55.7558, 37.6173, "RU"), "saint petersburg": (59.9311, 30.3609, "RU"),
}


def haversine(lat1, lon1, lat2, lon2) -> float:
    """Great-circle distance in km."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def resolve_location(name: str):
    """Resolve city name → (lat, lon, country) or None."""
    key = name.lower().strip()
    if key in WORLD_CITIES:
        return WORLD_CITIES[key]
    for city_key, coords in WORLD_CITIES.items():
        if key in city_key or city_key in key:
            return coords
    return None


def _ors_geocode(name: str, api_key: str):
    """Geocode a city name using ORS Geocoding API."""
    try:
        url = f"{ORS_BASE}/geocode/search"
        r = requests.get(url, params={
            "api_key": api_key,
            "text": name,
            "size": 1
        }, timeout=8)
        r.raise_for_status()
        features = r.json().get("features", [])
        if features:
            coords = features[0]["geometry"]["coordinates"]  # [lon, lat]
            return coords[1], coords[0]  # lat, lon
    except Exception as e:
        logger.warning(f"ORS geocode failed for '{name}': {e}")
    return None


def _ors_route(olat, olon, dlat, dlon, api_key: str):
    """
    Fetch real road route from ORS Directions API.
    Returns list of (lat, lon) waypoints + distance_km + duration_sec, or None on failure.
    """
    try:
        url = f"{ORS_BASE}/v2/directions/driving-car"
        headers = {
            "Authorization": api_key,
            "Content-Type": "application/json"
        }
        body = {
            "coordinates": [[olon, olat], [dlon, dlat]],
            "instructions": False,
            "geometry": True
        }
        r = requests.post(url, json=body, headers=headers, timeout=15)
        r.raise_for_status()
        data = r.json()

        routes = data.get("routes", [])
        if not routes:
            return None

        route = routes[0]
        summary = route.get("summary", {})
        distance_m = summary.get("distance", 0)
        duration_s = summary.get("duration", 0)

        # Decode geometry (encoded polyline or GeoJSON)
        geometry = route.get("geometry")
        if isinstance(geometry, str):
            # Encoded polyline
            coords = _decode_polyline(geometry)
        elif isinstance(geometry, dict):
            # GeoJSON
            raw = geometry.get("coordinates", [])
            coords = [(c[1], c[0]) for c in raw]  # [lon,lat] → (lat,lon)
        else:
            return None

        return {
            "waypoints": coords,
            "distance_km": round(distance_m / 1000, 1),
            "duration_sec": round(duration_s),
            "source": "ors_real"
        }
    except requests.exceptions.HTTPError as e:
        logger.warning(f"ORS route HTTP error: {e.response.status_code} — {e.response.text[:200]}")
    except Exception as e:
        logger.warning(f"ORS route failed: {e}")
    return None


def _decode_polyline(encoded: str):
    """Decode Google/ORS encoded polyline to list of (lat, lon)."""
    coords = []
    index, lat, lng = 0, 0, 0
    while index < len(encoded):
        shift, result = 0, 0
        while True:
            b = ord(encoded[index]) - 63
            index += 1
            result |= (b & 0x1f) << shift
            shift += 5
            if b < 0x20:
                break
        dlat = ~(result >> 1) if result & 1 else result >> 1
        lat += dlat
        shift, result = 0, 0
        while True:
            b = ord(encoded[index]) - 63
            index += 1
            result |= (b & 0x1f) << shift
            shift += 5
            if b < 0x20:
                break
        dlng = ~(result >> 1) if result & 1 else result >> 1
        lng += dlng
        coords.append((lat / 1e5, lng / 1e5))
    return coords


def _sample_waypoints(coords, n=8):
    """Sample n evenly-spaced waypoints from a list of coords."""
    if len(coords) <= n:
        return coords
    step = (len(coords) - 1) / (n - 1)
    return [coords[round(i * step)] for i in range(n)]


def _great_circle_waypoints(olat, olon, dlat, dlon, n=8):
    """SLERP great-circle interpolation for fallback."""
    if n < 2:
        return [(olat, olon), (dlat, dlon)]
    la1, lo1 = math.radians(olat), math.radians(olon)
    la2, lo2 = math.radians(dlat), math.radians(dlon)
    v1 = (math.cos(la1)*math.cos(lo1), math.cos(la1)*math.sin(lo1), math.sin(la1))
    v2 = (math.cos(la2)*math.cos(lo2), math.cos(la2)*math.sin(lo2), math.sin(la2))
    dot = max(-1.0, min(1.0, sum(a*b for a, b in zip(v1, v2))))
    omega = math.acos(dot)
    if abs(omega) < 1e-10:
        return [(olat, olon)] * n
    points = []
    for i in range(n):
        t = i / (n - 1)
        s0 = math.sin((1-t)*omega) / math.sin(omega) if abs(math.sin(omega)) > 1e-10 else 1
        s1 = math.sin(t*omega) / math.sin(omega) if abs(math.sin(omega)) > 1e-10 else 0
        vt = (s0*v1[0]+s1*v2[0], s0*v1[1]+s1*v2[1], s0*v1[2]+s1*v2[2])
        mag = math.sqrt(sum(c**2 for c in vt))
        if mag > 1e-10:
            vt = tuple(c/mag for c in vt)
        plat = math.degrees(math.asin(max(-1.0, min(1.0, vt[2]))))
        plon = math.degrees(math.atan2(vt[1], vt[0]))
        points.append((round(plat, 4), round(plon, 4)))
    return points


def build_route(origin: str, dest: str, weather_func: Callable,
                ors_api_key: str = '') -> dict:
    """
    Build a weather-aware route.
    Tries ORS real routing first; falls back to great-circle.
    weather_func(lat, lon) → weather dict
    """
    # ── Resolve coordinates ──
    o_coords = resolve_location(origin)
    d_coords = resolve_location(dest)

    ors_available = bool(ors_api_key and ors_api_key not in ('', 'YOUR_ORS_KEY_HERE'))

    # Try ORS geocoding for unknown cities
    if not o_coords and ors_available:
        gc = _ors_geocode(origin, ors_api_key)
        if gc:
            o_coords = (gc[0], gc[1], 'XX')
            logger.info(f"ORS geocoded origin '{origin}' → {gc}")

    if not d_coords and ors_available:
        gc = _ors_geocode(dest, ors_api_key)
        if gc:
            d_coords = (gc[0], gc[1], 'XX')
            logger.info(f"ORS geocoded dest '{dest}' → {gc}")

    # Hard fallback
    if not o_coords:
        logger.warning(f"Unknown origin: '{origin}', using Delhi")
        o_coords = (28.6139, 77.2090, "IN")
    if not d_coords:
        logger.warning(f"Unknown dest: '{dest}', using Mumbai")
        d_coords = (19.0760, 72.8777, "IN")

    olat, olon = o_coords[0], o_coords[1]
    dlat, dlon = d_coords[0], d_coords[1]

    # ── Try real ORS routing ──
    route_data = None
    route_source = "great_circle"

    if ors_available:
        route_data = _ors_route(olat, olon, dlat, dlon, ors_api_key)

    if route_data:
        all_waypoints = route_data["waypoints"]
        sampled = _sample_waypoints(all_waypoints, n=8)
        total_dist = route_data["distance_km"]
        duration_sec = route_data["duration_sec"]
        route_source = "ors_real"
        # Build polyline for map display (up to 50 points)
        display_polyline = _sample_waypoints(all_waypoints, n=min(50, len(all_waypoints)))
        logger.info(f"ORS route: {origin}→{dest} | {total_dist} km | {len(all_waypoints)} pts")
    else:
        # Fallback: great-circle
        sampled = _great_circle_waypoints(olat, olon, dlat, dlon, n=8)
        total_dist = round(haversine(olat, olon, dlat, dlon))
        duration_sec = int(total_dist / 80 * 3600)  # estimate at 80 km/h
        display_polyline = sampled
        if ors_available:
            logger.warning(f"ORS failed for {origin}→{dest}, using great-circle fallback")
        else:
            logger.info(f"No ORS key — using great-circle for {origin}→{dest}")

    # ── Fetch weather at each sampled waypoint ──
    segments = []
    worst_risk = 0
    risk_points = []

    for i, (lat, lon) in enumerate(sampled):
        try:
            w = weather_func(lat, lon)
        except Exception as e:
            logger.error(f"Weather fetch failed at waypoint {i}: {e}")
            w = {}

        risk = _compute_risk(w)
        dist_from_origin = haversine(olat, olon, lat, lon)

        seg = {
            'index':        i,
            'lat':          lat,
            'lon':          lon,
            'label':        'Origin' if i == 0 else ('Destination' if i == len(sampled)-1 else f'WP {i}'),
            'distance_km':  round(dist_from_origin),
            'temperature':  w.get('temperature', '--'),
            'humidity':     w.get('humidity', '--'),
            'wind_speed':   w.get('wind_speed', '--'),
            'rain_1h':      w.get('rain_1h', 0),
            'visibility':   w.get('visibility', 10000),
            'weather_main': w.get('weather_main', 'Clear'),
            'weather_desc': w.get('weather_description', 'Clear'),
            'risk':         risk,
            'risk_label':   _risk_label(risk),
            'risk_color':   _risk_color(risk),
        }
        if risk > worst_risk:
            worst_risk = risk
        if risk >= 50:
            risk_points.append(f"WP {i} ({round(dist_from_origin)} km)")
        segments.append(seg)

    avg_speed = _avg_speed(worst_risk)
    eta_hours = round(total_dist / avg_speed, 1)
    delay_hours = round((worst_risk / 100) * eta_hours * 0.4, 1)

    return {
        'origin':             origin.title(),
        'destination':        dest.title(),
        'origin_coords':      {'lat': olat, 'lon': olon},
        'dest_coords':        {'lat': dlat, 'lon': dlon},
        'distance_km':        round(total_dist),
        'eta_hours':          eta_hours,
        'avg_speed_kmh':      avg_speed,
        'weather_delay_hr':   delay_hours,
        'segments':           segments,
        'polyline':           display_polyline,
        'route_source':       route_source,
        'worst_risk':         worst_risk,
        'risk_label':         _risk_label(worst_risk),
        'risk_color':         _risk_color(worst_risk),
        'risk_points':        risk_points,
        'recommendation':     _recommendation(worst_risk, delay_hours, origin, dest),
        'transport_modes':    _transport_advice(worst_risk, total_dist),
    }


def _compute_risk(w: dict) -> int:
    score = 0
    vis   = w.get('visibility', 10000)
    wind  = w.get('wind_speed', 0)
    rain  = w.get('rain_1h', 0)
    cond  = w.get('weather_main', 'Clear')
    if vis < 500:    score += 40
    elif vis < 1000: score += 25
    elif vis < 3000: score += 10
    if wind >= 80:   score += 35
    elif wind >= 60: score += 22
    elif wind >= 40: score += 12
    if rain >= 20:   score += 30
    elif rain >= 10: score += 20
    elif rain >= 3:  score += 10
    if cond == 'Thunderstorm':      score += 25
    elif cond == 'Snow':            score += 20
    elif cond in ('Fog', 'Mist'):   score += 15
    return min(100, score)


def _risk_label(s):
    if s >= 70: return 'Dangerous'
    if s >= 50: return 'High Risk'
    if s >= 30: return 'Caution'
    if s >= 10: return 'Low Risk'
    return 'Clear'


def _risk_color(s):
    if s >= 70: return '#f43f5e'
    if s >= 50: return '#f97316'
    if s >= 30: return '#f59e0b'
    if s >= 10: return '#06b6d4'
    return '#10b981'


def _avg_speed(risk):
    if risk >= 70: return 40
    if risk >= 50: return 60
    if risk >= 30: return 75
    return 90


def _recommendation(risk, delay, origin, dest):
    if risk >= 70:
        return f"⛔ HIGH DANGER: Severe weather along {origin}→{dest}. Strongly recommend delaying. Delay est: +{delay}h."
    if risk >= 50:
        return f"⚠️ CAUTION: Significant weather on {origin}→{dest}. Reduce speed in hazardous sections. Allow +{delay}h."
    if risk >= 30:
        return f"🟡 MODERATE RISK: Some weather concerns. Drive carefully. Minor delay possible: +{delay}h."
    return f"✅ ROUTE CLEAR: Weather along {origin}→{dest} is favourable. Safe travels!"


def _transport_advice(risk, dist_km):
    modes = []
    if dist_km < 500:
        modes.append({'mode': '🚗 Car', 'recommended': risk < 50, 'note': 'Suitable for moderate risk or below'})
    if dist_km < 1500:
        modes.append({'mode': '🚂 Train', 'recommended': True, 'note': 'More weather-resilient than road travel'})
    if dist_km > 500:
        modes.append({'mode': '✈️ Flight', 'recommended': risk >= 50, 'note': 'Recommended for long routes in poor weather'})
    if dist_km < 200:
        modes.append({'mode': '🏍️ Motorcycle', 'recommended': risk < 20, 'note': 'Only for clear conditions'})
    return modes
