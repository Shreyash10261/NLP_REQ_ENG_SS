# NER Error Analysis Report

Based on evaluation set of ~600 testing samples.

## Top Misclassifications & Boundary Errors:

- **592 occurrences**: Missed Entity (ACTION)
- **588 occurrences**: Missed Entity (FEATURE)
- **532 occurrences**: Missed Entity (ACTOR)
- **518 occurrences**: Missed Entity (CONSTRAINT)
- **501 occurrences**: Missed Entity (QUALITY)
- **500 occurrences**: Missed Entity (PRIORITY)

## Proposed Fixes:
- If frequent misclassifications exist between `ACTION` and `FEATURE`, you may need harder differentiation in manual annotation guidelines.
- If 'Boundary Misalignment' dominates, it is because human annotators disagree strictly on where an action verb sequence ends (e.g., 'must provide' vs 'provide'). Ensure identical tagging bounds.
