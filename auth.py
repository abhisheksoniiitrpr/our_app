"""
auth.py
Minimal PIN gate for two people. Not real security — just keeps the
casual visitor out. Secrets come from st.secrets (never hard-coded).
"""

import streamlit as st


def check_pin(user_key, entered_pin):
    """user_key is 'HIS_PASSWORD' or 'HER_PASSWORD'."""
    real = st.secrets.get(user_key, "")
    return str(entered_pin) == str(real) and real != ""


def is_unlocked(user):
    return st.session_state.get(f"unlocked_{user}", False)


def unlock(user):
    st.session_state[f"unlocked_{user}"] = True


def login_gate(user, label, secret_key):
    """
    Renders a PIN entry form if the user isn't unlocked yet.
    Returns True once unlocked (and renders nothing further itself).
    """
    if is_unlocked(user):
        return True

    st.markdown(f"### 🔒 Enter PIN for {label}")
    with st.form(f"login_{user}"):
        pin = st.text_input("PIN", type="password", label_visibility="collapsed",
                             placeholder="••••")
        submitted = st.form_submit_button("Unlock ❤️")
    if submitted:
        if check_pin(secret_key, pin):
            unlock(user)
            st.rerun()
        else:
            st.error("Wrong PIN. Try again.")
    return False
