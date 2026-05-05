"""
Weather Alert System
Generates alerts for extreme weather conditions.
Supports: Heatwave, Freeze, Heavy Rain, Storm, Fog, High Wind, Poor AQI
"""

import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

# ─── Alert Thresholds ────────────────────────────────────────────────────────

ALERT_RULES = {
    'heatwave': {
        'condition': lambda d: d.get('temperature', 0) >= 40,
        'severity': 'danger',
        'title': '🌡️ Extreme Heat Warning',
        'message': 'Temperature exceeds 40°C. Stay hydrated, avoid outdoor activities.',
        'icon': '🔥'
    },
    'high_temp': {
        'condition': lambda d: 35 <= d.get('temperature', 0) < 40,
        'severity': 'warning',
        'title': '⚠️ High Temperature Advisory',
        'message': 'Temperature is very high. Limit outdoor exposure and stay cool.',
        'icon': '🌤️'
    },
    'freeze': {
        'condition': lambda d: d.get('temperature', 99) <= 0,
        'severity': 'warning',
        'title': '🥶 Freeze Warning',
        'message': 'Temperature at or below freezing. Risk of ice and frost.',
        'icon': '❄️'
    },
    'heavy_rain': {
        'condition': lambda d: d.get('rain_1h', 0) >= 10 or d.get('weather_main', '') == 'Thunderstorm',
        'severity': 'danger',
        'title': '⛈️ Heavy Rain / Storm Alert',
        'message': 'Heavy rainfall or thunderstorm detected. Avoid low-lying areas and open spaces.',
        'icon': '⛈️'
    },
    'moderate_rain': {
        'condition': lambda d: 2 <= d.get('rain_1h', 0) < 10 or d.get('weather_main', '') == 'Rain',
        'severity': 'info',
        'title': '🌧️ Rain Advisory',
        'message': 'Moderate rainfall expected. Carry an umbrella.',
        'icon': '🌧️'
    },
    'high_wind': {
        'condition': lambda d: d.get('wind_speed', 0) >= 60,
        'severity': 'danger',
        'title': '💨 High Wind Warning',
        'message': 'Wind speeds above 60 km/h. Secure loose objects and avoid travel.',
        'icon': '💨'
    },
    'strong_wind': {
        'condition': lambda d: 40 <= d.get('wind_speed', 0) < 60,
        'severity': 'warning',
        'title': '🌬️ Strong Wind Advisory',
        'message': 'Strong winds expected. Exercise caution while driving.',
        'icon': '🌬️'
    },
    'low_visibility': {
        'condition': lambda d: d.get('visibility', 10000) < 1000,
        'severity': 'warning',
        'title': '🌫️ Dense Fog Advisory',
        'message': 'Visibility below 1 km. Drive slowly with fog lights.',
        'icon': '🌫️'
    },
    'high_humidity': {
        'condition': lambda d: d.get('humidity', 0) >= 90,
        'severity': 'info',
        'title': '💧 High Humidity Alert',
        'message': 'Humidity above 90%. Conditions may feel oppressive.',
        'icon': '💧'
    },
    'poor_aqi': {
        'condition': lambda d: (d.get('aqi') or 0) >= 4,
        'severity': 'danger',
        'title': '😷 Poor Air Quality Warning',
        'message': 'Air quality is poor (AQI Level 4-5). Wear a mask outdoors.',
        'icon': '🏭'
    },
    'moderate_aqi': {
        'condition': lambda d: (d.get('aqi') or 0) == 3,
        'severity': 'warning',
        'title': '🌫️ Moderate Air Quality',
        'message': 'Air quality is moderate. Sensitive groups should limit exposure.',
        'icon': '🌿'
    }
}

AQI_LABELS = {
    1: ('Good', 'success', '#4CAF50'),
    2: ('Fair', 'info', '#2196F3'),
    3: ('Moderate', 'warning', '#FF9800'),
    4: ('Poor', 'danger', '#F44336'),
    5: ('Very Poor', 'danger', '#9C27B0'),
}


class AlertSystem:
    def __init__(self):
        self.active_alerts = []

    def check_alerts(self, weather_data: dict) -> List[Dict]:
        """
        Evaluate all alert rules against current weather data.
        Returns list of triggered alert dicts.
        """
        triggered = []
        for alert_key, rule in ALERT_RULES.items():
            try:
                if rule['condition'](weather_data):
                    triggered.append({
                        'type': alert_key,
                        'severity': rule['severity'],
                        'title': rule['title'],
                        'message': rule['message'],
                        'icon': rule['icon'],
                        'city': weather_data.get('city', 'Unknown')
                    })
            except Exception as e:
                logger.error(f"Error evaluating alert rule {alert_key}: {e}")

        self.active_alerts = triggered
        logger.info(f"Alerts triggered for {weather_data.get('city')}: {[a['type'] for a in triggered]}")
        return triggered

    def get_aqi_info(self, aqi_value: int) -> Dict:
        """Returns AQI label, class, and color"""
        if aqi_value and aqi_value in AQI_LABELS:
            label, cls, color = AQI_LABELS[aqi_value]
            return {'value': aqi_value, 'label': label, 'class': cls, 'color': color}
        return {'value': aqi_value, 'label': 'Unknown', 'class': 'secondary', 'color': '#9E9E9E'}

    def get_uv_advice(self, temperature: float, cloud_coverage: int) -> str:
        """Simple UV advice based on temperature and cloud cover"""
        if cloud_coverage > 70:
            return "Low UV risk due to cloud cover"
        if temperature >= 35:
            return "Very high UV — use SPF 50+, wear a hat"
        if temperature >= 28:
            return "High UV — apply sunscreen before going out"
        return "Moderate UV — sunscreen recommended"

    def get_activity_recommendations(self, weather_data: dict) -> List[str]:
        """Suggest activities based on weather conditions"""
        recs = []
        temp = weather_data.get('temperature', 20)
        cond = weather_data.get('weather_main', 'Clear')
        wind = weather_data.get('wind_speed', 0)
        hum = weather_data.get('humidity', 50)

        if cond in ('Clear', 'Clouds') and 15 <= temp <= 30 and wind < 30:
            recs.append("✅ Great day for outdoor exercise or a walk")
        if cond in ('Rain', 'Drizzle', 'Thunderstorm'):
            recs.append("🏠 Stay indoors — good time for indoor activities")
        if temp > 35:
            recs.append("🌊 Stay cool — swimming pools or air-conditioned spaces recommended")
        if temp < 5:
            recs.append("🧥 Bundle up — frost conditions possible")
        if 15 <= temp <= 25 and cond == 'Clear':
            recs.append("🚴 Perfect conditions for cycling or jogging")
        if hum > 80 and temp > 28:
            recs.append("💦 Stay hydrated — high heat index conditions")
        if not recs:
            recs.append("🌤️ Conditions are generally acceptable for most activities")

        return recs
