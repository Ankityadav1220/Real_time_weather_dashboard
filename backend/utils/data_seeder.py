"""
Historical Data Seeder
Generates 30 days of realistic synthetic weather observations per city.
Called once on first startup so ML models have data to train on immediately.
"""

import numpy as np
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Realistic city climate profiles
CITY_CLIMATES = {
    'Delhi': {
        'base_temp': 32, 'temp_amplitude': 8, 'temp_noise': 2.5,
        'base_hum': 55,  'hum_noise': 12,
        'base_wind': 14, 'wind_noise': 5,
        'base_pressure': 1008, 'pressure_noise': 6,
        'country': 'IN', 'lat': 28.61, 'lon': 77.21,
    },
    'Mumbai': {
        'base_temp': 30, 'temp_amplitude': 4, 'temp_noise': 1.5,
        'base_hum': 80,  'hum_noise': 8,
        'base_wind': 18, 'wind_noise': 6,
        'base_pressure': 1010, 'pressure_noise': 4,
        'country': 'IN', 'lat': 19.08, 'lon': 72.88,
    },
    'London': {
        'base_temp': 13, 'temp_amplitude': 5, 'temp_noise': 2,
        'base_hum': 78,  'hum_noise': 10,
        'base_wind': 22, 'wind_noise': 8,
        'base_pressure': 1015, 'pressure_noise': 8,
        'country': 'GB', 'lat': 51.51, 'lon': -0.13,
    },
    'New York': {
        'base_temp': 18, 'temp_amplitude': 7, 'temp_noise': 2,
        'base_hum': 68,  'hum_noise': 10,
        'base_wind': 20, 'wind_noise': 7,
        'base_pressure': 1018, 'pressure_noise': 7,
        'country': 'US', 'lat': 40.71, 'lon': -74.01,
    },
    'Tokyo': {
        'base_temp': 22, 'temp_amplitude': 6, 'temp_noise': 1.8,
        'base_hum': 72,  'hum_noise': 9,
        'base_wind': 14, 'wind_noise': 5,
        'base_pressure': 1016, 'pressure_noise': 5,
        'country': 'JP', 'lat': 35.68, 'lon': 139.69,
    },
    'Dubai': {
        'base_temp': 38, 'temp_amplitude': 7, 'temp_noise': 1.5,
        'base_hum': 42,  'hum_noise': 8,
        'base_wind': 10, 'wind_noise': 4,
        'base_pressure': 1004, 'pressure_noise': 4,
        'country': 'AE', 'lat': 25.20, 'lon': 55.27,
    },
}

WEATHER_CONDITIONS = [
    ('Clear', 'Clear Sky'),
    ('Clouds', 'Partly Cloudy'),
    ('Clouds', 'Overcast Clouds'),
    ('Rain', 'Light Rain'),
    ('Drizzle', 'Light Drizzle'),
    ('Thunderstorm', 'Thunderstorm'),
]

def _diurnal_temp(base, amplitude, hour):
    """Realistic temperature curve: coolest at dawn, hottest ~2-3pm"""
    return base + amplitude * np.sin(np.pi * (hour - 5) / 14) if 5 <= hour <= 19 else base - amplitude * 0.4

def seed_city(db, city: str, days: int = 30) -> int:
    """
    Generate `days` * 24 hourly observations for `city` and store in DB.
    Returns number of rows inserted.
    """
    climate = CITY_CLIMATES.get(city, CITY_CLIMATES['Delhi'])
    rng = np.random.default_rng(abs(hash(city)) % (2**32))

    # Check if already seeded
    existing = db.get_observations(city, limit=5)
    if len(existing) >= 5:
        logger.info(f"[Seeder] {city} already has data, skipping")
        return 0

    now = datetime.utcnow()
    start = now - timedelta(days=days)
    count = 0

    # Slow-moving weather pattern (changes every 6-12 hrs)
    pattern_change = 0
    current_condition = 0

    for hour_offset in range(days * 24):
        dt = start + timedelta(hours=hour_offset)
        hour = dt.hour

        # Change weather pattern occasionally
        if hour_offset % rng.integers(6, 13) == 0:
            current_condition = rng.integers(0, len(WEATHER_CONDITIONS))

        temp = _diurnal_temp(climate['base_temp'], climate['temp_amplitude'], hour)
        temp += rng.normal(0, climate['temp_noise'])

        hum = climate['base_hum'] + rng.normal(0, climate['hum_noise'])
        hum = float(np.clip(hum, 20, 99))

        wind = climate['base_wind'] + abs(rng.normal(0, climate['wind_noise']))
        pressure = climate['base_pressure'] + rng.normal(0, climate['pressure_noise'])

        cond_main, cond_desc = WEATHER_CONDITIONS[current_condition]
        rain = float(rng.uniform(0.5, 5)) if cond_main in ('Rain', 'Drizzle', 'Thunderstorm') else 0.0

        obs = {
            'city': city,
            'country': climate['country'],
            'latitude': climate['lat'],
            'longitude': climate['lon'],
            'temperature': round(float(temp), 1),
            'feels_like': round(float(temp - 2 + rng.normal(0, 0.5)), 1),
            'temp_min': round(float(temp - 3), 1),
            'temp_max': round(float(temp + 3), 1),
            'humidity': int(hum),
            'pressure': int(pressure),
            'wind_speed': round(float(wind), 1),
            'wind_direction': int(rng.integers(0, 360)),
            'visibility': int(rng.integers(6000, 10000)),
            'cloud_coverage': int(rng.integers(0, 100)),
            'weather_main': cond_main,
            'weather_description': cond_desc,
            'rain_1h': rain,
            'aqi': int(rng.integers(1, 5)),
        }

        # Override recorded_at timestamp to historical time
        import sqlite3
        with db.get_connection() as conn:
            conn.execute('''
                INSERT INTO weather_observations (
                    city, country, latitude, longitude, temperature, feels_like,
                    temp_min, temp_max, humidity, pressure, wind_speed, wind_direction,
                    visibility, cloud_coverage, weather_main, weather_description,
                    rain_1h, aqi, recorded_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ''', (
                obs['city'], obs['country'], obs['latitude'], obs['longitude'],
                obs['temperature'], obs['feels_like'], obs['temp_min'], obs['temp_max'],
                obs['humidity'], obs['pressure'], obs['wind_speed'], obs['wind_direction'],
                obs['visibility'], obs['cloud_coverage'], obs['weather_main'],
                obs['weather_description'], obs['rain_1h'], obs['aqi'],
                dt.strftime('%Y-%m-%d %H:%M:%S')
            ))
        count += 1

    logger.info(f"[Seeder] {city}: inserted {count} historical observations")
    return count


def seed_all_cities(db, days: int = 30):
    """Seed all default cities"""
    total = 0
    for city in CITY_CLIMATES:
        total += seed_city(db, city, days)
    logger.info(f"[Seeder] Total rows seeded: {total}")
    return total
