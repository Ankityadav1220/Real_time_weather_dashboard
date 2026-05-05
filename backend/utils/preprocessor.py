"""
Data Preprocessing Module — v2 (Fixed Time Format & Unit Conversion)
Handles cleaning, feature engineering, and normalization for ML models.
"""

import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler, StandardScaler
from typing import Tuple, List
import logging

logger = logging.getLogger(__name__)

class WeatherDataPreprocessor:
    """
    Handles all data preprocessing steps:
    - Missing value imputation with mixed format safety
    - Outlier detection and removal
    - Feature engineering (time-based, lag features)
    - Normalization and scaling
    """

    def __init__(self):
        self.scaler = MinMaxScaler(feature_range=(0, 1))
        self.standard_scaler = StandardScaler()
        self.is_fitted = False

    # ─── Missing Value Handling ───────────────────────────────────────────────

    def handle_missing_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """Fill missing values using forward fill, then backward fill, then median"""
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

        if not numeric_cols:
            return df

        # Modern Pandas ffill/bfill syntax
        df[numeric_cols] = df[numeric_cols].ffill().bfill()
        
        # Fallback to median for any remaining NaNs
        for col in numeric_cols:
            if df[col].isna().any():
                df[col] = df[col].fillna(df[col].median())

        logger.info(f"Missing values handled. Remaining nulls: {df.isna().sum().sum()}")
        return df

    # ─── Outlier Removal ─────────────────────────────────────────────────────

    def remove_outliers_iqr(self, df: pd.DataFrame, columns: List[str],
                            factor: float = 3.0) -> pd.DataFrame:
        original_len = len(df)
        for col in columns:
            if col not in df.columns:
                continue
            Q1 = df[col].quantile(0.25)
            Q3 = df[col].quantile(0.75)
            IQR = Q3 - Q1
            lower = Q1 - factor * IQR
            upper = Q3 + factor * IQR
            df = df[(df[col] >= lower) & (df[col] <= upper)]

        removed = original_len - len(df)
        logger.info(f"Outlier removal: {removed} rows removed ({removed/original_len*100:.1f}%)")
        return df.reset_index(drop=True)

    # ─── Feature Engineering (FIXED) ──────────────────────────────────────────

    def add_time_features(self, df: pd.DataFrame, datetime_col: str = 'recorded_at') -> pd.DataFrame:
        """Add cyclical time-based features with robust time parsing"""
        try:
            # 🎯 FIX: 'mixed' format aur 'coerce' errors handle karega 
            # Taaki "2026-04-09 08:18:15" aur ISO format dono chal sakein
            df[datetime_col] = pd.to_datetime(df[datetime_col], errors='coerce', format='mixed')
            
            # Jo rows convert nahi ho payi unhe drop karein
            df = df.dropna(subset=[datetime_col]).sort_values(datetime_col).reset_index(drop=True)

            # Extract basic time components
            df['hour'] = df[datetime_col].dt.hour
            df['day_of_week'] = df[datetime_col].dt.dayofweek
            df['month'] = df[datetime_col].dt.month
            df['day_of_year'] = df[datetime_col].dt.dayofyear

            # Cyclical encoding
            df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
            df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)
            df['month_sin'] = np.sin(2 * np.pi * df['month'] / 12)
            df['month_cos'] = np.cos(2 * np.pi * df['month'] / 12)

            # Categories
            df['is_day'] = ((df['hour'] >= 6) & (df['hour'] <= 20)).astype(int)
            df['is_peak_heat'] = ((df['hour'] >= 12) & (df['hour'] <= 16)).astype(int)

            return df
        except Exception as e:
            logger.error(f"Error in add_time_features: {e}")
            return df

    def add_lag_features(self, df: pd.DataFrame, target_col: str,
                         lags: List[int] = [1, 2, 3, 6, 12, 24]) -> pd.DataFrame:
        """Add lagged versions of the target variable"""
        for lag in lags:
            df[f'{target_col}_lag_{lag}'] = df[target_col].shift(lag)

        # Rolling stats
        df[f'{target_col}_rolling_mean_6'] = df[target_col].rolling(window=6, min_periods=1).mean()
        df[f'{target_col}_rolling_std_6'] = df[target_col].rolling(window=6, min_periods=1).std()

        # Rate of change
        df[f'{target_col}_diff_1'] = df[target_col].diff(1)

        return df

    def add_weather_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add derived weather features with Celsius to Fahrenheit correction"""
        if 'temperature' in df.columns and 'humidity' in df.columns:
            T_c = df['temperature']
            H = df['humidity']
            
            # 🎯 FIX: Heat Index formula Fahrenheit mangta hai
            T_f = (T_c * 9/5) + 32
            
            hi_f = (
                -42.379 + 2.04901523 * T_f + 10.14333127 * H +
                -0.22475541 * T_f * H + -0.00683783 * T_f**2 +
                -0.05481717 * H**2 + 0.00122874 * T_f**2 * H +
                0.00085282 * T_f * H**2 + -0.00000199 * T_f**2 * H**2
            )
            # Wapas Celsius mein badlein dashboard ke liye
            df['heat_index'] = (hi_f - 32) * 5/9

        # Wind chill (valid below 10°C, wind > 4.8 km/h)
        if 'temperature' in df.columns and 'wind_speed' in df.columns:
            T = df['temperature']
            V = df['wind_speed']
            df['wind_chill'] = 13.12 + 0.6215 * T - 11.37 * (V**0.16) + 0.3965 * T * (V**0.16)

        # Dew point
        if 'temperature' in df.columns and 'humidity' in df.columns:
            T = df['temperature']
            H = df['humidity']
            a, b = 17.27, 237.3
            # Safety check for log(0)
            H_safe = H.clip(lower=0.1)
            alpha = (a * T / (b + T)) + np.log(H_safe / 100.0)
            df['dew_point'] = (b * alpha) / (a - alpha)

        return df

    # ─── Scaling ─────────────────────────────────────────────────────────────

    def fit_scale(self, data: np.ndarray) -> np.ndarray:
        scaled = self.scaler.fit_transform(data.reshape(-1, 1))
        self.is_fitted = True
        return scaled.flatten()

    def transform(self, data: np.ndarray) -> np.ndarray:
        if not self.is_fitted:
            raise ValueError("Scaler not fitted.")
        return self.scaler.transform(data.reshape(-1, 1)).flatten()

    def inverse_transform(self, data: np.ndarray) -> np.ndarray:
        if not self.is_fitted:
            raise ValueError("Scaler not fitted.")
        return self.scaler.inverse_transform(data.reshape(-1, 1)).flatten()

    # ─── Full Pipeline ────────────────────────────────────────────────────────

    def preprocess_for_training(self, observations: list,
                                target: str = 'temperature') -> pd.DataFrame:
        if not observations:
            return pd.DataFrame()

        df = pd.DataFrame(observations)
        
        # 1. Handle missing values
        df = self.handle_missing_values(df)

        # 2. Time features (🎯 Iske andar hi ab fix hai)
        if 'recorded_at' in df.columns:
            df = self.add_time_features(df, 'recorded_at')

        # 3. Outliers
        cols_to_clean = ['temperature', 'humidity', 'wind_speed', 'pressure']
        cols_present = [c for c in cols_to_clean if c in df.columns]
        df = self.remove_outliers_iqr(df, cols_present)

        # 4. Lag features
        if target in df.columns:
            df = self.add_lag_features(df, target)

        # 5. Derived features
        df = self.add_weather_features(df)

        # 6. Final cleanup
        df = df.dropna().reset_index(drop=True)
        return df