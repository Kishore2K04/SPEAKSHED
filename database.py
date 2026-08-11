import sqlite3
import json

def _conn(db_path="tasks.db"):
    return sqlite3.connect(db_path)

def init_db(db_path="tasks.db"):
    c = _conn(db_path)
    cur = c.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task TEXT NOT NULL,
            time TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            recurring TEXT DEFAULT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    c.commit()
    c.close()

def add_task_db(task, iso_time, status="pending", recurring=None, db_path="tasks.db"):
    c = _conn(db_path)
    cur = c.cursor()
    cur.execute(
        "INSERT INTO tasks (task, time, status, recurring) VALUES (?, ?, ?, ?)",
        (task, iso_time, status, json.dumps(recurring) if recurring else None)
    )
    c.commit()
    tid = cur.lastrowid
    c.close()
    return tid

def _row_to_dict(r):
    return {
        "id": r[0], "task": r[1], "time": r[2],
        "status": r[3], "recurring": json.loads(r[4]) if r[4] else None
    }

def list_tasks_db(db_path="tasks.db"):
    c = _conn(db_path)
    cur = c.cursor()
    cur.execute("SELECT id, task, time, status, recurring FROM tasks ORDER BY time")
    rows = cur.fetchall()
    c.close()
    return [_row_to_dict(r) for r in rows]

def get_pending_tasks_db(db_path="tasks.db"):
    c = _conn(db_path)
    cur = c.cursor()
    cur.execute("SELECT id, task, time, status, recurring FROM tasks WHERE status='pending' ORDER BY time")
    rows = cur.fetchall()
    c.close()
    return [_row_to_dict(r) for r in rows]

def get_next_task_db(db_path="tasks.db"):
    tasks = get_pending_tasks_db(db_path)
    return tasks[0] if tasks else None

def get_task_by_id_db(tid, db_path="tasks.db"):
    c = _conn(db_path)
    cur = c.cursor()
    cur.execute("SELECT id, task, time, status, recurring FROM tasks WHERE id=?", (tid,))
    r = cur.fetchone()
    c.close()
    return _row_to_dict(r) if r else None

def update_task_db(tid, task=None, time=None, status=None, recurring=None, db_path="tasks.db"):
    c = _conn(db_path)
    cur = c.cursor()
    fields, vals = [], []
    if task is not None:
        fields.append("task=?"); vals.append(task)
    if time is not None:
        fields.append("time=?"); vals.append(time)
    if status is not None:
        fields.append("status=?"); vals.append(status)
    if recurring is not None:
        fields.append("recurring=?"); vals.append(json.dumps(recurring))
    vals.append(tid)
    if fields:
        sql = "UPDATE tasks SET " + ", ".join(fields) + " WHERE id=?"
        cur.execute(sql, vals)
        c.commit()
    c.close()

def delete_task_db(tid, db_path="tasks.db"):
    c = _conn(db_path)
    cur = c.cursor()
    cur.execute("DELETE FROM tasks WHERE id=?", (tid,))
    c.commit()
    c.close()

def count_completed_today_db(db_path="tasks.db"):
    from datetime import date
    c = _conn(db_path)
    cur = c.cursor()
    cur.execute("SELECT COUNT(*) FROM tasks WHERE status='done'")
    n = cur.fetchone()[0]
    c.close()
    return n