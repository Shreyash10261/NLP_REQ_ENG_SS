"""
cluster.py — Improved Requirement Clustering
==============================================
Groups similar requirement sentences using:
  1. Sentence-BERT embeddings (semantic vectors)
  2. Agglomerative Clustering with cosine distance

Improvements over original
--------------------------
• Switched from DBSCAN (too many single-item clusters) to
  **Agglomerative Clustering** with a tuned distance threshold.
• Uses ``distance_threshold`` instead of fixed cluster count,
  so it auto-determines the number of clusters.
• Added silhouette score evaluation for cluster quality.
• Improved cluster naming from FEATURE + ACTION entities.

Usage:
    from clustering.cluster import RequirementClusterer

    clusterer = RequirementClusterer()
    clusters = clusterer.cluster(requirements_list)
"""

from collections import defaultdict, Counter
from typing import Any

import numpy as np
from sklearn.cluster import AgglomerativeClustering
from sklearn.metrics import silhouette_score
from sklearn.metrics.pairwise import cosine_distances

from clustering.embeddings import SentenceEmbedder


class RequirementClusterer:
    """
    Cluster requirement sentences by semantic similarity.

    Parameters
    ----------
    distance_threshold : float
        Maximum cosine distance for merging clusters.
        Lower = stricter (more clusters).  Default 0.65 groups
        sentences that are reasonably related.
    embedder : SentenceEmbedder, optional
        Pre-loaded embedder.
    """

    def __init__(
        self,
        distance_threshold: float = 0.40,
        embedder: SentenceEmbedder | None = None,
    ):
        self.distance_threshold = distance_threshold
        self.embedder = embedder or SentenceEmbedder()

    def cluster(
        self,
        requirements: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Cluster a list of requirement dicts.

        Parameters
        ----------
        requirements : list[dict]
            Each dict must have a ``"sentence"`` key.

        Returns
        -------
        list[dict]
            One dict per cluster with keys:
                cluster_id, cluster_name, requirements, silhouette
        """
        if not requirements:
            return []

        # --- Step 1: Compute embeddings -------------------------------------
        sentences = [r["sentence"] for r in requirements]
        embeddings = self.embedder.encode(sentences)

        # Handle edge case: too few sentences for clustering
        if len(sentences) <= 2:
            return [{
                "cluster_id": 0,
                "cluster_name": self._generate_cluster_name(requirements, 0),
                "requirements": requirements,
            }]

        # --- Step 2: Compute distance matrix --------------------------------
        distance_matrix = cosine_distances(embeddings)

        # --- Step 3: Agglomerative Clustering -------------------------------
        clustering = AgglomerativeClustering(
            n_clusters=None,
            distance_threshold=self.distance_threshold,
            metric="precomputed",
            linkage="complete",
        )
        labels = clustering.fit_predict(distance_matrix)
        n_clusters = len(set(labels))

        # --- Step 4: Compute silhouette score (cluster quality) -------------
        sil_score = -1.0
        if n_clusters > 1 and n_clusters < len(sentences):
            sil_score = silhouette_score(distance_matrix, labels, metric="precomputed")

        # --- Step 5: Group requirements by cluster --------------------------
        cluster_map: dict[int, list[dict[str, Any]]] = defaultdict(list)
        for idx, label in enumerate(labels):
            cluster_map[label].append(requirements[idx])

        # --- Step 6: Build output -------------------------------------------
        clusters = []
        for cluster_id, reqs in sorted(cluster_map.items()):
            cluster_name = self._generate_cluster_name(reqs, cluster_id)
            clusters.append({
                "cluster_id": cluster_id,
                "cluster_name": cluster_name,
                "requirements": reqs,
                "silhouette_score": round(sil_score, 4),
            })

        return clusters

    @staticmethod
    def _generate_cluster_name(
        requirements: list[dict[str, Any]],
        cluster_id: int,
    ) -> str:
        """
        Auto-generate a professional cluster name from extracted entities.
        """
        feature_counts: Counter = Counter()
        action_counts: Counter = Counter()
        quality_counts: Counter = Counter()

        for req in requirements:
            grouped = req.get("grouped", {})
            for feature in grouped.get("FEATURE", []):
                feature_counts[feature.lower()] += 1
            for action in grouped.get("ACTION", []):
                action_counts[action.lower()] += 1
            for quality in grouped.get("QUALITY_ATTRIBUTE", []):
                quality_counts[quality.lower()] += 1
            for constraint in grouped.get("CONSTRAINT", []):
                # Catch specific important constraint contexts for naming
                if "offline" in constraint.lower():
                    quality_counts["offline support"] += 1

        parts = []
        
        # 1. Start with the core feature
        if feature_counts:
            top_feature = feature_counts.most_common(1)[0][0]
            parts.append(top_feature.title())
            
        # 2. Add modifying quality/context
        if quality_counts:
            top_quality = quality_counts.most_common(1)[0][0]
            parts.append(top_quality.title())

        # 3. Prepend specific action (avoiding generic verbs)
        if action_counts and feature_counts and not quality_counts:
            top_action = action_counts.most_common(1)[0][0]
            if top_action.lower() not in {"work", "use", "do", "make", "be"}:
                parts.insert(0, top_action.title())

        if parts:
            return " ".join(parts).replace("  ", " ").strip()
        
        return f"Cluster {cluster_id + 1}"
