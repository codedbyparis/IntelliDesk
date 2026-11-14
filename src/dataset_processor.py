"""Load and validate project-labeled ticket examples for classifier training."""

import json
from difflib import SequenceMatcher
from pathlib import Path

from src import config

NEAR_DUPLICATE_SIMILARITY_THRESHOLD = 0.85

REQUIRED_FIELDS = (
    "question",
    "category",
    "source_dataset",
    "source_url",
    "source_file",
    "source_line",
    "license",
    "labeling_note",
)


def load_labeled_records(path=None):
    """Return unique, attributed ticket examples with valid configured labels."""
    data_path = Path(path) if path is not None else config.CLASSIFIER_DATA_PATH
    if not data_path.is_file():
        raise FileNotFoundError(f"Classifier training data not found: {data_path}")

    records = []
    seen_questions = set()
    with data_path.open(encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(
                    f"Invalid JSON in {data_path.name} line {line_number}: {error}"
                ) from error
            if not isinstance(record, dict):
                raise ValueError(
                    f"Expected an object in {data_path.name} line {line_number}."
                )

            missing = [field for field in REQUIRED_FIELDS if field not in record]
            if missing:
                raise ValueError(
                    f"Missing fields in {data_path.name} line {line_number}: "
                    f"{', '.join(missing)}"
                )
            question = record["question"]
            category = record["category"]
            if not isinstance(question, str) or not question.strip():
                raise ValueError(
                    f"Empty question in {data_path.name} line {line_number}."
                )
            if category not in config.TICKET_CATEGORIES:
                raise ValueError(
                    f"Unknown category {category!r} in {data_path.name} "
                    f"line {line_number}."
                )
            for field in (
                "source_dataset",
                "source_url",
                "source_file",
                "license",
                "labeling_note",
            ):
                if not isinstance(record[field], str) or not record[field].strip():
                    raise ValueError(
                        f"Invalid {field} in {data_path.name} line {line_number}."
                    )
            if (
                not isinstance(record["source_line"], int)
                or record["source_line"] < 1
            ):
                raise ValueError(
                    f"Invalid source line in {data_path.name} line {line_number}."
                )

            normalized_question = " ".join(question.casefold().split())
            if normalized_question in seen_questions:
                raise ValueError(
                    f"Duplicate question in {data_path.name} line {line_number}; "
                    "remove duplicates before creating a train/test split."
                )
            seen_questions.add(normalized_question)
            records.append(record)

    if not records:
        raise ValueError(f"No labeled records found in {data_path}.")
    return records


def build_leakage_groups(records):
    """Group exact and near-duplicate questions so they cannot cross data splits."""
    normalized_questions = [
        " ".join(record["question"].casefold().split()) for record in records
    ]
    parents = list(range(len(records)))

    def find(index):
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index

    def union(first, second):
        first_root = find(first)
        second_root = find(second)
        if first_root != second_root:
            parents[second_root] = first_root

    for first in range(len(normalized_questions)):
        for second in range(first + 1, len(normalized_questions)):
            similarity = SequenceMatcher(
                None,
                normalized_questions[first],
                normalized_questions[second],
                autojunk=False,
            ).ratio()
            if similarity >= NEAR_DUPLICATE_SIMILARITY_THRESHOLD:
                union(first, second)

    group_ids = {}
    groups = []
    for index in range(len(records)):
        root = find(index)
        if root not in group_ids:
            group_ids[root] = len(group_ids)
        groups.append(group_ids[root])
    return groups


if __name__ == "__main__":
    examples = [
        {"question": "Outlook stuck opening in safe mode."},
        {"question": "Outlook stuck opening in safe mode!"},
        {"question": "Can't connect to campus Wi-Fi."},
    ]
    groups = build_leakage_groups(examples)
    assert groups[0] == groups[1]
    assert groups[0] != groups[2]
    print("Dataset processor checks passed.")
