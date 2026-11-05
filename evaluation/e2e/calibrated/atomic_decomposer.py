"""Atomic proposition decomposition and conjunction aggregation (Revision 2.4)."""

import re
from typing import List, Any

class AtomicPropositionDecomposer:
    """Decomposes compound clinical statements into material atomic propositions."""

    @classmethod
    def decompose(cls, statement: str) -> List[str]:
        """Decomposes compound sentences into atomic proposition strings."""
        statement = statement.strip()
        if not statement:
            return []

        # Remove leading list markers or bullets
        statement = re.sub(r"^[\d\.\-\*\s]+", "", statement)

        # Check for multi-clause split via semicolon
        if ";" in statement:
            parts = [p.strip() for p in statement.split(";") if len(p.strip()) > 10]
            if len(parts) > 1:
                return parts

        # Check for coordinated verb/action split: "Subject Verb1 ... and Verb2 ..."
        # e.g., "Metformin reduces hepatic glucose production and improves insulin sensitivity."
        coord_split = re.split(
            r"\s+and\s+(?=(?:also\s+)?(?:completely\s+)?(?:improves?|reduces?|causes?|cures?|treats?|lowers?|prevents?|presents?|includes?|interacts?|requires?|lists?|contains?)\b)",
            statement,
            flags=re.IGNORECASE
        )
        if len(coord_split) > 1:
            subject_match = re.match(r"^(\S+)", statement)
            subj = subject_match.group(1) if subject_match else ""
            propositions = [coord_split[0].rstrip(". ") + "."]
            for p in coord_split[1:]:
                p_clean = p.strip().rstrip(". ")
                if subj and not p_clean.lower().startswith(subj.lower()):
                    propositions.append(f"{subj} {p_clean}.")
                else:
                    propositions.append(f"{p_clean}.")
            return propositions

        # Check for compound conjunctions in predicate: " causes X and Y", " includes X as well as Y"
        match = re.search(r"^(.*?)(?: causes| includes| is used for| is indicated for| presents with) (.*)$", statement, re.IGNORECASE)
        if match:
            subject_verb = match.group(1)
            predicates = match.group(2)
            
            # Split predicates on ' and ' or ' as well as '
            pred_items = re.split(r",?\s+(?:and|as well as)\s+", predicates)
            if len(pred_items) > 1 and all(len(p.strip()) > 3 for p in pred_items):
                propositions = []
                for p in pred_items:
                    p_clean = p.strip().rstrip(".")
                    propositions.append(f"{subject_verb} {p_clean}.")
                return propositions

        # Default: single atomic proposition
        return [statement]

    @classmethod
    def aggregate_verdicts(cls, proposition_verdicts: List[Any]) -> Any:
        """Conjunctive aggregation: returns None if any proposition is None (structural failure), else 1 iff ALL are 1, else 0."""
        if not proposition_verdicts:
            return 0
        if any(v is None for v in proposition_verdicts):
            return None
        return 1 if all(v == 1 for v in proposition_verdicts) else 0
