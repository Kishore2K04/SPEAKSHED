import os
import json
import logging
import webbrowser
from datetime import datetime

import database as db
from scheduler import SchedulerManager
from intents import parse_intent
import tts
from stt import listen_for_wake_word, listen_once

try:
    import pystray
    from PIL import Image, ImageDraw
    TRAY_AVAILABLE = True
except ImportError:
    TRAY_AVAILABLE = False

CONFIG_PATH = "config.json"
DB_PATH = "tasks.db"
SITES_PATH = "sites.json"

logging.basicConfig(
    filename="scheduler.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("main")


def load_config():
    if not os.path.exists(CONFIG_PATH):
        default_cfg = {
            "timezone": "Asia/Kolkata",
            "wake_word": "jarvis",
            "quick_add_prefix": "quick",
            "vosk_model_path": "vosk-model",
            "listen_timeout": 8,
            "confirm_before_saving": True
        }
        with open(CONFIG_PATH, "w") as f:
            json.dump(default_cfg, f, indent=4)
        return default_cfg
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)


def load_sites():
    if not os.path.exists(SITES_PATH):
        return {}
    with open(SITES_PATH, "r") as f:
        return json.load(f)


class VoiceApp:
    def __init__(self):
        self.cfg = load_config()
        self.sites = load_sites()
        db.init_db(DB_PATH)
        self.scheduler = SchedulerManager(DB_PATH, self.cfg["timezone"], on_alert=self.handle_alert)
        self.last_fired_task_id = None
        self.running = True

    # -----------------------------------------------------
    def start(self):
        self.scheduler.start()
        for row in db.get_pending_tasks_db(DB_PATH):
            self.scheduler.schedule_from_db_row(row)

        pending = db.get_pending_tasks_db(DB_PATH)
        greeting = tts.get_daily_greeting(pending_count=len(pending))
        tts.speak(greeting, blocking=True)
        logger.info("App started. %d pending tasks.", len(pending))

        if TRAY_AVAILABLE:
            import threading
            threading.Thread(target=self._run_tray, daemon=True).start()

        self.main_loop()

    def _run_tray(self):
        img = Image.new("RGB", (64, 64), "black")
        d = ImageDraw.Draw(img)
        d.ellipse((8, 8, 56, 56), fill="cyan")
        icon = pystray.Icon("voice_scheduler", img, "Voice Scheduler",
                             menu=pystray.Menu(
                                 pystray.MenuItem("Quit", lambda: self.stop())
                             ))
        icon.run()

    def stop(self):
        self.running = False
        self.scheduler.shutdown()
        os._exit(0)

    # -----------------------------------------------------
    def main_loop(self):
        wake_word = self.cfg.get("wake_word", "jarvis")
        model_path = self.cfg.get("vosk_model_path", "vosk-model")
        timeout = self.cfg.get("listen_timeout", 8)

        while self.running:
            try:
                logger.info("Listening for wake word...")
                heard = listen_for_wake_word(wake_word, model_path)
                logger.info("Wake word triggered by phrase: %s", heard)
                tts.speak("Yes sir?", blocking=True)

                command_text = listen_once(timeout=timeout, model_path=model_path)
                logger.info("Command heard: %s", command_text)

                if not command_text:
                    tts.speak("Sorry, I didn't catch that. Try again.", blocking=True)
                    continue

                self.handle_command(command_text)

            except KeyboardInterrupt:
                self.stop()
            except Exception as e:
                logger.error("Main loop error: %s", e)
                tts.speak("Something went wrong, sir. Let's try again.", blocking=True)

    # -----------------------------------------------------
    def handle_command(self, text):
        intent = parse_intent(text, self.cfg)
        itype = intent.get("type")
        logger.info("Parsed intent: %s", intent)

        if itype == "exit":
            tts.speak("Shutting down. Goodbye sir.", blocking=True)
            self.stop()

        elif itype == "help":
            tts.speak("You can ask me to remind you of something, list tasks, delete a task, "
                       "mark one done, snooze, ask what's next, or open a website.", blocking=True)

        elif itype == "create_task":
            self._create_task(intent)

        elif itype == "list_tasks":
            self._list_tasks()

        elif itype == "next_task":
            self._next_task()

        elif itype == "delete_task":
            self._delete_task(intent["task_id"])

        elif itype == "mark_done":
            self._mark_done(intent["task_id"])

        elif itype == "snooze":
            self._snooze(intent)

        elif itype == "summary":
            self._summary()

        elif itype == "open_site":
            self._open_site(intent["site"])

        elif itype == "play_youtube":
            self._play_youtube(intent["query"])

        else:
            tts.speak("I didn't understand that. Could you rephrase?", blocking=True)

    # -----------------------------------------------------
    def _create_task(self, intent):
        task_text = intent["task"]
        iso_time = intent["time"]
        recurring = intent.get("recurring")

        if self.cfg.get("confirm_before_saving", True):
            dt = datetime.fromisoformat(iso_time)
            time_str = dt.strftime("%I:%M %p on %d %b")
            tts.speak(f"Got it sir. Reminding you to {task_text} at {time_str}.", blocking=True)

        tid = db.add_task_db(task_text, iso_time, recurring=recurring, db_path=DB_PATH)
        self.scheduler.schedule_task(tid, task_text, iso_time, recurring=recurring)
        logger.info("Task created: id=%s text=%s time=%s recurring=%s", tid, task_text, iso_time, recurring)

    def _list_tasks(self):
        tasks = db.get_pending_tasks_db(DB_PATH)
        if not tasks:
            tts.speak("You have no pending tasks, sir.", blocking=True)
            return
        tts.speak(f"You have {len(tasks)} pending tasks.", blocking=True)
        for t in tasks[:5]:
            dt = datetime.fromisoformat(t["time"])
            tts.speak(f"Task {t['id']}: {t['task']} at {dt.strftime('%I:%M %p on %d %b')}", blocking=True)

    def _next_task(self):
        t = db.get_next_task_db(DB_PATH)
        if not t:
            tts.speak("Nothing on your schedule right now, sir.", blocking=True)
            return
        dt = datetime.fromisoformat(t["time"])
        tts.speak(f"Your next task is: {t['task']}, at {dt.strftime('%I:%M %p on %d %b')}.", blocking=True)

    def _delete_task(self, task_id):
        self.scheduler.remove_job_for_task(task_id)
        db.delete_task_db(task_id, db_path=DB_PATH)
        tts.speak("Task deleted, sir.", blocking=True)
        logger.info("Task deleted: id=%s", task_id)

    def _mark_done(self, task_id):
        db.update_task_db(task_id, status="done", db_path=DB_PATH)
        self.scheduler.remove_job_for_task(task_id)
        tts.speak(tts.get_done_phrase(), blocking=True)
        logger.info("Task marked done: id=%s", task_id)

    def _snooze(self, intent):
        task_id = intent.get("task_id") or self.last_fired_task_id
        if not task_id:
            tts.speak("I'm not sure which task to snooze, sir.", blocking=True)
            return
        minutes = intent.get("minutes", 10)
        new_iso = self.scheduler.snooze_task(task_id, minutes)
        db.update_task_db(task_id, time=new_iso, db_path=DB_PATH)
        row = db.get_task_by_id_db(task_id, db_path=DB_PATH)
        if row:
            self.scheduler.schedule_from_db_row(row)
        tts.speak(f"Snoozed for {minutes} minutes, sir.", blocking=True)
        logger.info("Task snoozed: id=%s minutes=%s", task_id, minutes)

    def _summary(self):
        done_count = db.count_completed_today_db(DB_PATH)
        pending = db.get_pending_tasks_db(DB_PATH)
        tts.speak(
            f"Today you've completed {done_count} tasks. You have {len(pending)} still pending.",
            blocking=True
        )

    def _open_site(self, site_name):
        site_name = site_name.strip().lower()
        url = self.sites.get(site_name)
        if not url:
            url = f"https://{site_name.replace(' ', '')}.com"
            tts.speak(f"I don't have that saved, trying {url}", blocking=True)
        else:
            tts.speak(f"Opening {site_name}, sir.", blocking=True)
        webbrowser.open(url)
        logger.info("Opened site: %s -> %s", site_name, url)

    def _play_youtube(self, query):
        url = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"
        tts.speak(f"Searching YouTube for {query}, sir.", blocking=True)
        webbrowser.open(url)
        logger.info("YouTube search: %s", query)

    # -----------------------------------------------------
    def handle_alert(self, task_id, task_text):
        """Called by scheduler when a reminder fires."""
        self.last_fired_task_id = task_id
        tts.jarvis_reminder(task_text)
        logger.info("Alert fired for task %s: %s", task_id, task_text)

        # listen briefly for an in-the-moment "snooze"
        heard = listen_once(timeout=6, model_path=self.cfg.get("vosk_model_path", "vosk-model"))
        if heard and "snooze" in heard.lower():
            from intents import parse_intent as _pi
            intent = _pi(heard, self.cfg)
            self._snooze(intent)


if __name__ == "__main__":
    app = VoiceApp()
    app.start()