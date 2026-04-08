import json
import os
import spacy
from spacy.scorer import Scorer
from spacy.training import Example

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(base_dir)
    
    model_dir = os.path.join(project_dir, "ner_model", "output", "model-best")
    test_json = os.path.join(project_dir, "requirements_ner_dataset", "output", "requirements_ner_test.json")
    
    if not os.path.exists(model_dir):
        print(f"Waiting for model to complete training (not found: {model_dir})")
        return
        
    print(f"Loading trained model from {model_dir}...")
    nlp = spacy.load(model_dir)
    scorer = Scorer()
    
    print(f"Loading testing dataset from {test_json}...")
    with open(test_json, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    examples = []
    skipped = 0
    
    # Track top confusing cases
    confusions = {}
    
    for text, annotations in data:
        doc_pred = nlp(text)
        
        # Build gold reference doc
        doc_gold = nlp.make_doc(text)
        spans = []
        for start, end, label in annotations.get("entities", []):
            span = doc_gold.char_span(start, end, label=label, alignment_mode="contract")
            if span is None:
                span = doc_gold.char_span(start, end, label=label, alignment_mode="expand")
            if span:
                spans.append(span)
        
        try:
            doc_gold.ents = spans
            example = Example(doc_pred, doc_gold)
            examples.append(example)
            
            # Simple error tracking analysis
            pred_ents = {(e.start_char, e.end_char): e.label_ for e in doc_pred.ents}
            gold_ents = {(e.start_char, e.end_char): e.label_ for e in doc_gold.ents}
            
            for g_bounds, g_lbl in gold_ents.items():
                if g_bounds in pred_ents:
                    p_lbl = pred_ents[g_bounds]
                    if p_lbl != g_lbl:
                        combo = f"Expected {g_lbl}, got {p_lbl}"
                        confusions[combo] = confusions.get(combo, 0) + 1
                else: # Boundary missed or completely ignored
                    # Check for partial overlaps
                    matched = False
                    for p_bounds, p_lbl in pred_ents.items():
                        if not (p_bounds[1] <= g_bounds[0] or p_bounds[0] >= g_bounds[1]):
                            combo = f"Boundary Misalignment: True:{g_lbl} Predicted:{p_lbl}"
                            confusions[combo] = confusions.get(combo, 0) + 1
                            matched = True
                            break
                    if not matched:
                        combo = f"Missed Entity ({g_lbl})"
                        confusions[combo] = confusions.get(combo, 0) + 1
            
        except Exception as e:
            skipped += 1
            
    # Score metrics
    metrics = scorer.score(examples)
    
    print("\n================ NER PERFORMANCE METRICS ================")
    print(f"Total Samples Tested: {len(examples)} (Skipped: {skipped})")
    print(f"Overall Precision   : {metrics.get('ents_p', 0)*100:.2f}%")
    print(f"Overall Recall      : {metrics.get('ents_r', 0)*100:.2f}%")
    print(f"Overall F1-Score    : {metrics.get('ents_f', 0)*100:.2f}%")
    
    print("\n--- PER LABEL STATS ---")
    ents_per_type = metrics.get('ents_per_type', {})
    for ent_type, stats in ents_per_type.items():
        print(f"{ent_type.ljust(15)}: P={stats['p']*100:5.2f}% | R={stats['r']*100:5.2f}% | F1={stats['f']*100:5.2f}%")

    # Generate Error Analysis Report
    error_md = os.path.join(project_dir, "evaluation", "error_analysis.md")
    
    top_errors = sorted(confusions.items(), key=lambda x: x[1], reverse=True)[:15]
    
    md_content = "# NER Error Analysis Report\n\n"
    md_content += "Based on evaluation set of ~600 testing samples.\n\n"
    md_content += "## Top Misclassifications & Boundary Errors:\n\n"
    
    if len(top_errors) == 0:
        md_content += "No prominent errors detected! Model matches test set accurately.\n"
    else:
        for err_type, count in top_errors:
            md_content += f"- **{count} occurrences**: {err_type}\n"
    
    md_content += "\n## Proposed Fixes:\n"
    md_content += "- If frequent misclassifications exist between `ACTION` and `FEATURE`, you may need harder differentiation in manual annotation guidelines.\n"
    md_content += "- If 'Boundary Misalignment' dominates, it is because human annotators disagree strictly on where an action verb sequence ends (e.g., 'must provide' vs 'provide'). Ensure identical tagging bounds.\n"
    
    with open(error_md, "w", encoding="utf-8") as f:
        f.write(md_content)
        
    print(f"\nWritten complete Error Analysis artifact to: {error_md}")

if __name__ == "__main__":
    main()
