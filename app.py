
from flask import Flask
from flask_cors import CORS

from config import Config
from routes.main import main_bp
from routes.analyze import analyze_bp

# Create Flask app directly (no create_app function)
app = Flask(
    __name__,
    template_folder="templates",
    static_folder="static",
)

CORS(app)

# Register routes
app.register_blueprint(main_bp)
app.register_blueprint(analyze_bp)


if __name__ == "__main__":
    print("-" * 58)
    print("  DeepFakeShield AI Server")
    print("  URL: http://127.0.0.1:5000")
    print("  Model: Gemini")
    print("-" * 58)

    if not Config.GEMINI_API_KEY:
        print("  WARNING: GEMINI_API_KEY is not set.")

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True,
    )
