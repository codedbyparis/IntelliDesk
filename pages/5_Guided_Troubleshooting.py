"""Sample-only guided troubleshooting and local ticket escalation."""

import sqlite3

import streamlit as st

from src import config
from src.database import init_db, record_guided_outcome
from src.ticket_manager import create_ticket
from src.troubleshooting import WORKFLOWS
from src.ui import (
    apply_theme,
    render_auth_gate,
    render_page_header,
    render_sidebar,
)


def _guided_context(topic, workflow, completed_steps):
    """Build an explicit, sample-labeled snapshot of the troubleshooting session."""
    transcript = [
        {
            "role": "assistant",
            "content": f"Guided troubleshooting topic: {topic}",
            "status": "sample_guidance",
            "sources": [
                {
                    "source": workflow["source"],
                    "label": config.LABEL_SAMPLE,
                }
            ],
        }
    ]
    transcript.extend(
        {
            "role": "assistant",
            "content": f"Step {index}: {step}",
            "status": "sample_guidance",
            "sources": [
                {
                    "source": workflow["source"],
                    "label": config.LABEL_SAMPLE,
                }
            ],
        }
        for index, step in enumerate(workflow["steps"][:completed_steps], start=1)
    )
    return transcript


def _render_escalation(topic, workflow, user, completed_steps):
    """Submit an unresolved guided issue to the local ticket queue."""
    with st.container(border=True):
        st.subheader("Create a support ticket")
        st.caption(
            "This submits to IntelliDesk's local IT queue. It does not send a request "
            "to an external helpdesk."
        )
        with st.form("guided-ticket-form"):
            requester_name = st.text_input("Your name", key="guided-ticket-name")
            contact = st.text_input(
                "Contact email or phone",
                key="guided-ticket-contact",
            )
            description = st.text_area(
                "Describe the remaining issue",
                value=f"{topic}: the sample troubleshooting steps did not resolve my issue.",
                max_chars=2000,
                key="guided-ticket-description",
            )
            category = st.selectbox(
                "Ticket category",
                config.TICKET_CATEGORIES,
                index=config.TICKET_CATEGORIES.index(workflow["category"]),
                key="guided-ticket-category",
            )
            submitted = st.form_submit_button(
                "Submit ticket",
                key="submit-guided-ticket",
                type="primary",
                icon=":material/send:",
            )
        if submitted:
            try:
                ticket_id = create_ticket(
                    requester_name=requester_name,
                    contact=contact,
                    category=category,
                    description=description,
                    user_id=user["id"],
                    context=_guided_context(topic, workflow, completed_steps),
                )
            except (ValueError, sqlite3.Error) as error:
                st.error(f"Could not submit the ticket: {error}")
            else:
                st.session_state["guided_ticket_created"] = ticket_id
                st.rerun()


def main():
    st.set_page_config(
        page_title="IntelliDesk · Guided troubleshooting",
        page_icon=":material/quiz:",
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
        "SAMPLE SELF-SERVICE",
        "Guided troubleshooting",
        "Work through example steps, then report whether they helped or create a ticket.",
    )
    st.warning(
        "These are demonstration workflows based on sample documents, not verified "
        "university procedures. Follow your institution's official guidance when available."
    )

    created_ticket = st.session_state.pop("guided_ticket_created", None)
    if created_ticket:
        st.success(f"Ticket #{created_ticket} was submitted to the local IT queue.")

    topic = st.selectbox("Choose an issue", tuple(WORKFLOWS), key="guided-topic")
    workflow = WORKFLOWS[topic]
    if st.session_state.get("guided_active_topic") != topic:
        st.session_state["guided_active_topic"] = topic
        st.session_state["guided_step"] = 0
        st.session_state.pop("guided_finished", None)
        st.session_state.pop("guided_outcome_recorded", None)

    st.caption(f"Sample source: `{workflow['source']}` · not official")
    st.progress(
        min(st.session_state.get("guided_step", 0) + 1, len(workflow["steps"]))
        / len(workflow["steps"])
    )

    finished = st.session_state.get("guided_finished")
    if finished == "resolved":
        st.success("Thanks for reporting that the sample steps resolved your issue.")
        if st.button("Start another issue", key="guided-start-over"):
            st.session_state.pop("guided_finished", None)
            st.session_state.pop("guided_outcome_recorded", None)
            st.session_state["guided_step"] = 0
            st.rerun()
        return

    if finished == "unresolved":
        _render_escalation(
            topic,
            workflow,
            user,
            st.session_state.get("guided_step", 0) + 1,
        )
        return

    step_index = st.session_state.get("guided_step", 0)
    st.subheader(f"Step {step_index + 1} of {len(workflow['steps'])}")
    st.info(workflow["steps"][step_index])
    st.caption("Try this step, then continue if the issue remains.")

    left, right = st.columns(2)
    if left.button(
        "This resolved my issue",
        key=f"guided-resolved-{topic}",
        type="primary",
        width="stretch",
    ):
        try:
            record_guided_outcome(user["id"], topic, True, step_index + 1)
        except sqlite3.Error as error:
            st.error(f"Could not save your reported outcome: {error}")
        else:
            st.session_state["guided_finished"] = "resolved"
            st.rerun()

    if step_index + 1 < len(workflow["steps"]):
        if right.button(
            "Continue to next step",
            key=f"guided-next-{topic}-{step_index}",
            width="stretch",
        ):
            st.session_state["guided_step"] = step_index + 1
            st.rerun()
    elif right.button(
        "Still not resolved — create a ticket",
        key=f"guided-unresolved-{topic}",
        width="stretch",
    ):
        try:
            record_guided_outcome(
                user["id"], topic, False, len(workflow["steps"])
            )
        except sqlite3.Error as error:
            st.error(f"Could not save your reported outcome: {error}")
        else:
            st.session_state["guided_finished"] = "unresolved"
            st.rerun()


if __name__ == "__main__":
    main()
