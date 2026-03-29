"""
pipeline.py — Improved End-to-End Requirements Engineering Pipeline
=====================================================================
All 8 phases with improvements:

    Phase 1: Raw Text Input
    Phase 2: Sentence Segmentation
    Phase 3: Requirement Detection       (DistilBERT classifier)
    Phase 4: Named Entity Recognition    (spaCy + BERT NER)
    Phase 4b: Requirement Structuring    (actor-action-constraint)  ★ NEW
    Phase 5: Requirement Clustering      (Sentence-BERT + Agglomerative)  ★ IMPROVED
    Phase 6: Prioritization              (Multi-signal scoring)  ★ IMPROVED
    Phase 7: Summarization               (T5/BART, dynamic length)  ★ FIXED
    Phase 7b: Explainability             (Transparent reasoning)  ★ NEW
    Phase 8: Structured Output           (JSON / Markdown / Console)  ★ IMPROVED
"""

import re
from typing import Any

from requirement_classifier.inference import RequirementClassifier
from ner_model.inference_ner import NERExtractor
from structuring.structurer import RequirementStructurer
from clustering.cluster import RequirementClusterer
from prioritization.prioritizer import RequirementPrioritizer
from summarization.summarizer import RequirementSummarizer
from explainability.explainer import ExplainabilityEngine
from output_generator.generator import OutputGenerator


class RequirementsEngineeringPipeline:
    """
    Full pipeline: Raw Text → Structured, Prioritized, Explained Requirements.
    """

    def __init__(
        self,
        classifier_dir: str = "requirement_classifier/saved_model",
        ner_model_dir: str = "ner_model/output/model-best",
        confidence_threshold: float = 0.5,
        summarizer_model: str = "t5-small",
        cluster_distance: float = 0.65,
    ):
        print("=" * 60)
        print("  Initializing Requirements Engineering Pipeline")
        print("=" * 60)

        print("\n[Phase 3] Loading Requirement Detection model …")
        self.classifier = RequirementClassifier(classifier_dir)

        print("[Phase 4] Loading NER Extraction model …")
        self.ner = NERExtractor(ner_model_dir)

        print("[Phase 4b] Initializing Requirement Structurer …")
        self.structurer = RequirementStructurer()

        print("[Phase 5] Loading Sentence-BERT for clustering …")
        self.clusterer = RequirementClusterer(distance_threshold=cluster_distance)

        print("[Phase 6] Initializing multi-signal prioritizer …")
        self.prioritizer = RequirementPrioritizer()

        print(f"[Phase 7] Loading summarization model ({summarizer_model}) …")
        self.summarizer = RequirementSummarizer(model_key=summarizer_model)

        print("[Phase 7b] Initializing explainability engine …")
        self.explainer = ExplainabilityEngine()

        print("[Phase 8] Initializing output generator …")
        self.output_generator = OutputGenerator()

        self.confidence_threshold = confidence_threshold
        print("\n✓ Pipeline fully initialized and ready.\n")

    @staticmethod
    def segment_sentences(text: str) -> list[str]:
        """Split raw text into individual sentences."""
        raw_sentences = re.split(r'(?<=[.!?])\s+', text.strip())
        return [s.strip() for s in raw_sentences if s.strip()]

    def _detect_and_extract(self, text: str) -> list[dict[str, Any]]:
        """Phases 2–4b: segment → classify → NER → structure."""
        sentences = self.segment_sentences(text)
        requirements = []

        for sentence in sentences:
            classification = self.classifier.predict(sentence)

            if (
                classification["label"] == "Requirement"
                and classification["confidence"] >= self.confidence_threshold
            ):
                entities = self.ner.extract(sentence)
                grouped = self.ner.extract_grouped(sentence)

                req = {
                    "sentence": sentence,
                    "confidence": classification["confidence"],
                    "entities": entities,
                    "grouped": grouped,
                }

                # Phase 4b: Structure into actor-action-constraint
                req = self.structurer.structure(req)

                requirements.append(req)

        return requirements

    def run(
        self,
        text: str,
        output_json: str = "output/requirements.json",
        output_md: str = "output/requirements.md",
        print_to_console: bool = True,
    ) -> list[dict[str, Any]]:
        """Execute the complete improved pipeline."""

        print("─" * 60)
        print("  RUNNING FULL PIPELINE (IMPROVED)")
        print("─" * 60)

        # --- Phases 2–4b: Detect, Extract, Structure ------------------------
        print("\n▶ Phases 2–4b: Segmentation → Classification → NER → Structuring …")
        requirements = self._detect_and_extract(text)
        total_sentences = len(self.segment_sentences(text))
        print(
            f"  Found {len(requirements)} requirements "
            f"out of {total_sentences} sentences."
        )

        if not requirements:
            print("  No requirements detected. Pipeline complete.")
            return []

        # Count functional vs non-functional
        func_count = sum(
            1 for r in requirements
            if r.get("structured", {}).get("requirement_type") == "functional"
        )
        nfr_count = len(requirements) - func_count
        print(f"  Types: {func_count} functional, {nfr_count} non-functional")

        # --- Phase 5: Clustering -------------------------------------------
        print("\n▶ Phase 5: Clustering similar requirements (Agglomerative) …")
        clusters = self.clusterer.cluster(requirements)
        sil = clusters[0].get("silhouette_score", -1) if clusters else -1
        print(f"  Formed {len(clusters)} cluster(s).")
        if sil > 0:
            print(f"  Silhouette score: {sil:.4f}")

        # --- Phase 6: Prioritization ----------------------------------------
        print("\n▶ Phase 6: Multi-signal prioritization …")
        clusters = self.prioritizer.prioritize_clusters(clusters)
        priority_counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for c in clusters:
            priority_counts[c.get("cluster_priority", "LOW")] += 1
        print(
            f"  Priorities: "
            f"{priority_counts['HIGH']} HIGH, "
            f"{priority_counts['MEDIUM']} MEDIUM, "
            f"{priority_counts['LOW']} LOW"
        )

        # --- Phase 7: Summarization ----------------------------------------
        print("\n▶ Phase 7: Generating cluster summaries (dynamic length) …")
        clusters = self.summarizer.summarize_clusters(clusters)
        print("  Summaries generated.")

        # --- Phase 7b: Explainability --------------------------------------
        print("\n▶ Phase 7b: Generating explanations …")
        clusters = self.explainer.explain_clusters(clusters)
        print("  Explanations generated.")

        # --- Phase 8: Structured Output ------------------------------------
        print("\n▶ Phase 8: Generating structured output …")
        self.output_generator.to_json(clusters, output_json)
        self.output_generator.to_markdown(clusters, output_md)

        if print_to_console:
            self.output_generator.to_console(clusters)

        print("\n✓ Pipeline complete.")
        return clusters
