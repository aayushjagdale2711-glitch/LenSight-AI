import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
    GEMINI_MODEL = "gemini-3.5-flash-lite"
    GEMINI_API_URL = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_MODEL}:generateContent"
    )
    GEMINI_TIMEOUT = 120
    GEMINI_TEMPERATURE = 0.1

    MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB
    ALLOWED_IMAGE_MIMES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
    ALLOWED_VIDEO_MIMES = {"video/mp4", "video/webm", "video/quicktime", "video/x-msvideo"}
    ALLOWED_AUDIO_MIMES = {
        "audio/mpeg", "audio/mp3", "audio/wav", "audio/x-wav",
        "audio/ogg", "audio/webm", "audio/mp4", "audio/aac",
        "audio/flac", "audio/x-flac", "audio/m4a", "audio/x-m4a"
    }

    VIDEO_FRAME_COUNT = 5
    VIDEO_FRAME_WINDOW = 5.0  # seconds

    # Shared JSON schema block appended to prompts.
    RESPONSE_SCHEMA = """
Return ONLY valid JSON in exactly this structure:

{
  "assessment": "Potentially Synthetic" | "No Major Synthetic Indicators Observed" | "Inconclusive",
  "confidence": 0-100,
  "risk_level": "LOW" | "MEDIUM" | "HIGH",
  "indicators": [
    {
      "name": "short indicator name",
      "severity": "LOW" | "MEDIUM" | "HIGH",
      "explanation": "short explanation"
    }
  ],
  "summary": "short forensic summary",
  "limitations": [
    "limitation 1",
    "limitation 2"
  ]
}
"""

    IMAGE_PROMPT = """
You are the analysis engine for a student prototype called DeepFakeShield AI.

Inspect the supplied image for visible characteristics that may indicate it is
AI-generated, synthetic, or digitally manipulated. Consider things like:
- Unnatural textures, lighting, or shadows
- Anatomical inconsistencies (hands, eyes, teeth, ears)
- Background warping or impossible geometry
- Compression artifacts, GAN fingerprints, or over-smoothing
- Inconsistent reflections, physics, or perspective

IMPORTANT:
- Do not claim an image is definitely real or definitely AI-generated.
- Keep the explanation concise and understandable.
- "confidence" means confidence in the assessment, not proof.
- Do not invent forensic tests that were not performed.
""" + RESPONSE_SCHEMA

    VIDEO_PROMPT = """
You are the analysis engine for a student prototype called DeepFakeShield AI.

You have been provided with __FRAME_COUNT__ frames extracted from the first
__WINDOW__ seconds of a video. Inspect these frames for visible characteristics
that may indicate the video is AI-generated, a deepfake, or digitally
manipulated. Consider things like:
- Unnatural textures, lighting, or shadows
- Anatomical inconsistencies (hands, eyes, teeth, ears)
- Background warping or impossible geometry
- Temporal inconsistencies between frames (flickering, morphing)
- Compression artifacts, GAN fingerprints, or over-smoothing
- Inconsistent reflections, physics, or perspective
- Face-swap boundary artifacts or blending issues

IMPORTANT:
- Do not claim a video is definitely real or definitely AI-generated.
- Keep the explanation concise and understandable.
- "confidence" means confidence in the assessment, not proof.
- Do not invent forensic tests that were not performed.
- Mention which frame(s) contributed to each indicator when possible.
""" + RESPONSE_SCHEMA

    AUDIO_PROMPT = """
You are the analysis engine for a student prototype called DeepFakeShield AI.

You have been provided with an audio file. Using your multimodal audio analysis
capabilities, inspect the audio carefully to determine whether it is:
- Natural human speech recorded from a real person, OR
- AI-generated / synthesized speech (TTS, voice cloning, deepfake audio), OR
- Digitally manipulated / spliced human audio

Consider the following forensic cues:
- Prosody and intonation: natural human speech has subtle variations in pitch,
  rhythm, stress, and emotion. AI voices often sound overly smooth, flat, or
  have unnatural cadence.
- Breathing, lip smacks, and micro-pauses: real humans produce these naturally;
  AI often lacks or over-produces them.
- Background noise consistency: real recordings have consistent ambient noise;
  AI audio is often unnaturally clean or has inconsistent noise floors.
- Spectral artifacts: look for signs of vocoder artifacts, metallic timbre,
  robotic resonance, or frequency-band anomalies typical of neural TTS.
- Pronunciation anomalies: AI may mispronounce rare words, mishandle homographs,
  or produce unnatural phoneme transitions.
- Emotional authenticity: genuine emotion vs. simulated/flat affect.
- Splicing / editing artifacts: abrupt cuts, mismatched reverb, inconsistent
  room tone between segments.
- Voice cloning signatures: slight unnatural uniformity in vowel formants,
  "too perfect" articulation, or absence of natural vocal fry/creak.

IMPORTANT:
- Do not claim audio is definitely real or definitely AI-generated.
- Keep the explanation concise and understandable.
- "confidence" means confidence in the assessment, not proof.
- Do not invent forensic tests that were not performed.
- In the "summary", explicitly state whether the audio appears to be
  HUMAN SPEECH, AI-GENERATED SPEECH, or INCONCLUSIVE, and briefly justify.
""" + RESPONSE_SCHEMA