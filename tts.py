import pyttsx3
import threading
import datetime

_engine = None
_lock = threading.Lock()

GREETINGS = [
    "Voice scheduler active. Let's make today count, sir.",
    "Voice scheduler active. Good to have you back.",
    "Voice scheduler active. One step at a time, sir. I've got your back.",
    "Voice scheduler active. Ready when you are.",
    "Voice scheduler active. New day, clean slate.",
    "Voice scheduler active. Let's get things done, shall we?",
    "Voice scheduler active. I've been keeping an eye on your tasks, sir.",
    "Voice scheduler active. Whatever's on your plate today, we'll handle it.",
    "Voice scheduler active. Systems online. You're in good hands.",
    "Voice scheduler active. Let's turn that to-do list into a done list.",
    "Voice scheduler active. Rise and shine, sir.",
    "Voice scheduler active. Let's make some progress today.",
    "Voice scheduler active. All systems nominal, sir.",
    "Voice scheduler active. Standing by, as always.",
]

DONE_PHRASES = [
    "Nice one, sir.",
    "Done and dusted.",
    "One less thing to worry about.",
    "Marked complete, sir.",
    "Good work.",
]


def _init():
    global _engine
    if _engine is None:
        _engine = pyttsx3.init()
        rate = _engine.getProperty('rate')
        _engine.setProperty('rate', rate - 15)
        voices = _engine.getProperty("voices")
        for v in voices:
            if "male" in v.name.lower() or "david" in v.name.lower():
                _engine.setProperty("voice", v.id)
                break


def speak(text, blocking=False):
    if not text:
        return
    _init()

    def _say(t):
        try:
            with _lock:
                _engine.say(t)
                _engine.runAndWait()
        except Exception:
            pass

    if blocking:
        _say(text)
    else:
        threading.Thread(target=_say, args=(text,), daemon=True).start()


def get_daily_greeting(pending_count=None):
    day_index = datetime.date.today().timetuple().tm_yday
    line = GREETINGS[day_index % len(GREETINGS)]
    if pending_count is not None:
        if pending_count == 0:
            line += " No pending tasks right now."
        elif pending_count == 1:
            line += " You have 1 task on the board."
        else:
            line += f" You have {pending_count} tasks on the board."
    return line


def get_done_phrase():
    import random
    return random.choice(DONE_PHRASES)


def jarvis_reminder(message):
    hour = datetime.datetime.now().hour
    if hour < 12:
        greeting = "Good morning sir."
    elif hour < 18:
        greeting = "Good afternoon sir."
    else:
        greeting = "Good evening sir."
    now = datetime.datetime.now().strftime("%I:%M %p")
    final = f"{greeting} This is your task scheduler. The time is {now}. I am reminding you that {message}, sir."
    speak(final)