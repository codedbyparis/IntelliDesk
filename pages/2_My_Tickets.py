"""User-facing support ticket creation and tracking."""

import sqlite3

import streamlit as st

from src import config
from src.classifier import predict_category
from src.database import (
    get_ticket_context_feedback,
    init_db,
    record_ticket_context_feedback,
)
from src.ticket_manager import create_ticket, list_tickets
from src.ui import (
    apply_theme,
    get_classifier,
    render_page_header,
    render_auth_gate,
    render_sidebar,
    render_status_badge,
)


def _search_matches(ticket, query):
    """Search the ticket details stored by the current database schema."""
    if not query:
        return True
    phrase = query.casefold()
    fields = ("id", "requester_name", "contact", "category", "description")
    return phrase in " ".join(str(ticket.get(field, "")) for field in fields).casefold()


def _render_ticket(ticket, user):
    """Render a ticket summary and its available details."""
    with st.container(border=True):
        heading, badge = st.columns([4, 1])
        heading.markdown(f"**Ticket #{ticket['id']}**")
        with badge:
            render_status_badge(ticket["status"])
        st.caption(
            f"{ticket['category']} · Created {ticket['created_at']}"
        )
        st.write(ticket["description"])
        with st.expander("Ticket details"):
            st.caption(f"Requester: {ticket['requester_name']}")
            st.caption(f"Contact: {ticket['contact']}")
            if ticket["conversation_id"] is not None:
                st.caption(f"Conversation: #{ticket['conversation_id']}")
            st.caption(f"Last updated: {ticket['updated_at']}")
        if ticket["context"]:
            with st.expander("Conversation shared with IT"):
                for message in ticket["context"]:
                    st.markdown(f"**{message['role'].title()}**")
                    st.write(message["content"])
                    for source in message["sources"]:
                        st.caption(f"Source: {source['source']}")
            feedback = get_ticket_context_feedback(ticket["id"], user["id"])
            if feedback is None:
                st.caption("Did the attached conversation help the IT team understand the issue?")
                helpful, not_helpful = st.columns(2)
                if helpful.button(
                    "Yes, it helped",
                    key=f"context-helpful-{ticket['id']}",
                ):
                    try:
                        record_ticket_context_feedback(
                            ticket["id"], user["id"], True
                        )
                    except sqlite3.Error as error:
                        st.error(f"Could not save your feedback: {error}")
                    else:
                        st.rerun()
                if not_helpful.button(
                    "No, it did not",
                    key=f"context-not-helpful-{ticket['id']}",
                ):
                    try:
                        record_ticket_context_feedback(
                            ticket["id"], user["id"], False
                        )
                    except sqlite3.Error as error:
                        st.error(f"Could not save your feedback: {error}")
                    else:
                        st.rerun()
            else:
                st.caption(
                    "You marked the attached context as "
                    f"{'helpful' if feedback else 'not helpful'}."
                )


def main():
    st.set_page_config(
        page_title="IntelliDesk · My Tickets",
        page_icon=":material/confirmation_number:",
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
        "SUPPORT REQUESTS",
        "My tickets",
        "Create a request and track its status from this local support workspace.",
    )
    st.caption("Only tickets belonging to your signed-in account appear here.")

    notice = st.session_state.pop("ticket_created_notice", None)
    if notice:
        st.success(f"Ticket #{notice} submitted successfully · Open")

    with st.container(border=True):
        st.subheader("Create a support ticket")
        st.caption(
            "Describe the issue and choose a category. Any available model suggestion "
            "is editable before submission."
        )

        identity = st.columns(2)
        requester_name = identity[0].text_input(
            "Your name",
            key="new-ticket-name",
            placeholder="Name",
        )
        contact = identity[1].text_input(
            "Contact email or phone",
            key="new-ticket-contact",
            placeholder="you@example.edu",
        )
        description = st.text_area(
            "Issue description",
            key="new-ticket-description",
            placeholder="What is happening? Include any useful error message or steps you tried.",
            height=120,
            max_chars=2000,
        )

        suggested_category = None
        suggestion_message = None
        if description.strip():
            try:
                model = get_classifier()
                suggested_category, confidence = predict_category(description, model)
            except FileNotFoundError:
                suggestion_message = (
                    "Classifier training is pending; manual category selection is active."
                )
            except (ImportError, OSError):
                suggestion_message = (
                    "Classifier suggestions are unavailable in this environment; "
                    "manual selection is active."
                )
            except ValueError:
                suggestion_message = (
                    "The classifier could not process this description; "
                    "manual selection is active."
                )
            else:
                st.info(
                    f"Suggested category: **{suggested_category}** "
                    f"({confidence:.0%} model probability). Confirm or change it below."
                )
        elif not config.CLASSIFIER_MODEL_PATH.is_file():
            suggestion_message = (
                "Classifier training is pending; manual category selection is active."
            )

        if suggestion_message:
            st.caption(suggestion_message)

        category_widget_key = "new-ticket-category"
        previous_suggestion = st.session_state.get(
            "classifier-category-suggestion"
        )
        current_category = st.session_state.get(category_widget_key)
        if suggested_category:
            if (
                current_category is None
                or current_category == previous_suggestion
                or (
                    previous_suggestion is None
                    and current_category == "Other"
                )
            ):
                st.session_state[category_widget_key] = suggested_category
            st.session_state["classifier-category-suggestion"] = suggested_category
        elif current_category is None:
            st.session_state[category_widget_key] = "Other"

        selected_category = st.session_state[category_widget_key]
        if selected_category not in config.TICKET_CATEGORIES:
            selected_category = "Other"
            st.session_state[category_widget_key] = selected_category
        category = st.selectbox(
            "Confirm or change category",
            config.TICKET_CATEGORIES,
            index=None,
            key=category_widget_key,
        )
        if st.button(
            "Submit support ticket",
            key="submit-new-ticket",
            type="primary",
            icon=":material/send:",
        ):
            try:
                ticket_id = create_ticket(
                    requester_name=requester_name,
                    contact=contact,
                    category=category,
                    description=description,
                    user_id=user["id"],
                )
            except (ValueError, sqlite3.Error) as error:
                st.error(f"Could not submit the ticket: {error}")
            else:
                st.session_state["ticket_created_notice"] = ticket_id
                st.rerun()

    st.subheader("Ticket history")
    controls = st.columns([1, 1, 2])
    status_filter = controls[0].selectbox(
        "Status",
        ["All"] + config.TICKET_STATUSES,
        key="my-tickets-status",
    )
    category_filter = controls[1].selectbox(
        "Category",
        ["All"] + config.TICKET_CATEGORIES,
        key="my-tickets-category",
    )
    search = controls[2].text_input(
        "Search",
        placeholder="Search ticket ID or description",
        key="my-tickets-search",
    )
    tickets = list_tickets(
        status=None if status_filter == "All" else status_filter,
        category=None if category_filter == "All" else category_filter,
        user_id=user["id"],
    )
    tickets = [ticket for ticket in tickets if _search_matches(ticket, search)]

    if tickets:
        st.caption(f"{len(tickets)} ticket(s)")
        for ticket in tickets:
            _render_ticket(ticket, user)
    elif search or status_filter != "All" or category_filter != "All":
        st.info("No tickets match those filters. Adjust the filters and try again.")
    else:
        st.info(
            "No support tickets yet. Create a ticket above whenever you need help "
            "from the support team."
        )


if __name__ == "__main__":
    main()
