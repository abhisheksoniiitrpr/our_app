"""
Us — Our Little Space ❤️
A tiny private daily task manager for two people.

Single-file navigation (sidebar radio) is used instead of Streamlit's
multipage folder structure to keep the project to as few files as
possible while still covering every feature.
"""

import random
import datetime
import streamlit as st

import database as db
import auth

# --------------------------------------------------------------- setup ----
st.set_page_config(page_title="Us — Our Little Space ❤️", page_icon="❤️", layout="centered")
db.init_db()

with open("assets/styles.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

QUOTES = [
    "You + Me = My favourite team ❤️",
    "Small tasks, big love.",
    "Getting things done, together.",
    "One day at a time, together. ❤️",
]

LOVE_NOTES = {
    "❤️ Proud of you": [
        "Someone thinks you're doing great. ❤️",
        "You're doing better than you think. ❤️",
    ],
    "💕 Miss you": [
        "Someone out there is thinking of you right now. 💕",
    ],
    "😘 Go crush it": [
        "Go get it. You've got this today. 😘",
    ],
    "🫶 You got this": [
        "One task at a time. You got this. 🫶",
    ],
}

CATEGORIES = ["College", "Work", "Fitness", "Personal", "Relationship", "Other"]
PRIORITIES = ["🔴 High", "🟡 Medium", "🟢 Low"]
PRIORITY_MAP = {"🔴 High": "High", "🟡 Medium": "Medium", "🟢 Low": "Low"}
PRIORITY_CLASS = {"High": "priority-high", "Medium": "priority-medium", "Low": "priority-low"}

if "nav" not in st.session_state:
    st.session_state.nav = "🏠 Home"

# ---------------------------------------------------------- run carry-fwd
# Run once per session load — cheap UPDATE, safe to repeat, never duplicates.
for u in ("his", "her"):
    db.carry_forward_tasks(u)


# ---------------------------------------------------------------- helpers
def priority_badge(p):
    return f'<span class="{PRIORITY_CLASS.get(p, "")}">{ "🔴" if p=="High" else "🟡" if p=="Medium" else "🟢"} {p}</span>'


def render_task(t):
    col1, col2 = st.columns([0.08, 0.92])
    with col1:
        checked = st.checkbox("", value=bool(t["completed"]), key=f"chk_{t['id']}",
                               label_visibility="collapsed")
    with col2:
        cls = "task-done" if t["completed"] else ""
        carried = '<span class="carried-label">↪ Carried from yesterday</span>' if t["carried_forward"] and not t["completed"] else ""
        meta = f"{priority_badge(t['priority'])} · {t['category']}"
        if t["due_time"]:
            meta += f" · ⏰ {t['due_time']}"
        st.markdown(
            f"<div class='{cls}'><b>{t['title']}</b> {carried}<br>"
            f"<span style='font-size:0.85rem;color:#b39ba1'>{meta}</span></div>",
            unsafe_allow_html=True,
        )
        if t["description"]:
            st.caption(t["description"])

    if checked != bool(t["completed"]):
        db.toggle_complete(t["id"])
        st.rerun()

    with st.expander("Edit / Delete", expanded=False):
        with st.form(f"edit_{t['id']}"):
            new_title = st.text_input("Task", value=t["title"])
            new_desc = st.text_area("Description", value=t["description"], height=60)
            c1, c2, c3 = st.columns(3)
            with c1:
                new_cat = st.selectbox("Category", CATEGORIES,
                                        index=CATEGORIES.index(t["category"]) if t["category"] in CATEGORIES else 5)
            with c2:
                cur_p = f"🔴 High" if t["priority"] == "High" else "🟡 Medium" if t["priority"] == "Medium" else "🟢 Low"
                new_p = st.selectbox("Priority", PRIORITIES, index=PRIORITIES.index(cur_p))
            with c3:
                new_due = st.text_input("Due time (e.g. 5:00 PM)", value=t["due_time"])
            save_col, del_col = st.columns(2)
            save = save_col.form_submit_button("💾 Save")
            confirm_delete = del_col.checkbox("Confirm delete", key=f"cd_{t['id']}")
            delete = del_col.form_submit_button("🗑️ Delete")
        if save:
            db.edit_task(t["id"], new_title, new_desc, new_cat, PRIORITY_MAP[new_p], new_due)
            st.rerun()
        if delete:
            if confirm_delete:
                db.delete_task(t["id"])
                st.rerun()
            else:
                st.warning("Check 'Confirm delete' first.")


def task_page(user, label, accent):
    if not auth.login_gate(user, label, f"{user.upper()}_PASSWORD"):
        return

    today = db.today_str()
    st.markdown(f"## {accent} {label} Daily Tasks")
    st.caption(datetime.date.today().strftime("%A, %B %d, %Y"))

    with st.expander("➕ Add Task", expanded=False):
        with st.form(f"add_{user}", clear_on_submit=True):
            title = st.text_input("Task name")
            desc = st.text_area("Description (optional)", height=60)
            c1, c2, c3 = st.columns(3)
            with c1:
                cat = st.selectbox("Category", CATEGORIES)
            with c2:
                pr = st.selectbox("Priority", PRIORITIES, index=1)
            with c3:
                due = st.text_input("Due time (optional)")
            add = st.form_submit_button("Add ❤️")
        if add:
            if title.strip():
                db.add_task(user, title, desc, cat, PRIORITY_MAP[pr], due)
                st.rerun()
            else:
                st.error("Give the task a name first.")

    tasks = db.get_tasks(user, today)

    filt = st.radio("Filter", ["All", "Pending", "Completed"], horizontal=True, key=f"filt_{user}")
    cat_filter = st.selectbox("Category filter", ["All"] + CATEGORIES, key=f"catf_{user}")
    sort_by = st.selectbox("Sort by", ["Priority", "Due time", "Creation time"], key=f"sort_{user}")

    if filt == "Pending":
        tasks = [t for t in tasks if not t["completed"]]
    elif filt == "Completed":
        tasks = [t for t in tasks if t["completed"]]
    if cat_filter != "All":
        tasks = [t for t in tasks if t["category"] == cat_filter]

    order = {"High": 0, "Medium": 1, "Low": 2}
    if sort_by == "Priority":
        tasks.sort(key=lambda t: order.get(t["priority"], 3))
    elif sort_by == "Due time":
        tasks.sort(key=lambda t: t["due_time"] or "99:99")
    else:
        tasks.sort(key=lambda t: t["created_at"])

    done, total = db.progress_for(user, today)
    st.markdown("#### Today's Progress")
    st.progress(done / total if total else 0)
    st.caption(f"{done} / {total} completed ❤️" if total else "No tasks yet today.")
    if total and done == total:
        st.success("All done! Proud of you ❤️")
        st.balloons()

    st.markdown("---")
    if not tasks:
        st.info("Nothing here. Add a task above ✨")
    for t in tasks:
        with st.container():
            st.markdown("<div class='love-card'>", unsafe_allow_html=True)
            render_task(t)
            st.markdown("</div>", unsafe_allow_html=True)

    streak = db.get_streaks(user)
    st.markdown("---")
    s1, s2 = st.columns(2)
    s1.metric("🔥 Current streak", f"{streak['current']} days")
    s2.metric("🏆 Best streak", f"{streak['best']} days")

    st.markdown("---")
    st.markdown("#### Send some love ❤️")
    lc = st.columns(4)
    for i, (btn_label, msgs) in enumerate(LOVE_NOTES.items()):
        if lc[i].button(btn_label, key=f"love_{user}_{i}"):
            st.toast(random.choice(msgs), icon="❤️")
            st.success(random.choice(msgs))


# ------------------------------------------------------------------ pages
def home_page():
    st.markdown("<h1 style='text-align:center'>Our Little Space ❤️</h1>", unsafe_allow_html=True)
    st.markdown(
        "<div class='subtitle' style='text-align:center'>"
        "Two people. One little space. A thousand things to do together."
        "</div>", unsafe_allow_html=True,
    )
    st.markdown(
        f"<div class='quote-box'>“{random.choice(QUOTES)}”</div>",
        unsafe_allow_html=True,
    )
    st.markdown(f"<p style='text-align:center;color:#b39ba1'>{datetime.date.today().strftime('%A, %B %d, %Y')}</p>",
                unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("<div class='love-card' style='text-align:center'>", unsafe_allow_html=True)
        st.markdown("### ❤️ HIS SPACE")
        st.caption("Manage his daily tasks")
        if st.button("Enter His Space", key="go_his"):
            st.session_state.nav = "❤️ His"
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
    with c2:
        st.markdown("<div class='love-card' style='text-align:center'>", unsafe_allow_html=True)
        st.markdown("### 💕 HER SPACE")
        st.caption("Manage her daily tasks")
        if st.button("Enter Her Space", key="go_her"):
            st.session_state.nav = "💕 Her"
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)


def us_page():
    st.markdown("## 💞 Us")
    today = db.today_str()
    hd, ht = db.progress_for("his", today)
    wd, wt = db.progress_for("her", today)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**His Progress**")
        st.progress(hd / ht if ht else 0)
        st.caption(f"{hd} / {ht} completed")
    with c2:
        st.markdown("**Her Progress**")
        st.progress(wd / wt if wt else 0)
        st.caption(f"{wd} / {wt} completed")

    st.markdown("### Together")
    st.write(f"🔥 {hd + wd} tasks completed today")
    st.write(f"💪 {(ht - hd) + (wt - wd)} tasks remaining")

    his_full = ht > 0 and hd == ht
    her_full = wt > 0 and wd == wt
    if his_full and her_full:
        st.success("Perfect day for both of you. ❤️")
    elif his_full or her_full:
        st.info("Someone is absolutely crushing it today 👀❤️")
    elif (ht - hd) + (wt - wd) > 0:
        st.warning("Tomorrow is another chance. You've got this together. ❤️")


def history_page():
    st.markdown("## 📅 History")
    user = st.selectbox("Whose history?", ["his", "her"], format_func=lambda u: "❤️ His" if u == "his" else "💕 Her")
    dates = db.get_available_dates(user)
    if not dates:
        st.info("No history yet — add some tasks first ✨")
        return
    date = st.selectbox("Pick a date", dates)
    data = db.get_history(user, date)
    st.markdown(f"### {date}")
    for t in data["completed"]:
        st.write(f"✓ {t['title']}")
    for t in data["pending"]:
        st.write(f"✗ {t['title']}")
    st.markdown(f"**Completion: {data['pct']}%**")


# -------------------------------------------------------------------- nav
st.sidebar.title("Navigate")
st.session_state.nav = st.sidebar.radio(
    "", ["🏠 Home", "❤️ His", "💕 Her", "💞 Us", "📅 History"],
    index=["🏠 Home", "❤️ His", "💕 Her", "💞 Us", "📅 History"].index(st.session_state.nav),
    label_visibility="collapsed",
)

page = st.session_state.nav
if page == "🏠 Home":
    home_page()
elif page == "❤️ His":
    task_page("his", "His", "❤️")
elif page == "💕 Her":
    task_page("her", "Her", "💕")
elif page == "💞 Us":
    us_page()
elif page == "📅 History":
    history_page()
