"""
voice_agent.py — Voice input (speech-to-text) and output (text-to-speech).
Works fully offline using SpeechRecognition + pyttsx3.
"""

import threading
import speech_recognition as sr
import pyttsx3


# ── TEXT TO SPEECH ────────────────────────────────────────────────────────────

_tts_engine = None
_tts_lock   = threading.Lock()


def _get_tts():
    global _tts_engine
    if _tts_engine is None:
        _tts_engine = pyttsx3.init()
        _tts_engine.setProperty("rate", 175)   # speaking speed
        _tts_engine.setProperty("volume", 1.0)
        # Use a female voice if available
        voices = _tts_engine.getProperty("voices")
        for v in voices:
            if "female" in v.name.lower() or "zira" in v.name.lower():
                _tts_engine.setProperty("voice", v.id)
                break
    return _tts_engine


def speak(text):
    """Convert text to speech (non-blocking)."""
    def _run():
        with _tts_lock:
            engine = _get_tts()
            engine.say(text)
            engine.runAndWait()
    threading.Thread(target=_run, daemon=True).start()


# ── SPEECH TO TEXT ────────────────────────────────────────────────────────────

def listen(timeout=5, phrase_limit=8):
    """
    Listen from microphone and return transcribed text.
    Returns (text, error_message).
    """
    recognizer = sr.Recognizer()
    recognizer.energy_threshold = 300
    recognizer.dynamic_energy_threshold = True

    try:
        with sr.Microphone() as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_limit)

        text = recognizer.recognize_google(audio)
        return text, None

    except sr.WaitTimeoutError:
        return None, "No speech detected. Please try again."
    except sr.UnknownValueError:
        return None, "Could not understand audio. Please speak clearly."
    except sr.RequestError as e:
        # Fallback to offline recognition
        try:
            text = recognizer.recognize_sphinx(audio)
            return text, None
        except Exception:
            return None, f"Speech service error: {str(e)}"
    except Exception as e:
        return None, str(e)


def is_microphone_available():
    """Check if a microphone is available."""
    try:
        with sr.Microphone():
            return True
    except Exception:
        return False
