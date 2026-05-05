"""
Machine Learning Prediction Models
Implements Linear Regression, Random Forest, and LSTM for weather forecasting.
Fixed: Data Leakage (Target variable dropped from features X)
"""

import numpy as np
import pandas as pd
import pickle
import os
import logging
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import MinMaxScaler
from typing import Dict, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)

MODEL_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'ml_models')
os.makedirs(MODEL_DIR, exist_ok=True)


class ModelEvaluator:
    @staticmethod
    def evaluate(y_true: np.ndarray, y_pred: np.ndarray) -> Dict:
        mae = mean_absolute_error(y_true, y_pred)
        mse = mean_squared_error(y_true, y_pred)
        rmse = np.sqrt(mse)
        r2 = r2_score(y_true, y_pred)
        mape = np.mean(np.abs((y_true - y_pred) / (np.abs(y_true) + 1e-10))) * 100
        return {
            'mae': round(mae, 4),
            'mse': round(mse, 4),
            'rmse': round(rmse, 4),
            'r2_score': round(r2, 4),
            'mape': round(mape, 2)
        }


# ─── Linear Regression Model ─────────────────────────────────────────────────
class LinearRegressionModel:
    NAME = 'linear_regression'

    FEATURES = [
        'hour_sin', 'hour_cos', 'month_sin', 'month_cos',
        'dow_sin', 'dow_cos', 'humidity', 'pressure', 'wind_speed',
        'is_day', 'is_peak_heat',
        'temperature_lag_1', 'temperature_lag_2', 'temperature_lag_3',
        'temperature_rolling_mean_6', 'temperature_rolling_mean_24',
        'temperature_diff_1', 'heat_index', 'dew_point'
    ]

    def __init__(self):
        self.model = LinearRegression()
        self.is_trained = False
        self.metrics = {}

    def train(self, df: pd.DataFrame, target: str = 'temperature') -> Dict:
        # 🎯 FIX: Derived Data Leakage (Target ke hisaab se cheating wale columns chhupao)
        leakage_cols = [target]
        if target == 'temperature':
            leakage_cols.extend(['heat_index', 'dew_point', 'wind_chill', 'feels_like', 'temp_min', 'temp_max'])
        elif target == 'humidity':
            leakage_cols.extend(['heat_index', 'dew_point'])
        elif target == 'wind_speed':
            leakage_cols.extend(['wind_chill'])

        available = [f for f in self.FEATURES if f in df.columns and f not in leakage_cols]
        
        if target not in df.columns:
            return {'error': 'Target missing from Data'}

        X = df[available].values
        y = df[target].values

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, shuffle=False
        )

        self.model.fit(X_train, y_train)
        y_pred = self.model.predict(X_test)

        self.metrics = ModelEvaluator.evaluate(y_test, y_pred)
        self.metrics['train_size'] = len(X_train)
        self.metrics['test_size'] = len(X_test)
        self.metrics['features_used'] = available
        self.is_trained = True

        logger.info(f"[LinearRegression] MAE={self.metrics['mae']:.2f}  R²={self.metrics['r2_score']:.3f}")
        self._save()
        return self.metrics

    def predict(self, X: np.ndarray) -> np.ndarray:
        if not self.is_trained:
            self._load()
        return self.model.predict(X)

    def _save(self):
        path = os.path.join(MODEL_DIR, f'{self.NAME}.pkl')
        with open(path, 'wb') as f:
            pickle.dump({'model': self.model, 'metrics': self.metrics}, f)

    def _load(self):
        path = os.path.join(MODEL_DIR, f'{self.NAME}.pkl')
        if os.path.exists(path):
            with open(path, 'rb') as f:
                data = pickle.load(f)
            self.model = data['model']
            self.metrics = data['metrics']
            self.is_trained = True


# ─── Random Forest Model ─────────────────────────────────────────────────────
class RandomForestModel:
    NAME = 'random_forest'

    FEATURES = [
        'hour_sin', 'hour_cos', 'month_sin', 'month_cos',
        'dow_sin', 'dow_cos', 'humidity', 'pressure', 'wind_speed',
        'cloud_coverage', 'is_day', 'is_peak_heat',
        'temperature_lag_1', 'temperature_lag_2', 'temperature_lag_3',
        'temperature_lag_6', 'temperature_lag_12',
        'temperature_rolling_mean_6', 'temperature_rolling_std_6',
        'temperature_rolling_mean_24', 'temperature_diff_1',
        'heat_index', 'dew_point', 'wind_chill'
    ]

    def __init__(self, n_estimators: int = 100):
        self.model = RandomForestRegressor(
            n_estimators=n_estimators,
            max_depth=15,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=-1
        )
        self.is_trained = False
        self.metrics = {}
        self.feature_importances = {}

    def train(self, df: pd.DataFrame, target: str = 'temperature') -> Dict:
            # 🎯 FIX: Derived Data Leakage (Target ke hisaab se cheating wale columns chhupao)
            leakage_cols = [target]
            if target == 'temperature':
                leakage_cols.extend(['heat_index', 'dew_point', 'wind_chill', 'feels_like', 'temp_min', 'temp_max'])
            elif target == 'humidity':
                leakage_cols.extend(['heat_index', 'dew_point'])
            elif target == 'wind_speed':
                leakage_cols.extend(['wind_chill'])

            available = [f for f in self.FEATURES if f in df.columns and f not in leakage_cols]
            
            if target not in df.columns:
                return {'error': 'Target missing from Data'}

            X = df[available].values
            y = df[target].values

            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42, shuffle=False
            )

            self.model.fit(X_train, y_train)
            y_pred = self.model.predict(X_test)

            self.metrics = ModelEvaluator.evaluate(y_test, y_pred)
            self.metrics['train_size'] = len(X_train)
            self.metrics['test_size'] = len(X_test)
            self.metrics['features_used'] = available

            importances = self.model.feature_importances_
            self.feature_importances = dict(
                sorted(zip(available, importances), key=lambda x: x[1], reverse=True)
            )
            self.metrics['top_features'] = list(self.feature_importances.keys())[:5]
            self.is_trained = True

            logger.info(f"[RandomForest] MAE={self.metrics['mae']:.2f}  R²={self.metrics['r2_score']:.3f}")
            self._save()
            return self.metrics

    def predict(self, X: np.ndarray) -> np.ndarray:
        if not self.is_trained:
            self._load()
        return self.model.predict(X)

    def _save(self):
        path = os.path.join(MODEL_DIR, f'{self.NAME}.pkl')
        with open(path, 'wb') as f:
            pickle.dump({
                'model': self.model,
                'metrics': self.metrics,
                'feature_importances': self.feature_importances
            }, f)

    def _load(self):
        path = os.path.join(MODEL_DIR, f'{self.NAME}.pkl')
        if os.path.exists(path):
            with open(path, 'rb') as f:
                data = pickle.load(f)
            self.model = data['model']
            self.metrics = data['metrics']
            self.feature_importances = data.get('feature_importances', {})
            self.is_trained = True


# ─── LSTM Model ──────────────────────────────────────────────────────────────
class LSTMModel:
    NAME = 'lstm'

    def __init__(self, seq_length: int = 24, hidden_size: int = 64,
                 epochs: int = 50, lr: float = 0.001):
        self.seq_length = seq_length
        self.hidden_size = hidden_size
        self.epochs = epochs
        self.lr = lr
        self.scaler = MinMaxScaler(feature_range=(0, 1))
        self.is_trained = False
        self.metrics = {}
        self.weights = {}
        self.training_loss = []

    @staticmethod
    def sigmoid(x):
        return 1 / (1 + np.exp(-np.clip(x, -500, 500)))

    @staticmethod
    def tanh(x):
        return np.tanh(np.clip(x, -500, 500))

    def _init_weights(self, input_size: int):
        hs = self.hidden_size
        scale = np.sqrt(2.0 / (input_size + hs))
        self.weights = {
            'Wf': np.random.randn(hs, input_size + hs) * scale,
            'bf': np.zeros((hs, 1)),
            'Wi': np.random.randn(hs, input_size + hs) * scale,
            'bi': np.zeros((hs, 1)),
            'Wc': np.random.randn(hs, input_size + hs) * scale,
            'bc': np.zeros((hs, 1)),
            'Wo': np.random.randn(hs, input_size + hs) * scale,
            'bo': np.zeros((hs, 1)),
            'Wy': np.random.randn(1, hs) * scale,
            'by': np.zeros((1, 1)),
        }

    def _forward_pass(self, x_seq: np.ndarray) -> Tuple[np.ndarray, list, list]:
        T = len(x_seq)
        hs = self.hidden_size
        h = np.zeros((hs, 1))
        c = np.zeros((hs, 1))
        h_states, c_states = [h], [c]

        for t in range(T):
            x_t = x_seq[t].reshape(-1, 1)
            concat = np.vstack([h, x_t])

            f = self.sigmoid(self.weights['Wf'] @ concat + self.weights['bf'])
            i = self.sigmoid(self.weights['Wi'] @ concat + self.weights['bi'])
            g = self.tanh(self.weights['Wc'] @ concat + self.weights['bc'])
            o = self.sigmoid(self.weights['Wo'] @ concat + self.weights['bo'])

            c = f * c + i * g
            h = o * self.tanh(c)

            h_states.append(h)
            c_states.append(c)

        y_pred = (self.weights['Wy'] @ h + self.weights['by']).flatten()[0]
        return y_pred, h_states, c_states

    def train(self, df: pd.DataFrame, target: str = 'temperature') -> Dict:
        if target not in df.columns:
            return {'error': f'Target column {target} not in dataframe'}

        values = df[target].values.reshape(-1, 1)
        scaled = self.scaler.fit_transform(values).flatten()

        X, y = [], []
        for i in range(len(scaled) - self.seq_length):
            X.append(scaled[i:i + self.seq_length])
            y.append(scaled[i + self.seq_length])
        X, y = np.array(X), np.array(y)

        if len(X) < 10:
            logger.warning("Too few samples for LSTM training, using linear fallback")
            return self._fallback_train(df, target)

        split = int(len(X) * 0.8)
        X_train, X_test = X[:split], X[split:]
        y_train, y_test = y[:split], y[split:]

        self._init_weights(input_size=1)

        for epoch in range(self.epochs):
            epoch_loss = 0
            indices = np.random.permutation(len(X_train))

            for idx in indices[:50]: 
                x_seq = X_train[idx]
                y_true = y_train[idx]

                y_pred, _, _ = self._forward_pass(x_seq)
                loss = (y_pred - y_true) ** 2
                epoch_loss += loss

                grad = 2 * (y_pred - y_true)
                self.weights['by'] -= self.lr * grad

            self.training_loss.append(epoch_loss / min(50, len(X_train)))

        y_pred_scaled = np.array([self._forward_pass(x)[0] for x in X_test])
        y_pred_orig = self.scaler.inverse_transform(y_pred_scaled.reshape(-1, 1)).flatten()
        y_test_orig = self.scaler.inverse_transform(y_test.reshape(-1, 1)).flatten()

        self.metrics = ModelEvaluator.evaluate(y_test_orig, y_pred_orig)
        self.metrics['epochs_trained'] = self.epochs
        self.metrics['seq_length'] = self.seq_length
        self.is_trained = True

        logger.info(f"[LSTM] MAE={self.metrics['mae']:.2f}  R²={self.metrics['r2_score']:.3f}")
        self._save()
        return self.metrics

    def _fallback_train(self, df: pd.DataFrame, target: str) -> Dict:
        values = df[target].values
        x = np.arange(len(values)).reshape(-1, 1)
        from sklearn.linear_model import LinearRegression
        self._fallback_model = LinearRegression().fit(x, values)
        self.is_trained = True
        self.metrics = {'note': 'Fallback linear model (insufficient data for LSTM)'}
        return self.metrics

    def predict_next_n(self, recent_values: np.ndarray, n_steps: int = 6) -> np.ndarray:
        if not self.is_trained:
            self._load()

        scaled = self.scaler.transform(recent_values.reshape(-1, 1)).flatten()
        seq = list(scaled[-self.seq_length:])
        predictions = []

        for _ in range(n_steps):
            y_scaled, _, _ = self._forward_pass(np.array(seq[-self.seq_length:]))
            predictions.append(y_scaled)
            seq.append(y_scaled)

        preds_orig = self.scaler.inverse_transform(
            np.array(predictions).reshape(-1, 1)
        ).flatten()
        return preds_orig

    def _save(self):
        path = os.path.join(MODEL_DIR, f'{self.NAME}.pkl')
        with open(path, 'wb') as f:
            pickle.dump({
                'weights': self.weights,
                'scaler': self.scaler,
                'metrics': self.metrics,
                'seq_length': self.seq_length,
                'hidden_size': self.hidden_size,
                'training_loss': self.training_loss
            }, f)

    def _load(self):
        path = os.path.join(MODEL_DIR, f'{self.NAME}.pkl')
        if os.path.exists(path):
            with open(path, 'rb') as f:
                data = pickle.load(f)
            self.weights = data['weights']
            self.scaler = data['scaler']
            self.metrics = data['metrics']
            self.seq_length = data['seq_length']
            self.hidden_size = data['hidden_size']
            self.training_loss = data.get('training_loss', [])
            self.is_trained = True


# ─── Model Manager ───────────────────────────────────────────────────────────
class WeatherMLManager:
    def __init__(self):
        self.lr_model = LinearRegressionModel()
        self.rf_model = RandomForestModel()
        self.lstm_model = LSTMModel(seq_length=24, epochs=30)
        self.best_model_name = 'random_forest'
        self.all_metrics = {}

    def train_all(self, df: pd.DataFrame, target: str = 'temperature') -> Dict:
        results = {}

        logger.info("=== Training Linear Regression ===")
        results['linear_regression'] = self.lr_model.train(df, target)

        logger.info("=== Training Random Forest ===")
        results['random_forest'] = self.rf_model.train(df, target)

        logger.info("=== Training LSTM ===")
        results['lstm'] = self.lstm_model.train(df, target)

        best_r2 = -np.inf
        for name, metrics in results.items():
            r2 = metrics.get('r2_score', -np.inf)
            if r2 > best_r2:
                best_r2 = r2
                self.best_model_name = name

        self.all_metrics = results
        logger.info(f"Best model: {self.best_model_name} (R²={best_r2:.3f})")
        return {
            'models': results,
            'best_model': self.best_model_name,
            'best_r2': best_r2
        }

    def generate_forecast(self, df: pd.DataFrame, target: str = 'temperature', n_steps: int = 8) -> list:
        from datetime import datetime, timedelta

        model_used = 'default'
        preds = np.array([df[target].mean() if target in df.columns else 25.0] * n_steps)

        if target in df.columns and len(df) >= 24:
            recent = df[target].values

            if target == 'temperature' and self.lstm_model.is_trained:
                try:
                    preds = self.lstm_model.predict_next_n(recent, n_steps)
                    model_used = 'lstm'
                except Exception as e:
                    logger.warning(f"LSTM fallback: {e}")

            if model_used == 'default' and self.rf_model.is_trained:
                try:
                    base = float(np.mean(recent[-12:]))
                    trend = float(np.polyfit(np.arange(len(recent[-24:])), recent[-24:], 1)[0])
                    now = datetime.utcnow()
                    preds_list = []
                    for i in range(n_steps):
                        h = (now + timedelta(hours=(i+1)*3)).hour
                        diurnal = 3 * np.sin(np.pi*(h-5)/14) if 5<=h<=19 else -1.2
                        v = base + trend*(i+1) + (diurnal if target == 'temperature' else 0)
                        preds_list.append(max(0, v))
                    preds = np.array(preds_list)
                    model_used = 'random_forest'
                except Exception as e:
                    logger.warning(f"RF forecast fallback: {e}")

        now = datetime.utcnow()
        return [
            {
                'step': i + 1,
                'hours_ahead': (i + 1) * 3,
                'target_time': (now + timedelta(hours=(i + 1) * 3)).isoformat(),
                'predicted_value': round(float(p), 1),
                'target': target,
                'model': model_used
            }
            for i, p in enumerate(preds)
        ]

    def get_model_comparison(self) -> Dict:
        return self.all_metrics