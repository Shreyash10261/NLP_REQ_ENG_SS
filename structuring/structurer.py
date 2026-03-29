"""
structurer.py — Requirement Structuring
=========================================
Converts raw NER-enriched requirement dicts into structured format
with explicit actor-action-constraint separation and requirement
type classification (functional vs non-functional).

Input:
    "Users must be able to login within 2 seconds during peak hours."

Output:
    {
        "actor": "Users",
        "action": "login",
        "feature": "login",
        "quality_attribute": null,
        "constraints": ["within 2 seconds", "during peak hours"],
        "priority_indicator": null,
        "requirement_type": "non-functional",
        "structured_statement": "Users shall login within 2 seconds, during peak hours."
    }

Usage:
    from structuring.structurer import RequirementStructurer

    structurer = RequirementStructurer()
    structured = structurer.structure(requirement_dict)
"""

from typing import Any


# ---------------------------------------------------------------------------
# Non-functional requirement indicators
# ---------------------------------------------------------------------------
NFR_QUALITY_KEYWORDS = {
    "performance", "security", "reliability", "availability",
    "scalability", "usability", "maintainability", "portability",
    "fast", "slow", "secure", "reliable", "available", "scalable",
    "encrypt", "securely", "responsive", "smooth", "performant",
    "high availability", "real time", "real-time",
}

NFR_CONSTRAINT_PATTERNS = [
    "within", "under", "in real time", "real-time",
    "during", "at rest", "in transit",
]


class RequirementStructurer:
    """
    Convert NER-enriched requirements into structured actor-action-constraint format.
    """

    def structure(self, requirement: dict[str, Any]) -> dict[str, Any]:
        """
        Structure a single requirement from its NER entities.

        Parameters
        ----------
        requirement : dict
            Must have ``sentence`` and ``grouped`` keys from NER extraction.

        Returns
        -------
        dict
            Original dict enriched with a ``structured`` key containing
            the actor-action-constraint breakdown.
        """
        grouped = requirement.get("grouped", {})
        sentence = requirement.get("sentence", "")

        # Extract primary entities (first of each type)
        actors = grouped.get("ACTOR", [])
        actions = grouped.get("ACTION", [])
        features = grouped.get("FEATURE", [])
        quality_attrs = grouped.get("QUALITY_ATTRIBUTE", [])
        constraints = grouped.get("CONSTRAINT", [])
        priorities = grouped.get("PRIORITY_INDICATOR", [])

        # Determine requirement type
        req_type = self._classify_type(
            sentence, quality_attrs, constraints
        )

        # Build structured representation
        structured = {
            "actor": actors[0] if actors else None,
            "action": actions[0] if actions else None,
            "feature": features[0] if features else None,
            "all_features": features if features else [],
            "quality_attribute": quality_attrs[0] if quality_attrs else None,
            "constraints": constraints if constraints else [],
            "priority_indicator": priorities[0] if priorities else None,
            "requirement_type": req_type,
            "structured_statement": self._build_statement(
                actors, actions, features, constraints, quality_attrs
            ),
        }

        requirement["structured"] = structured
        return requirement

    def structure_all(
        self,
        requirements: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Structure a list of requirements."""
        return [self.structure(r) for r in requirements]

    def structure_clusters(
        self,
        clusters: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Structure all requirements within clusters."""
        for cluster in clusters:
            cluster["requirements"] = self.structure_all(
                cluster["requirements"]
            )
        return clusters

    @staticmethod
    def _classify_type(
        sentence: str,
        quality_attrs: list[str],
        constraints: list[str],
    ) -> str:
        """
        Classify requirement as functional or non-functional.

        Non-functional indicators:
          • Has quality attribute entities (performance, security, etc.)
          • Has time/condition constraints
          • Contains NFR keywords
        """
        sentence_lower = sentence.lower()

        # Check quality attributes
        if quality_attrs:
            return "non-functional"

        # Check constraint patterns
        for pattern in NFR_CONSTRAINT_PATTERNS:
            for constraint in constraints:
                if pattern in constraint.lower():
                    return "non-functional"

        # Check keywords in sentence
        for keyword in NFR_QUALITY_KEYWORDS:
            if keyword in sentence_lower:
                return "non-functional"

        return "functional"

    @staticmethod
    def _build_statement(
        actors: list[str],
        actions: list[str],
        features: list[str],
        constraints: list[str],
        quality_attrs: list[str],
    ) -> str:
        """
        Build a canonical requirement statement from entities.

        Format: "<Actor> shall <action> <feature> <quality> <constraints>."
        """
        parts = []

        # Actor
        if actors:
            parts.append(actors[0])
        else:
            parts.append("The system")

        # Shall + action
        parts.append("shall")
        if actions:
            parts.append(actions[0])

        # Feature
        if features:
            parts.append(features[0])

        # Quality
        if quality_attrs:
            parts.append(f"with {quality_attrs[0]} requirements")

        # Constraints
        if constraints:
            parts.append(", ".join(constraints))

        statement = " ".join(parts)
        if not statement.endswith("."):
            statement += "."
        return statement
