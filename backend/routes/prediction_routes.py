"""
ML Prediction Routes
GET  /api/prediction?city=<city>&target=temperature&steps=8
POST /api/train
GET  /api/model-metrics
"""

from flask import Blueprint, request, jsonify, current_app
import logging
import numpy as np
from database.db_manager import DatabaseManager
from backend.models.ml_models import WeatherMLManager
from backend.utils.preprocessor import WeatherDataPreprocessor

logger = logging.getLogger(__name__)
prediction_bp = Blueprint('prediction', __name__)

db          = DatabaseManager()
preprocessor = WeatherDataPreprocessor()

# Module-level manager — shared across requests
_ml_manager = WeatherMLManager()


def _get_ml_manager() -> WeatherMLManager:
    mgr = current_app.config.get('ML_MANAGER')
    return mgr if mgr is not None else _ml_manager


@prediction_bp.route('/prediction', methods=['GET'])
def predict():
    city   = request.args.get('city', 'Delhi').strip()
    target = request.args.get('target', 'temperature')
    steps  = min(int(request.args.get('steps', 8)), 24)

    if target not in ('temperature', 'humidity', 'wind_speed'):
        return jsonify({'error': 'target must be temperature, humidity, or wind_speed'}), 400

    try:
        ml = _get_ml_manager()
        observations = db.get_observations(city, limit=500)

        if len(observations) >= 20:
            df = preprocessor.preprocess_for_training(observations, target=target)
            if len(df) >= 10:
                predictions = ml.generate_forecast(df, target=target, n_steps=steps)
            else:
                predictions = _trend_predictions(observations, target, steps)
        else:
            predictions = _trend_predictions(observations, target, steps)

        for pred in predictions:
            # Saved safely using the newly added function
            db.save_prediction({
                'city': city,
                'prediction_type': target,
                'target_time': pred['target_time'],
                'predicted_value': pred['predicted_value'],
                'model_name': pred.get('model', 'unknown')
            })

        return jsonify({
            'success': True,
            'city': city,
            'target': target,
            'steps': len(predictions),
            'data': predictions
        })

    except Exception as e:
        logger.error(f"Prediction error for {city}: {e}", exc_info=True)
        return jsonify({'error': 'Prediction failed', 'detail': str(e)}), 500


@prediction_bp.route('/train', methods=['POST'])
def train():
    body   = request.get_json() or {}
    city   = body.get('city', 'Delhi')
    target = body.get('target', 'temperature')

    try:
        observations = db.get_observations(city, limit=720)
        if len(observations) < 20:
            return jsonify({
                'success': False,
                'message': f'Only {len(observations)} observations for {city}. Need at least 20.'
            }), 400

        df = preprocessor.preprocess_for_training(observations, target=target)
        ml = _get_ml_manager()
        results = ml.train_all(df, target=target)

        current_app.config['ML_METRICS'] = {
            'linear_regression': ml.lr_model.metrics,
            'random_forest':     ml.rf_model.metrics,
            'lstm':              ml.lstm_model.metrics,
            'best_model':        ml.best_model_name,
        }
        current_app.config['ML_MANAGER'] = ml

        return jsonify({
            'success': True,
            'city': city,
            'target': target,
            'training_samples': len(df),
            'results': results
        })

    except Exception as e:
        logger.error(f"Training error: {e}", exc_info=True)
        return jsonify({'error': 'Training failed', 'detail': str(e)}), 500


@prediction_bp.route('/model-metrics', methods=['GET'])
def model_metrics():
    try:
        metrics = current_app.config.get('ML_METRICS', {})

        if not metrics:
            ml = _get_ml_manager()
            ml.lr_model._load()
            ml.rf_model._load()
            ml.lstm_model._load()

            if any([ml.lr_model.is_trained, ml.rf_model.is_trained, ml.lstm_model.is_trained]):
                metrics = {
                    'linear_regression': ml.lr_model.metrics,
                    'random_forest':     ml.rf_model.metrics,
                    'lstm':              ml.lstm_model.metrics,
                    'best_model':        ml.best_model_name,
                }

        if not metrics:
            return jsonify({
                'success': True,
                'status': 'training_in_progress',
                'message': 'Models are being trained in the background. Refresh in 10–15 seconds.',
                'metrics': {}
            })

        return jsonify({'success': True, 'metrics': metrics})

    except Exception as e:
        logger.error(f"Metrics error: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


def _trend_predictions(observations: list, target: str, steps: int) -> list:
    from datetime import datetime, timedelta

    if observations:
        vals = [o.get(target) for o in observations[-24:] if o.get(target) is not None]
    else:
        vals = []

    if len(vals) >= 3:
        x = np.arange(len(vals))
        coeffs = np.polyfit(x, vals, 1)
        base  = float(np.mean(vals[-6:]))
        trend = float(coeffs[0])
    else:
        base, trend = 25.0, 0.0

    now = datetime.utcnow()
    preds = []
    for i in range(steps):
        hour = (now + timedelta(hours=(i+1)*3)).hour
        diurnal = 3 * np.sin(np.pi * (hour - 5) / 14) if 5 <= hour <= 19 else -1.2
        val = base + trend*(i+1) + diurnal
        preds.append({
            'step': i+1,
            'hours_ahead': (i+1)*3,
            'target_time': (now + timedelta(hours=(i+1)*3)).isoformat(),
            'predicted_value': round(float(val), 1),
            'target': target,
            'model': 'trend_extrapolation'
        })
    return preds