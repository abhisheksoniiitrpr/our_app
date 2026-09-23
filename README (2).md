# Us — Our Little Space ❤️

A tiny, private, black/red-themed daily task manager for two people. One Home
page, two personal task lists (His / Her), a combined "Us" view, and a
History page — all in one Streamlit app.

## Features
- Add / edit / delete / complete tasks, each with priority, category, due time
- Automatic carry-forward: unfinished tasks move to today, with no duplicates,
  even if the app wasn't opened for several days
- Filters (All / Pending / Completed) and sorting (priority / due time / creation)
- Simple PIN login per person (via Streamlit secrets, not hard-coded)
- History page with completion % per day
- Simple streak tracker (current + best)
- "Send some love" quick-message buttons

## Project structure
```
couples-task-app/
├── app.py              # all pages + navigation (sidebar radio)
├── database.py         # SQLite layer (swap this file for Supabase later)
├── auth.py             # PIN gate
├── assets/styles.css   # dark romantic theme
├── requirements.txt
├── .gitignore
├── .streamlit/secrets.toml.example
└── README.md
```

## Run locally
```bash
git clone <repository-url>
cd couples-task-app
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# edit .streamlit/secrets.toml with your own PINs
streamlit run app.py
```

## Deploy on Streamlit Community Cloud
1. Push this folder to a GitHub repo:
   ```bash
   git init
   git add .
   git commit -m "Us — our little space"
   git branch -M main
   git remote add origin <repository-url>
   git push -u origin main
   ```
2. Go to https://share.streamlit.io → **New app** → pick your repo/branch → main file `app.py`.
3. In **App settings → Secrets**, paste:
   ```toml
   HIS_PASSWORD = "your-pin"
   HER_PASSWORD = "your-pin"
   ```
4. Deploy.

## ⚠️ Important limitation: SQLite on Streamlit Community Cloud
This app uses a local `tasks.db` SQLite file for simplicity. Streamlit
Community Cloud's filesystem is **not guaranteed to persist** — the container
can be restarted or redeployed (on a new push, inactivity spin-down, or
platform maintenance), and the database file can be wiped when that happens.
SQLite here is fine for local use, or for "it's OK if we occasionally lose
history," but it is **not a durable long-term store** on Cloud.

### Migrating to Supabase later
Because all persistence goes through `database.py`, migration only touches
that one file:
1. Create a free Supabase project, then create a `tasks` table with the same
   columns used here (`id, user, title, description, category, priority,
   due_time, original_date, current_date, completed, completed_at,
   carried_forward, created_at`).
2. `pip install supabase` and add it to `requirements.txt`.
3. In `database.py`, replace the `sqlite3` connection with a Supabase client
   built from `st.secrets["SUPABASE_URL"]` and `st.secrets["SUPABASE_KEY"]`,
   and rewrite each function (`add_task`, `get_tasks`, `toggle_complete`,
   etc.) to call `.table("tasks")...` instead of raw SQL, returning the same
   list-of-dict / dict shapes so `app.py` doesn't need to change.
4. Add `SUPABASE_URL` and `SUPABASE_KEY` to Streamlit secrets (never hard-code
   them).

## Notes
- PINs are a light gate for two known people, not real security.
- If you'd rather use Streamlit's multipage folder structure later, split
  `task_page()`, `us_page()`, and `history_page()` out of `app.py` into
  `pages/1_His.py`, `pages/2_Her.py`, etc. — `database.py` and `auth.py`
  need no changes to support that.
