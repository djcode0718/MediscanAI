# app/evidence.py
"""
MediScanAI Compact Evidence Formatter & Token Budget Manager.
Transforms raw retrieved multi-channel evidence into clean, source-grounded,
deduplicated, and budget-governed tagged blocks ([E1], [E2], ...).
"""

import re
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field


PLACEHOLDER_VALUES = {
    "none", "n/a", "na", "null", "empty", "none reported", "not specified", "unknown", "undefined"
}

BOILERPLATE_PREFIX_PATTERNS = [
    re.compile(r"^(?:\d+(?:\.\d+)*\s+)?(?:INDICATIONS(?:\s+AND\s+USAGE)?|INDICATIONS)\s*[:.\-—]?\s*", re.I),
    re.compile(r"^(?:\d+(?:\.\d+)*\s+)?(?:WARNINGS(?:\s+AND\s+PRECAUTIONS)?|WARNINGS)\s*[:.\-—]?\s*", re.I),
    re.compile(r"^(?:\d+(?:\.\d+)*\s+)?(?:DOSAGE(?:\s+AND\s+ADMINISTRATION)?|DOSAGE)\s*[:.\-—]?\s*", re.I),
    re.compile(r"^(?:\d+(?:\.\d+)*\s+)?(?:ADVERSE\s+REACTIONS?)\s*[:.\-—]?\s*", re.I),
]


def clean_text_field(val: Any) -> Optional[str]:
    """Clean whitespace and filter placeholder strings."""
    if val is None:
        return None
    s = str(val).strip()
    if not s:
        return None
    cleaned = " ".join(s.split())
    if cleaned.lower() in PLACEHOLDER_VALUES:
        return None
    return cleaned


def strip_boilerplate_prefix(text: str) -> str:
    """Strip repeated section titles and numbering like '1 INDICATIONS AND USAGE'."""
    res = text.strip()
    for pat in BOILERPLATE_PREFIX_PATTERNS:
        res = pat.sub("", res).strip()
    return res


def cut_at_sentence_boundary(text: str, max_chars: int) -> str:
    """
    Truncate text at the last sentence boundary before max_chars.
    Never cuts mid-sentence. If even the first sentence exceeds max_chars,
    preserves that first sentence to maintain grammatical integrity.
    """
    cleaned = " ".join(text.split())
    if len(cleaned) <= max_chars:
        return cleaned

    # Find sentence boundaries: period/exclamation/question followed by space or end
    matches = list(re.finditer(r"[.!?](?:\s+|$)", cleaned))
    if not matches:
        return cleaned

    # Find the last match whose end is <= max_chars
    valid_cut = None
    for m in matches:
        if m.end() <= max_chars:
            valid_cut = m.end()
        else:
            break

    if valid_cut is not None:
        return cleaned[:valid_cut].strip()

    # If first sentence boundary is beyond max_chars, return first sentence rather than cutting mid-sentence
    first_end = matches[0].end()
    return cleaned[:first_end].strip()


def extract_item_id(item_obj: Any, key: Any, channel: str) -> str:
    """Extract a canonical identifier for an item."""
    if isinstance(item_obj, dict):
        if channel == "diseases":
            chunk = item_obj.get("chunk", {})
            if isinstance(chunk, dict) and "chunk_id" in chunk:
                return f"disease_chunk_{chunk['chunk_id']}"
            if "id" in item_obj:
                return f"disease_chunk_{item_obj['id']}"
        elif "id" in item_obj:
            return f"drug_{item_obj['id']}"
    return str(key)


@dataclass
class EvidenceItem:
    channel: str
    raw_id: str
    covers_ids: List[str]
    item_type: str  # DISEASE, DRUG, DRUG_NAME_MATCH, GRAPH_DISEASE, GRAPH_DRUG
    fields: Dict[str, str]
    tag: str = ""
    text_block: str = ""
    token_est: int = 0


def deduplicate_drug_items(
    items: List[Tuple[Any, float, Any]],
    max_items: int = 3,
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Deduplicate drug records by normalized (generic_name, sorted substance_name).
    Keeps best-ranked representative, collects other brands as 'Also marketed as: ...' (max 5),
    and records covers_ids.
    Returns: (deduped_records, omitted_ids)
    """
    seen: Dict[Tuple[str, tuple], Dict[str, Any]] = {}
    ordered_reps: List[Dict[str, Any]] = []
    omitted_ids: List[str] = []

    for key, score, obj in items:
        if not isinstance(obj, dict):
            continue

        raw_id = str(obj.get("id", key))
        generic = clean_text_field(obj.get("generic_name")) or ""
        norm_generic = generic.upper()

        substances = obj.get("substance_name", [])
        if isinstance(substances, str):
            substances = [substances]
        norm_subs = tuple(sorted(str(s).strip().upper() for s in substances if clean_text_field(s)))

        dedup_key = (norm_generic, norm_subs)

        brand = clean_text_field(obj.get("brand_name"))

        if dedup_key in seen:
            rep = seen[dedup_key]
            rep["covers_ids"].append(raw_id)
            if brand and brand.lower() != rep["primary_brand"].lower():
                if brand not in rep["also_marketed_as"] and len(rep["also_marketed_as"]) < 5:
                    rep["also_marketed_as"].append(brand)
            omitted_ids.append(raw_id)
        else:
            rep_record = {
                "key": key,
                "score": score,
                "obj": obj,
                "raw_id": raw_id,
                "primary_brand": brand or generic or "Unknown",
                "generic_name": generic,
                "substances": [str(s).strip() for s in substances if clean_text_field(s)],
                "also_marketed_as": [],
                "covers_ids": [raw_id],
            }
            seen[dedup_key] = rep_record
            ordered_reps.append(rep_record)

    # Enforce max_items per channel
    final_items = ordered_reps[:max_items]
    for dropped_rep in ordered_reps[max_items:]:
        omitted_ids.extend(dropped_rep["covers_ids"])

    return final_items, omitted_ids


def estimate_tokens(text: str) -> int:
    """Token count estimation using tiktoken cl100k_base with character fallback."""
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except Exception:
        return max(1, len(text) // 4)


def build_evidence_item_block(
    item: EvidenceItem,
    tag: str,
    field_caps: Dict[str, int],
    allowed_drug_fields: Set[str],
    cap_multiplier: float = 1.0,
) -> str:
    """Build the single-line or multi-line tagged text block for an item."""
    parts = [f"{tag} {item.item_type} | id={item.raw_id}"]

    if item.item_type == "DISEASE":
        if "condition" in item.fields:
            parts.append(f"Condition: {item.fields['condition']}")
        if "symptoms" in item.fields:
            parts.append(f"Listed symptoms: {item.fields['symptoms']}")

    elif item.item_type in ("DRUG", "GRAPH_DRUG"):
        if "brand_name" in allowed_drug_fields and "brand_name" in item.fields:
            parts.append(f"Brand: {item.fields['brand_name']}")
        if "generic_name" in allowed_drug_fields and "generic_name" in item.fields:
            parts.append(f"Generic: {item.fields['generic_name']}")
        if "also_marketed_as" in item.fields:
            parts.append(f"Also marketed as: {item.fields['also_marketed_as']}")
        if "active_ingredients" in allowed_drug_fields and "active_ingredients" in item.fields:
            parts.append(f"Active ingredients: {item.fields['active_ingredients']}")

        # Long text fields governed by caps
        for fld in ("indications", "warnings", "dosage", "adverse_reactions"):
            if fld in allowed_drug_fields and fld in item.fields:
                base_cap = field_caps.get(fld, 300)
                effective_cap = max(80, int(base_cap * cap_multiplier))
                capped_val = cut_at_sentence_boundary(item.fields[fld], effective_cap)
                if capped_val:
                    parts.append(f"{fld.capitalize()}: {capped_val}")

    elif item.item_type == "DRUG_NAME_MATCH":
        if "name" in item.fields:
            parts.append(f"name: {item.fields['name']}")

    elif item.item_type == "GRAPH_DISEASE":
        if "condition" in item.fields:
            parts.append(f"Condition: {item.fields['condition']}")
        if "symptoms" in item.fields:
            parts.append(f"Symptoms: {item.fields['symptoms']}")

    return " | ".join(parts)


class CompactEvidenceFormatter:
    """
    Orchestrates compact evidence generation with deduplication, sentence-boundary caps,
    and token budget enforcement.
    """

    def __init__(
        self,
        max_items_per_channel: int = 3,
        drug_fields: str = "brand_name,generic_name,active_ingredients,indications",
        field_caps: Optional[Dict[str, int]] = None,
    ):
        self.max_items_per_channel = max_items_per_channel
        self.allowed_drug_fields = set(f.strip().lower() for f in drug_fields.split(",") if f.strip())
        self.field_caps = field_caps or {
            "indications": 700,
            "warnings": 300,
            "dosage": 300,
            "adverse_reactions": 300,
            "symptoms": 12,
        }

    def format(
        self,
        all_retrievals: Dict[str, List[Any]],
        token_budget: Optional[int] = None,
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Formats all retrievals into compact evidence blocks.
        Returns:
            formatted_text: str (tagged blocks)
            evidence_trace: dict (metadata, covers_ids, trimmed items, token counts)
        """
        evidence_items: List[EvidenceItem] = []
        omitted_ids: List[str] = []

        channel_order = [
            "diseases",
            "drugs",
            "drugs_from_ocr",
            "drug_dict",
            "graph_diseases",
            "graph_drugs",
        ]

        # 1. Collect & deduplicate per channel
        for chan in channel_order:
            raw_results = all_retrievals.get(chan, [])
            if not raw_results:
                continue

            if chan in ("drugs", "drugs_from_ocr"):
                deduped, chan_omitted = deduplicate_drug_items(
                    raw_results, max_items=self.max_items_per_channel
                )
                omitted_ids.extend(chan_omitted)

                for rep in deduped:
                    obj = rep["obj"]
                    fields = {}
                    if rep["primary_brand"]:
                        fields["brand_name"] = rep["primary_brand"]
                    if rep["generic_name"]:
                        fields["generic_name"] = rep["generic_name"]
                    if rep["also_marketed_as"]:
                        fields["also_marketed_as"] = "; ".join(rep["also_marketed_as"])
                    if rep["substances"]:
                        fields["active_ingredients"] = "; ".join(rep["substances"])

                    ind_raw = clean_text_field(obj.get("indications_and_usage"))
                    if ind_raw:
                        fields["indications"] = strip_boilerplate_prefix(ind_raw)

                    warn_raw = clean_text_field(obj.get("warnings_and_cautions") or obj.get("warnings"))
                    if warn_raw:
                        fields["warnings"] = strip_boilerplate_prefix(warn_raw)

                    dose_raw = clean_text_field(obj.get("dosage_and_administration") or obj.get("dosage"))
                    if dose_raw:
                        fields["dosage"] = strip_boilerplate_prefix(dose_raw)

                    # Corrupted key fallback for adréactions
                    adv_raw = clean_text_field(obj.get("adverse_reactions") or obj.get("adréactions"))
                    if adv_raw:
                        fields["adverse_reactions"] = strip_boilerplate_prefix(adv_raw)

                    raw_id = rep["raw_id"]
                    item_type = "DRUG"
                    evidence_items.append(
                        EvidenceItem(
                            channel=chan,
                            raw_id=raw_id,
                            covers_ids=rep["covers_ids"],
                            item_type=item_type,
                            fields=fields,
                        )
                    )

            elif chan == "diseases":
                for idx, item in enumerate(raw_results):
                    if idx >= self.max_items_per_channel:
                        raw_id = extract_item_id(item[2] if len(item) > 2 else {}, item[0], chan)
                        omitted_ids.append(raw_id)
                        continue

                    key, score, obj = item
                    raw_id = extract_item_id(obj, key, chan)
                    chunk_data = obj.get("chunk", obj) if isinstance(obj, dict) else {}
                    cond_name = clean_text_field(chunk_data.get("disease", key))

                    symptoms_raw = chunk_data.get("symptoms", [])
                    if isinstance(symptoms_raw, str):
                        symptoms_raw = [s.strip() for s in symptoms_raw.split(",") if s.strip()]
                    symptoms_capped = [clean_text_field(s) for s in symptoms_raw if clean_text_field(s)]
                    symptoms_capped = symptoms_capped[: self.field_caps.get("symptoms", 12)]

                    fields = {}
                    if cond_name:
                        fields["condition"] = cond_name
                    if symptoms_capped:
                        fields["symptoms"] = "; ".join(symptoms_capped)

                    evidence_items.append(
                        EvidenceItem(
                            channel=chan,
                            raw_id=raw_id,
                            covers_ids=[raw_id],
                            item_type="DISEASE",
                            fields=fields,
                        )
                    )

            elif chan == "drug_dict":
                for idx, item in enumerate(raw_results):
                    if idx >= self.max_items_per_channel:
                        omitted_ids.append(str(item[0]))
                        continue

                    key, score, obj = item
                    name_raw = clean_text_field(obj.get("drug_name", key) if isinstance(obj, dict) else key)
                    fields = {}
                    if name_raw:
                        fields["name"] = name_raw

                    raw_id = str(obj.get("id", key) if isinstance(obj, dict) else key)
                    evidence_items.append(
                        EvidenceItem(
                            channel=chan,
                            raw_id=raw_id,
                            covers_ids=[raw_id],
                            item_type="DRUG_NAME_MATCH",
                            fields=fields,
                        )
                    )

            elif chan == "graph_diseases":
                for idx, item in enumerate(raw_results):
                    if idx >= self.max_items_per_channel:
                        omitted_ids.append(str(item[0]))
                        continue
                    key, score, obj = item
                    cond_name = clean_text_field(obj.get("disease", key) if isinstance(obj, dict) else key)
                    symptoms_raw = obj.get("symptoms", []) if isinstance(obj, dict) else []
                    symptoms_capped = [clean_text_field(s) for s in symptoms_raw if clean_text_field(s)]
                    symptoms_capped = symptoms_capped[: self.field_caps.get("symptoms", 12)]

                    fields = {}
                    if cond_name:
                        fields["condition"] = cond_name
                    if symptoms_capped:
                        fields["symptoms"] = "; ".join(symptoms_capped)

                    raw_id = str(key)
                    evidence_items.append(
                        EvidenceItem(
                            channel=chan,
                            raw_id=raw_id,
                            covers_ids=[raw_id],
                            item_type="GRAPH_DISEASE",
                            fields=fields,
                        )
                    )

            elif chan == "graph_drugs":
                for idx, item in enumerate(raw_results):
                    if idx >= self.max_items_per_channel:
                        omitted_ids.append(str(item[0]))
                        continue
                    key, score, obj = item
                    fields = {}
                    for fld in ("brand_name", "generic_name", "active_ingredients", "indications"):
                        src_k = "indications_and_usage" if fld == "indications" else fld
                        val = clean_text_field(obj.get(src_k) if isinstance(obj, dict) else None)
                        if val:
                            fields[fld] = strip_boilerplate_prefix(val) if fld == "indications" else val

                    raw_id = str(key)
                    evidence_items.append(
                        EvidenceItem(
                            channel=chan,
                            raw_id=raw_id,
                            covers_ids=[raw_id],
                            item_type="GRAPH_DRUG",
                            fields=fields,
                        )
                    )

        # 2. Token Budget Enforcement (Progressive shrinking then round-robin dropping)
        multiplier = 1.0
        active_items = list(evidence_items)
        trims_recorded: List[Dict[str, Any]] = []

        def build_rendered(items: List[EvidenceItem], mult: float) -> Tuple[str, List[Dict[str, Any]], int]:
            blocks = []
            trace_items = []
            for idx, itm in enumerate(items, 1):
                tag = f"[E{idx}]"
                txt = build_evidence_item_block(
                    itm, tag, self.field_caps, self.allowed_drug_fields, cap_multiplier=mult
                )
                tokens = estimate_tokens(txt)
                blocks.append(txt)
                trace_items.append({
                    "id": itm.raw_id,
                    "covers_ids": itm.covers_ids,
                    "tag": tag,
                    "channel": itm.channel,
                    "item_type": itm.item_type,
                    "tokens": tokens,
                })
            joined = "\n".join(blocks)
            total_toks = estimate_tokens(joined)
            return joined, trace_items, total_toks

        rendered_text, item_traces, total_evidence_tokens = build_rendered(active_items, multiplier)

        if token_budget is not None and total_evidence_tokens > token_budget:
            # Stage A: Progressively shrink caps
            for shrink_factor in (0.75, 0.50, 0.35):
                multiplier = shrink_factor
                rendered_text, item_traces, total_evidence_tokens = build_rendered(active_items, multiplier)
                trims_recorded.append({
                    "action": "shrink_caps",
                    "multiplier": multiplier,
                    "tokens": total_evidence_tokens,
                })
                if total_evidence_tokens <= token_budget:
                    break

            # Stage B: If still over budget, drop lowest-ranked items round-robin across channels
            if total_evidence_tokens > token_budget and len(active_items) > 1:
                # Group item indices by channel reversed (lowest ranked first)
                chan_indices = {}
                for idx, itm in enumerate(active_items):
                    chan_indices.setdefault(itm.channel, []).append(idx)

                # Round-robin drop from channel with most items
                while total_evidence_tokens > token_budget and len(active_items) > 1:
                    # Pick channel with largest remaining items
                    best_chan = max(chan_indices.keys(), key=lambda ch: len(chan_indices[ch]))
                    if not chan_indices[best_chan]:
                        break
                    drop_idx = chan_indices[best_chan].pop()
                    dropped_itm = active_items[drop_idx]
                    omitted_ids.extend(dropped_itm.covers_ids)
                    trims_recorded.append({
                        "action": "drop_item",
                        "dropped_id": dropped_itm.raw_id,
                        "channel": dropped_itm.channel,
                    })

                    # Rebuild active items from remaining
                    remaining_indices = sorted([i for indices in chan_indices.values() for i in indices])
                    active_items = [active_items[i] for i in remaining_indices]

                    # Re-index chan_indices
                    chan_indices = {}
                    for idx, itm in enumerate(active_items):
                        chan_indices.setdefault(itm.channel, []).append(idx)

                    rendered_text, item_traces, total_evidence_tokens = build_rendered(active_items, multiplier)

        evidence_trace = {
            "evidence_items": item_traces,
            "total_evidence_tokens": total_evidence_tokens,
            "retrieved_but_omitted_ids": sorted(list(set(omitted_ids))),
            "trims": trims_recorded,
            "cap_multiplier": multiplier,
        }

        return rendered_text, evidence_trace
