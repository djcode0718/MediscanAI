"""
Deterministic Entity and Indication Attribution Checker (Revision 2.4).
Verifies claim-level grounding and product-evidence isolation without LLM inference.
"""

import re
from typing import Dict, List, Any, Optional, Set, Union
from dataclasses import dataclass, field


@dataclass
class AttributionResult:
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    flagged_citations: List[Dict[str, Any]] = field(default_factory=list)
    cross_block_copies: List[Dict[str, Any]] = field(default_factory=list)


def parse_evidence_text(evidence: Union[str, List[Any]]) -> Dict[str, Dict[str, Any]]:
    """
    Parses evidence blocks into a structured dictionary keyed by tag (e.g., 'E1', 'E2').
    Captures: tag, item_type, brand, generic, active_ingredients, also_marketed, name, indications, full_text.
    """
    blocks = {}
    if isinstance(evidence, list):
        for idx, itm in enumerate(evidence, 1):
            tag = f"E{idx}"
            if isinstance(itm, dict):
                itype = itm.get("item_type") or itm.get("type", "UNKNOWN")
                f = itm.get("fields") or {}
                raw_text = itm.get("raw_text") or str(f)
            else:
                itype = getattr(itm, "item_type", "UNKNOWN")
                f = getattr(itm, "fields", {}) or {}
                raw_text = getattr(itm, "raw_text", str(f))

            blocks[tag] = {
                "tag": tag,
                "type": itype,
                "brand": (f.get("brand_name") or f.get("brand") or "").strip(),
                "generic": (f.get("generic_name") or f.get("generic") or "").strip(),
                "active_ingredients": (f.get("active_ingredients") or "").strip(),
                "also_marketed": (f.get("also_marketed_as") or "").strip(),
                "name": (f.get("name") or "").strip(),
                "indications": (f.get("indications") or "").strip(),
                "raw_text": raw_text,
            }
        return blocks

    # Parse text format "[E1] DRUG | id=... | Brand: ... | Indications: ..."
    pattern = re.compile(r"\[(E\d+)\]\s*([^\[]+)")
    for match in pattern.finditer(evidence):
        tag = match.group(1)
        content = match.group(2).strip()

        # Parse key fields
        brand = ""
        generic = ""
        active = ""
        also = ""
        name = ""
        indications = ""

        b_m = re.search(r"Brand:\s*([^|]+)", content)
        if b_m:
            brand = b_m.group(1).strip()
        g_m = re.search(r"Generic:\s*([^|]+)", content)
        if g_m:
            generic = g_m.group(1).strip()
        a_m = re.search(r"Active ingredients:\s*([^|]+)", content)
        if a_m:
            active = a_m.group(1).strip()
        al_m = re.search(r"Also marketed as:\s*([^|]+)", content)
        if al_m:
            also = al_m.group(1).strip()
        n_m = re.search(r"name:\s*([^|\n]+)", content)
        if n_m:
            name = n_m.group(1).strip()
        ind_m = re.search(r"Indications:\s*(.+)", content, re.DOTALL)
        if ind_m:
            indications = ind_m.group(1).strip()

        itype = "UNKNOWN"
        if "DRUG" in content.split("|")[0]:
            itype = "DRUG"
        elif "DISEASE" in content.split("|")[0]:
            itype = "DISEASE"
        elif "DRUG_NAME_MATCH" in content.split("|")[0]:
            itype = "DRUG_NAME_MATCH"

        blocks[tag] = {
            "tag": tag,
            "type": itype,
            "brand": brand,
            "generic": generic,
            "active_ingredients": active,
            "also_marketed": also,
            "name": name,
            "indications": indications,
            "raw_text": content,
        }
    return blocks


def extract_word_ngrams(text: str, n: int = 6) -> Set[str]:
    """Extract normalized word n-grams (default 6-grams)."""
    words = re.findall(r"\b[A-Za-z0-9_-]+\b", text.lower())
    if len(words) < n:
        return set()
    return {" ".join(words[i:i + n]) for i in range(len(words) - n + 1)}


def check_entity_attribution(
    answer_text: str,
    evidence: Union[str, List[Any]],
    min_ngram_match: int = 6,
) -> AttributionResult:
    """
    Validates that:
    1. For each sentence citing [E#], any drug/brand/ingredient names stated in that sentence
       appear in that cited block (brand, generic, active ingredients, also marketed, or name).
    2. Flag any >=6-word run of an indications sentence copied from an evidence block
       other than the cited block.
    """
    errors = []
    flagged_citations = []
    cross_block_copies = []

    blocks = parse_evidence_text(evidence)
    if not blocks:
        return AttributionResult(is_valid=True)

    # Collect known drug entities across ALL blocks to identify mentions
    all_drug_entities: Dict[str, Set[str]] = {}
    for tag, blk in blocks.items():
        ents = set()
        for field in ("brand", "generic", "also_marketed", "name"):
            val = blk.get(field) or ""
            if val and len(val) >= 3:
                # Remove punctuation / descriptors
                clean_val = re.sub(r"[^\w\s-]", "", val).strip().lower()
                if len(clean_val) >= 3:
                    ents.add(clean_val)
                    # Also individual components if multi-ingredient
                    for part in re.split(r"[,;/]+", val):
                        cp = re.sub(r"[^\w\s-]", "", part).strip().lower()
                        if len(cp) >= 3 and cp not in ("capsule", "tablet", "tablets", "solution", "injection"):
                            ents.add(cp)
        # Active ingredients
        act = blk.get("active_ingredients") or ""
        if act:
            for part in re.split(r"[,;/]+", act):
                cp = re.sub(r"[^\w\s-]", "", part).strip().lower()
                if len(cp) >= 3:
                    ents.add(cp)
        all_drug_entities[tag] = ents

    # Precompute 6-grams for indications of each block
    block_indication_ngrams: Dict[str, Set[str]] = {}
    for tag, blk in blocks.items():
        ind_text = blk.get("indications") or ""
        if ind_text:
            block_indication_ngrams[tag] = extract_word_ngrams(ind_text, n=min_ngram_match)
        else:
            block_indication_ngrams[tag] = set()

    # Split answer into sentences
    # Exclude mandatory warning section
    clean_answer = answer_text.split("### ⚠️ Important Warning")[0].strip()
    sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9*#])", clean_answer)

    for s_idx, sentence in enumerate(sentences):
        tags_in_sentence = re.findall(r"\[(E\d+)\]", sentence)
        if not tags_in_sentence:
            continue

        sent_lower = sentence.lower()
        sentence_ngrams = extract_word_ngrams(sentence, n=min_ngram_match)

        for tag in tags_in_sentence:
            if tag not in blocks:
                errors.append(f"Sentence cites invalid/unknown evidence tag [{tag}].")
                continue

            target_block = blocks[tag]
            allowed_ents = all_drug_entities.get(tag, set())

            # 1. Check for cross-block entity attribution:
            # Does the sentence mention a drug entity from another block that is NOT in the cited block?
            for other_tag, other_ents in all_drug_entities.items():
                if other_tag == tag:
                    continue
                for other_ent in other_ents:
                    if len(other_ent) < 4:
                        continue
                    # Word boundary match
                    pattern = rf"\b{re.escape(other_ent)}\b"
                    if re.search(pattern, sent_lower):
                        # If this entity is not in the cited block's allowed entities, flag it
                        if not any(other_ent in allowed for allowed in allowed_ents):
                            err = (
                                f"Cross-block entity attribution: sentence cites [{tag}] but mentions "
                                f"entity '{other_ent}' from [{other_tag}]."
                            )
                            errors.append(err)
                            flagged_citations.append({
                                "sentence": sentence,
                                "cited_tag": tag,
                                "intruding_entity": other_ent,
                                "source_tag": other_tag,
                            })

            # 2. Check for cross-block indication copying (>=6 word run from another block's indications)
            for other_tag, other_ngrams in block_indication_ngrams.items():
                if other_tag == tag:
                    continue
                shared = sentence_ngrams.intersection(other_ngrams)
                if shared:
                    # Check if these ngrams are also in the cited block's indications
                    cited_ngrams = block_indication_ngrams.get(tag, set())
                    unauthorized_shared = shared - cited_ngrams
                    if unauthorized_shared:
                        sample_ngram = next(iter(unauthorized_shared))
                        err = (
                            f"Cross-block indication plagiarism: sentence cites [{tag}] but contains "
                            f">={min_ngram_match}-word run '{sample_ngram}' copied from [{other_tag}]."
                        )
                        errors.append(err)
                        cross_block_copies.append({
                            "sentence": sentence,
                            "cited_tag": tag,
                            "source_tag": other_tag,
                            "matching_ngram": sample_ngram,
                        })

    is_valid = (len(errors) == 0)
    return AttributionResult(
        is_valid=is_valid,
        errors=errors,
        flagged_citations=flagged_citations,
        cross_block_copies=cross_block_copies,
    )
