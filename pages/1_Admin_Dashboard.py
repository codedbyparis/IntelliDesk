"""Administrative ticket dashboard for IntelliDesk."""

import streamlit as st

from src import config
from src.database import get_connection, init_db
from src.ticket_manager import (
    get_statistics,
    list_tickets,
    update_ticket_status,
)
from src.ui import (
    apply_theme,
    render_page_header,
    render_auth_gate,
    render_sidebar,
    render_status_badge,
)


def _matches_search(ticket, query):
    """Match a search phrase against the ticket fields available in SQLite."""
    if not query:
        return True
    phrase = query.casefold()
    searchable = " ".join(
        str(ticket.get(field, ""))
        for field in ("id", "requester_name", "contact", "category", "description")
    )
    return phrase in searchable.casefold()


def _render_ticket(ticket):
    """Display one ticket using supported database fields only."""
    with st.container(border=True):
        heading, badge = st.columns([4, 1])
        heading.markdown(f"**Ticket #{ticket['id']} · {ticket['category']}**")
        with badge:
            render_status_badge(ticket["status"])
        st.caption(
            f"Created {ticket['created_at']} · {ticket['requester_name']} · "
            f"{ticket['contact']}"
        )
        st.write(ticket["description"])
        if ticket["conversation_id"] is not None:
            st.caption(f"Conversation #{ticket['conversation_id']}")
        if ticket["context"]:
            with st.expander("Attached conversation context"):
                for message in ticket["context"]:
                    st.markdown(f"**{message['role'].title()}**")
                    st.write(message["content"])
                    for source in message["sources"]:
                        citation = source["source"]
                        if source.get("page") is not None:
                            citation += f" · page {source['page']}"
                        st.caption(
                            f"{source.get('label', 'sample').title()} source · {citation}"
                        )


def main():
    st.set_page_config(
        page_title="IntelliDesk · Dashboard",
        page_icon=":material/dashboard:",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    apply_theme()
    init_db()
    user = render_auth_gate()
    if user is None:
        st.stop()
    if user["role"] != "admin":
        st.error("The IT ticket queue is available only to administrator accounts.")
        st.stop()
    render_sidebar(user)

    render_page_header(
        "LOCAL IT SUPPORT",
        "IT ticket queue",
        "Review and update tickets in this local admin queue; no external helpdesk is connected.",
    )

    try:
        import plotly.graph_objects as go
    except ImportError as error:
        st.error("Ticket charts are unavailable because Plotly could not be loaded.")
        st.code(str(error))
        return

    statistics = get_statistics()
    by_status = statistics["by_status"]
    total = statistics["total"]

    metrics = st.columns(4)
    metrics[0].metric("Total tickets", total)
    metrics[1].metric("Open", by_status[config.TICKET_STATUSES[0]])
    metrics[2].metric("In progress", by_status[config.TICKET_STATUSES[1]])
    metrics[3].metric("Resolved", by_status[config.TICKET_STATUSES[2]])

    st.subheader("Reported outcomes and escalation context")
    outcome_columns = st.columns(3)
    answer_resolution = statistics["answer_resolution"]
    guided_resolution = statistics["guided_resolution"]
    escalation_context = statistics["escalation_context"]
    outcome_columns[0].metric(
        "Chat answers reported resolved",
        (
            f"{answer_resolution['rate']:.0%}"
            if answer_resolution["rate"] is not None
            else "No feedback"
        ),
        delta=(
            f"{answer_resolution['resolved']} of {answer_resolution['responses']} responses"
            if answer_resolution["responses"]
            else None
        ),
    )
    outcome_columns[1].metric(
        "Guided issues reported resolved",
        (
            f"{guided_resolution['rate']:.0%}"
            if guided_resolution["rate"] is not None
            else "No feedback"
        ),
        delta=(
            f"{guided_resolution['resolved']} of {guided_resolution['responses']} sessions"
            if guided_resolution["responses"]
            else None
        ),
    )
    outcome_columns[2].metric(
        "Tickets with context attached",
        (
            f"{escalation_context['coverage']:.0%}"
            if escalation_context["coverage"] is not None
            else "No data"
        ),
        delta=(
            f"{escalation_context['attached']} of "
            f"{escalation_context['tickets']} tickets"
            if escalation_context["tickets"]
            else None
        ),
    )
    if escalation_context["ratings"]:
        st.caption(
            "User feedback says attached context was helpful in "
            f"{escalation_context['helpful']} of {escalation_context['ratings']} "
            "submitted ratings. These are reported outcomes, not simulated results."
        )
    else:
        st.caption(
            "No context-helpfulness ratings have been submitted. Context coverage "
            "measures attachment presence, not the quality of the IT resolution."
        )

    st.subheader("Frequently Asked Questions")
    st.caption(
        "Questions submitted by users through the IntelliDesk chatbot, "
        "ranked by how often the same question was asked."
    )

    with get_connection() as connection:
        faq_rows = connection.execute(
            """
            SELECT
                MIN(TRIM(content)) AS question,
                COUNT(*) AS times_asked,
                COUNT(DISTINCT conversation_id) AS conversation_count
            FROM messages
            WHERE role = 'user'
              AND TRIM(content) <> ''
            GROUP BY LOWER(TRIM(content))
            ORDER BY times_asked DESC, question COLLATE NOCASE ASC
            LIMIT 10
            """
        ).fetchall()

    if faq_rows:
        faq_total = sum(row["times_asked"] for row in faq_rows)
        faq_columns = st.columns(3)
        faq_columns[0].metric("Question patterns", len(faq_rows))
        faq_columns[1].metric("Questions represented", faq_total)
        faq_columns[2].metric("Most asked count", faq_rows[0]["times_asked"])

        st.dataframe(
            [
                {
                    "Question": row["question"],
                    "Times asked": row["times_asked"],
                    "Different conversations": row["conversation_count"],
                }
                for row in faq_rows
            ],
            hide_index=True,
            width="stretch",
        )
        st.caption(
            "Matching ignores capitalization and leading/trailing spaces. "
            "Questions with different wording are counted separately."
        )
    else:
        st.info(
            "No questions have been recorded yet. Questions will appear here "
            "after users interact with IntelliDesk."
        )

    st.subheader("Recent tickets")
    filters = st.columns([1, 1, 2])
    status_filter = filters[0].selectbox(
        "Status",
        ["All"] + config.TICKET_STATUSES,
        key="dashboard-status-filter",
    )
    category_filter = filters[1].selectbox(
        "Category",
        ["All"] + config.TICKET_CATEGORIES,
        key="dashboard-category-filter",
    )
    search = filters[2].text_input(
        "Search tickets",
        placeholder="Search description, requester, or ticket ID",
        key="dashboard-ticket-search",
    )
    tickets = list_tickets(
        status=None if status_filter == "All" else status_filter,
        category=None if category_filter == "All" else category_filter,
    )
    tickets = [ticket for ticket in tickets if _matches_search(ticket, search)]

    if tickets:
        st.caption(f"Showing {min(len(tickets), 8)} of {len(tickets)} matching tickets")
        for ticket in tickets[:8]:
            _render_ticket(ticket)
    else:
        st.info("No tickets match these filters. Try another status or category.")

    st.subheader("Manage ticket status")
    all_tickets = list_tickets()
    if all_tickets:
        manage_cols = st.columns([2, 1, 1])
        selected_ticket = manage_cols[0].selectbox(
            "Select a ticket",
            all_tickets,
            format_func=lambda ticket: (
                f"#{ticket['id']} · {ticket['category']} · "
                f"{ticket['requester_name']} · {ticket['status']}"
            ),
            key="dashboard-ticket-selection",
        )
        current_status = selected_ticket["status"]
        status_index = (
            config.TICKET_STATUSES.index(current_status)
            if current_status in config.TICKET_STATUSES
            else 0
        )
        new_status = manage_cols[1].selectbox(
            "Set status",
            config.TICKET_STATUSES,
            index=status_index,
            key=f"dashboard-new-status-{selected_ticket['id']}",
        )
        if manage_cols[2].button(
            "Update status",
            key="dashboard-update-status",
            type="primary",
            icon=":material/check:",
            width="stretch",
        ):
            if update_ticket_status(selected_ticket["id"], new_status):
                st.success(f"Ticket #{selected_ticket['id']} updated to {new_status}.")
                st.rerun()
            else:
                st.error(f"Ticket #{selected_ticket['id']} no longer exists.")
    else:
        st.caption("There are no tickets to update yet.")

    st.subheader("Ticket analytics")
    if total:
        chart_columns = st.columns(2)
        category_data = [
            (category, count)
            for category, count in statistics["by_category"].items()
            if count > 0
        ]
        category_chart = go.Figure(
            data=[
                go.Bar(
                    x=[count for _, count in category_data],
                    y=[category for category, _ in category_data],
                    orientation="h",
                    marker_color="#4774e8",
                )
            ]
        )
        category_chart.update_layout(
            title="Tickets by category",
            height=330,
            margin=dict(l=12, r=12, t=55, b=16),
            plot_bgcolor="white",
            paper_bgcolor="white",
            showlegend=False,
            xaxis_title="Tickets",
            yaxis_title=None,
        )
        chart_columns[0].plotly_chart(
            category_chart,
            width="stretch",
            config={"displayModeBar": False},
        )

        status_data = [
            (status, by_status[status])
            for status in config.TICKET_STATUSES
            if by_status[status] > 0
        ]
        status_chart = go.Figure(
            data=[
                go.Pie(
                    labels=[status for status, _ in status_data],
                    values=[count for _, count in status_data],
                    hole=0.68,
                    marker_colors=[
                        {
                            "Open": "#e6a43b",
                            "In Progress": "#4774e8",
                            "Resolved": "#24a58a",
                        }[status]
                        for status, _ in status_data
                    ],
                    textinfo="label+percent",
                )
            ]
        )
        status_chart.update_layout(
            title="Tickets by status",
            height=330,
            margin=dict(l=12, r=12, t=55, b=16),
            paper_bgcolor="white",
            legend_title_text="",
        )
        chart_columns[1].plotly_chart(
            status_chart,
            width="stretch",
            config={"displayModeBar": False},
        )

        daily_data = statistics["per_day"]
        if daily_data:
            trend_chart = go.Figure(
                data=[
                    go.Scatter(
                        x=[item["day"] for item in daily_data],
                        y=[item["count"] for item in daily_data],
                        mode="lines+markers",
                        line_color="#4774e8",
                        marker_color="#4774e8",
                    )
                ]
            )
            trend_chart.update_layout(
                title="Ticket volume over time",
                height=300,
                margin=dict(l=12, r=12, t=55, b=16),
                plot_bgcolor="white",
                paper_bgcolor="white",
                xaxis_title="Date",
                yaxis_title="Tickets",
            )
            st.plotly_chart(
                trend_chart,
                width="stretch",
                config={"displayModeBar": False},
            )
        else:
            st.info("Daily ticket trends will appear after tickets are created.")
    else:
        st.info("Analytics will appear after the first support ticket is created.")


if __name__ == "__main__":
    main()
