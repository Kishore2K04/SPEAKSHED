from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timedelta
import dateutil.parser
import pytz
import uuid
import logging

logger = logging.getLogger("scheduler")


class SchedulerManager:
    def __init__(self, db_path, timezone_str, on_alert=None):
        self.db_path = db_path
        self.tz = pytz.timezone(timezone_str)
        self.scheduler = BackgroundScheduler(timezone=self.tz)
        self.task_job_map = {}  # task_id -> job_id
        self.on_alert = on_alert  # callback(task_id, task_text) -- set by main.py

    def start(self):
        self.scheduler.start()

    def shutdown(self):
        try:
            self.scheduler.shutdown(wait=False)
        except Exception as e:
            logger.warning(f"Shutdown error: {e}")

    def _run_alert(self, task_id, task_text):
        if self.on_alert:
            try:
                self.on_alert(task_id, task_text)
            except Exception as e:
                logger.error(f"on_alert callback failed: {e}")

    def schedule_task(self, task_id, task_text, iso_time, recurring=None):
        try:
            dt = dateutil.parser.isoparse(iso_time)
        except Exception:
            dt = dateutil.parser.parse(iso_time)

        if dt.tzinfo is None:
            dt = self.tz.localize(dt)
        else:
            dt = dt.astimezone(self.tz)

        job_id = f"task-{task_id}-{uuid.uuid4().hex[:8]}"

        if recurring == "day":
            trigger = CronTrigger(hour=dt.hour, minute=dt.minute, timezone=self.tz)
        elif recurring == "week":
            trigger = CronTrigger(day_of_week=dt.weekday(), hour=dt.hour, minute=dt.minute, timezone=self.tz)
        else:
            trigger = DateTrigger(run_date=dt, timezone=self.tz)

        job = self.scheduler.add_job(
            self._run_alert,
            trigger=trigger,
            args=[task_id, task_text],
            id=job_id,
            replace_existing=True
        )

        self.task_job_map[task_id] = job_id
        return job

    def schedule_from_db_row(self, row):
        # row is a dict here (from database.py), always has .get()
        if row.get("status") != "pending":
            return
        try:
            self.schedule_task(
                row["id"],
                row["task"],
                row["time"],
                row.get("recurring")
            )
        except Exception as e:
            logger.error(f"Failed to reschedule task {row.get('id')}: {e}")

    def remove_job_for_task(self, task_id):
        job_id = self.task_job_map.get(task_id)
        if job_id:
            try:
                self.scheduler.remove_job(job_id)
            except Exception as e:
                logger.warning(f"Could not remove job {job_id}: {e}")
            del self.task_job_map[task_id]

    def snooze_task(self, task_id, minutes=10):
        new_dt = datetime.now(tz=self.tz) + timedelta(minutes=minutes)
        new_iso = new_dt.isoformat()
        self.remove_job_for_task(task_id)
        return new_iso