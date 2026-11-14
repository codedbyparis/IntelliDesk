"""
document_loader.py - Reads knowledge-base documents from disk.

Each page of each document becomes one "page record", a dictionary:
    {"text": ..., "source": ..., "page": ..., "label": ..., "metadata": ...}
This file only loads text. Cleaning and chunking happen in later files.
"""

import json

import pymupdf

from src import config


def load_pdf(file_path):
    """Read a PDF and return a list of {"page": number, "text": text}, one per page with text."""
    pages = []
    with pymupdf.open(str(file_path)) as pdf:
        for page_number, page in enumerate(pdf, start=1):
            text = page.get_text()
            if text.strip():
                pages.append({"page": page_number, "text": text})
    return pages


def load_text_file(file_path):
    """Read a .txt file. A text file has no pages, so everything is page 1."""
    text = file_path.read_text(encoding="utf-8-sig")
    if text.strip():
        return [{"page": 1, "text": text}]
    return []


def load_jsonl_file(file_path):
    """Read normalized JSONL records prepared for the knowledge base."""
    records = []
    with file_path.open(encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as error:
                print(
                    f"Warning: invalid JSON in {file_path.name} "
                    f"line {line_number}: {error}"
                )
                continue

            if not isinstance(record, dict):
                print(
                    f"Warning: record in {file_path.name} line {line_number} "
                    "is not an object (skipped)"
                )
                continue

            text = record.get("text")
            source = record.get("source")
            metadata = record.get("metadata", {})
            page = record.get("page")
            if not isinstance(text, str) or not text.strip():
                print(
                    f"Warning: empty or invalid text in {file_path.name} "
                    f"line {line_number} (skipped)"
                )
                continue
            if not isinstance(source, str) or not source.strip():
                print(
                    f"Warning: missing source in {file_path.name} "
                    f"line {line_number} (skipped)"
                )
                continue
            if page is not None and not isinstance(page, int):
                print(
                    f"Warning: invalid page in {file_path.name} "
                    f"line {line_number} (skipped)"
                )
                continue
            if not isinstance(metadata, dict):
                print(
                    f"Warning: invalid metadata in {file_path.name} "
                    f"line {line_number} (skipped)"
                )
                continue

            records.append(
                {
                    "text": text,
                    "source": source,
                    "page": page,
                    "metadata": metadata,
                }
            )
    return records


def load_documents():
    """Load every supported file from every knowledge-base folder.

    Returns a list of page records (see the top of this file).
    """
    documents = []

    for label, folder in config.KNOWLEDGE_BASE_FOLDERS.items():
        if not folder.exists():
            print(f"Warning: folder not found: {folder}")
            continue

        for file_path in sorted(folder.iterdir()):
            extension = file_path.suffix.lower()
            if extension not in config.SUPPORTED_EXTENSIONS:
                continue

            try:
                if extension == ".pdf":
                    pages = load_pdf(file_path)
                elif extension == ".txt":
                    pages = load_text_file(file_path)
                else:
                    pages = load_jsonl_file(file_path)
            except Exception as error:
                print(f"Warning: could not read {file_path.name}: {error}")
                continue

            if not pages:
                print(f"Warning: no text found in {file_path.name} (skipped)")
                continue

            for page in pages:
                document = {
                    "text": page["text"],
                    "source": page.get("source", file_path.name),
                    "page": page.get("page", 1),
                    "label": label,
                }
                if page.get("metadata"):
                    document["metadata"] = page["metadata"]
                documents.append(document)

    return documents


# ---------------------------------------------------------------------------
# Quick self-check: run with  python -m src.document_loader
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as temp_folder:
        test_jsonl = Path(temp_folder) / "records.jsonl"
        test_jsonl.write_text(
            "\n".join(
                [
                    json.dumps(
                        {
                            "text": "A searchable support record.",
                            "source": "Mack test record",
                            "page": None,
                            "metadata": {"record_id": "test-1"},
                        }
                    ),
                    "{malformed json",
                    json.dumps({"text": "", "source": "empty record"}),
                ]
            ),
            encoding="utf-8",
        )
        test_records = load_jsonl_file(test_jsonl)
        assert len(test_records) == 1
        assert test_records[0]["source"] == "Mack test record"
        assert test_records[0]["metadata"]["record_id"] == "test-1"
    print("Normalized JSONL checks passed.\n")

    documents = load_documents()
    print(f"Loaded {len(documents)} page(s) from the knowledge base\n")
    for doc in documents:
        preview = doc["text"][:70].replace("\n", " ")
        print(f"[{doc['label']}] {doc['source']} (page {doc['page']}, {len(doc['text'])} characters)")
        print(f"    {preview}...")