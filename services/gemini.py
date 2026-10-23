import base64
import json

import requests

from config import Config


ALLOWED_ASSESSMENTS = {
    "Potentially Synthetic",
    "No Major Synthetic Indicators Observed",
    "Inconclusive",
}
ALLOWED_LEVELS = {"LOW", "MEDIUM", "HIGH"}


def _parse_raw(text):
    """Strip markdown fences and parse JSON."""
    text = (text or "").strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return json.loads(text.strip())


def _normalize(parsed):
    """Guarantee every field the frontend expects is present and valid."""
    if not isinstance(parsed, dict):
        parsed = {}

    assessment = parsed.get("assessment", "Inconclusive")
    if assessment not in ALLOWED_ASSESSMENTS:
        assessment = "Inconclusive"

    try:
        confidence = int(round(float(parsed.get("confidence", 0))))
    except (TypeError, ValueError):
        confidence = 0
    confidence = max(0, min(100, confidence))

    risk_level = str(parsed.get("risk_level", "MEDIUM")).upper()
    if risk_level not in ALLOWED_LEVELS:
        risk_level = "MEDIUM"

    indicators = []
    raw_ind = parsed.get("indicators") or []
    if isinstance(raw_ind, list):
        for ind in raw_ind:
            if not isinstance(ind, dict):
                continue
            severity = str(ind.get("severity", "LOW")).upper()
            if severity not in ALLOWED_LEVELS:
                severity = "LOW"
            indicators.append({
                "name": str(ind.get("name", "Unnamed")),
                "severity": severity,
                "explanation": str(ind.get("explanation", "")),
            })

    summary = str(parsed.get("summary", "No summary generated."))

    raw_lim = parsed.get("limitations") or []
    if isinstance(raw_lim, list):
        limitations = [str(x) for x in raw_lim if x]
    else:
        limitations = [str(raw_lim)]
    if not limitations:
        limitations = ["No limitations were specified by the model."]

    return {
        "assessment": assessment,
        "confidence": confidence,
        "risk_level": risk_level,
        "indicators": indicators,
        "summary": summary,
        "limitations": limitations,
    }


def _call_gemini(parts):
    """Send parts to the Gemini API and return the normalized result dict."""
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": Config.GEMINI_API_KEY,
    }

    payload = {
        "contents": [{"parts": parts}],
        "generationConfig": {
            "temperature": Config.GEMINI_TEMPERATURE,
            "responseMimeType": "application/json",
        },
    }

    resp = requests.post(
        Config.GEMINI_API_URL,
        headers=headers,
        json=payload,
        timeout=Config.GEMINI_TIMEOUT,
    )

    try:
        res_data = resp.json()
    except ValueError:
        raise RuntimeError(
            f"Gemini returned non-JSON (status {resp.status_code}): {resp.text[:500]}"
        )

    if resp.status_code != 200:
        detail = json.dumps(res_data.get("error", res_data), indent=2)
        raise RuntimeError(f"Gemini API error {resp.status_code}: {detail}")

    candidates = res_data.get("candidates", [])
    if not candidates:
        block = res_data.get("promptFeedback", {})
        raise RuntimeError(f"Gemini returned no candidates. Feedback: {block}")

    raw_text = "".join(
        p.get("text", "")
        for p in candidates[0].get("content", {}).get("parts", [])
    )

    try:
        parsed = _parse_raw(raw_text)
    except json.JSONDecodeError:
        raise RuntimeError(f"Gemini response was not valid JSON: {raw_text[:500]}")

    return _normalize(parsed)


def analyze_image(image_bytes, mime_type):
    """Analyze a single image with Gemini."""
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    parts = [
        {"text": Config.IMAGE_PROMPT},
        {"inline_data": {"mime_type": mime_type, "data": b64}},
    ]
    result = _call_gemini(parts)
    result["frames_analyzed"] = 0
    return result


def analyze_video_frames(frames):
    """
    Analyze extracted video frames with Gemini.

    `frames` is a list of dicts with keys: data (base64), mime_type, timestamp.
    """
    # Plain token replacement — safe with the JSON braces in the prompt.
    prompt = (
        Config.VIDEO_PROMPT
        .replace("__FRAME_COUNT__", str(len(frames)))
        .replace("__WINDOW__", str(Config.VIDEO_FRAME_WINDOW))
    )

    parts = [{"text": prompt}]
    for i, frame in enumerate(frames):
        parts.append({"text": f"[Frame {i + 1} — timestamp {frame['timestamp']}s]"})
        parts.append({
            "inline_data": {
                "mime_type": frame["mime_type"],
                "data": frame["data"],
            }
        })

    result = _call_gemini(parts)
    result["frames_analyzed"] = len(frames)
    result["frame_timestamps"] = [f["timestamp"] for f in frames]
    return result