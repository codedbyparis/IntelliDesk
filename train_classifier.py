"""Train, evaluate, and save the local supervised ticket-category classifier."""

import json
from collections import Counter, defaultdict

import joblib
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import StratifiedGroupKFold

from src import config
from src.classifier import build_classifier, load_classifier, predict_category
from src.dataset_processor import (
    NEAR_DUPLICATE_SIMILARITY_THRESHOLD,
    build_leakage_groups,
    load_labeled_records,
)

TEST_SIZE = 0.25
RANDOM_STATE = 42
N_SPLITS = round(1 / TEST_SIZE)


def main():
    records = load_labeled_records()
    questions = [record["question"] for record in records]
    categories = [record["category"] for record in records]
    groups = build_leakage_groups(records)
    counts = Counter(categories)
    classes = sorted(counts)
    too_small = [category for category in classes if counts[category] < 2]
    if too_small:
        raise ValueError(
            "Each category needs at least two records for stratified evaluation: "
            + ", ".join(too_small)
        )

    categories_by_group = defaultdict(set)
    for group, category in zip(groups, categories):
        categories_by_group[group].add(category)
    mixed_groups = [
        group for group, group_categories in categories_by_group.items()
        if len(group_categories) > 1
    ]
    if mixed_groups:
        raise ValueError(
            "Near-duplicate issue descriptions have conflicting labels. "
            "Review those records before training."
        )

    splitter = StratifiedGroupKFold(
        n_splits=N_SPLITS,
        shuffle=True,
        random_state=RANDOM_STATE,
    )
    selected_split = None
    for fold_number, (train_indices, test_indices) in enumerate(
        splitter.split(questions, categories, groups), start=1
    ):
        y_train = [categories[index] for index in train_indices]
        y_test = [categories[index] for index in test_indices]
        if set(y_train) == set(classes) and set(y_test) == set(classes):
            selected_split = (fold_number, train_indices, test_indices)
            break
    if selected_split is None:
        raise ValueError(
            "Could not create a leakage-safe stratified holdout containing every "
            "category in both splits. Review the labeled data; no ungrouped fallback "
            "will be used."
        )

    fold_number, train_indices, test_indices = selected_split
    x_train = [questions[index] for index in train_indices]
    x_test = [questions[index] for index in test_indices]
    y_train = [categories[index] for index in train_indices]
    y_test = [categories[index] for index in test_indices]
    train_record_ids = {
        (records[index]["source_file"], records[index]["source_line"])
        for index in train_indices
    }
    test_record_ids = {
        (records[index]["source_file"], records[index]["source_line"])
        for index in test_indices
    }
    if train_record_ids & test_record_ids:
        raise AssertionError("A source record appears in both training and test splits.")
    train_groups = {groups[index] for index in train_indices}
    test_groups = {groups[index] for index in test_indices}
    if train_groups & test_groups:
        raise AssertionError("A near-duplicate group appears in both data splits.")

    classifier = build_classifier()
    classifier.fit(x_train, y_train)
    predictions = classifier.predict(x_test)
    accuracy = float(accuracy_score(y_test, predictions))
    precision = float(
        precision_score(y_test, predictions, average="macro", zero_division=0)
    )
    recall = float(
        recall_score(y_test, predictions, average="macro", zero_division=0)
    )
    f1 = float(f1_score(y_test, predictions, average="macro", zero_division=0))
    matrix = confusion_matrix(y_test, predictions, labels=classes)

    print(f"Distinct labeled records: {len(records)}")
    print(
        f"Training records: {len(x_train)}; held-out test records: {len(x_test)} "
        f"(stratified group fold {fold_number}/{N_SPLITS})"
    )
    print(
        "Leakage control: exact duplicates rejected; near duplicates grouped at "
        f"similarity >= {NEAR_DUPLICATE_SIMILARITY_THRESHOLD:.2f}."
    )
    print("Records by category:")
    for category in classes:
        print(f"  {category}: {counts[category]}")
    print("\nHeld-out metrics (macro average):")
    print(f"  Accuracy : {accuracy:.3f}")
    print(f"  Precision: {precision:.3f}")
    print(f"  Recall   : {recall:.3f}")
    print(f"  F1-score : {f1:.3f}")
    print("\nPer-category held-out metrics:")
    for category in classes:
        precision = precision_score(
            y_test, predictions, labels=[category], average="macro", zero_division=0
        )
        recall = recall_score(
            y_test, predictions, labels=[category], average="macro", zero_division=0
        )
        f1 = f1_score(
            y_test, predictions, labels=[category], average="macro", zero_division=0
        )
        print(
            f"  {category}: precision={precision:.3f}, recall={recall:.3f}, "
            f"F1={f1:.3f}"
        )

    print("\nConfusion matrix (rows = actual, columns = predicted):")
    print("Actual \\ Predicted | " + " | ".join(classes))
    for category, row in zip(classes, matrix):
        print(f"{category} | " + " | ".join(str(int(value)) for value in row))

    classifier.fit(questions, categories)
    config.CLASSIFIER_MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(classifier, config.CLASSIFIER_MODEL_PATH, compress=3)
    print(f"\nSaved locally trained classifier to {config.CLASSIFIER_MODEL_PATH}")

    metrics = {
        "dataset": "Mack IT Support Dataset v1 (project-labeled subset)",
        "records": len(records),
        "category_counts": dict(sorted(counts.items())),
        "split": {
            "method": "StratifiedGroupKFold",
            "fold": fold_number,
            "folds": N_SPLITS,
            "random_state": RANDOM_STATE,
            "training_records": len(x_train),
            "test_records": len(x_test),
            "near_duplicate_similarity_threshold": (
                NEAR_DUPLICATE_SIMILARITY_THRESHOLD
            ),
        },
        "metrics": {
            "accuracy": accuracy,
            "precision_macro": precision,
            "recall_macro": recall,
            "f1_macro": f1,
        },
        "confusion_matrix": {
            "labels": classes,
            "values": [[int(value) for value in row] for row in matrix],
        },
    }
    with config.CLASSIFIER_METRICS_PATH.open("w", encoding="utf-8") as file:
        json.dump(metrics, file, ensure_ascii=False, indent=2)
        file.write("\n")
    print(f"Saved held-out evaluation metrics to {config.CLASSIFIER_METRICS_PATH}")

    saved_classifier = load_classifier(config.CLASSIFIER_MODEL_PATH)
    predicted_category, confidence = predict_category(questions[0], saved_classifier)
    if predicted_category not in config.TICKET_CATEGORIES or not 0.0 <= confidence <= 1.0:
        raise RuntimeError("The saved classifier did not produce a valid prediction.")
    with config.CLASSIFIER_METRICS_PATH.open(encoding="utf-8") as file:
        saved_metrics = json.load(file)
    if saved_metrics["confusion_matrix"]["values"] != metrics["confusion_matrix"]["values"]:
        raise RuntimeError("The saved classifier metrics did not verify.")
    print(
        "Artifact verification passed: model reloaded, prediction returned "
        f"{predicted_category!r}, and metrics/confusion matrix were read back."
    )
    print(
        "Evaluation caveat: labels are project-assigned from issue descriptions; "
        "the Mack source file itself has no category labels. Metrics describe this "
        "small, stratified, grouped held-out subset, not production accuracy."
    )


if __name__ == "__main__":
    main()
