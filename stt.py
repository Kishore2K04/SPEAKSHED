import json
import time
import vosk
import pyaudio

RATE = 16000
CHUNK = 4000

model = None
recognizer = None


def init_model(model_path="vosk-model"):
    global model, recognizer
    if model is None:
        model = vosk.Model(model_path)
        recognizer = vosk.KaldiRecognizer(model, RATE)


def listen_once(timeout=8, model_path="vosk-model"):
    """Blocking single-shot listen. Returns transcribed text or ''."""
    init_model(model_path)
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paInt16, channels=1,
                     rate=RATE, input=True, frames_per_buffer=CHUNK)
    stream.start_stream()
    start = time.time()
    partial = ""
    try:
        while True:
            data = stream.read(CHUNK, exception_on_overflow=False)
            if recognizer.AcceptWaveform(data):
                res = json.loads(recognizer.Result())
                text = res.get("text", "").strip()
                stream.stop_stream()
                stream.close()
                p.terminate()
                return text
            else:
                res = json.loads(recognizer.PartialResult())
                partial = res.get("partial", "")
            if time.time() - start > timeout:
                stream.stop_stream()
                stream.close()
                p.terminate()
                return partial
    except Exception:
        try:
            stream.stop_stream()
            stream.close()
            p.terminate()
        except Exception:
            pass
        return ""


def listen_for_wake_word(wake_word="jarvis", model_path="vosk-model"):
    """Blocks until the wake word is heard in a phrase. Returns the full phrase heard."""
    init_model(model_path)
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paInt16, channels=1,
                     rate=RATE, input=True, frames_per_buffer=CHUNK)
    stream.start_stream()
    try:
        while True:
            data = stream.read(CHUNK, exception_on_overflow=False)
            if recognizer.AcceptWaveform(data):
                res = json.loads(recognizer.Result())
                text = res.get("text", "").strip().lower()
                if wake_word in text:
                    stream.stop_stream()
                    stream.close()
                    p.terminate()
                    return text
    except Exception:
        try:
            stream.stop_stream()
            stream.close()
            p.terminate()
        except Exception:
            pass
        return ""