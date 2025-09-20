from typing import Dict, Any, List
import json

def build_summary_card(user_text: str, ocr_text: str, retrievals: Dict[str, List], llm_output: str) -> Dict[str, Any]:
    card = {
        "user_text": user_text,
        "ocr_text": ocr_text,
        "llm_output": llm_output,
        "retrieved": {}
    }
    for idx_name, items in retrievals.items():
        card["retrieved"][idx_name] = []
        for key, score, obj in items:
            preview = {}
            data_source = obj.get('chunk', obj) if isinstance(obj, dict) else obj
            if isinstance(data_source, dict):
                for candidate in ("disease", "symptoms", "brand_name", "generic_name", "drug_name", "indications_and_usage"):
                    if candidate in data_source:
                        preview[candidate] = data_source[candidate]
            card["retrieved"][idx_name].append({
                "key": key,
                "score": score,
                "preview": preview
            })
    return card

def pretty_print_card(card: Dict[str, Any]) -> str:
    s = []
    s.append("=== MediScanAI Result ===")
    if card.get("ocr_text"):
        s.append(f"OCR: {card['ocr_text']}")
    s.append(f"User: {card['user_text']}")
    
    s.append("\n-- LLM RESPONSE --\n")
    llm_output = card.get("llm_output", "")
    if isinstance(llm_output, dict) and "error" in llm_output:
        s.append(f"Error: {llm_output['error']}")
        s.append(f"Raw Text: {llm_output.get('raw_text', '')}")
    elif isinstance(llm_output, dict):
        s.append(json.dumps(llm_output, indent=2))
    else:
        s.append(str(llm_output))

    s.append("\n-- Retrieved (short) --\n")
    for idx, items in card.get("retrieved", {}).items():
        s.append(f"[{idx}]")
        for it in items:
            s.append(f" - {it['key']} (score: {it['score']:.4f}) preview: {it['preview']}")
    return "\n".join(s)