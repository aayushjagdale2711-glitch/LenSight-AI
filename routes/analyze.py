import base64
import json
import re
import io
import tempfile
import os

import requests
from flask import Blueprint, request, jsonify

from config import Config

analyze_bp = Blueprint("analyze", __name__)


def classify_media(mime_type):
    if mime_type in Config.ALLOWED_IMAGE_MIMES:
        return "image"
    if mime_type in Config.ALLOWED_VIDEO_MIMES:
        return "video"
    if mime_type in Config.ALLOWED_AUDIO_MIMES:
        return "audio"
    return "unknown"


def extract_json(text):
    """Attempt to extract JSON from model response text."""
    if not text:
        return None
    # Try direct JSON
    try:
        return json.loads(text)
    except Exception:
        pass
    # Try to find JSON in code block or inline
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            return None
    return None


def call_gemini(parts):
    """Send a list of parts (text + inline_data) to Gemini."""
    if not Config.GEMINI_API_KEY:
        return None, "GEMINI_API_KEY is not set"

    payload = {
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": {
            "temperature": Config.GEMINI_TEMPERATURE,
            "responseMimeType": "application/json",
        },
    }

    try:
        resp = requests.post(
            Config.GEMINI_API_URL,
            params={"key": Config.GEMINI_API_KEY},
            json=payload,
            timeout=Config.GEMINI_TIMEOUT,
        )
    except requests.RequestException as e:
        return None, f"Request failed: {e}"

    if resp.status_code != 200:
        return None, f"Gemini HTTP {resp.status_code}: {resp.text[:400]}"

    try:
        data = resp.json()
    except Exception:
        return None, "Gemini returned invalid JSON"

    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception:
        return None, f"Unexpected Gemini response structure: {str(data)[:400]}"

    parsed = extract_json(text)
    if parsed is None:
        return None, f"Could not parse JSON from Gemini output: {text[:400]}"

    return parsed, None


def analyze_image(file_bytes, mime_type):
    b64 = base64.b64encode(file_bytes).decode("utf-8")
    parts = [
        {"text": Config.IMAGE_PROMPT},
        {"inline_data": {"mime_type": mime_type, "data": b64}},
    ]
    return call_gemini(parts)


def analyze_video(file_bytes, mime_type, original_filename):
    """Extract frames and send to Gemini."""
    import imageio.v3 as iio

    suffix = os.path.splitext(original_filename)[1] or ".mp4"
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name

        # Read metadata
        try:
            meta = iio.immeta(tmp_path, plugin="pyav")
            fps = meta.get("fps", 25) or 25
            duration = meta.get("duration", Config.VIDEO_FRAME_WINDOW) or Config.VIDEO_FRAME_WINDOW
        except Exception:
            fps = 25
            duration = Config.VIDEO_FRAME_WINDOW

        window = min(Config.VIDEO_FRAME_WINDOW, float(duration))
        n_frames = Config.VIDEO_FRAME_COUNT
        timestamps = [round(window * (i + 1) / (n_frames + 1), 2) for i in range(n_frames)]

        frames_b64 = []
        frames = iio.imiter(tmp_path, plugin="pyav")
        from PIL import Image

        frame_list = []
        max_needed = int(window * fps) + 1
        for idx, frame in enumerate(frames):
            if idx > max_needed:
                break
            frame_list.append(frame)

        if not frame_list:
            return None, "No frames could be extracted from the video"

        for ts in timestamps:
            frame_idx = min(int(ts * fps), len(frame_list) - 1)
            frame = frame_list[frame_idx]
            img = Image.fromarray(frame)
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=85)
            frames_b64.append(base64.b64encode(buf.getvalue()).decode("utf-8"))

    except Exception as e:
        return None, f"Frame extraction failed: {e}"
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass

    prompt = Config.VIDEO_PROMPT.replace("__FRAME_COUNT__", str(len(frames_b64))) \
                                 .replace("__WINDOW__", str(Config.VIDEO_FRAME_WINDOW))

    parts = [{"text": prompt}]
    for b64 in frames_b64:
        parts.append({"inline_data": {"mime_type": "image/jpeg", "data": b64}})

    result, err = call_gemini(parts)
    if result is not None:
        result["frames_analyzed"] = len(frames_b64)
        result["frame_timestamps"] = timestamps
    return result, err


def analyze_audio(file_bytes, mime_type):
    """Send audio to Gemini multimodal for human vs. AI classification."""
    b64 = base64.b64encode(file_bytes).decode("utf-8")
    parts = [
        {"text": Config.AUDIO_PROMPT},
        {"inline_data": {"mime_type": mime_type, "data": b64}},
    ]
    return call_gemini(parts)


@analyze_bp.route("/analyze", methods=["POST"])
def analyze():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    f = request.files["file"]
    if not f or not f.filename:
        return jsonify({"error": "Empty file"}), 400

    file_bytes = f.read()
    if len(file_bytes) == 0:
        return jsonify({"error": "Empty file"}), 400
    if len(file_bytes) > Config.MAX_FILE_SIZE:
        return jsonify({"error": f"File exceeds {Config.MAX_FILE_SIZE // (1024*1024)} MB limit"}), 400

    mime = f.mimetype or ""
    kind = classify_media(mime)

    # Fallback: infer from extension for audio
    if kind == "unknown":
        ext = os.path.splitext(f.filename)[1].lower()
        ext_map = {
            ".mp3": "audio/mpeg", ".wav": "audio/wav", ".ogg": "audio/ogg",
            ".flac": "audio/flac", ".m4a": "audio/mp4", ".aac": "audio/aac",
        }
        if ext in ext_map:
            mime = ext_map[ext]
            kind = "audio"

    if kind == "image":
        result, err = analyze_image(file_bytes, mime)
    elif kind == "video":
        result, err = analyze_video(file_bytes, mime, f.filename)
    elif kind == "audio":
        result, err = analyze_audio(file_bytes, mime)
    else:
        return jsonify({"error": f"Unsupported file type: {mime}"}), 400

    if err:
        return jsonify({"error": "Analysis failed", "details": err}), 500

    result["media_type"] = kind
    return jsonify(result), 200