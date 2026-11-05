"""Deterministic Entity and Scoped-Absence Scanner (Revision 2.4)."""

import re
from typing import List, Dict, Tuple, Optional

class AbsenceScanner:
    """Pre-scan and post-scan engine for evidence-scoped limitations and entity presence."""

    ABSENCE_PATTERNS = [
        r"does not (?:mention|list|provide|state|contain|describe|specify)",
        r"do not (?:mention|list|provide|state|contain|describe|specify)",
        r"(?:there is )?no (?:other |alternative )?(?:information|mention|documentation|evidence|data|guidelines|conditions)(?:\s+(?:is|are|was|were|have been))?\s+(?:provided|available|found|documented|identified|suggested|in|about|regarding)",
        r"not (?:mentioned|found|provided|listed|documented|available|identifiable|verifiable) in (?:the )?(?:available|retrieved|provided)? (?:sources|context|evidence)",
        r"sources do not",
        r"available sources (?:lack|omit|do not)",
        r"(?:cannot|could not) be (?:determined|verified|established|found)",
        r"is not verifiable",
        r"not found in the (?:provided|available|retrieved)? (?:evidence|sources|context)"
    ]

    GLOBAL_DENIAL_PATTERNS = [
        r"does not exist(?: as a medication)?",
        r"is not a real (?:medication|drug|condition)",
        r"no clinical evidence exists (?:globally|worldwide|in medical literature)",
        r"there is no evidence in medicine",
        r"does not exist in medical science",
        r"there is no scientific evidence anywhere in medical literature"
    ]

    @classmethod
    def is_scoped_absence_statement(cls, text: str) -> bool:
        """Detects whether a statement asserts a scoped absence or limitation in retrieved sources."""
        text_lower = text.lower()
        for pat in cls.ABSENCE_PATTERNS:
            if re.search(pat, text_lower):
                return True
        return False

    @classmethod
    def is_global_denial_statement(cls, text: str) -> bool:
        """Detects whether a statement improperly asserts global nonexistence or universal absence."""
        text_lower = text.lower()
        for pat in cls.GLOBAL_DENIAL_PATTERNS:
            if re.search(pat, text_lower):
                return True
        return False

    @classmethod
    def scan_context_for_entity(
        cls,
        entity_name: str,
        context_chunks: List[Dict[str, str]]
    ) -> List[Tuple[str, int]]:
        """Scans context chunks for mentions of an entity. Returns [(chunk_id, match_count)]."""
        if not entity_name or len(entity_name.strip()) < 3:
            return []
        
        matches = []
        pattern = re.compile(r"\b" + re.escape(entity_name.strip().lower()) + r"\b")
        
        for idx, chunk in enumerate(context_chunks):
            cid = chunk.get("chunk_id", f"E{idx+1}")
            text = chunk.get("text", chunk.get("content", "")).lower()
            count = len(pattern.findall(text))
            if count > 0:
                matches.append((cid, count))
                
        return matches

    @classmethod
    def extract_absence_targets(cls, statement: str) -> Tuple[str, str]:
        """Extracts the entity and attribute claimed to be absent from the statement."""
        text = statement.strip()
        
        # 1. Pattern: "[attribute] for [entity] was not found / is not / could not be..."
        m1 = re.search(r"(?:the\s+)?(.+?)\s+for\s+(.+?)\s+(?:was not found|is not|could not be|does not|do not)", text, re.IGNORECASE)
        if m1:
            attr = m1.group(1).strip()
            ent = m1.group(2).strip()
            return ent, attr
            
        # 2. Pattern: "...(does not|do not) provide/mention/list [attribute] for [entity]"
        m2 = re.search(r"(?:does not|do not)\s+(?:provide|mention|list|state|contain)\s+(.+?)\s+for\s+(.+?)(?:\.|$)", text, re.IGNORECASE)
        if m2:
            attr = m2.group(1).strip()
            ent = m2.group(2).strip()
            return ent, attr

        # 3. Pattern: "...information about/regarding [entity]"
        m3 = re.search(r"(?:information|mention|guidelines|data)\s+(?:about|regarding)\s+(.+?)(?:\.|$)", text, re.IGNORECASE)
        if m3:
            ent = m3.group(1).strip()
            return ent, ""
            
        return "", ""

    @classmethod
    def verify_evidence_absence(
        cls,
        statement: str,
        context_chunks: List[Dict[str, str]]
    ) -> Tuple[bool, Optional[str]]:
        """Deterministically verifies whether a scoped absence statement is consistent with retrieved evidence."""
        if cls.is_global_denial_statement(statement):
            return False, "Global nonexistence claim exceeds retrieved context scope"
            
        if not cls.is_scoped_absence_statement(statement):
            return False, "Statement is an affirmative claim, not an evidence-scoped absence statement"

        ent, attr = cls.extract_absence_targets(statement)
        full_context = " ".join(c.get("text", "") for c in context_chunks).lower()

        # If an entity was extracted
        if ent:
            ent_clean = re.sub(r"\b\d+\s*(?:mg|ml|mcg|g)\b", "", ent, flags=re.IGNORECASE).strip()
            ent_words = [w for w in ent_clean.lower().split() if len(w) > 3 and w not in ["solution", "tablets", "capsules", "inhalation", "about"]]
            
            ent_found_in_ctx = any(w in full_context for w in ent_words) if ent_words else False
            
            # If entity is completely absent from context (e.g. Xanthroflurane, Glycozempra)
            if not ent_found_in_ctx:
                # Legitimate evidence absence of ungrounded entity
                return True, None

            # If entity IS found in context, check if the specific claimed attribute is also present in context!
            if attr:
                attr_words = [w for w in attr.lower().split() if len(w) > 3 and w not in ["recommendations", "information", "guidelines", "clinical"]]
                if attr_words:
                    for c in context_chunks:
                        c_text = c.get("text", "").lower()
                        if any(ew in c_text for ew in ent_words):
                            if all(aw in c_text for aw in attr_words):
                                return False, f"Claimed missing attribute '{attr}' is explicitly present in context for {ent}"
        
        return True, None
