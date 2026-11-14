"""Browsable view of source documents used by the local retrieval index."""

import streamlit as st

from src import config
from src.database import init_db
from src.ui import apply_theme, render_auth_gate, render_page_header, render_sidebar


def _format_size(byte_count):
    """Return a short human-readable size for a local document."""
    if byte_count < 1024:
        return f"{byte_count} B"
    if byte_count < 1024 * 1024:
        return f"{byte_count / 1024:.1f} KB"
    return f"{byte_count / (1024 * 1024):.1f} MB"


def _documents():
    """List supported knowledge documents without exposing generated index files."""
    documents = []
    for label, folder in config.KNOWLEDGE_BASE_FOLDERS.items():
        if not folder.is_dir():
            continue
        for path in sorted(folder.iterdir(), key=lambda item: item.name.casefold()):
            if not path.is_file() or path.suffix.lower() not in config.SUPPORTED_EXTENSIONS:
                continue
            documents.append(
                {
                    "name": path.name,
                    "label": label,
                    "path": path,
                    "size": path.stat().st_size,
                }
            )
    return documents


def main():
    st.set_page_config(
        page_title="IntelliDesk · Knowledge Base",
        page_icon=":material/library_books:",
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
        "SUPPORT DOCUMENTS",
        "Knowledge base",
        "Browse the source files available to the assistant. Search looks at document names.",
    )
    st.info(
        "Sample documents are demonstration material, not verified university policy. "
        "Only files in the knowledge-base folders are listed; generated index files "
        "are not user documents."
    )

    documents = _documents()
    verified_count = sum(
        document["label"] == config.LABEL_VERIFIED for document in documents
    )
    sample_count = len(documents) - verified_count
    metrics = st.columns(2)
    metrics[0].metric("Sample documents", sample_count)
    metrics[1].metric("Verified documents", verified_count)

    query = st.text_input(
        "Search document names",
        placeholder="For example, Wi-Fi or email",
        key="knowledge-search",
    ).casefold()
    visible_documents = [
        document
        for document in documents
        if query in document["name"].casefold()
    ]

    if not visible_documents:
        if documents:
            st.info("No document names match that search. Try a shorter phrase.")
        else:
            st.info(
                "The knowledge-base folders do not contain any supported documents yet."
            )
        return

    st.caption(f"{len(visible_documents)} document(s)")
    for start in range(0, len(visible_documents), 2):
        columns = st.columns(2)
        for column, document in zip(columns, visible_documents[start : start + 2]):
            label = (
                "Verified"
                if document["label"] == config.LABEL_VERIFIED
                else "Sample · not official"
            )
            with column:
                with st.container(border=True):
                    st.markdown(f"**{document['name']}**")
                    st.caption(f"{label} · {document['path'].suffix[1:].upper()}")
                    st.caption(f"Source file · {_format_size(document['size'])}")
                    if document["label"] == config.LABEL_SAMPLE:
                        st.caption("Use as sample information only; not university policy.")


if __name__ == "__main__":
    main()
