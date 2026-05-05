"""
DatabaseManager — SQLite with WAL mode, connection timeout, thread-safe.
Fixed: Added save_prediction function to prevent 500 error.
"""
import sqlite3
import logging
import os
import threading
from datetime import datetime
from contextlib import contextmanager

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(__file__), 'weather.db')
_local  = threading.local()

class DatabaseManager:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._lock = threading.Lock()

    def _new_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(
            self.db_path,
            check_same_thread=False,
            timeout=30,              # wait up to 30s on lock
            isolation_level=None,    # autocommit; we manage transactions
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")      # WAL for concurrency
        conn.execute("PRAGMA synchronous=NORMAL")    # good balance
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA cache_size=2000")
        return conn

    @contextmanager
    def get_connection(self):
        """Thread-local connection context manager."""
        if not getattr(_local, 'conn', None):
            _local.conn = self._new_connection()
        conn = _local.conn
        try:
            conn.execute("BEGIN")
            yield conn
            conn.execute("COMMIT")
        except Exception:
            try: conn.execute("ROLLBACK")
            except Exception: pass
            raise

    def init_db(self):
        conn = self._new_connection()
        try:
            conn.executescript('''
                CREATE TABLE IF NOT EXISTS weather_observations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    city TEXT NOT NULL,
                    country TEXT,
                    temperature REAL,
                    feels_like REAL,
                    temp_min REAl,
                    temp_max REAL,
                    humidity INTEGER,
                    pressure INTEGER,
                    wind_speed REAL,
                    wind_direction INTEGER,
                    cloud_coverage INTEGER,
                    visibility INTEGER,
                    weather_main TEXT,
                    weather_description TEXT,
                    rain_1h REAL DEFAULT 0,
                    aqi INTEGER,
                    latitude REAL,
                    longitude REAL,
                    recorded_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_obs_city ON weather_observations(city);
                CREATE INDEX IF NOT EXISTS idx_obs_city_time ON weather_observations(city, recorded_at);

                CREATE TABLE IF NOT EXISTS weather_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    city TEXT NOT NULL,
                    alert_type TEXT,
                    severity TEXT,
                    message TEXT,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_alerts_city ON weather_alerts(city);

                CREATE TABLE IF NOT EXISTS api_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    endpoint TEXT,
                    method TEXT,
                    status_code INTEGER,
                    city TEXT,
                    elapsed_ms REAL,
                    error TEXT,
                    logged_at TEXT
                );

                CREATE TABLE IF NOT EXISTS community_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    city TEXT NOT NULL,
                    report_type TEXT,
                    severity TEXT,
                    note TEXT,
                    reported_at TEXT NOT NULL,
                    UNIQUE(city, report_type, reported_at)
                );
                CREATE INDEX IF NOT EXISTS idx_cr_city ON community_reports(city);
                
                -- ADDED TO FIX 500 ERROR
                CREATE TABLE IF NOT EXISTS model_predictions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    city TEXT,
                    model_name TEXT,
                    target TEXT,
                    predicted_value REAL,
                    forecast_time TEXT,
                    created_at TEXT
                );
            ''')
            logger.info(f"Database initialised at {self.db_path}")
        except Exception as e:
            logger.error(f"DB init error: {e}")
        finally:
            conn.close()

    def save_observation(self, data: dict):
        if not data.get('city'):
            return
        try:
            with self.get_connection() as conn:
                conn.execute('''
                    INSERT INTO weather_observations
                    (city, country, temperature, feels_like, temp_min, temp_max, humidity, pressure, wind_speed,
                     wind_direction, cloud_coverage, visibility, weather_main,
                     weather_description, rain_1h, aqi, latitude, longitude, recorded_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ''', (
                    data.get('city'), data.get('country'), data.get('temperature'), data.get('feels_like'),
                    data.get('temp_min'), data.get('temp_max'),
                    data.get('humidity'), data.get('pressure'), data.get('wind_speed'),
                    data.get('wind_direction'), data.get('cloud_coverage'), data.get('visibility'),
                    data.get('weather_main'), data.get('weather_description'), data.get('rain_1h', 0),
                    data.get('aqi'), data.get('latitude'), data.get('longitude'),
                    data.get('recorded_at', datetime.utcnow().isoformat())
                ))
        except Exception as e:
            logger.warning(f"save_observation error: {e}")

    def get_observations(self, city: str, limit: int = 100) -> list:
        try:
            conn = self._new_connection()
            rows = conn.execute('''
                SELECT * FROM weather_observations
                WHERE LOWER(city)=LOWER(?)
                ORDER BY recorded_at DESC LIMIT ?
            ''', (city, limit)).fetchall()
            conn.close()
            return [dict(r) for r in rows]
        except Exception as e:
            logger.warning(f"get_observations error: {e}")
            return []

    def save_alert(self, city: str, alert_type: str, severity: str, message: str):
        try:
            with self.get_connection() as conn:
                conn.execute('''
                    INSERT INTO weather_alerts (city, alert_type, severity, message, created_at)
                    VALUES (?,?,?,?,?)
                ''', (city, alert_type, severity, message, datetime.utcnow().isoformat()))
        except Exception as e:
            logger.warning(f"save_alert error: {e}")
            
    def get_alerts(self, city: str, limit: int = 10) -> list:
        try:
            conn = self._new_connection()
            rows = conn.execute('''
                SELECT * FROM weather_alerts
                WHERE LOWER(city)=LOWER(?)
                ORDER BY created_at DESC LIMIT ?
            ''', (city, limit)).fetchall()
            conn.close()
            return [dict(r) for r in rows]
        except Exception as e:
            logger.warning(f"get_alerts error: {e}")
            return []        

    def log_request(self, endpoint, method, status, city=None, elapsed=None, error=None):
        try:
            conn = self._new_connection()
            conn.execute("BEGIN")
            conn.execute('''
                INSERT INTO api_logs (endpoint, method, status_code, city, elapsed_ms, error, logged_at)
                VALUES (?,?,?,?,?,?,?)
            ''', (endpoint, method, status, city, elapsed, error, datetime.utcnow().isoformat()))
            conn.execute("COMMIT")
            conn.close()
        except Exception:
            pass
    
    def save_forecasts(self, city: str, forecasts: list):
        try:
            pass 
        except Exception as e:
            logger.warning(f"save_forecasts error: {e}")

    # 🎯 FIX: Added the missing function that caused the 500 error!
    def save_prediction(self, pred_data: dict):
        try:
            with self.get_connection() as conn:
                conn.execute('''
                    INSERT INTO model_predictions 
                    (city, model_name, target, predicted_value, forecast_time, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    pred_data.get('city', 'Unknown'),
                    pred_data.get('model_name', 'Unknown'),
                    pred_data.get('prediction_type', 'temperature'),
                    pred_data.get('predicted_value', 0.0),
                    pred_data.get('target_time', datetime.utcnow().isoformat()),
                    datetime.utcnow().isoformat()
                ))
        except Exception as e:
            logger.warning(f"save_prediction error: {e}")