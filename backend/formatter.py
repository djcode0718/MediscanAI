# # # backend/formatter.py
# # from typing import Dict, Any, List

# # def build_summary_card(user_text: str, ocr_text: str, retrievals: Dict[str, List], llm_output: str) -> Dict[str, Any]:
# #     """
# #     Create a formatted structure for the frontend to render.
# #     retrievals: mapping index_name -> list of (key, score, obj)
# #     """
# #     card = {
# #         "user_text": user_text,
# #         "ocr_text": ocr_text,
# #         "llm_output": llm_output,
# #         "retrieved": {}
# #     }
# #     for idx_name, items in retrievals.items():
# #         card["retrieved"][idx_name] = []
# #         for key, score, obj in items:
# #             # keep small preview of object based on keys
# #             preview = {}
# #             # try to extract key fields if present
# #             for candidate in ("disease", "symptoms", "brand_name", "generic_name", "drug_name", "indications_and_usage"):
# #                 if candidate in obj:
# #                     preview[candidate] = obj[candidate]
# #             card["retrieved"][idx_name].append({
# #                 "key": key,
# #                 "score": score,
# #                 "preview": preview
# #             })
# #     return card

# # def pretty_print_card(card: Dict[str, Any]) -> str:
# #     s = []
# #     s.append("=== MediScanAI Result ===")
# #     if card["ocr_text"]:
# #         s.append(f"OCR: {card['ocr_text']}")
# #     s.append(f"User: {card['user_text']}")
# #     s.append("\n-- LLM RESPONSE --\n")
# #     s.append(card["llm_output"])
# #     s.append("\n-- Retrieved (short) --\n")
# #     for idx, items in card["retrieved"].items():
# #         s.append(f"[{idx}]")
# #         for it in items:
# #             s.append(f" - {it['key']} (score: {it['score']:.4f}) preview: {it['preview']}")
# #     return "\n".join(s)



# #formatter.py

# from typing import Dict, Any, List
# import json

# def build_summary_card(user_text: str, ocr_text: str, retrievals: Dict[str, List], llm_data: Dict[str, Any]) -> Dict[str, Any]:
#     """
#     Create a formatted structure for the frontend to render.
#     """
#     card = {
#         "user_text": user_text,
#         "ocr_text": ocr_text,
#         "llm_output": llm_data,
#         "retrieved": {}
#     }
#     for idx_name, items in retrievals.items():
#         card["retrieved"][idx_name] = []
#         for key, score, obj in items:
#             preview = {}
            
#             data_source = obj.get('chunk', obj) if isinstance(obj, dict) else obj

#             if isinstance(data_source, dict):
#                 for candidate in ("disease", "symptoms", "brand_name", "generic_name", "drug_name", "indications_and_usage"):
#                     if candidate in data_source:
#                         preview[candidate] = data_source[candidate]
            
#             card["retrieved"][idx_name].append({
#                 "key": key,
#                 "score": score,
#                 "preview": preview
#             })
#     return card

# def pretty_print_card(card: Dict[str, Any]) -> str:
#     s = []
#     s.append("=== MediScanAI Result ===")
#     if card.get("ocr_text"):
#         s.append(f"OCR: {card['ocr_text']}")
#     s.append(f"User: {card['user_text']}")
    
#     s.append("\n-- LLM RESPONSE --\n")
#     llm_output = card.get("llm_output", {})
#     if "error" in llm_output:
#         s.append(f"Error: {llm_output['error']}")
#         s.append(f"Raw Text: {llm_output.get('raw_text', '')}")
#     else:
#         s.append(json.dumps(llm_output, indent=2))

#     s.append("\n-- Retrieved (short) --\n")
#     for idx, items in card.get("retrieved", {}).items():
#         s.append(f"[{idx}]")
#         for it in items:
#             s.append(f" - {it['key']} (score: {it['score']:.4f}) preview: {it['preview']}")
#     return "\n".join(s)