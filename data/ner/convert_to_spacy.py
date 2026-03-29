"""
convert_to_spacy.py
====================
Converts JSON-annotated NER data into spaCy 3 binary (.spacy) format.

The JSON format uses **text-based** entity annotations to avoid
manual character-offset errors:

    {
      "text": "Users need faster login during peak hours.",
      "entities": [["Users", "ACTOR"], ["login", "FEATURE"], ...]
    }

The script automatically computes character offsets via string search,
aligns them to spaCy token boundaries, and filters out any overlapping
spans to guarantee a clean DocBin.

Usage:
    python data/ner/convert_to_spacy.py
"""

import json
import os
import spacy
from spacy.tokens import DocBin
from spacy.util import filter_spans

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TRAIN_JSON = os.path.join(SCRIPT_DIR, "train.json")
DEV_JSON = os.path.join(SCRIPT_DIR, "dev.json")
TRAIN_SPACY = os.path.join(SCRIPT_DIR, "train.spacy")
DEV_SPACY = os.path.join(SCRIPT_DIR, "dev.spacy")


def _find_entity_offsets(text: str, entity_text: str, search_start: int = 0):
    """
    Find the character start and end offsets of *entity_text* in *text*.

    Returns (start, end) or None if not found.
    """
    idx = text.find(entity_text, search_start)
    if idx == -1:
        # Try case-insensitive search as fallback
        idx = text.lower().find(entity_text.lower(), search_start)
    if idx == -1:
        return None
    return idx, idx + len(entity_text)


def convert_json_to_spacy(input_path: str, output_path: str) -> None:
    """
    Read a JSON annotation file and write a spaCy DocBin binary file.

    Each JSON entry has the shape:
        {
            "text": "...",
            "entities": [["entity_text", "LABEL"], ...]
        }

    Character offsets are computed automatically from the entity text.
    Overlapping spans are resolved by keeping the longest span
    (via spaCy's ``filter_spans``).
    """
    nlp = spacy.blank("en")
    doc_bin = DocBin()

    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    total_entities = 0
    skipped_entities = 0

    for entry_idx, entry in enumerate(data):
        text = entry["text"]
        raw_entities = entry["entities"]

        doc = nlp.make_doc(text)
        spans = []

        for ent_text, label in raw_entities:
            total_entities += 1

            # --- Auto-compute character offsets ---
            offsets = _find_entity_offsets(text, ent_text)
            if offsets is None:
                print(
                    f"  ⚠  Entry {entry_idx}: entity text '{ent_text}' "
                    f"not found in: \"{text}\""
                )
                skipped_entities += 1
                continue

            start, end = offsets

            # --- Align to token boundaries ---
            span = doc.char_span(start, end, label=label, alignment_mode="contract")
            if span is None:
                # Try expand mode as fallback
                span = doc.char_span(start, end, label=label, alignment_mode="expand")
            if span is None:
                print(
                    f"  ⚠  Entry {entry_idx}: could not align '{ent_text}' "
                    f"[{start}:{end}] → {label}"
                )
                skipped_entities += 1
                continue

            spans.append(span)

        # --- Remove overlapping spans (keep longest) ---
        filtered_spans = filter_spans(spans)
        if len(filtered_spans) < len(spans):
            diff = len(spans) - len(filtered_spans)
            print(
                f"  ℹ  Entry {entry_idx}: removed {diff} overlapping span(s)"
            )
            skipped_entities += diff

        doc.ents = filtered_spans
        doc_bin.add(doc)

    doc_bin.to_disk(output_path)
    kept = total_entities - skipped_entities
    print(
        f"✓ Converted {len(data)} docs → {output_path}\n"
        f"  Entities: {kept}/{total_entities} kept "
        f"({skipped_entities} skipped/filtered)"
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("Converting training data …")
    convert_json_to_spacy(TRAIN_JSON, TRAIN_SPACY)

    print("\nConverting dev data …")
    convert_json_to_spacy(DEV_JSON, DEV_SPACY)

    print("\nDone! Files ready for spaCy training.")
