"""
WeatherIQ AI Intelligence System — v6
Production upgrade: global location state, ORS routing, no auth.
"""
from flask import Flask, jsonify, render_template
import logging, os, threading

logging.basicConfig(level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger(__name__)


def _background_init(app):
    """Seed historical data + train ML models on startup"""
    with app.app_context():
        try:
            from database.db_manager import DatabaseManager
            from backend.utils.data_seeder import seed_all_cities
            from backend.models.ml_models import WeatherMLManager
            from backend.utils.preprocessor import WeatherDataPreprocessor

            db = DatabaseManager()
            preprocessor = WeatherDataPreprocessor()
            logger.info("=== Seeding 30 days of historical data ===")
            seed_all_cities(db, days=30)

            logger.info("=== Training ML models ===")
            ml = WeatherMLManager()
            for city in ['Delhi', 'London', 'Mumbai']:
                obs = db.get_observations(city, limit=500)
                if len(obs) >= 30:
                    df = preprocessor.preprocess_for_training(obs, target='temperature')
                    if len(df) >= 20:
                        result = ml.train_all(df, target='temperature')
                        logger.info(
                            f"Trained on {city} | best={result['best_model']} "
                            f"R2={result['best_r2']:.3f}"
                        )
                        app.config['ML_METRICS'] = {
                            'linear_regression': ml.lr_model.metrics,
                            'random_forest':     ml.rf_model.metrics,
                            'lstm':              ml.lstm_model.metrics,
                            'best_model':        ml.best_model_name,
                        }
                        app.config['ML_MANAGER'] = ml
                        break
            logger.info("=== WeatherIQ AI System Ready ===")
        except Exception as e:
            logger.error(f"Background init error: {e}", exc_info=True)


def create_app():
    app = Flask(
        __name__,
        template_folder='frontend/templates',
        static_folder='frontend/static'
    )

    app.config.update(
        SECRET_KEY           = os.environ.get('SECRET_KEY', 'weatheriq-ai-2026'),
        OPENWEATHER_API_KEY  = os.environ.get('OPENWEATHER_API_KEY', ''),
        OPENROUTESERVICE_KEY = os.environ.get('OPENROUTESERVICE_KEY', ''),
        DEBUG                = os.environ.get('FLASK_DEBUG', 'True') == 'True',
        ML_METRICS           = {},
        ML_MANAGER           = None,
        SESSION_COOKIE_SAMESITE = 'Lax',
    )

    @app.after_request
    def add_cors(r):
        r.headers['Access-Control-Allow-Origin']  = '*'
        r.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        r.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        return r

    # Init DB
    from database.db_manager import DatabaseManager
    DatabaseManager().init_db()

    # Register blueprints — auth removed
    from backend.routes.weather_routes      import weather_bp
    from backend.routes.prediction_routes   import prediction_bp
    from backend.routes.main_routes         import main_bp
    from backend.routes.intelligence_routes import intel_bp

    app.register_blueprint(weather_bp,    url_prefix='/api')
    app.register_blueprint(prediction_bp, url_prefix='/api')
    app.register_blueprint(main_bp)
    app.register_blueprint(intel_bp)

    @app.errorhandler(404)
    def not_found(e):
        return render_template('404.html', page='404'), 404

    @app.errorhandler(500)
    def server_error(e):
        logger.error(f"Server error: {e}")
        return jsonify({'error': 'Internal server error'}), 500

    threading.Thread(target=_background_init, args=(app,), daemon=True).start()
    return app


if __name__ == '__main__':
    app = create_app()
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"Starting WeatherIQ AI on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
