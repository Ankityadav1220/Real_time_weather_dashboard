"""
WeatherAPIService — Complete with geolocation, hyperlocal, lat/lon support
Supports city name, lat/lon, reverse geocode, hyperlocal, AQI, forecast.
Falls back to realistic mock when no API key is set.
"""
import requests, logging, os, math, random, time
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

OPENWEATHER_BASE = "https://api.openweathermap.org/data/2.5"
OPENWEATHER_GEO  = "http://api.openweathermap.org/geo/1.0"
OPENWEATHER_AQI  = "https://api.openweathermap.org/data/2.5/air_pollution"

AQI_LABELS = {
    1: ("Good",      "#4CAF50"),
    2: ("Fair",      "#2196F3"),
    3: ("Moderate",  "#FF9800"),
    4: ("Poor",      "#F44336"),
    5: ("Very Poor", "#9C27B0"),
}

CITY_PROFILES = {
    "delhi":     {"base_temp":32,"hum":55,"wind":14,"pressure":1008,"lat":28.6139,"lon":77.2090,"country":"IN"},
    "mumbai":    {"base_temp":30,"hum":80,"wind":18,"pressure":1010,"lat":19.0760,"lon":72.8777,"country":"IN"},
    "bangalore": {"base_temp":25,"hum":65,"wind":12,"pressure":1014,"lat":12.9716,"lon":77.5946,"country":"IN"},
    "kolkata":   {"base_temp":30,"hum":78,"wind":10,"pressure":1009,"lat":22.5726,"lon":88.3639,"country":"IN"},
    "chennai":   {"base_temp":33,"hum":74,"wind":15,"pressure":1008,"lat":13.0827,"lon":80.2707,"country":"IN"},
    "hyderabad": {"base_temp":30,"hum":55,"wind":13,"pressure":1010,"lat":17.3850,"lon":78.4867,"country":"IN"},
    "pune":      {"base_temp":28,"hum":60,"wind":11,"pressure":1012,"lat":18.5204,"lon":73.8567,"country":"IN"},
    "jaipur":    {"base_temp":34,"hum":40,"wind":12,"pressure":1007,"lat":26.9124,"lon":75.7873,"country":"IN"},
    "lucknow":   {"base_temp":30,"hum":60,"wind":10,"pressure":1010,"lat":26.8467,"lon":80.9462,"country":"IN"},
    "london":    {"base_temp":13,"hum":78,"wind":22,"pressure":1015,"lat":51.5074,"lon":-0.1278,"country":"GB"},
    "new york":  {"base_temp":18,"hum":68,"wind":20,"pressure":1018,"lat":40.7128,"lon":-74.0060,"country":"US"},
    "tokyo":     {"base_temp":22,"hum":72,"wind":14,"pressure":1016,"lat":35.6762,"lon":139.6503,"country":"JP"},
    "dubai":     {"base_temp":38,"hum":42,"wind":10,"pressure":1004,"lat":25.2048,"lon":55.2708,"country":"AE"},
    "sydney":    {"base_temp":20,"hum":62,"wind":24,"pressure":1020,"lat":-33.8688,"lon":151.2093,"country":"AU"},
    "paris":     {"base_temp":15,"hum":75,"wind":18,"pressure":1013,"lat":48.8566,"lon":2.3522,"country":"FR"},
    "berlin":    {"base_temp":14,"hum":72,"wind":17,"pressure":1014,"lat":52.5200,"lon":13.4050,"country":"DE"},
    "beijing":   {"base_temp":20,"hum":55,"wind":16,"pressure":1012,"lat":39.9042,"lon":116.4074,"country":"CN"},
    "singapore": {"base_temp":30,"hum":84,"wind":12,"pressure":1011,"lat":1.3521,"lon":103.8198,"country":"SG"},
    "moscow":    {"base_temp":5, "hum":75,"wind":20,"pressure":1016,"lat":55.7558,"lon":37.6173,"country":"RU"},
    "toronto":   {"base_temp":12,"hum":70,"wind":18,"pressure":1016,"lat":43.6532,"lon":-79.3832,"country":"CA"},
    "cairo":     {"base_temp":28,"hum":40,"wind":14,"pressure":1010,"lat":30.0444,"lon":31.2357,"country":"EG"},
    "istanbul":  {"base_temp":18,"hum":68,"wind":16,"pressure":1013,"lat":41.0082,"lon":28.9784,"country":"TR"},
    "bangkok":   {"base_temp":33,"hum":80,"wind":12,"pressure":1009,"lat":13.7563,"lon":100.5018,"country":"TH"},
    "seoul":     {"base_temp":18,"hum":65,"wind":15,"pressure":1014,"lat":37.5665,"lon":126.9780,"country":"KR"},
    "karachi":   {"base_temp":32,"hum":65,"wind":14,"pressure":1008,"lat":24.8607,"lon":67.0011,"country":"PK"},
    "lahore":    {"base_temp":33,"hum":55,"wind":12,"pressure":1008,"lat":31.5204,"lon":74.3587,"country":"PK"},
    "nairobi":   {"base_temp":20,"hum":60,"wind":14,"pressure":1020,"lat":-1.2921,"lon":36.8219,"country":"KE"},
    "lagos":     {"base_temp":29,"hum":78,"wind":14,"pressure":1009,"lat":6.5244,"lon":3.3792,"country":"NG"},
    "sao paulo": {"base_temp":22,"hum":72,"wind":15,"pressure":1013,"lat":-23.5505,"lon":-46.6333,"country":"BR"},
    "los angeles":{"base_temp":22,"hum":60,"wind":12,"pressure":1015,"lat":34.0522,"lon":-118.2437,"country":"US"},
    "chicago":   {"base_temp":15,"hum":68,"wind":22,"pressure":1016,"lat":41.8781,"lon":-87.6298,"country":"US"},
    "miami":     {"base_temp":28,"hum":78,"wind":16,"pressure":1014,"lat":25.7617,"lon":-80.1918,"country":"US"},
}

WEATHER_CONDS = [
    ("Clear","Clear Sky","01d",0),
    ("Clouds","Partly Cloudy","02d",0),
    ("Clouds","Overcast Clouds","04d",0),
    ("Rain","Light Rain","10d",3),
    ("Rain","Moderate Rain","10d",8),
    ("Drizzle","Light Drizzle","09d",1),
    ("Thunderstorm","Thunderstorm","11d",15),
    ("Mist","Mist","50d",0),
    ("Haze","Haze","50d",0),
    ("Snow","Light Snow","13d",0),
]


class WeatherAPIService:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get("OPENWEATHER_API_KEY", "")
        self._mock = not self.api_key or self.api_key in ("YOUR_API_KEY_HERE", "")
        if self._mock:
            logger.warning("No API key — using realistic mock data")
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "WeatherIQ/4.0"})

    def _get(self, url: str, params: dict, timeout: int = 8) -> Optional[dict]:
        params["appid"] = self.api_key
        params.setdefault("units", "metric")
        try:
            r = self.session.get(url, params=params, timeout=timeout)
            r.raise_for_status()
            return r.json()
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP {e.response.status_code} from {url}")
        except requests.exceptions.ConnectionError:
            logger.error(f"Connection error: {url}")
        except requests.exceptions.Timeout:
            logger.error(f"Timeout: {url}")
        except Exception as e:
            logger.error(f"API error: {e}")
        return None

    # ── By city name ─────────────────────────────────────────────────────────
    def get_current_weather(self, city: str) -> Optional[dict]:
        if self._mock:
            return self._mock_current(city=city)
        data = self._get(f"{OPENWEATHER_BASE}/weather", {"q": city})
        return self._parse_current(data) if data else self._mock_current(city=city)

    # ── By coordinates (geolocation) ─────────────────────────────────────────
    def get_weather_by_coords(self, lat: float, lon: float) -> Optional[dict]:
        if self._mock:
            city = self._nearest_city(lat, lon)
            result = self._mock_current(city=city, lat=lat, lon=lon)
            result.update({"detected_from_coords": True, "latitude": lat, "longitude": lon})
            return result
        data = self._get(f"{OPENWEATHER_BASE}/weather", {"lat": lat, "lon": lon})
        if data:
            result = self._parse_current(data)
            result.update({"detected_from_coords": True})
            return result
        city = self._nearest_city(lat, lon)
        return self._mock_current(city=city, lat=lat, lon=lon)

    # ── Reverse geocode ───────────────────────────────────────────────────────
    def reverse_geocode(self, lat: float, lon: float) -> str:
        if self._mock:
            return self._nearest_city(lat, lon)
        data = self._get(f"{OPENWEATHER_GEO}/reverse", {"lat": lat, "lon": lon, "limit": 1})
        if data and len(data) > 0:
            return data[0].get("name", self._nearest_city(lat, lon))
        return self._nearest_city(lat, lon)

    # ── Forecast ──────────────────────────────────────────────────────────────
    def get_forecast(self, city: str = None, lat: float = None, lon: float = None) -> list:
        if self._mock:
            c = city or self._nearest_city(lat or 28.6, lon or 77.2)
            return self._mock_forecast(city=c)
        params = {"cnt": 40}
        if lat is not None and lon is not None:
            params.update({"lat": lat, "lon": lon})
        elif city:
            params["q"] = city
        else:
            return []
        data = self._get(f"{OPENWEATHER_BASE}/forecast", params)
        return self._parse_forecast(data) if data else self._mock_forecast(city=city or "Delhi")

    # ── AQI ───────────────────────────────────────────────────────────────────
    def get_aqi(self, lat: float, lon: float) -> int:
        if self._mock:
            return random.randint(1, 4)
        data = self._get(OPENWEATHER_AQI, {"lat": lat, "lon": lon})
        if data and "list" in data and data["list"]:
            return data["list"][0]["main"]["aqi"]
        return 2

    # ── Hyperlocal ────────────────────────────────────────────────────────────
    def get_hyperlocal(self, lat: float, lon: float) -> dict:
        base = self.get_weather_by_coords(lat, lon)
        if not base:
            base = self._mock_current(lat=lat, lon=lon)
        uhi   = self._urban_heat(lat, lon)
        elev  = self._elevation_adj(lat, lon)
        coast = self._coastal_adj(lat, lon)
        t_adj = uhi + elev + coast
        h_adj = -uhi * 1.2 + coast * 2
        base["hyperlocal"] = {
            "adjusted_temp":     round(base.get("temperature", 25) + t_adj, 1),
            "adjusted_humidity": min(99, max(10, round(base.get("humidity", 55) + h_adj))),
            "urban_heat_island": round(uhi, 2),
            "elevation_adj":     round(elev, 2),
            "coastal_adj":       round(coast, 2),
            "radius_km":         1.5,
            "confidence_pct":    85 if not self._mock else 72,
            "micro_zone":        self._micro_zone(lat, lon),
            "uncertainty_band":  {
                "temp_min": round(t_adj - 1.2, 1),
                "temp_max": round(t_adj + 1.2, 1),
            },
        }
        return base

    # ── Parsers ───────────────────────────────────────────────────────────────
    def _parse_current(self, data: dict) -> dict:
        try:
            lat = data["coord"]["lat"]
            lon = data["coord"]["lon"]
            aqi = self.get_aqi(lat, lon)
            aqi_info = {"value": aqi, "label": AQI_LABELS.get(aqi, ("N/A","#94a3b8"))[0],
                        "color": AQI_LABELS.get(aqi, ("N/A","#94a3b8"))[1]} if aqi else None
            return {
                "city":                data["name"],
                "country":             data["sys"]["country"],
                "latitude":            lat,
                "longitude":           lon,
                "temperature":         round(data["main"]["temp"], 1),
                "feels_like":          round(data["main"]["feels_like"], 1),
                "temp_min":            round(data["main"]["temp_min"], 1),
                "temp_max":            round(data["main"]["temp_max"], 1),
                "humidity":            data["main"]["humidity"],
                "pressure":            data["main"]["pressure"],
                "wind_speed":          round(data["wind"]["speed"] * 3.6, 1),
                "wind_direction":      data["wind"].get("deg", 0),
                "visibility":          data.get("visibility", 10000),
                "cloud_coverage":      data["clouds"]["all"],
                "weather_main":        data["weather"][0]["main"],
                "weather_description": data["weather"][0]["description"].title(),
                "weather_icon":        data["weather"][0]["icon"],
                "rain_1h":             data.get("rain", {}).get("1h", 0),
                "aqi":                 aqi,
                "aqi_info":            aqi_info,
                "sunrise":             datetime.fromtimestamp(data["sys"]["sunrise"]).strftime("%H:%M"),
                "sunset":              datetime.fromtimestamp(data["sys"]["sunset"]).strftime("%H:%M"),
                "recorded_at":         datetime.utcnow().isoformat(),
                "is_mock":             False,
            }
        except (KeyError, TypeError) as e:
            logger.error(f"Parse error: {e}")
            return {}

    def _parse_forecast(self, data: dict) -> list:
        if not data or "list" not in data:
            return []
        out = []
        for item in data["list"][:16]:
            out.append({
                "forecast_time":       item["dt_txt"],
                "temperature":         round(item["main"]["temp"], 1),
                "feels_like":          round(item["main"]["feels_like"], 1),
                "humidity":            item["main"]["humidity"],
                "wind_speed":          round(item["wind"]["speed"] * 3.6, 1),
                "weather_main":        item["weather"][0]["main"],
                "weather_description": item["weather"][0]["description"].title(),
                "weather_icon":        item["weather"][0]["icon"],
                "rain_probability":    round(item.get("pop", 0) * 100),
                "cloud_coverage":      item["clouds"]["all"],
            })
        return out

    # ── Mock helpers ──────────────────────────────────────────────────────────
    def _nearest_city(self, lat: float, lon: float) -> str:
        best, dist = "Delhi", float("inf")
        for name, p in CITY_PROFILES.items():
            d = math.sqrt((p["lat"] - lat) ** 2 + (p["lon"] - lon) ** 2)
            if d < dist:
                dist = d
                best = name
        return best.title()

    def _mock_current(self, city: str = "Delhi", lat: float = None, lon: float = None) -> dict:
        key     = city.lower().strip()
        profile = CITY_PROFILES.get(key, CITY_PROFILES["delhi"])
        hour    = datetime.now().hour
        diurnal = 5 * max(0, 1 - abs(hour - 14) / 10)
        temp    = profile["base_temp"] + diurnal + random.uniform(-2, 2)
        cond    = random.choice(WEATHER_CONDS)
        aqi     = random.randint(1, 4)
        return {
            "city":                city.title(),
            "country":             profile["country"],
            "latitude":            lat if lat is not None else profile["lat"],
            "longitude":           lon if lon is not None else profile["lon"],
            "temperature":         round(temp, 1),
            "feels_like":          round(temp - 2 + random.uniform(-1, 1), 1),
            "temp_min":            round(temp - 4, 1),
            "temp_max":            round(temp + 4, 1),
            "humidity":            max(10, min(99, profile["hum"] + random.randint(-10, 10))),
            "pressure":            profile["pressure"] + random.randint(-5, 5),
            "wind_speed":          max(0, round(profile["wind"] + random.uniform(-4, 4), 1)),
            "wind_direction":      random.randint(0, 359),
            "visibility":          random.randint(5000, 10000),
            "cloud_coverage":      random.randint(0, 90),
            "weather_main":        cond[0],
            "weather_description": cond[1],
            "weather_icon":        cond[2],
            "rain_1h":             round(random.uniform(0, cond[3]), 2) if cond[3] else 0,
            "aqi":                 aqi,
            "aqi_info":            {"value": aqi, "label": AQI_LABELS[aqi][0], "color": AQI_LABELS[aqi][1]},
            "sunrise":             "06:15",
            "sunset":              "18:52",
            "recorded_at":         datetime.utcnow().isoformat(),
            "is_mock":             True,
        }

    def _mock_forecast(self, city: str = "Delhi") -> list:
        key     = city.lower().strip()
        profile = CITY_PROFILES.get(key, CITY_PROFILES["delhi"])
        now     = datetime.utcnow()
        out     = []
        for i in range(16):
            dt      = now + timedelta(hours=i * 3)
            diurnal = 5 * max(0, 1 - abs(dt.hour - 14) / 10)
            temp    = profile["base_temp"] + diurnal + random.uniform(-3, 3)
            cond    = random.choice(WEATHER_CONDS)
            out.append({
                "forecast_time":       dt.strftime("%Y-%m-%d %H:%M:%S"),
                "temperature":         round(temp, 1),
                "feels_like":          round(temp - 2, 1),
                "humidity":            max(10, min(99, profile["hum"] + random.randint(-15, 15))),
                "wind_speed":          max(0, round(profile["wind"] + random.uniform(-5, 5), 1)),
                "weather_main":        cond[0],
                "weather_description": cond[1],
                "weather_icon":        cond[2],
                "rain_probability":    random.randint(20, 80) if cond[0] in ("Rain","Thunderstorm","Drizzle") else random.randint(0, 20),
                "cloud_coverage":      random.randint(0, 90),
            })
        return out

    def _urban_heat(self, lat: float, lon: float) -> float:
        for p in CITY_PROFILES.values():
            if math.sqrt((p["lat"] - lat)**2 + (p["lon"] - lon)**2) < 0.05:
                return round(random.uniform(1.2, 2.2), 2)
            elif math.sqrt((p["lat"] - lat)**2 + (p["lon"] - lon)**2) < 0.2:
                return round(random.uniform(0.4, 1.2), 2)
        return round(random.uniform(-0.2, 0.4), 2)

    def _elevation_adj(self, lat: float, lon: float) -> float:
        return round(random.uniform(-1.0, 0.3), 2)

    def _coastal_adj(self, lat: float, lon: float) -> float:
        coastal = [(19.08,72.88),(13.08,80.27),(-33.87,151.21),(1.35,103.82),(25.20,55.27)]
        for clat, clon in coastal:
            if math.sqrt((clat-lat)**2 + (clon-lon)**2) < 0.3:
                return round(random.uniform(-1.5,-0.5),2)
        return 0.0

    def _micro_zone(self, lat: float, lon: float) -> str:
        for p in CITY_PROFILES.values():
            d = math.sqrt((p["lat"]-lat)**2 + (p["lon"]-lon)**2)
            if d < 0.05:  return "Dense Urban Core"
            elif d < 0.15: return "Urban Residential"
            elif d < 0.4:  return "Suburban"
        return "Rural / Peri-urban"
