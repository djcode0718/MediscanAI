

# #backend/core.py
# from typing import Optional, Dict, Any
# from backend.ocr import extract_text_from_image, ocr_text_join
# from backend.retriever import MultiRetriever
# from backend.llm import generate
# from backend.formatter import build_summary_card, pretty_print_card
# from backend.utils import normalize_text

# DEFAULT_INDEXES = {
#     "diseases": {
#         "index_path": "indexes/diseases_faiss.index",
#         "jsonl_path": "data/diseases_faiss_data.jsonl",
#         "id_key": "id"
#     },
#     "drugs": {
#         "index_path": "indexes/drugs_faiss.index",
#         "jsonl_path": "data/drugs_faiss_data.jsonl",
#         "id_key": "brand_name"
#     },
#     "drug_dict": {
#         "index_path": "indexes/drug_dict_faiss.index",
#         "jsonl_path": "data/drug_dict_faiss_data.jsonl",
#         "id_key": "id"
#     }
# }

# class Pipeline:
#     def __init__(self, indexes_config: Dict[str, Dict] = None):
#         self.config = indexes_config or DEFAULT_INDEXES
#         self.retriever = MultiRetriever(self.config)

#     def run(self, user_text: str, image_path: Optional[str] = None, top_k: int = 5) -> Dict[str, Any]:
#         """
#         Orchestrate the entire pipeline:
#         - run OCR (if provided)
#         - combine text
#         - run retrievals
#         - perform cross-check (drug <-> disease)
#         - call local Mistral via Ollama
#         - format output
#         """
#         user_norm = normalize_text(user_text or "")
#         ocr_text = ""
#         if image_path:
#             ocr_res = extract_text_from_image(image_path)
#             ocr_text = ocr_text_join(ocr_res["texts"])

#         combined_text = " ".join([t for t in [user_norm, normalize_text(ocr_text)] if t]).strip()

#         if not combined_text:
#             combined_text = user_norm or ""

#         retrievals = self.retriever.search_all(combined_text, top_k=top_k)

#         canonical_drug = None
#         drug_details = None
#         disease_matches = []

#         dd_results = retrievals.get("drug_dict", [])
#         if dd_results:
#             key, score, obj = dd_results[0]
#             canonical_drug = obj.get("drug_name") or obj.get("brand_name") or obj.get("generic_name") or key

#         drug_results = retrievals.get("drugs", [])
#         if drug_results:
#             key, score, obj = drug_results[0]
#             drug_details = obj

#         disease_results = retrievals.get("diseases", [])
#         for key, score, obj in disease_results:
#             disease_matches.append(obj)

#         mismatch_warning = None
#         if canonical_drug and drug_details and disease_matches:
#             indications = (drug_details.get("indications_and_usage", "") or "").lower()
#             found = False
#             for disease in disease_matches:
#                 dname = str(disease.get("disease", "")).lower()
#                 if dname and dname in indications:
#                     found = True
#                     break
#                 for s in disease.get("symptoms", []) or []:
#                     if s and str(s).lower()[:3] and str(s).lower() in indications:
#                         found = True
#                         break
#                 if found:
#                     break
#             if not found:
#                 mismatch_warning = {
#                     "drug": canonical_drug,
#                     "drug_details": drug_details,
#                     "diseases": disease_matches
#                 }

#         prompt_parts = []
#         prompt_parts.append("You are MediScanAI assistant. Use the retrieved facts below to answer the user. Be concise and safe. If unsure, advise to consult a physician.")
#         prompt_parts.append("\n=== USER INPUT ===")
#         prompt_parts.append(f"User text: {user_text}")
#         if ocr_text:
#             prompt_parts.append(f"OCR: {ocr_text}")

#         prompt_parts.append("\n=== RETRIEVED ===")
#         for idx_name, items in retrievals.items():
#             prompt_parts.append(f"\n-- {idx_name.upper()} (top {len(items)}) --")
#             for key, score, obj in items:
#                 brief_text = str(obj)
#                 prompt_parts.append(f"* {brief_text} (score: {score:.4f})")

#         if mismatch_warning:
#             prompt_parts.append("\n=== CROSS-CHECK ANALYSIS ===")
#             prompt_parts.append(
#                 f"Potential mismatch detected: The detected drug '{mismatch_warning['drug']}' does not appear to match the retrieved disease(s). "
#                 "Explain why this could be inappropriate, warn user, and suggest appropriate alternatives (name drugs/classes or OTC options) and next steps."
#             )
#         else:
#             prompt_parts.append("\nNo obvious mismatch detected. Provide guidance and next steps based on retrieved info.")

#         full_prompt = "\n".join(prompt_parts)
#         print("full promp : ",full_prompt)

#         llm_response = generate(full_prompt)

#         card = build_summary_card(user_text, ocr_text, retrievals, llm_response)

#         card_meta = {
#             "mismatch": bool(mismatch_warning),
#             "mismatch_details": mismatch_warning
#         }

#         return {
#             "card": card,
#             "meta": card_meta
#         }


# import json
# from typing import Optional, Dict, Any
# from backend.ocr import extract_text_from_image, ocr_text_join
# from backend.retriever import MultiRetriever
# from backend.llm import generate
# from backend.formatter import build_summary_card
# from backend.utils import normalize_text

# DEFAULT_INDEXES = {
#     "diseases": {
#         "index_path": "indexes/diseases_faiss.index",
#         "jsonl_path": "data/diseases_faiss_data.jsonl",
#         "id_key": "id"
#     },
#     "drugs": {
#         "index_path": "indexes/drugs_faiss.index",
#         "jsonl_path": "data/drugs_faiss_data.jsonl",
#         "id_key": "brand_name"
#     },
#     "drug_dict": {
#         "index_path": "indexes/drug_dict_faiss.index",
#         "jsonl_path": "data/drug_dict_faiss_data.jsonl",
#         "id_key": "id"
#     }
# }

# class Pipeline:
#     def __init__(self, indexes_config: Dict[str, Dict] = None):
#         self.config = indexes_config or DEFAULT_INDEXES
#         self.retriever = MultiRetriever(self.config)

#     def run(self, user_text: str, image_path: Optional[str] = None, top_k: int = 5) -> Dict[str, Any]:
#         user_norm = normalize_text(user_text or "")
#         ocr_text = ""
#         if image_path:
#             ocr_res = extract_text_from_image(image_path)
#             ocr_text = ocr_text_join(ocr_res["texts"])

#         combined_text = " ".join([t for t in [user_norm, normalize_text(ocr_text)] if t]).strip()

#         if not combined_text:
#             combined_text = user_norm or ""

#         retrievals = self.retriever.search_all(combined_text, top_k=top_k)

#         prompt_context = []
#         prompt_context.append("\n=== USER INPUT ===")
#         prompt_context.append(f"User text: {user_text}")
#         if ocr_text:
#             prompt_context.append(f"OCR: {ocr_text}")

#         prompt_context.append("\n=== RETRIEVED DATA ===")
#         for idx_name, items in retrievals.items():
#             prompt_context.append(f"\n-- Retrieved from {idx_name.upper()} --")
#             for key, score, obj in items:
#                 prompt_context.append(f"* {str(obj)} (score: {score:.4f})")

#         structured_prompt = f"""
# You are MediScanAI, an expert medical analysis assistant. Your task is to analyze the user's query and the retrieved data to provide a helpful, structured response.
# Your response MUST be a single, valid JSON object. Do not include any text or formatting before or after the JSON object.

# Based on the provided context below, generate a JSON object with the following schema:
# {{
#   "likely_condition": {{
#     "name": "string",
#     "confidence_score": "string (e.g., 'High', 'Medium', 'Low')",
#     "supporting_symptoms": ["string"],
#     "summary": "string"
#   }},
#   "medication_suggestions": [
#     {{
#       "brand_name": "string",
#       "generic_ingredients": "string",
#       "use_indication": "string"
#     }}
#   ],
#   "dosage_information": "string",
#   "self_care_tips": ["string"],
#   "warnings": ["string"]
# }}

# Here is the context to analyze:
# {''.join(prompt_context)}

# Now, generate the JSON response.
# """
#         full_prompt = structured_prompt.strip()

#         llm_response_str = generate(full_prompt)

#         llm_data = {}
#         try:
#             llm_data = json.loads(llm_response_str)
#         except json.JSONDecodeError:
#             llm_data = {"raw_text": llm_response_str, "error": "Failed to parse LLM response as JSON."}

#         card = build_summary_card(user_text, ocr_text, retrievals, llm_data)

#         card_meta = {
#             "mismatch": False, # Mismatch logic is disabled for this simplified flow
#             "mismatch_details": None
#         }

#         return {
#             "card": card,
#             "meta": card_meta
#         }


# import json
# from typing import Optional, Dict, Any
# from backend.ocr import extract_text_from_image, ocr_text_join
# from backend.retriever import MultiRetriever
# from backend.llm import generate
# from backend.formatter import build_summary_card
# from backend.utils import normalize_text

# DEFAULT_INDEXES = {
#     "diseases": {
#         "index_path": "indexes/diseases_faiss.index",
#         "jsonl_path": "data/diseases_faiss_data.jsonl",
#         "id_key": "id"
#     },
#     "drugs": {
#         "index_path": "indexes/drugs_faiss.index",
#         "jsonl_path": "data/drugs_faiss_data.jsonl",
#         "id_key": "brand_name"
#     },
#     "drug_dict": {
#         "index_path": "indexes/drug_dict_faiss.index",
#         "jsonl_path": "data/drug_dict_faiss_data.jsonl",
#         "id_key": "id"
#     }
# }

# class Pipeline:
#     def __init__(self, indexes_config: Dict[str, Dict] = None):
#         self.config = indexes_config or DEFAULT_INDEXES
#         self.retriever = MultiRetriever(self.config)

#     def run(self, user_text: str, image_path: Optional[str] = None, top_k: int = 5) -> Dict[str, Any]:
#         user_norm = normalize_text(user_text or "")
#         ocr_text = ""
#         if image_path:
#             ocr_res = extract_text_from_image(image_path)
#             ocr_text = ocr_text_join(ocr_res["texts"])

#         combined_text = " ".join([t for t in [user_norm, normalize_text(ocr_text)] if t]).strip()

#         if not combined_text:
#             combined_text = user_norm or ""

#         retrievals = self.retriever.search_all(combined_text, top_k=top_k)

#         prompt_context = []
#         prompt_context.append("\n=== USER INPUT ===")
#         prompt_context.append(f"User text: {user_text}")
#         if ocr_text:
#             prompt_context.append(f"OCR: {ocr_text}")

#         prompt_context.append("\n=== RETRIEVED DATA ===")
#         for idx_name, items in retrievals.items():
#             prompt_context.append(f"\n-- Retrieved from {idx_name.upper()} --")
#             for key, score, obj in items:
#                 prompt_context.append(f"* {str(obj)} (score: {score:.4f})")

#         structured_prompt = f"""
# You are MediScanAI, an expert medical analysis assistant. Your task is to analyze the user's query and the retrieved data to provide a helpful, structured response.
# Your response MUST be a single, valid JSON object. Do not include any text or formatting before or after the JSON object.

# Based on the provided context below, generate a JSON object with the following schema:
# {{
#   "likely_condition": {{
#     "name": "string",
#     "confidence_score": "string (e.g., 'High', 'Medium', 'Low')",
#     "supporting_symptoms": ["string"],
#     "summary": "string"
#   }},
#   "medication_suggestions": [
#     {{
#       "brand_name": "string",
#       "generic_ingredients": "string",
#       "use_indication": "string"
#     }}
#   ],
#   "dosage_information": "string",
#   "self_care_tips": ["string"],
#   "warnings": ["string"]
# }}

# Here is the context to analyze:
# {''.join(prompt_context)}

# Now, generate the JSON response.
# """
#         full_prompt = structured_prompt.strip()

#         llm_response_str = generate(full_prompt)

#         llm_data = {}
#         try:
#             start_index = llm_response_str.find('{')
#             end_index = llm_response_str.rfind('}')
#             if start_index != -1 and end_index != -1 and end_index > start_index:
#                 json_str = llm_response_str[start_index:end_index+1]
#                 llm_data = json.loads(json_str)
#             else:
#                 raise json.JSONDecodeError("No JSON object found in the response.", llm_response_str, 0)
#         except json.JSONDecodeError:
#             llm_data = {"raw_text": llm_response_str, "error": "Failed to parse LLM response as JSON."}

#         card = build_summary_card(user_text, ocr_text, retrievals, llm_data)

#         card_meta = {
#             "mismatch": False,
#             "mismatch_details": None
#         }

#         return {
#             "card": card,
#             "meta": card_meta
#         }


#core.py


# import json
# from typing import Optional, Dict, Any
# from backend.ocr import extract_text_from_image, ocr_text_join
# from backend.retriever import MultiRetriever
# from backend.llm import generate
# from backend.formatter import build_summary_card
# from backend.utils import normalize_text

# DEFAULT_INDEXES = {
#     "diseases": {
#         "index_path": "indexes/diseases_faiss.index",
#         "jsonl_path": "data/diseases_faiss_data.jsonl",
#         "id_key": "id"
#     },
#     "drugs": {
#         "index_path": "indexes/drugs_faiss.index",
#         "jsonl_path": "data/drugs_faiss_data.jsonl",
#         "id_key": "brand_name"
#     },
#     "drug_dict": {
#         "index_path": "indexes/drug_dict_faiss.index",
#         "jsonl_path": "data/drug_dict_faiss_data.jsonl",
#         "id_key": "id"
#     }
# }

# class Pipeline:
#     def __init__(self, indexes_config: Dict[str, Dict] = None):
#         self.config = indexes_config or DEFAULT_INDEXES
#         self.retriever = MultiRetriever(self.config)

#     def run(self, user_text: str, image_path: Optional[str] = None, top_k: int = 5) -> Dict[str, Any]:
#         user_norm = normalize_text(user_text or "")
#         ocr_text = ""
#         if image_path:
#             ocr_res = extract_text_from_image(image_path)
#             ocr_text = ocr_text_join(ocr_res["texts"])

#         combined_text = " ".join([t for t in [user_norm, normalize_text(ocr_text)] if t]).strip()

#         if not combined_text:
#             combined_text = user_norm or ""

#         retrievals = self.retriever.search_all(combined_text, top_k=top_k)

#         prompt_context = []
#         prompt_context.append("\n=== USER INPUT ===")
#         prompt_context.append(f"User text: {user_text}")
#         if ocr_text:
#             prompt_context.append(f"OCR: {ocr_text}")

#         prompt_context.append("\n=== RETRIEVED DATA ===")
#         for idx_name, items in retrievals.items():
#             prompt_context.append(f"\n-- Retrieved from {idx_name.upper()} --")
#             for key, score, obj in items:
#                 prompt_context.append(f"* {str(obj)} (score: {score:.4f})")

#         structured_prompt = f"""
# You are MediScanAI, an expert medical analysis assistant. Your task is to analyze the user's query and the retrieved data to provide a helpful, structured response.
# Your response MUST be a single, valid JSON object. Do not include any text or formatting before or after the JSON object.

# CRITICAL INSTRUCTION: Pay special attention to the OCR text. If the drug identified in the OCR context does not seem appropriate for the user's stated symptoms, you must set `is_mismatch` to `true` and provide a clear explanation.

# Based on the provided context below, generate a JSON object with the following schema:
# {{
#   "likely_condition": {{
#     "name": "string",
#     "confidence_score": "string (e.g., 'High', 'Medium', 'Low')",
#     "supporting_symptoms": ["string"],
#     "summary": "string"
#   }},
#   "medication_suggestions": [
#     {{
#       "brand_name": "string",
#       "generic_ingredients": "string",
#       "use_indication": "string"
#     }}
#   ],
#   "dosage_information": "string",
#   "self_care_tips": ["string"],
#   "warnings": ["string"],
#   "mismatch_analysis": {{
#     "is_mismatch": "boolean",
#     "explanation": "string (Explain why the drug from the OCR text might be incorrect for the user's stated symptoms. If no mismatch, this can be an empty string.)"
#   }}
# }}

# Here is the context to analyze:
# {''.join(prompt_context)}

# Now, generate the JSON response.
# """
#         full_prompt = structured_prompt.strip()

#         llm_response_str = generate(full_prompt)

#         llm_data = {}
#         try:
#             start_index = llm_response_str.find('{')
#             end_index = llm_response_str.rfind('}')
#             if start_index != -1 and end_index != -1 and end_index > start_index:
#                 json_str = llm_response_str[start_index:end_index+1]
#                 llm_data = json.loads(json_str)
#             else:
#                 raise json.JSONDecodeError("No JSON object found in the response.", llm_response_str, 0)
#         except json.JSONDecodeError:
#             llm_data = {"raw_text": llm_response_str, "error": "Failed to parse LLM response as JSON."}

#         card = build_summary_card(user_text, ocr_text, retrievals, llm_data)

#         # Use the LLM's analysis to populate the mismatch metadata
#         mismatch_analysis = llm_data.get("mismatch_analysis", {})
#         is_mismatch = mismatch_analysis.get("is_mismatch", False)
#         mismatch_details = mismatch_analysis.get("explanation", None)

#         card_meta = {
#             "mismatch": is_mismatch,
#             "mismatch_details": mismatch_details
#         }

#         return {
#             "card": card,
#             "meta": card_meta
#         }

# import json
# from typing import Optional, Dict, Any, Tuple
# from backend.ocr import extract_text_from_image, ocr_text_join
# from backend.retriever import MultiRetriever
# from backend.llm import generate
# from backend.formatter import build_summary_card
# from backend.utils import normalize_text
# from backend.embeddings import embed_texts

# DEFAULT_INDEXES = {
#     "diseases": {
#         "index_path": "indexes/diseases_faiss.index",
#         "jsonl_path": "data/diseases_faiss_data.jsonl",
#         "id_key": "id"
#     },
#     "drugs": {
#         "index_path": "indexes/drugs_faiss.index",
#         "jsonl_path": "data/drugs_faiss_data.jsonl",
#         "id_key": "brand_name"
#     },
#     "drug_dict": {
#         "index_path": "indexes/drug_dict_faiss.index",
#         "jsonl_path": "data/drug_dict_faiss_data.jsonl",
#         "id_key": "id"
#     }
# }

# class Pipeline:
#     def __init__(self, indexes_config: Dict[str, Dict] = None):
#         self.config = indexes_config or DEFAULT_INDEXES
#         self.retriever = MultiRetriever(self.config)

#     def _perform_hybrid_mismatch_check(
#         self, ocr_text: str, disease_results: list, drug_results: list
#     ) -> Tuple[bool, str]:
#         """
#         Performs a fast, rule-based check for mismatches before calling the LLM.
#         Returns (is_mismatch, explanation).
#         """
#         if not ocr_text or not disease_results:
#             return False, ""

#         # 1. Find the most likely drug name from the OCR text using the drug_dict index
#         ocr_emb = embed_texts([ocr_text])[0]
#         ocr_drug_search = self.retriever.idx_wrappers["drug_dict"].search(ocr_emb, top_k=1)
#         if not ocr_drug_search:
#             return False, ""
        
#         _, _, ocr_drug_obj = ocr_drug_search[0]
#         ocr_drug_name = ocr_drug_obj.get("drug_name")
#         if not ocr_drug_name:
#             return False, ""

#         # 2. Find the full details (indications) for this OCR'd drug
#         # We search the 'drugs' index with the OCR drug name to find its full data
#         drug_emb = embed_texts([ocr_drug_name])[0]
#         full_drug_search = self.retriever.idx_wrappers["drugs"].search(drug_emb, top_k=1)
#         if not full_drug_search:
#             return False, ""
            
#         _, _, full_drug_obj = full_drug_search[0]
#         indications = full_drug_obj.get("indications_and_usage", "").lower()
#         if not indications:
#             return False, ""

#         # 3. Get the top disease and its symptoms
#         top_disease_obj = disease_results[0][2] # (key, score, obj)
#         top_disease_data = top_disease_obj.get('chunk', {})
#         disease_name = top_disease_data.get("disease", "").lower()
#         symptoms = [s.lower() for s in top_disease_data.get("symptoms", [])]

#         # 4. Perform the check
#         if disease_name and disease_name in indications:
#             return False, "" 

#         for symptom in symptoms:
#             if symptom and symptom in indications:
#                 return False, ""

#         explanation = f"The drug identified in the image ('{ocr_drug_name}') is not indicated for the user's likely condition ('{disease_name.title()}')."
#         return True, explanation

#     def run(self, user_text: str, image_path: Optional[str] = None, top_k: int = 3) -> Dict[str, Any]:
#         user_norm = normalize_text(user_text or "")
#         ocr_text = ""
#         if image_path:
#             ocr_res = extract_text_from_image(image_path)
#             ocr_text = ocr_text_join(ocr_res["texts"])

#         combined_text = " ".join([t for t in [user_norm, normalize_text(ocr_text)] if t]).strip()

#         if not combined_text:
#             combined_text = user_norm or ""

#         retrievals = self.retriever.search_all(combined_text, top_k=top_k)

#         # Perform the deterministic, rule-based mismatch check first
#         is_mismatch, mismatch_explanation = self._perform_hybrid_mismatch_check(
#             ocr_text, retrievals.get("diseases", []), retrievals.get("drugs", [])
#         )

#         mismatch_injection = ""
#         if is_mismatch:
#             mismatch_injection = f"CRITICAL PRE-ANALYSIS: Our system has detected a mismatch. {mismatch_explanation} You must reflect this fact in your JSON output. Set `is_mismatch` to `true` and use the provided explanation."

#         prompt_context = []
#         prompt_context.append("\n=== USER INPUT ===")
#         prompt_context.append(f"User text: {user_text}")
#         if ocr_text:
#             prompt_context.append(f"OCR: {ocr_text}")

#         prompt_context.append("\n=== RETRIEVED DATA ===")
#         for idx_name, items in retrievals.items():
#             prompt_context.append(f"\n-- Retrieved from {idx_name.upper()} --")
#             for key, score, obj in items:
#                 prompt_context.append(f"* {str(obj)} (score: {score:.4f})")

#         structured_prompt = f"""
# You are MediScanAI, an expert medical analysis assistant. Your task is to analyze the user's query and the retrieved data to provide a helpful, structured response.
# Your response MUST be a single, valid JSON object. Do not include any text or formatting before or after the JSON object.

# {mismatch_injection}

# Based on the provided context below, generate a JSON object with the following schema:
# {{
#   "likely_condition": {{
#     "name": "string",
#     "confidence_score": "string (e.g., 'High', 'Medium', 'Low')",
#     "supporting_symptoms": ["string"],
#     "summary": "string"
#   }},
#   "medication_suggestions": [
#     {{
#       "brand_name": "string",
#       "generic_ingredients": "string",
#       "use_indication": "string"
#     }}
#   ],
#   "dosage_information": "string",
#   "self_care_tips": ["string"],
#   "warnings": ["string"],
#   "mismatch_analysis": {{
#     "is_mismatch": "boolean",
#     "explanation": "string (Explain why the drug from the OCR text might be incorrect. If no mismatch, this can be an empty string.)"
#   }}
# }}

# Here is the context to analyze:
# {''.join(prompt_context)}

# Now, generate the JSON response.
# """
#         full_prompt = structured_prompt.strip()

#         llm_response_str = generate(full_prompt)

#         llm_data = {}
#         try:
#             start_index = llm_response_str.find('{')
#             end_index = llm_response_str.rfind('}')
#             if start_index != -1 and end_index != -1 and end_index > start_index:
#                 json_str = llm_response_str[start_index:end_index+1]
#                 llm_data = json.loads(json_str)
#             else:
#                 raise json.JSONDecodeError("No JSON object found in the response.", llm_response_str, 0)
#         except json.JSONDecodeError:
#             llm_data = {"raw_text": llm_response_str, "error": "Failed to parse LLM response as JSON."}

#         card = build_summary_card(user_text, ocr_text, retrievals, llm_data)
        
#         # The mismatch is now determined by our reliable hybrid check
#         card_meta = {
#             "mismatch": is_mismatch,
#             "mismatch_details": mismatch_explanation
#         }

#         return {
#             "card": card,
#             "meta": card_meta
#         }


# import json
# from typing import Optional, Dict, Any, Tuple
# from backend.ocr import extract_text_from_image, ocr_text_join
# from backend.retriever import MultiRetriever
# from backend.llm import generate
# from backend.formatter import build_summary_card
# from backend.utils import normalize_text
# from backend.embeddings import embed_texts

# DEFAULT_INDEXES = {
#     "diseases": {
#         "index_path": "indexes/diseases_faiss.index",
#         "jsonl_path": "data/diseases_faiss_data.jsonl",
#         "id_key": "id"
#     },
#     "drugs": {
#         "index_path": "indexes/drugs_faiss.index",
#         "jsonl_path": "data/drugs_faiss_data.jsonl",
#         "id_key": "brand_name"
#     },
#     "drug_dict": {
#         "index_path": "indexes/drug_dict_faiss.index",
#         "jsonl_path": "data/drug_dict_faiss_data.jsonl",
#         "id_key": "id"
#     }
# }

# class Pipeline:
#     def __init__(self, indexes_config: Dict[str, Dict] = None):
#         self.config = indexes_config or DEFAULT_INDEXES
#         self.retriever = MultiRetriever(self.config)

#     def _perform_hybrid_mismatch_check(
#         self, ocr_text: str, disease_results: list
#     ) -> Tuple[Optional[bool], str]:
#         """
#         Performs a robust, rule-based check and returns a definitive result.
#         Returns (is_mismatch, explanation), where is_mismatch can be True, False, or None.
#         """
#         if not ocr_text:
#             return None, "No image provided; mismatch check is not applicable."
#         if not disease_results:
#             return None, "Could not determine a likely condition; mismatch check is inconclusive."

#         ocr_drug_name_search = self.retriever.search_specific("drug_dict", ocr_text, top_k=1)
#         if not ocr_drug_name_search:
#             return None, "Could not identify a specific drug from the image; mismatch check is inconclusive."
        
#         ocr_drug_name = ocr_drug_name_search[0][2].get("drug_name")
#         if not ocr_drug_name:
#              return None, "Could not identify a specific drug from the image; mismatch check is inconclusive."

#         full_drug_search = self.retriever.search_specific("drugs", ocr_drug_name, top_k=1)
#         if not full_drug_search:
#             return None, f"Could not find detailed information for the OCR drug '{ocr_drug_name}'; mismatch check is inconclusive."
            
#         indications = full_drug_search[0][2].get("indications_and_usage", "").lower()
#         if not indications:
#             return None, f"No usage information found for the OCR drug '{ocr_drug_name}'; mismatch check is inconclusive."

#         # Check against the top_k retrieved diseases for any match
#         for _, _, disease_obj in disease_results:
#             disease_data = disease_obj.get('chunk', {})
#             disease_name = disease_data.get("disease", "").lower()
#             symptoms = [s.lower() for s in disease_data.get("symptoms", [])]

#             if disease_name and disease_name in indications:
#                 explanation = f"The drug from the image ('{ocr_drug_name.title()}') appears appropriate, as its indications mention treating '{disease_name.title()}'."
#                 return False, explanation

#             for symptom in symptoms:
#                 if symptom and symptom in indications:
#                     explanation = f"The drug from the image ('{ocr_drug_name.title()}') appears appropriate as its indications mention treating symptoms like '{symptom}'."
#                     return False, explanation

#         # If no match was found after checking all top diseases, it's a mismatch
#         top_disease_name = disease_results[0][2].get('chunk', {}).get("disease", "the user's condition")
#         explanation = f"Mismatch Detected: The drug from the image ('{ocr_drug_name.title()}') is not indicated for the user's likely condition ('{top_disease_name.title()}')."
#         return True, explanation

#     def run(self, user_text: str, image_path: Optional[str] = None, top_k: int = 3) -> Dict[str, Any]:
#         user_norm = normalize_text(user_text or "")
#         ocr_text = ""
#         if image_path:
#             ocr_res = extract_text_from_image(image_path)
#             ocr_text = ocr_text_join(ocr_res["texts"])

#         # --- Step 1: Isolated Retrievals ---
#         disease_results = self.retriever.search_specific('diseases', user_norm, top_k=top_k)
        
#         drug_query_text = " ".join([t for t in [user_norm, ocr_text] if t]).strip()
#         drug_results = self.retriever.search_specific('drugs', drug_query_text, top_k=top_k)
#         drug_dict_results = self.retriever.search_specific('drug_dict', drug_query_text, top_k=top_k)

#         retrievals = {
#             "diseases": disease_results,
#             "drugs": drug_results,
#             "drug_dict": drug_dict_results
#         }
        
#         # --- Step 2: Robust Mismatch Check ---
#         is_mismatch, mismatch_explanation = self._perform_hybrid_mismatch_check(ocr_text, disease_results)
        
#         # --- Step 3: Prepare Prompt with Deterministic Analysis ---
#         mismatch_injection = f"CRITICAL PRE-ANALYSIS: Our system's rule-based check concluded: '{mismatch_explanation}'. You must use this analysis to populate the 'mismatch_analysis' section of your JSON response. Set 'is_mismatch' to {str(is_mismatch).lower() if isinstance(is_mismatch, bool) else 'null'} and use the provided explanation."

#         prompt_context = []
#         prompt_context.append(f"\n=== USER INPUT ===\nUser text: {user_text}")
#         if ocr_text:
#             prompt_context.append(f"OCR: {ocr_text}")

#         prompt_context.append("\n=== RETRIEVED DATA ===")
#         for idx_name, items in retrievals.items():
#             prompt_context.append(f"\n-- Retrieved from {idx_name.upper()} --")
#             for key, score, obj in items:
#                 prompt_context.append(f"* {str(obj)} (score: {score:.4f})")

#         structured_prompt = f"""
# You are MediScanAI, an expert medical analysis assistant. Your task is to analyze the user's query and the retrieved data to provide a helpful, structured response. Your response MUST be a single, valid JSON object.

# {mismatch_injection}

# Based on the context below, generate a JSON object with the schema provided.
# {{
#   "likely_condition": {{...}},
#   "medication_suggestions": [{{...}}],
#   "dosage_information": "string",
#   "self_care_tips": ["string"],
#   "warnings": ["string"],
#   "mismatch_analysis": {{
#     "is_mismatch": "boolean or null",
#     "explanation": "string (You must use the explanation from the CRITICAL PRE-ANALYSIS.)"
#   }}
# }}

# Here is the context to analyze:
# {''.join(prompt_context)}

# Now, generate the JSON response.
# """
#         full_prompt = structured_prompt.strip()

#         llm_response_str = generate(full_prompt)

#         llm_data = {}
#         try:
#             start_index = llm_response_str.find('{')
#             end_index = llm_response_str.rfind('}')
#             if start_index != -1 and end_index != -1 and end_index > start_index:
#                 json_str = llm_response_str[start_index:end_index+1]
#                 llm_data = json.loads(json_str)
#             else:
#                 raise json.JSONDecodeError("No JSON object found in the response.", llm_response_str, 0)
#         except json.JSONDecodeError:
#             llm_data = {"raw_text": llm_response_str, "error": "Failed to parse LLM response as JSON."}

#         card = build_summary_card(user_text, ocr_text, retrievals, llm_data)
        
#         card_meta = {
#             "mismatch": is_mismatch,
#             "mismatch_details": mismatch_explanation
#         }

#         return {
#             "card": card,
#             "meta": card_meta
#         }

# import json
# from typing import Optional, Dict, Any, Tuple
# from backend.ocr import extract_text_from_image, ocr_text_join
# from backend.retriever import MultiRetriever
# from backend.llm import generate
# from backend.formatter import build_summary_card
# from backend.utils import normalize_text
# from backend.embeddings import embed_texts

# DEFAULT_INDEXES = {
#     "diseases": {
#         "index_path": "indexes/diseases_faiss.index",
#         "jsonl_path": "data/diseases_faiss_data.jsonl",
#         "id_key": "id"
#     },
#     "drugs": {
#         "index_path": "indexes/drugs_faiss.index",
#         "jsonl_path": "data/drugs_faiss_data.jsonl",
#         "id_key": "brand_name"
#     },
#     "drug_dict": {
#         "index_path": "indexes/drug_dict_faiss.index",
#         "jsonl_path": "data/drug_dict_faiss_data.jsonl",
#         "id_key": "id"
#     }
# }

# class Pipeline:
#     def __init__(self, indexes_config: Dict[str, Dict] = None):
#         self.config = indexes_config or DEFAULT_INDEXES
#         self.retriever = MultiRetriever(self.config)

#     def _perform_hybrid_mismatch_check(
#         self, ocr_text: str, disease_results: list
#     ) -> Tuple[Optional[bool], str]:
#         """
#         Performs a robust, multi-candidate check and returns a definitive result.
#         Returns (is_mismatch, explanation), where is_mismatch can be True, False, or None.
#         """
#         if not ocr_text:
#             return None, "No image provided; mismatch check is not applicable."
#         if not disease_results:
#             return None, "Could not determine a likely condition; mismatch check is inconclusive."

#         # Step 1: Get top 3 potential drug candidates from OCR
#         ocr_drug_candidates = self.retriever.search_specific("drug_dict", ocr_text, top_k=3)
#         if not ocr_drug_candidates:
#             return None, "Could not identify any potential drugs from the image; mismatch check is inconclusive."

#         checked_drug_names = []
#         # Step 2: Loop through each candidate to find a match
#         for _, _, candidate_obj in ocr_drug_candidates:
#             ocr_drug_name = candidate_obj.get("drug_name")
#             if not ocr_drug_name:
#                 continue

#             checked_drug_names.append(ocr_drug_name)
#             full_drug_search = self.retriever.search_specific("drugs", ocr_drug_name, top_k=1)
            
#             if not full_drug_search:
#                 continue # This candidate is not in our detailed drug database

#             indications = full_drug_search[0][2].get("indications_and_usage", "").lower()
#             if not indications:
#                 continue # This candidate has no usage info

#             # Check this candidate's indications against all top diseases
#             for _, _, disease_obj in disease_results:
#                 disease_data = disease_obj.get('chunk', {})
#                 disease_name = disease_data.get("disease", "").lower()
#                 symptoms = [s.lower() for s in disease_data.get("symptoms", [])]

#                 if disease_name and disease_name in indications:
#                     explanation = f"The medicine appears appropriate, as it contains '{ocr_drug_name.title()}' which is indicated for '{disease_name.title()}'."
#                     return False, explanation

#                 for symptom in symptoms:
#                     if symptom and symptom in indications:
#                         explanation = f"The medicine appears appropriate, as it contains '{ocr_drug_name.title()}' which is used for symptoms like '{symptom}'."
#                         return False, explanation
        
#         # Step 3: If loop finishes, evaluate the result
#         top_disease_name = disease_results[0][2].get('chunk', {}).get("disease", "the user's condition")
#         if not checked_drug_names:
#             return None, "Could not find detailed information for any drug identified in the image; mismatch check is inconclusive."

#         explanation = f"Mismatch Detected: The drug ingredients identified in the image (e.g., '{', '.join(checked_drug_names)}') do not appear to be indicated for the user's likely condition ('{top_disease_name.title()}')."
#         return True, explanation


#     def run(self, user_text: str, image_path: Optional[str] = None, top_k: int = 3) -> Dict[str, Any]:
#         user_norm = normalize_text(user_text or "")
#         ocr_text = ""
#         if image_path:
#             ocr_res = extract_text_from_image(image_path)
#             ocr_text = ocr_text_join(ocr_res["texts"])

#         disease_results = self.retriever.search_specific('diseases', user_norm, top_k=top_k)
        
#         drug_query_text = " ".join([t for t in [user_norm, ocr_text] if t]).strip()
#         drug_results = self.retriever.search_specific('drugs', drug_query_text, top_k=top_k)
#         drug_dict_results = self.retriever.search_specific('drug_dict', drug_query_text, top_k=top_k)

#         retrievals = {
#             "diseases": disease_results,
#             "drugs": drug_results,
#             "drug_dict": drug_dict_results
#         }
        
#         is_mismatch, mismatch_explanation = self._perform_hybrid_mismatch_check(ocr_text, disease_results)
        
#         mismatch_injection = f"CRITICAL PRE-ANALYSIS: Our system's rule-based check concluded: '{mismatch_explanation}'. You must use this analysis to populate the 'mismatch_analysis' section of your JSON response. Set 'is_mismatch' to {str(is_mismatch).lower() if isinstance(is_mismatch, bool) else 'null'} and use the provided explanation."

#         prompt_context = []
#         prompt_context.append(f"\n=== USER INPUT ===\nUser text: {user_text}")
#         if ocr_text:
#             prompt_context.append(f"OCR: {ocr_text}")

#         prompt_context.append("\n=== RETRIEVED DATA ===")
#         for idx_name, items in retrievals.items():
#             prompt_context.append(f"\n-- Retrieved from {idx_name.upper()} --")
#             for key, score, obj in items:
#                 prompt_context.append(f"* {str(obj)} (score: {score:.4f})")

#         structured_prompt = f"""
# You are MediScanAI, an expert medical analysis assistant. Your task is to analyze the user's query and the retrieved data to provide a helpful, structured response. Your response MUST be a single, valid JSON object.

# {mismatch_injection}

# Based on the context below, generate a JSON object with the schema provided.
# {{
#   "likely_condition": {{...}},
#   "medication_suggestions": [{{...}}],
#   "dosage_information": "string",
#   "self_care_tips": ["string"],
#   "warnings": ["string"],
#   "mismatch_analysis": {{
#     "is_mismatch": "boolean or null",
#     "explanation": "string (You must use the explanation from the CRITICAL PRE-ANALYSIS.)"
#   }}
# }}

# Here is the context to analyze:
# {''.join(prompt_context)}

# Now, generate the JSON response.
# """
#         full_prompt = structured_prompt.strip()

#         llm_response_str = generate(full_prompt)

#         llm_data = {}
#         try:
#             start_index = llm_response_str.find('{')
#             end_index = llm_response_str.rfind('}')
#             if start_index != -1 and end_index != -1 and end_index > start_index:
#                 json_str = llm_response_str[start_index:end_index+1]
#                 llm_data = json.loads(json_str)
#             else:
#                 raise json.JSONDecodeError("No JSON object found in the response.", llm_response_str, 0)
#         except json.JSONDecodeError:
#             llm_data = {"raw_text": llm_response_str, "error": "Failed to parse LLM response as JSON."}

#         card = build_summary_card(user_text, ocr_text, retrievals, llm_data)
        
#         card_meta = {
#             "mismatch": is_mismatch,
#             "mismatch_details": mismatch_explanation
#         }

#         return {
#             "card": card,
#             "meta": card_meta
#         }

import json
from typing import Optional, Dict, Any, Tuple
from backend.ocr import extract_text_from_image, ocr_text_join
from backend.retriever import MultiRetriever
from backend.llm import generate
from backend.formatter import build_summary_card
from backend.utils import normalize_text
from backend.embeddings import embed_texts

DEFAULT_INDEXES = {
    "diseases": {
        "index_path": "indexes/diseases_faiss.index",
        "jsonl_path": "data/diseases_faiss_data.jsonl",
        "id_key": "id"
    },
    "drugs": {
        "index_path": "indexes/drugs_faiss.index",
        "jsonl_path": "data/drugs_faiss_data.jsonl",
        "id_key": "brand_name"
    },
    "drug_dict": {
        "index_path": "indexes/drug_dict_faiss.index",
        "jsonl_path": "data/drug_dict_faiss_data.jsonl",
        "id_key": "id"
    }
}

class Pipeline:
    def __init__(self, indexes_config: Dict[str, Dict] = None):
        self.config = indexes_config or DEFAULT_INDEXES
        self.retriever = MultiRetriever(self.config)

    def _perform_hybrid_mismatch_check(
        self, ocr_text: str, disease_results: list
    ) -> Tuple[Optional[bool], str]:
        """
        Performs a robust, multi-candidate, symptom-level check.
        Returns (is_mismatch, explanation), where is_mismatch can be True, False, or None.
        """
        if not ocr_text:
            return None, "No image provided; mismatch check is not applicable."
        if not disease_results:
            return None, "Could not determine a likely condition; mismatch check is inconclusive."

        # 1. Get top 3 potential drug candidates from OCR text
        ocr_drug_candidates = self.retriever.search_specific("drug_dict", ocr_text, top_k=3)
        if not ocr_drug_candidates:
            return None, "Could not identify any potential drugs from the image; mismatch check is inconclusive."

        # 2. Collect all symptoms from the top retrieved diseases
        all_likely_symptoms = set()
        for _, _, disease_obj in disease_results:
            disease_data = disease_obj.get('chunk', {})
            for symptom in disease_data.get("symptoms", []):
                all_likely_symptoms.add(symptom.lower())

        # 3. Loop through each drug candidate to find a match at the symptom level
        checked_drug_names = []
        for _, _, candidate_obj in ocr_drug_candidates:
            ocr_drug_name = candidate_obj.get("drug_name")
            if not ocr_drug_name:
                continue

            checked_drug_names.append(ocr_drug_name)
            full_drug_search = self.retriever.search_specific("drugs", ocr_drug_name, top_k=1)
            
            if not full_drug_search:
                continue 

            indications = full_drug_search[0][2].get("indications_and_usage", "").lower()
            if not indications:
                continue 

            # The core symptom-level check
            for symptom in all_likely_symptoms:
                if symptom and symptom in indications:
                    explanation = f"The medicine appears appropriate. It contains '{ocr_drug_name.title()}', which is used for symptoms like '{symptom}', consistent with the user's likely condition."
                    return False, explanation
        
        # 4. If the loop finishes without a match, determine the final result
        top_disease_name = disease_results[0][2].get('chunk', {}).get("disease", "the user's condition")
        if not checked_drug_names:
            return None, "Could not find detailed information for any drug identified in the image; mismatch check is inconclusive."

        explanation = f"Mismatch Detected: The active ingredients from the image (e.g., '{', '.join(checked_drug_names)}') do not appear to treat the symptoms of the user's likely condition ('{top_disease_name.title()}')."
        return True, explanation

    def run(self, user_text: str, image_path: Optional[str] = None, top_k: int = 3) -> Dict[str, Any]:
        user_norm = normalize_text(user_text or "")
        ocr_text = ""
        if image_path:
            ocr_res = extract_text_from_image(image_path)
            ocr_text = ocr_text_join(ocr_res["texts"])

        # --- Step 1: Isolated Retrievals ---
        disease_results = self.retriever.search_specific('diseases', user_norm, top_k=top_k)
        
        # Drug search uses a combined query to find relevant alternatives
        drug_query_text = " ".join([t for t in [user_norm, ocr_text] if t]).strip()
        if not drug_query_text: drug_query_text = user_norm # Fallback if only image has text
        
        drug_results = self.retriever.search_specific('drugs', drug_query_text, top_k=top_k)
        drug_dict_results = self.retriever.search_specific('drug_dict', drug_query_text, top_k=top_k)

        retrievals = {
            "diseases": disease_results,
            "drugs": drug_results,
            "drug_dict": drug_dict_results
        }
        
        # --- Step 2: Robust Mismatch Check ---
        is_mismatch, mismatch_explanation = self._perform_hybrid_mismatch_check(ocr_text, disease_results)
        
        # --- Step 3: Prepare Prompt with Deterministic Analysis ---
        mismatch_injection = f"CRITICAL PRE-ANALYSIS: Our system's rule-based check concluded: '{mismatch_explanation}'. You must use this analysis to populate the 'mismatch_analysis' section of your JSON response. Set 'is_mismatch' to {str(is_mismatch).lower() if isinstance(is_mismatch, bool) else 'null'} and use the provided explanation."

        prompt_context = []
        prompt_context.append(f"\n=== USER INPUT ===\nUser text: {user_text}")
        if ocr_text:
            prompt_context.append(f"OCR: {ocr_text}")

        prompt_context.append("\n=== RETRIEVED DATA ===")
        for idx_name, items in retrievals.items():
            prompt_context.append(f"\n-- Retrieved from {idx_name.upper()} --")
            for key, score, obj in items:
                prompt_context.append(f"* {str(obj)} (score: {score:.4f})")

        structured_prompt = f"""
You are MediScanAI, an expert medical analysis assistant. Your task is to analyze the user's query and the retrieved data to provide a helpful, structured response. Your response MUST be a single, valid JSON object.

{mismatch_injection}

Based on the context below, generate a JSON object with the schema provided.
{{
  "likely_condition": {{...}},
  "medication_suggestions": [{{...}}],
  "dosage_information": "string",
  "self_care_tips": ["string"],
  "warnings": ["string"],
  "mismatch_analysis": {{
    "is_mismatch": "boolean or null",
    "explanation": "string (You must use the explanation from the CRITICAL PRE-ANALYSIS.)"
  }}
}}

Here is the context to analyze:
{''.join(prompt_context)}

Now, generate the JSON response.
"""
        full_prompt = structured_prompt.strip()

        llm_response_str = generate(full_prompt)

        llm_data = {}
        try:
            start_index = llm_response_str.find('{')
            end_index = llm_response_str.rfind('}')
            if start_index != -1 and end_index != -1 and end_index > start_index:
                json_str = llm_response_str[start_index:end_index+1]
                llm_data = json.loads(json_str)
            else:
                raise json.JSONDecodeError("No JSON object found in the response.", llm_response_str, 0)
        except json.JSONDecodeError:
            llm_data = {"raw_text": llm_response_str, "error": "Failed to parse LLM response as JSON."}

        card = build_summary_card(user_text, ocr_text, retrievals, llm_data)
        
        card_meta = {
            "mismatch": is_mismatch,
            "mismatch_details": mismatch_explanation
        }

        return {
            "card": card,
            "meta": card_meta
        }