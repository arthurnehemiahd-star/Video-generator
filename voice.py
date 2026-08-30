"""
voice.py
--------
Speech in/out for the assistant. Uses SpeechRecognition (mic -> text)
and pyttsx3 (text -> speech) — both are OPTIONAL dependencies, listed in
requirements-voice.txt rather than the main requirements.txt, since they
need system-level audio libraries (PortAudio, an OS TTS engine) that not
every machine has, and pulling them in by default would break setup for
anyone who just wants text chat.

IMPORTANT: this module could not be tested with real audio hardware in
the environment this project was built in (no microphone/speaker, no
network to install the packages). The code follows the standard,
well-documented usage pattern for both libraries, but you should treat
this as untested until you've tried it on your own machine — see the
troubleshooting notes below if something doesn't work first try.

Install with:
    pip install -r requirements-voice.txt
On Linux you'll likely also need: sudo apt install portaudio19-dev espeak
"""

class VoiceNotAvailableError(Exception):
    pass


def _import_voice_libs():
    try:
        import speech_recognition as sr
        import pyttsx3
        return sr, pyttsx3
    except ImportError as e:
        raise VoiceNotAvailableError(
            "Voice packages aren't installed. Run: "
            "pip install -r requirements-voice.txt "
            "(Linux also needs: sudo apt install portaudio19-dev espeak)"
        ) from e


def listen(timeout: float = 8.0) -> str:
    """
    Records from the default microphone until a pause, then transcribes
    with the recognizer's default engine (Google's free web API — no key
    needed, but it does require internet access).
    """
    sr, _ = _import_voice_libs()
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
        audio = recognizer.listen(source, timeout=timeout)
    try:
        return recognizer.recognize_google(audio)
    except sr.UnknownValueError:
        return ""
    except sr.RequestError as e:
        raise VoiceNotAvailableError(f"Speech recognition service error: {e}") from e


def speak(text: str) -> None:
    """Speaks text aloud through the default system speaker, offline."""
    _, pyttsx3 = _import_voice_libs()
    engine = pyttsx3.init()
    engine.say(text)
    engine.runAndWait()


def is_available() -> bool:
    try:
        _import_voice_libs()
        return True
    except VoiceNotAvailableError:
        return False
