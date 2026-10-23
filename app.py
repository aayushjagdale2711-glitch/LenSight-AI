import subprocess
import sys

def ensure_dependencies():
    """
    Checks for missing libraries and automatically installs them 
    into the active running Python interpreter environment.
    """
    dependencies = {
        "imageio": "imageio",
        "imageio_ffmpeg": "imageio-ffmpeg",
        "PIL": "pillow",
        "requests": "requests",
        "flask_cors": "flask-cors"
    }
    
    to_install = []
    for module_name, package_name in dependencies.items():
        try:
            __import__(module_name)
        except ImportError:
            to_install.append(package_name)

    if to_install:
        print("-" * 58)
        print("  DeepFakeShield AI — Environment Initialization")
        print(f"  Missing libraries detected: {to_install}")
        print(f"  Target path: {sys.executable}")
        print("  Attempting automatic package installation...")
        print("-" * 58)
        try:
            # Runs pip directly against the running interpreter to prevent environment mismatches
            subprocess.check_call([sys.executable, "-m", "pip", "install", *to_install])
            print("\n[*] Installation successful! Reloading packages...\n")
        except Exception as e:
            print(f"\n[!] Automatic installation failed: {e}")
            print(f"[!] Please manually run the following in your command prompt:")
            print(f"    {sys.executable} -m pip install {' '.join(to_install)}")
            print("-" * 58)
            sys.exit(1)

# Run the dependency checker before importing any application modules
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

if __name__ == "__main__":
    app = create_app()
    print("-" * 58)
    print("  DeepFakeShield AI Server")
    print("  URL: http://127.0.0.1:5000")
    print("  Model: Gemini")
    print("  Video support: Active (imageio-ffmpeg)")
    print("-" * 58)
    if not Config.GEMINI_API_KEY:
        print("  WARNING: GEMINI_API_KEY is not set. API calls will fail.")
    print()
    app.run(host="127.0.0.1", port=5000, debug=True)