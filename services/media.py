import base64
import io
import mimetypes
import tempfile
import os
import sys

# Guaranteed to be available after the app.py dependency resolution check
import imageio.v3 as iio
from PIL import Image

from config import Config


def read_and_validate_file(file):
    """Read the uploaded file and determine its validated MIME and media type."""
    file_bytes = file.read()
    if not file_bytes:
        return {"error": "The uploaded file is empty."}

    if len(file_bytes) > Config.MAX_FILE_SIZE:
        mb = Config.MAX_FILE_SIZE // (1024 * 1024)
        return {"error": f"File exceeds the {mb} MB limit."}

    mime_type = file.mimetype
    if not mime_type or mime_type == "application/octet-stream":
        mime_type, _ = mimetypes.guess_type(file.filename or "")

    if not mime_type:
        return {"error": "Could not determine the file type."}

    if mime_type in Config.ALLOWED_IMAGE_MIMES:
        media_type = "image"
    elif mime_type in Config.ALLOWED_VIDEO_MIMES:
        media_type = "video"
    else:
        allowed = sorted(Config.ALLOWED_IMAGE_MIMES | Config.ALLOWED_VIDEO_MIMES)
        return {"error": f"Unsupported file type: {mime_type}. Allowed: {', '.join(allowed)}"}

    return {
        "bytes": file_bytes,
        "mime_type": mime_type,
        "media_type": media_type,
    }


def extract_video_frames(video_bytes, count=5, window=5.0):
    """
    Extract `count` frames evenly spaced in the first `window` seconds of a video.
    Uses imageio + imageio-ffmpeg (bundled ffmpeg binary, no system dependency).

    Returns: [{"data": base64_jpeg, "mime_type": "image/jpeg", "timestamp": float}, ...]
    """
    tmp_path = None
    try:
        # delete=False is required for Windows to release file access to FFmpeg
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
            tmp.write(video_bytes)
            tmp_path = tmp.name

        try:
            meta = iio.immeta(tmp_path, plugin="FFMPEG")
        except Exception as e:
            raise ValueError(f"FFmpeg failed to probe video metadata: {str(e)}")

        fps = float(meta.get("fps") or 30.0)
        duration = float(meta.get("duration") or 0.0)

        if duration <= 0:
            try:
                nframes = iio.improps(tmp_path, plugin="FFMPEG").shape[0]
                duration = nframes / fps
            except Exception:
                duration = window

        effective_window = min(window, duration)
        if effective_window <= 0:
            raise ValueError("Video duration is too short to extract frames.")

        if count == 1:
            timestamps = [effective_window / 2.0]
        else:
            step = effective_window / count
            timestamps = [step * (i + 0.5) for i in range(count)]

        frames = []
        for ts in timestamps:
            frame_idx = int(ts * fps)
            try:
                frame = iio.imread(tmp_path, index=frame_idx, plugin="FFMPEG")
            except Exception:
                # If an individual frame index fails, continue to get other frames
                continue

            img = Image.fromarray(frame)
            if img.mode != "RGB":
                img = img.convert("RGB")

            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=85)
            b64 = base64.b64encode(buf.getvalue()).decode("utf-8")

            frames.append({
                "data": b64,
                "mime_type": "image/jpeg",
                "timestamp": round(ts, 2),
            })

        if not frames:
            raise ValueError("No frames could be extracted from the video file.")

        return frames

    finally:
        # Explicit file cleanup for Windows OS stability
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass