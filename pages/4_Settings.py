"""Application information and local component status."""

import streamlit as st

from src import config
from src.database import init_db
from src.llm_client import check_ollama
from src.ui import (
    apply_theme,
    render_auth_gate,
    render_page_header,
    render_sidebar,
)


def main():
    st.set_page_config(
        page_title="IntelliDesk · Settings & About",
        page_icon=":material/settings:",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    apply_theme()
    init_db()
    user = render_auth_gate()
    if user is None:
        st.stop()
    render_sidebar(user)
    render_page_header(
        "APPLICATION",
        "Settings & about",
        "How IntelliDesk is configured and which local components power the demo.",
    )

    ollama_available, ollama_message = check_ollama()
    classifier_exists = config.CLASSIFIER_MODEL_PATH.is_file()
    status_columns = st.columns(2)
    if ollama_available:
        status_columns[0].success(
            f"Local model ready · {config.OLLAMA_MODEL}",
            icon=":material/check_circle:",
        )
    else:
        status_columns[0].warning(
            f"Local model unavailable · {ollama_message}",
            icon=":material/error:",
        )

    if classifier_exists:
        status_columns[1].success(
            "Trained local classifier available. Category suggestions remain editable.",
            icon=":material/model_training:",
        )
    else:
        status_columns[1].info(
            "No trained classifier artifact is available in this environment. "
            "Manual ticket categories remain available.",
            icon=":material/pending:",
        )

    st.subheader("Application")
    app_columns = st.columns(2)
    with app_columns[0]:
        with st.container(border=True):
            st.markdown("**IntelliDesk**")
            st.write(config.APP_DESCRIPTION)
            st.caption("Application version is not declared in this project.")
    with app_columns[1]:
        with st.container(border=True):
            st.markdown("**Local processing**")
            st.write(
                "Answer generation uses the local Ollama endpoint. No cloud language "
                "model is configured for this application."
            )
            st.caption(
                "Local accounts and conversation/ticket records are stored in SQLite. "
                "User accounts cannot grant administrator access."
            )

    st.subheader("Technology")
    tech_columns = st.columns(3)
    with tech_columns[0]:
        with st.container(border=True):
            st.markdown("**Answer generation**")
            st.write("Qwen3 1.7B · local Ollama")
            st.caption("Responses are grounded in retrieved passages.")
    with tech_columns[1]:
        with st.container(border=True):
            st.markdown("**Knowledge retrieval**")
            st.write("Custom TF-IDF and cosine similarity using NumPy")
            st.caption("Local documents are cleaned, chunked, and ranked by similarity.")
    with tech_columns[2]:
        with st.container(border=True):
            st.markdown("**Ticket classifier**")
            st.write("Scikit-learn TF-IDF + Logistic Regression")
            if classifier_exists:
                st.caption(
                    "Trained locally with a grouped holdout. Predictions are editable "
                    "suggestions; manual categories remain available."
                )
            else:
                st.caption(
                    "Training is pending. Users can select or correct ticket "
                    "categories manually."
                )

    st.subheader("Knowledge and privacy")
    st.markdown(
        "- Knowledge sources labeled **Sample** are demonstrations, not verified "
        "university procedures.\n"
        "- Add only approved university guidance to the **Verified** knowledge folder.\n"
        "- Conversations and tickets are visible to their signed-in owner; admins can "
        "review the local ticket queue. Chat context attachment is optional.\n"
        "- The queue does not dispatch tickets to an external helpdesk. Resolution "
        "metrics are based on explicit user feedback.\n"
        "- The application uses a local model endpoint and disables Streamlit usage "
        "statistics in this project configuration."
    )


if __name__ == "__main__":
    main()
