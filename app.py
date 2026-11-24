"""Streamlit chat interface for the IntelliDesk helpdesk assistant."""
import re
import sqlite3

import streamlit as st

from src import config
from src.classifier import predict_category
from src.database import (
    add_message,
    create_conversation,
    get_conversation_context,
    get_history,
    get_message_feedback,
    get_messages,
    init_db,
    record_message_feedback,
)
from src.index_store import index_exists
from src.llm_client import check_ollama
from src.rag_pipeline import answer_question
from src.ticket_manager import create_ticket
from src.ui import (
    apply_theme,
    get_classifier,
    render_page_header,
    render_auth_gate,
    render_sidebar,
)


def _show_sources(sources):
    """Display provenance and sample-versus-verified labels below an answer."""
    if not sources:
        return

    sample_sources = [
        source for source in sources if source.get("label") != config.LABEL_VERIFIED
    ]
    label = "Sources" if not sample_sources else "Sources · includes sample material"
    with st.container(border=True):
        st.caption(label)
        if sample_sources:
            st.markdown(
                '<div class="source-note">Sample troubleshooting information — '
                "not verified university policy.</div>",
                unsafe_allow_html=True,
            )
        for source in sources:
            is_verified = source.get("label") == config.LABEL_VERIFIED
            badge = "Verified source" if is_verified else "Sample · not official"
            citation = source["source"]
            if source.get("page") is not None:
                citation += f" · page {source['page']}"
            record_id = source.get("metadata", {}).get("record_id")
            if record_id:
                citation += f" · record {record_id}"
            st.markdown(f"**{badge}**")
            st.caption(citation)


def _error_result(message):
    """Return the standard pipeline result shape for setup errors."""
    return {
        "status": config.STATUS_ERROR,
        "answer": (
            "I can't generate an answer right now because a required local "
            "component is unavailable. You can create a support ticket so the "
            "IT team can help you."
        ),
        "sources": [],
        "best_score": 0.0,
        "uses_sample_content": False,
        "offer_ticket": True,
        "error": message,
    }


def _render_ticket_form(conversation_id, messages, user):
    """Offer an editable category suggestion when a response needs escalation."""
    latest_user_message = next(
        (message["content"] for message in reversed(messages) if message["role"] == "user"),
        "",
    )
    suggested_category = None
    classifier_message = None
    try:
        model = get_classifier()
        suggested_category, confidence = predict_category(latest_user_message, model)
    except FileNotFoundError:
        classifier_message = "Category prediction is pending; choose a category manually."
    except (ImportError, OSError):
        classifier_message = (
            "The classifier is unavailable in this environment; choose a category manually."
        )
    except ValueError:
        classifier_message = (
            "The classifier could not process this description; choose a category manually."
        )
    else:
        st.caption(
            f"Suggested category: **{suggested_category}** · "
            f"model probability {confidence:.0%}. You can change it below."
        )
    if classifier_message:
        st.caption(classifier_message)

    notice = st.session_state.get("ticket_notice")
    if notice and notice["conversation_id"] == conversation_id:
        st.success(f"Ticket #{notice['ticket_id']} was submitted · Open")

    selected_category = (
        suggested_category
        if suggested_category in config.TICKET_CATEGORIES
        else "Other"
    )
    category_label = (
        "Confirm or change the suggested category"
        if suggested_category
        else "Ticket category"
    )
    with st.container(border=True):
        st.subheader("Create a support ticket")
        st.caption("Share a few details so the support team can follow up.")
        with st.form(key=f"ticket-form-{conversation_id}"):
            requester_name = st.text_input("Your name")
            contact = st.text_input("Contact email or phone")
            category = st.selectbox(
                category_label,
                config.TICKET_CATEGORIES,
                index=config.TICKET_CATEGORIES.index(selected_category),
            )
            description = st.text_area(
                "Describe the issue",
                value=latest_user_message,
                key=f"ticket-description-{conversation_id}",
            )
            include_context = st.checkbox(
                "Attach the recent conversation, answer status, and sources to this ticket",
                value=True,
                key=f"ticket-context-{conversation_id}",
            )
            submitted = st.form_submit_button(
                "Submit ticket",
                type="primary",
                icon=":material/send:",
                width="stretch",
            )

    if submitted:
        try:
            ticket_id = create_ticket(
                requester_name=requester_name,
                contact=contact,
                category=category,
                description=description,
                conversation_id=conversation_id,
                user_id=user["id"],
                context=(
                    get_conversation_context(conversation_id, user["id"])
                    if include_context
                    else None
                ),
            )
        except (ValueError, sqlite3.Error) as error:
            st.error(f"Could not submit the ticket: {error}")
        else:
            st.session_state["ticket_notice"] = {
                "conversation_id": conversation_id,
                "ticket_id": ticket_id,
            }
            st.rerun()


def _process_question(
    question, conversation_id, user_id, has_index, ollama_ok, ollama_message
):
    """Persist the question, run the existing RAG pipeline, and persist its result."""
    history = get_history(conversation_id, user_id=user_id)
    add_message(conversation_id, "user", question, user_id=user_id)
    with st.spinner("Searching support information and preparing a response…"):
        if not has_index:
            result = _error_result("The search index has not been built.")
        elif not ollama_ok:
            result = _error_result(ollama_message)
        else:
            result = answer_question(question, history)
    add_message(
        conversation_id,
        "assistant",
        result["answer"],
        result["status"],
        result["sources"],
        user_id=user_id,
    )
    st.rerun()


def _render_resolution_feedback(message, user):
    """Collect an explicit resolution vote for the latest generated answer."""
    feedback = get_message_feedback(message["id"], user["id"])
    if feedback is True:
        st.success("You marked this answer as resolving your issue.")
        return feedback
    if feedback is False:
        st.info("Thanks for the feedback. You can create a ticket with this conversation.")
        return feedback

    st.caption("Did these steps resolve your issue?")
    resolved_column, unresolved_column = st.columns(2)
    if resolved_column.button(
        "Yes, that resolved it",
        key=f"answer-resolved-{message['id']}",
        type="primary",
    ):
        try:
            record_message_feedback(message["id"], user["id"], True)
        except sqlite3.Error as error:
            st.error(f"Could not save your feedback: {error}")
        else:
            st.rerun()
    if unresolved_column.button(
        "No, I still need help",
        key=f"answer-unresolved-{message['id']}",
    ):
        try:
            record_message_feedback(message["id"], user["id"], False)
        except sqlite3.Error as error:
            st.error(f"Could not save your feedback: {error}")
        else:
            st.rerun()
    return None


def main():
    st.set_page_config(
        page_title="IntelliDesk · AI Assistant",
        page_icon=":material/support_agent:",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    apply_theme()
    init_db()

    user = render_auth_gate()
    if user is None:
        st.stop()

    if "conversation_id" not in st.session_state:
        st.session_state["conversation_id"] = create_conversation(user_id=user["id"])
    render_sidebar(user)

    conversation_id = st.session_state["conversation_id"]
    messages = get_messages(conversation_id, user_id=user["id"])
    has_index = index_exists()
    ollama_ok, ollama_message = check_ollama()

    render_page_header(
        "LOCAL AI · IT SUPPORT",
        "How can we help?",
        "Ask a question about an IT issue. Answers use the available support documents "
        "and show where the information came from.",
    )

    if not has_index:
        st.error(
            "The search index is missing. From the project root, build it with "
            "`python build_index.py` before using the assistant."
        )
    if not ollama_ok:
        st.warning(
            f"Local Qwen is unavailable: {ollama_message} "
            "No cloud model will be used. You can still submit a support ticket."
        )

    with st.container(key="chat-shell"):
        if not messages:
            with st.container(border=True):
                st.subheader("Welcome to IntelliDesk")
                st.write(
                    "Describe what is happening and I’ll look for relevant support "
                    "information. If the documents do not contain a reliable answer, "
                    "I’ll say so and offer a support ticket."
                )
                st.caption("Try a common question")
                suggestions = [
                    ("How do I connect to campus Wi-Fi?", ":material/wifi:"),
                    ("I cannot access my university email.", ":material/mail:"),
                    ("How do I reset my student portal password?", ":material/lock_reset:"),
                    ("My LMS is not loading.", ":material/school:"),
                ]
                columns = st.columns(2)
                for position, (question, icon) in enumerate(suggestions):
                    if columns[position % 2].button(
                        question,
                        key=f"suggestion-{position}",
                        icon=icon,
                        width="stretch",
                    ):
                        st.session_state["pending_question"] = question
                        st.rerun()

        for message in messages:
            avatar = (
                ":material/support_agent:"
                if message["role"] == "assistant"
                else ":material/person:"
            )
            with st.chat_message(message["role"], avatar=avatar):
                st.markdown(message["content"])
                if message["role"] == "assistant":
                    _show_sources(message["sources"])
                    if message["status"] == config.STATUS_ERROR:
                        st.caption("Local service unavailable · ticket escalation is available.")
                    elif message["status"] and message["status"] != config.STATUS_ANSWERED:
                        st.caption(
                            "No supported answer found · ticket escalation is available."
                        )

        latest_assistant = next(
            (message for message in reversed(messages) if message["role"] == "assistant"),
            None,
        )
        if latest_assistant and latest_assistant["status"] == config.STATUS_ANSWERED:
            feedback = _render_resolution_feedback(latest_assistant, user)
            if feedback is False:
                _render_ticket_form(conversation_id, messages, user)
        elif latest_assistant:
            _render_ticket_form(conversation_id, messages, user)

        pending_question = st.session_state.pop("pending_question", None)
        question = pending_question or st.chat_input(
            "Describe your IT issue…",
            max_chars=2000,
            key="chat-question",
        )

    if question:
        _process_question(
            question,
            conversation_id,
            user["id"],
            has_index,
            ollama_ok,
            ollama_message,
        )


if __name__ == "__main__":
    main()
