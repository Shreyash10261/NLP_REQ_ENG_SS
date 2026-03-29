import argparse
import os

import spacy
from spacy.scorer import Scorer
from spacy.tokens import DocBin
from spacy.training import Example



# Defaults
DEFAULT_MODEL_DIR = os.path.join("ner_model", "output", "model-best")
DEFAULT_TEST_DATA = os.path.join("data", "ner", "dev.spacy")


def evaluate_ner(
    model_dir: str = DEFAULT_MODEL_DIR,
    test_data: str = DEFAULT_TEST_DATA,
) -> dict:
    # Load trained model
    nlp = spacy.load(model_dir)
    print(f"Loaded model from: {model_dir}")
    print(f"Pipeline components: {nlp.pipe_names}")

    # Load gold-standard test docs
    doc_bin = DocBin().from_disk(test_data)
    gold_docs = list(doc_bin.get_docs(nlp.vocab))

    # Build Example objects (predicted vs gold)
    examples = []
    for gold_doc in gold_docs:
       
        pred_doc = nlp.make_doc(gold_doc.text)
        pred_doc = nlp(gold_doc.text)
        example = Example(pred_doc, gold_doc)
        examples.append(example)

    # Score
    scorer = Scorer()
    scores = scorer.score(examples)

    # Pretty-print 
    print("\n" + "=" * 55)
    print("  NER MODEL — EVALUATION REPORT")
    print("=" * 55)

    # Overall entity scores
    ents_p = scores.get("ents_p", 0)
    ents_r = scores.get("ents_r", 0)
    ents_f = scores.get("ents_f", 0)
    print(f"  {'Entity Precision':>25s} : {ents_p:.4f}")
    print(f"  {'Entity Recall':>25s} : {ents_r:.4f}")
    print(f"  {'Entity F1':>25s} : {ents_f:.4f}")
    print("-" * 55)

    # Per-entity-type scores (if available)
    per_type = scores.get("ents_per_type", {})
    if per_type:
        print("\n  Per-entity-type breakdown:\n")
        print(f"  {'Entity Type':<25s} {'P':>8s} {'R':>8s} {'F1':>8s}")
        print(f"  {'-'*25} {'-'*8} {'-'*8} {'-'*8}")
        for ent_type, type_scores in sorted(per_type.items()):
            p = type_scores.get("p", 0)
            r = type_scores.get("r", 0)
            f = type_scores.get("f", 0)
            print(f"  {ent_type:<25s} {p:>8.4f} {r:>8.4f} {f:>8.4f}")
    print()

    return scores



# CLI
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate spaCy NER model.")
    parser.add_argument("--model_dir", default=DEFAULT_MODEL_DIR)
    parser.add_argument("--test_data", default=DEFAULT_TEST_DATA)
    args = parser.parse_args()
    evaluate_ner(model_dir=args.model_dir, test_data=args.test_data)
