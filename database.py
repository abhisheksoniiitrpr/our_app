"""
database.py
SQLite persistence layer for "Us — Our Little Space".

Design note: everything goes through this module so the storage backend
(SQLite now, Supabase later) can be swapped without touching app.py.
To migrate: replace the functions below with Supabase client calls that
return the same shapes (list[dict] / dict), keep the same function names.
"""

import sqlite3
import datetime
from contextlib import contextmanager

DB_PATH = "tasks.db"


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")  # safer for concurrent access
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Create tables if they don't exist. Safe to call every run."""
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user TEXT NOT NULL,                -- 'his' or 'her'
                title TEXT NOT NULL,
                description TEXT DEFAULT '',
                category TEXT DEFAULT 'Other',
                priority TEXT DEFAULT 'Medium',     -- High / Medium / Low
                due_time TEXT DEFAULT '',
                original_date TEXT NOT NULL,        -- date first created (YYYY-MM-DD)
                list_date TEXT NOT NULL,         -- which day's list it lives on
                completed INTEGER DEFAULT 0,
                completed_at TEXT,                  -- date it was completed
                carried_forward INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_user_date ON tasks(user, list_date)"
        )


def today_str():
    return datetime.date.today().isoformat()


# ---------------------------------------------------------------- CRUD ----

def add_task(user, title, description="", category="Other", priority="Medium", due_time=""):
    t = today_str()
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO tasks
               (user, title, description, category, priority, due_time,
                original_date, list_date, completed, carried_forward, created_at)
               VALUES (?,?,?,?,?,?,?,?,0,0,?)""",
            (user, title.strip(), description.strip(), category, priority,
             due_time, t, t, datetime.datetime.now().isoformat()),
        )


def get_tasks(user, date):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM tasks WHERE user=? AND list_date=? ORDER BY created_at",
            (user, date),
        ).fetchall()
        return [dict(r) for r in rows]


def toggle_complete(task_id):
    with get_conn() as conn:
        row = conn.execute("SELECT completed FROM tasks WHERE id=?", (task_id,)).fetchone()
        if row is None:
            return
        new_state = 0 if row["completed"] else 1
        conn.execute(
            "UPDATE tasks SET completed=?, completed_at=? WHERE id=?",
            (new_state, today_str() if new_state else None, task_id),
        )


def edit_task(task_id, title, description, category, priority, due_time):
    with get_conn() as conn:
        conn.execute(
            """UPDATE tasks SET title=?, description=?, category=?, priority=?, due_time=?
               WHERE id=?""",
            (title.strip(), description.strip(), category, priority, due_time, task_id),
        )


def delete_task(task_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM tasks WHERE id=?", (task_id,))


# ----------------------------------------------------- carry-forward ----

def carry_forward_tasks(user, list_date=None):
    """
    Move any still-incomplete task whose list_date is BEFORE today onto
    today's list. Because this UPDATEs the existing row (rather than
    inserting a new one), it can never create duplicates, and it correctly
    handles a task that's been sitting incomplete for several days — one
    UPDATE brings it straight to today regardless of how long it's been.
    Completed tasks are never touched.
    """
    list_date = list_date or today_str()
    with get_conn() as conn:
        conn.execute(
            """UPDATE tasks
               SET list_date=?, carried_forward=1
               WHERE user=? AND completed=0 AND list_date<?""",
            (list_date, user, list_date),
        )


# -------------------------------------------------------------- history ----

def get_history(user, date):
    """
    completed: tasks finished on `date`
    pending:   tasks that existed on `date` and were not yet done by then
    (a task existed on `date` if it was created on/before `date` and either
    still isn't completed, or was completed after `date`)
    """
    with get_conn() as conn:
        completed = conn.execute(
            "SELECT * FROM tasks WHERE user=? AND completed_at=?", (user, date)
        ).fetchall()
        pending = conn.execute(
            """SELECT * FROM tasks WHERE user=? AND original_date<=?
               AND (completed=0 OR completed_at>?)""",
            (user, date, date),
        ).fetchall()
        completed = [dict(r) for r in completed]
        pending = [dict(r) for r in pending]
        total = len(completed) + len(pending)
        pct = round(len(completed) / total * 100) if total else 0
        return {"completed": completed, "pending": pending, "pct": pct}


def get_available_dates(user):
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT DISTINCT original_date AS d FROM tasks WHERE user=?
               UNION SELECT DISTINCT completed_at AS d FROM tasks WHERE user=? AND completed_at IS NOT NULL
               ORDER BY d DESC""",
            (user, user),
        ).fetchall()
        return [r["d"] for r in rows]


# --------------------------------------------------------------- streaks ----

def get_streaks(user):
    """A day 'counts' if at least one task was completed that day."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT DISTINCT completed_at AS d FROM tasks WHERE user=? AND completed_at IS NOT NULL ORDER BY d DESC",
            (user,),
        ).fetchall()
    days = {datetime.date.fromisoformat(r["d"]) for r in rows}
    if not days:
        return {"current": 0, "best": 0}

    # current streak: walk back from today (allow today to be un-done yet)
    today = datetime.date.today()
    current = 0
    cursor = today
    if cursor not in days:
        cursor -= datetime.timedelta(days=1)
    while cursor in days:
        current += 1
        cursor -= datetime.timedelta(days=1)

    # best streak: longest run in the whole set
    best = 0
    run = 0
    for d in sorted(days):
        if (d - datetime.timedelta(days=1)) in days:
            run += 1
        else:
            run = 1
        best = max(best, run)

    return {"current": current, "best": best}


def progress_for(user, date):
    tasks = get_tasks(user, date)
    total = len(tasks)
    done = sum(1 for t in tasks if t["completed"])
    return done, total
