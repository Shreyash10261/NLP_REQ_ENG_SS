import argparse
import os

import torch
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    f1_score,
    precision_score,
    recall_score,
)
from torch.utils.data import DataLoader
from transformers import DistilBertTokenizer

from requirement_classifier.dataset import RequirementDataset
from requirement_classifier.model import LABEL_MAP, load_model

# Defaults
DEFAULT_MODEL_DIR = os.path.join("requirement_classifier", "saved_model")
DEFAULT_TEST_CSV = os.path.join("data", "requirement_classification", "test.csv")
DEFAULT_BATCH_SIZE = 16
DEFAULT_MAX_LEN = 128


def evaluate(
    model_dir: str,
    test_csv: str,
    batch_size: int = DEFAULT_BATCH_SIZE,
    max_length: int = DEFAULT_MAX_LEN,
) -> dict:
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    # Load model and tokenizer
    model = load_model(model_dir)
    model.to(device)
    model.eval()

    tokenizer = DistilBertTokenizer.from_pretrained(model_dir)
    test_dataset = RequirementDataset(test_csv, tokenizer, max_length)
    test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False)

    # Collect predictions
    all_preds, all_labels = [], []
    with torch.no_grad():
        for batch in test_loader:
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            labels = batch["labels"]

            outputs = model(input_ids=input_ids, attention_mask=attention_mask)
            preds = torch.argmax(outputs.logits, dim=1).cpu()

            all_preds.extend(preds.tolist())
            all_labels.extend(labels.tolist())

    # Compute metrics
    metrics = {
        "accuracy": accuracy_score(all_labels, all_preds),
        "precision": precision_score(all_labels, all_preds, zero_division=0),
        "recall": recall_score(all_labels, all_preds, zero_division=0),
        "f1": f1_score(all_labels, all_preds, zero_division=0),
    }

    # Pretty-print results
    print("\n" + "=" * 50)
    print("  REQUIREMENT CLASSIFIER — EVALUATION REPORT")
    print("=" * 50)
    for k, v in metrics.items():
        print(f"  {k.capitalize():>12s} : {v:.4f}")
    print("-" * 50)
    print("\nDetailed classification report:\n")
    target_names = [LABEL_MAP[i] for i in sorted(LABEL_MAP)]
    print(classification_report(all_labels, all_preds, target_names=target_names))

    return metrics


# CLI
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate the fine-tuned requirement classifier."
    )
    parser.add_argument("--model_dir", default=DEFAULT_MODEL_DIR)
    parser.add_argument("--test_csv", default=DEFAULT_TEST_CSV)
    parser.add_argument("--batch_size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--max_length", type=int, default=DEFAULT_MAX_LEN)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    evaluate(
        model_dir=args.model_dir,
        test_csv=args.test_csv,
        batch_size=args.batch_size,
        max_length=args.max_length,
    )
