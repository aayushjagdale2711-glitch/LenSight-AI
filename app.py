
import subprocess
import sys

def ensure_dependencies():
    dependencies = {
        "imageio": "imageio",
        "imageio_ffmpeg": "imageio-ffmpeg",
        "PIL": "pillow",
        "requests": "requests",
        "flask_cors": "flask-cors",
    }

    to_install = []
    for module_name, package_name in dependencies.items():
        try:
            __import__(module_name)
        except ImportError:
            to_install.append(package_name)

    if to_install:
        raise ImportError(
            "Missing dependencies: "
            + ", ".join(to_install)
            + ". Install them using requirements.txt."
        )

ensure_dependencies()

from flask import Flask
from flask_cors import CORS

from config import Config
from routes.main import main_bp
from routes.analyze import analyze_bp


def create_app():
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )

    CORS(app)

    app.register_blueprint(main_bp)
    app.register_blueprint(analyze_bp)

    return app


# IMPORTANT: Vercel needs this top-level application instance.
app = create_app()


if __name__ == "__main__":
    print("-" * 58)
    print("  DeepFakeShield AI Server")
    print("  URL: http://127.0.0.1:5000")
    print("  Model: Gemini")
    print("-" * 58)

    if not Config.GEMINI_API_KEY:
        print("  WARNING: GEMINI_API_KEY is not set.")

    app.run(host="127.0.0.1", port=5000, debug=True)
