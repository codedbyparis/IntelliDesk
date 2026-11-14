"""Shared presentation helpers for the Streamlit application."""

from html import escape
import sqlite3

import streamlit as st

from src.auth import authenticate_user, register_user
from src.classifier import load_classifier
from src.database import create_conversation, list_conversations


THEME_CSS = """
<style>
:root {
  --ink: #172033;
  --muted: #64748b;
  --line: #e3e9f2;
  --surface: #ffffff;
  --canvas: #f5f7fb;
  --navy: #101a2d;
  --blue: #4774e8;
  --blue-dark: #355fc8;
  --teal: #24a58a;
}

.stApp {
  color: var(--ink);
  background: var(--canvas);
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont,
    "Segoe UI", sans-serif;
}
[data-testid="stHeader"] { background: transparent; }
[data-testid="stMain"] { background: var(--canvas); }
[data-testid="stMainBlockContainer"] {
  max-width: 1360px;
  padding: 2rem 2.5rem 5.5rem;
}

[data-testid="stSidebar"] {
  background: var(--navy);
  border-right: 1px solid #26344b;
}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
  color: #aebbd0;
}
[data-testid="stSidebar"] [data-testid="stSidebarContent"] {
  padding: 1rem .85rem 1.2rem;
}
[data-testid="stSidebarNav"] { display: none; }
[data-testid="stSidebar"] [data-testid="stPageLink"] {
  margin: .15rem 0;
}
[data-testid="stSidebar"] [data-testid="stPageLink"] a {
  min-height: 2.45rem;
  border-radius: .65rem;
  color: #cbd5e1;
  transition: background .15s ease, color .15s ease;
}
[data-testid="stSidebar"] [data-testid="stPageLink"] a:hover {
  background: #1d2b43;
  color: #fff;
}
[data-testid="stSidebar"] .stButton button {
  border-radius: .7rem;
}
[data-testid="stSidebar"] .stButton button[kind="primary"] {
  background: var(--blue);
  border-color: var(--blue);
  color: white;
}
[data-testid="stSidebar"] hr {
  border-color: #29374e;
}

.brand-lockup {
  display: flex;
  align-items: center;
  gap: .75rem;
  padding: .45rem .25rem 1.2rem;
}
.brand-mark {
  display: grid;
  place-items: center;
  width: 2.55rem;
  height: 2.55rem;
  border-radius: .8rem;
  color: #fff;
  background: #4774e8;
  font-size: 1.05rem;
  font-weight: 750;
  letter-spacing: -.05em;
}
.brand-name {
  color: #f8fafc;
  font-weight: 700;
  font-size: 1.05rem;
  letter-spacing: -.02em;
}
.brand-caption {
  margin-top: .12rem;
  color: #91a1bb;
  font-size: .62rem;
  font-weight: 650;
  letter-spacing: .12em;
}
.sidebar-section-label {
  margin: .8rem .35rem .4rem;
  color: #8292ab;
  font-size: .68rem;
  font-weight: 700;
  letter-spacing: .11em;
  text-transform: uppercase;
}
.sidebar-profile {
  display: flex;
  align-items: center;
  gap: .65rem;
  padding: .85rem .55rem .25rem;
  border-top: 1px solid #29374e;
}
.profile-avatar {
  display: grid;
  place-items: center;
  width: 2rem;
  height: 2rem;
  border-radius: 50%;
  background: #243552;
  color: #dce7fa;
  font-size: .72rem;
  font-weight: 700;
}
.profile-title { color: #e4eaf3; font-size: .78rem; font-weight: 650; }
.profile-meta { color: #8fa0b8; font-size: .67rem; }

.page-eyebrow {
  margin-bottom: .35rem;
  color: var(--blue-dark);
  font-size: .68rem;
  font-weight: 750;
  letter-spacing: .13em;
  text-transform: uppercase;
}
h1, h2, h3 { letter-spacing: -.035em; }
h1 { color: var(--ink); font-weight: 720; }
h2, h3 { color: #202b40; font-weight: 680; }
[data-testid="stCaptionContainer"] { color: var(--muted); }

[data-testid="stMetric"] {
  padding: 1rem 1.05rem;
  border: 1px solid var(--line);
  border-radius: .9rem;
  background: var(--surface);
  box-shadow: 0 2px 8px rgba(20, 35, 60, .035);
}
[data-testid="stMetricLabel"] { color: var(--muted); font-weight: 600; }
[data-testid="stMetricValue"] { color: var(--ink); font-weight: 720; }

.stButton button, [data-testid="stFormSubmitButton"] button {
  border-radius: .7rem;
  font-weight: 620;
  transition: transform .15s ease, box-shadow .15s ease, border-color .15s ease;
}
.stButton button:hover, [data-testid="stFormSubmitButton"] button:hover {
  border-color: #b8c7e4;
  box-shadow: 0 4px 12px rgba(30, 55, 100, .08);
  transform: translateY(-1px);
}
button[kind="primary"] {
  background: var(--blue);
  border-color: var(--blue);
  color: #fff;
}
button[kind="primary"]:hover {
  background: var(--blue-dark);
  border-color: var(--blue-dark);
}

[data-testid="stChatMessage"] {
  margin: .7rem 0;
  padding: .9rem 1rem;
  border: 1px solid var(--line);
  border-radius: 1rem;
  background: var(--surface);
  box-shadow: 0 2px 8px rgba(20, 35, 60, .025);
}
[data-testid="stChatInput"] {
  border: 1px solid #d5deeb;
  border-radius: .95rem;
  background: #fff;
  box-shadow: 0 8px 26px rgba(20, 35, 60, .08);
}
.st-key-chat-shell { max-width: 900px; margin: 0 auto; }
[data-testid="stExpander"] {
  border-color: var(--line);
  border-radius: .8rem;
  background: var(--surface);
}
[data-testid="stAlert"] { border-radius: .8rem; }

.status-badge {
  display: inline-flex;
  align-items: center;
  padding: .22rem .58rem;
  border-radius: 99px;
  font-size: .72rem;
  font-weight: 700;
  line-height: 1.4;
  white-space: nowrap;
}
.status-open { color: #9a5a08; background: #fff3d8; }
.status-in-progress { color: #315eb7; background: #e9f0ff; }
.status-resolved { color: #14785f; background: #e1f5ee; }
.ticket-card {
  margin: .4rem 0 .7rem;
  padding: .15rem .1rem;
}
.source-note {
  padding: .65rem .8rem;
  border-left: 3px solid #e6a43b;
  border-radius: .35rem;
  background: #fff8e9;
  color: #76521c;
  font-size: .82rem;
}

@media (max-width: 900px) {
  [data-testid="stMainBlockContainer"] { padding: 1.5rem 1.25rem 5rem; }
  [data-testid="stHorizontalBlock"] {
    flex-wrap: wrap;
    gap: .75rem;
  }
  [data-testid="stHorizontalBlock"] [data-testid="stColumn"] {
    min-width: calc(50% - .5rem) !important;
    flex: 1 1 calc(50% - .5rem);
  }
}
@media (max-width: 640px) {
  [data-testid="stMainBlockContainer"] { padding: 1.25rem .9rem 5rem; }
  [data-testid="stHorizontalBlock"] {
    flex-wrap: wrap;
    gap: .65rem;
  }
  [data-testid="stHorizontalBlock"] [data-testid="stColumn"] {
    min-width: min(100%, 15rem) !important;
    flex: 1 1 14rem;
  }
  h1 { font-size: 1.8rem !important; }
  [data-testid="stChatMessage"] { padding: .72rem .8rem; }
}
</style>
"""

PAGES = (
    ("app.py", "AI Assistant", ":material/forum:"),
    ("pages/1_Admin_Dashboard.py", "Dashboard", ":material/dashboard:"),
    ("pages/2_My_Tickets.py", "My Tickets", ":material/confirmation_number:"),
    ("pages/3_Knowledge_Base.py", "Knowledge Base", ":material/library_books:"),
    ("pages/4_Settings.py", "Settings & About", ":material/settings:"),
    (
        "pages/5_Guided_Troubleshooting.py",
        "Guided troubleshooting",
        ":material/quiz:",
    ),
)


@st.cache_resource(show_spinner=False)
def get_classifier():
    """Load a trained classifier once, when a ticket workflow requests it."""
    return load_classifier()


def render_auth_gate():
    """Render login/registration and return the authenticated account, if any."""
    user = st.session_state.get("current_user")
    if user:
        return user

    st.title("Welcome to IntelliDesk")
    st.caption("Sign in to your private helpdesk workspace or create a user account.")
    login_tab, register_tab = st.tabs(["Sign in", "Create account"])

    with login_tab:
        with st.form("login-form"):
            username = st.text_input("Username", key="login-username")
            password = st.text_input(
                "Password", type="password", key="login-password"
            )
            submitted = st.form_submit_button("Sign in", type="primary")
        if submitted:
            try:
                user = authenticate_user(username, password)
            except sqlite3.Error as error:
                st.error(f"Could not sign in because local storage failed: {error}")
            else:
                if user is None:
                    st.error("Username or password is incorrect.")
                else:
                    st.session_state["current_user"] = user
                    st.rerun()

    with register_tab:
        st.caption(
            "User accounts cannot create or grant administrator privileges. "
            "An administrator must be provisioned from the project terminal."
        )
        with st.form("register-form"):
            username = st.text_input("Choose a username", key="register-username")
            password = st.text_input(
                "Choose a password",
                type="password",
                help="Use 12–256 characters.",
                key="register-password",
            )
            confirmation = st.text_input(
                "Confirm password",
                type="password",
                key="register-password-confirm",
            )
            submitted = st.form_submit_button("Create account", type="primary")
        if submitted:
            if password != confirmation:
                st.error("The passwords do not match.")
            else:
                try:
                    user = register_user(username, password)
                except (ValueError, sqlite3.Error) as error:
                    st.error(f"Could not create the account: {error}")
                else:
                    st.session_state["current_user"] = user
                    st.rerun()
    return None


def apply_theme():
    """Apply the shared local design system."""
    st.markdown(THEME_CSS, unsafe_allow_html=True)


def render_page_header(eyebrow, title, description):
    """Render a consistent page title and supporting description."""
    st.markdown(f'<div class="page-eyebrow">{escape(eyebrow)}</div>', unsafe_allow_html=True)
    st.title(title)
    st.caption(description)


def render_sidebar(user):
    """Render the common navigation, conversation history, and local profile."""
    with st.sidebar:
        st.markdown(
            '<div class="brand-lockup">'
            '<div class="brand-mark">ID</div>'
            '<div><div class="brand-name">IntelliDesk</div>'
            '<div class="brand-caption">IT SUPPORT WORKSPACE</div></div></div>',
            unsafe_allow_html=True,
        )

        if st.button(
            "New chat",
            key="sidebar-new-chat",
            icon=":material/add:",
            type="primary",
            width="stretch",
        ):
            st.session_state["conversation_id"] = create_conversation(
                user_id=user["id"]
            )
            st.session_state.pop("ticket_notice", None)
            st.switch_page("app.py")

        st.markdown('<div class="sidebar-section-label">Workspace</div>', unsafe_allow_html=True)
        for page, label, icon in PAGES:
            if label == "Dashboard" and user["role"] != "admin":
                continue
            st.page_link(page, label=label, icon=icon)

        st.markdown('<div class="sidebar-section-label">Recent conversations</div>', unsafe_allow_html=True)
        conversations = list_conversations(limit=6, user_id=user["id"])
        if conversations:
            for conversation in conversations:
                title = " ".join(conversation["title"].split())
                if st.button(
                    title[:32] + ("…" if len(title) > 32 else ""),
                    key=f"history-{conversation['id']}",
                    icon=":material/chat_bubble_outline:",
                    width="stretch",
                    type="tertiary",
                ):
                    st.session_state["conversation_id"] = conversation["id"]
                    st.switch_page("app.py")
        else:
            st.caption("Your conversations will appear here.")

        if st.button("Sign out", key="sidebar-sign-out", width="stretch"):
            st.session_state.clear()
            st.rerun()

        st.markdown(
            '<div class="sidebar-profile">'
            f'<div class="profile-avatar">{escape(user["username"][:2].upper())}</div>'
            f'<div><div class="profile-title">{escape(user["username"])}</div>'
            f'<div class="profile-meta">{escape(user["role"].title())} account · '
            'Qwen3 1.7B · Ollama</div></div></div>',
            unsafe_allow_html=True,
        )


def render_status_badge(status):
    """Render a compact status badge for the configured ticket states."""
    badge_class = {
        "Open": "status-open",
        "In Progress": "status-in-progress",
        "Resolved": "status-resolved",
    }.get(status, "status-open")
    st.markdown(
        f'<span class="status-badge {badge_class}">{escape(str(status))}</span>',
        unsafe_allow_html=True,
    )
