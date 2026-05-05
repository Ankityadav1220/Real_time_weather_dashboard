"""Entry point — loads .env then starts WeatherIQ."""
from dotenv import load_dotenv
load_dotenv()
from app import create_app
import os

app = create_app()
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"\n🌦️  WeatherIQ AI Dashboard starting on http://localhost:{port}\n")
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
