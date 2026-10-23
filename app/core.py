# # backend/core_new.py

# from typing import Optional, Dict, Any, List
# from backend.ocr import extract_text_from_image, ocr_text_join
# from backend.retriever import MultiRetriever
# from backend.llm import generate
# from backend.utils import normalize_text
# from backend.prompt import ANALYSIS_PROMPT_TEMPLATE


# DEFAULT_INDEXES = {
#     "diseases": {
#         "index_path": "indexes/diseases_faiss.index",
#         "jsonl_path": "data/diseases_faiss_data.jsonl",
#         "id_key": "id"
#     },
#     "drugs": {
#         "index_path": "indexes/drugs_faiss.index",
#         "jsonl_path": "data/drugs_faiss_data.jsonl",
#         "id_key": "id"
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

#     def _format_retrievals(self, retrievals_dict: Dict[str, List]) -> str:
#         """Helper function to format retrieval results into a string for the prompt."""
#         context_str = ""
#         for index_name, results in retrievals_dict.items():
#             context_str += f"\n-- Retrieved from {index_name.upper()} --\n"
#             if not results:
#                 context_str += "No results found.\n"
#                 continue
#             for key, score, obj in results:
#                 context_str += f"* Result: {str(obj)} (Score: {score:.4f})\n"
#         return context_str

#     def run(self, user_text: str, image_path: Optional[str] = None, top_k: int = 5) -> str:
#         """
#         Executes the full MediscanAI pipeline using the LLM-centric analysis approach.
#         Returns the formatted markdown response from the LLM.
#         """
#         user_norm = normalize_text(user_text or "")
#         ocr_text = ""
#         if image_path:
#             ocr_res = extract_text_from_image(image_path)
#             ocr_text = ocr_text_join(ocr_res["texts"])

#         # --- Step 1: Perform Separate Retrievals (as inspired by test_retriever.py) ---
        
#         # Retrieve context relevant to the user's symptoms
#         retrievals_for_user_text = {
#             "diseases": self.retriever.search_specific('diseases', user_norm, top_k=top_k),
#             "drugs": self.retriever.search_specific('drugs', user_norm, top_k=top_k),
#         }

#         # Retrieve context relevant to the medicine in the image
#         retrievals_for_ocr_text = {}
#         if ocr_text:
#             retrievals_for_ocr_text = {
#                 "drug_dict": self.retriever.search_specific('drug_dict', ocr_text, top_k=top_k),
#                 "drugs": self.retriever.search_specific('drugs', ocr_text, top_k=top_k),
#             }

#         # --- Step 2: Format Retrieved Context for the Prompt ---
#         formatted_user_retrievals = self._format_retrievals(retrievals_for_user_text)
#         formatted_ocr_retrievals = self._format_retrievals(retrievals_for_ocr_text)

#         # --- Step 3: Build the Final Prompt ---
#         full_prompt = ANALYSIS_PROMPT_TEMPLATE.format(
#             user_text=user_text,
#             ocr_text=ocr_text if ocr_text else "No image provided.",
#             retrievals_for_user_text=formatted_user_retrievals,
#             retrievals_for_ocr_text=formatted_ocr_retrievals
#         )

#         # --- Step 4: Call the LLM and Return the Response ---
#         llm_response = generate(full_prompt)

#         # The LLM now generates the final, user-facing markdown.
#         # No more complex JSON parsing or card building is needed here.
#         return llm_response.strip()


# backend/core_new.py

# from typing import Optional, Dict, Any, List, Tuple
# from backend.ocr import extract_text_from_image, ocr_text_join
# from backend.retriever import MultiRetriever
# from backend.llm import generate
# from backend.utils import normalize_text
# from backend.prompt import ANALYSIS_PROMPT_TEMPLATE


# DEFAULT_INDEXES = {
#     "diseases": {
#         "index_path": "indexes/diseases_faiss.index",
#         "jsonl_path": "data/diseases_faiss_data.jsonl",
#         "id_key": "id"
#     },
#     "drugs": {
#         "index_path": "indexes/drugs_faiss.index",
#         "jsonl_path": "data/drugs_faiss_data.jsonl",
#         "id_key": "id"
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

#     def _format_retrievals(self, retrievals_dict: Dict[str, List]) -> str:
#         context_str = ""
#         for index_name, results in retrievals_dict.items():
#             context_str += f"\n-- Retrieved from {index_name.upper()} --\n"
#             if not results:
#                 context_str += "No results found.\n"
#                 continue
#             for key, score, obj in results:
#                 context_str += f"* Result: {str(obj)} (Score: {score:.4f})\n"
#         return context_str

#     def run(self, user_text: str, image_path: Optional[str] = None, top_k: int = 5) -> Tuple[str, str]:
#         """
#         Executes the full MediscanAI pipeline using the LLM-centric analysis approach.
#         Returns a tuple containing the formatted markdown response and the extracted OCR text.
#         """
#         user_norm = normalize_text(user_text or "")
#         ocr_text = ""
#         if image_path:
#             ocr_res = extract_text_from_image(image_path)
#             ocr_text = ocr_text_join(ocr_res["texts"])

#         retrievals_for_user_text = {
#             "diseases": self.retriever.search_specific('diseases', user_norm, top_k=top_k),
#             "drugs": self.retriever.search_specific('drugs', user_norm, top_k=top_k),
#         }

#         retrievals_for_ocr_text = {}
#         if ocr_text:
#             retrievals_for_ocr_text = {
#                 "drug_dict": self.retriever.search_specific('drug_dict', ocr_text, top_k=top_k),
#                 "drugs": self.retriever.search_specific('drugs', ocr_text, top_k=top_k),
#             }

#         formatted_user_retrievals = self._format_retrievals(retrievals_for_user_text)
#         formatted_ocr_retrievals = self._format_retrievals(retrievals_for_ocr_text)

#         full_prompt = ANALYSIS_PROMPT_TEMPLATE.format(
#             user_text=user_text,
#             ocr_text=ocr_text if ocr_text else "No image provided.",
#             retrievals_for_user_text=formatted_user_retrievals,
#             retrievals_for_ocr_text=formatted_ocr_retrievals
#         )

#         llm_response = generate(full_prompt)

#         return llm_response.strip(), ocr_text


import logging
from typing import Optional, Dict, Any, List
from dataclasses import asdict
import time
from app.ocr import extract_text_from_image, ocr_text_join
from app.retriever import MultiRetriever
from app.llm import generate_with_mode, generate_with_mode_meta, GenerationParams
from app.utils import normalize_text
from app.prompt import ANALYSIS_PROMPT_TEMPLATE
from app.formatter import build_summary_card
from backend.core.config import get_settings, Settings
from app.graph import GraphRetriever
from evaluation.retrieval.pool_evidence import normalize_disease_chunk_id

logger = logging.getLogger("mediscanai.rag.core")


def extract_retrieved_ids_per_channel(retrievals_dict: Dict[str, List]) -> Dict[str, List[str]]:
    """Normalizes retrieved items per channel into structured ID lists."""
    channel_ids: Dict[str, List[str]] = {}
    for ch_name, items in retrievals_dict.items():
        ids = []
        for key, score, obj in items:
            if ch_name == "diseases":
                raw_chunk_id = (obj.get("chunk", {}).get("id") if isinstance(obj, dict) else None) or key
                ids.append(normalize_disease_chunk_id(str(raw_chunk_id)))
            elif ch_name in ("drugs", "drugs_from_ocr"):
                if isinstance(obj, dict) and "id" in obj:
                    ids.append(f"drug_{obj['id']}")
                elif str(key).startswith("drug_"):
                    ids.append(str(key))
                else:
                    ids.append(f"drug_{key}")
            elif ch_name == "drug_dict":
                if isinstance(obj, dict) and "id" in obj:
                    ids.append(f"drug_dict_{obj['id']}")
                else:
                    ids.append(str(key))
            else:
                ids.append(str(key))
        channel_ids[ch_name] = ids
    return channel_ids


DEFAULT_INDEXES = {
    "diseases": {
        "index_path": "indexes/diseases_faiss.index",
        "jsonl_path": "data/diseases_faiss_data.jsonl",
        "id_key": "id"
    },
    "drugs": {
        "index_path": "indexes/drugs_faiss.index",
        "jsonl_path": "data/drugs_faiss_data.jsonl",
        "id_key": "id"
    },
    "drug_dict": {
        "index_path": "indexes/drug_dict_faiss.index",
        "jsonl_path": "data/drug_dict_faiss_data.jsonl",
        "id_key": "id"
    }
}

class Pipeline:
    def __init__(
        self,
        indexes_config: Optional[Dict[str, Dict]] = None,
        retriever: Optional[Any] = None,
        settings: Optional[Settings] = None,
        graph_retriever: Optional[GraphRetriever] = None,
    ):
        self.config = indexes_config or DEFAULT_INDEXES
        self.retriever = retriever if retriever is not None else MultiRetriever(self.config)
        self.settings = settings or get_settings()
        if graph_retriever is not None:
            self.graph_retriever = graph_retriever
        elif self.settings.NEO4J_ENABLED:
            self.graph_retriever = GraphRetriever(settings=self.settings)
        else:
            self.graph_retriever = None

        # Emergency Triage Guardrail (Phase 1.2.d)
        self.guardrail = None
        if self.settings.EMERGENCY_GUARDRAIL_ENABLED:
            try:
                from app.guardrail import EmergencyGuardrail
                from pathlib import Path
                cfg_path = Path(self.settings.EMERGENCY_GUARDRAIL_CONFIG_PATH)
                if not cfg_path.is_absolute():
                    from backend.core.config import _BASE_DIR
                    cfg_path = _BASE_DIR / cfg_path
                self.guardrail = EmergencyGuardrail(config_path=cfg_path)
            except Exception as e:
                logger.error(f"Failed to initialize EmergencyGuardrail: {e}. Engaging fail-safe fallback.", exc_info=True)
                from app.guardrail import EmergencyGuardrail
                self.guardrail = EmergencyGuardrail(config_path=None)

    def _format_retrievals(self, retrievals_dict: Dict[str, List]) -> str:
        context_str = ""
        for index_name, results in retrievals_dict.items():
            context_str += f"\n-- Retrieved from {index_name.upper()} --\n"
            if not results:
                context_str += "No results found.\n"
                continue
            for key, score, obj in results:
                context_str += f"* Result: {str(obj)} (Score: {score:.4f})\n"
        return context_str

    def run(
        self,
        user_text: str,
        image_path: Optional[str] = None,
        top_k: int = 5,
        llm_mode: str = "offline",
        *,
        return_trace: bool = False,
        ocr_text_override: Optional[str] = None,
        gen_params: Optional[GenerationParams] = None,
    ) -> Dict[str, Any]:
        _t_pipeline_start = time.perf_counter()
        pipeline_timings: Dict[str, int] = {}

        # Thread Pipeline.settings into GenerationParams (no module globals)
        effective_temp = gen_params.temperature if gen_params and gen_params.temperature is not None else getattr(self.settings, "GEN_TEMPERATURE", None)
        effective_seed = gen_params.seed if gen_params and gen_params.seed is not None else getattr(self.settings, "GEN_SEED", None)
        effective_num_ctx = gen_params.num_ctx if gen_params and gen_params.num_ctx is not None else getattr(self.settings, "OLLAMA_NUM_CTX", None)
        effective_num_predict = gen_params.num_predict if gen_params and gen_params.num_predict is not None else getattr(self.settings, "OLLAMA_NUM_PREDICT", None)

        if any(v is not None for v in (effective_temp, effective_seed, effective_num_ctx, effective_num_predict)):
            gen_params = GenerationParams(
                temperature=effective_temp,
                seed=effective_seed,
                num_ctx=effective_num_ctx,
                num_predict=effective_num_predict,
            )

        print("\n🔍 [RAG CORE] Running MediScanAI Core Pipeline...")
        user_norm = normalize_text(user_text or "")
        ocr_text = ""
        ocr_failed = False
        ocr_error_type = None

        # 1. OCR Extraction (Resilient to engine exceptions)
        if ocr_text_override is not None:
            ocr_text = ocr_text_override
            pipeline_timings["ocr_total_ms"] = 0
            print(f"📷 [Vision] OCR text override provided ({len(ocr_text)} characters).")
        elif image_path:
            print("📷 [Vision] Running PaddleOCR on medicine image...")
            _t_ocr = time.perf_counter()
            try:
                ocr_res = extract_text_from_image(image_path)
                ocr_text = ocr_text_join(ocr_res.get("texts", []))
                pipeline_timings["ocr_total_ms"] = int((time.perf_counter() - _t_ocr) * 1000)
                print(f"   ↳ OCR label extraction completed ({len(ocr_text)} characters extracted).")
            except Exception as e:
                ocr_failed = True
                ocr_error_type = type(e).__name__
                pipeline_timings["ocr_total_ms"] = int((time.perf_counter() - _t_ocr) * 1000)
                pipeline_timings["ocr_failed"] = True
                logger.warning(f"OCR extraction failed ({ocr_error_type}): {e}")
                print(f"   ⚠️ OCR extraction failed ({ocr_error_type}). Proceeding with safe fallback handling.")
        else:
            print("📷 [Vision] No image provided. Skipping OCR.")

        # 1b. Multimodal Emergency Query Assembly
        clean_user = (user_text or "").strip()
        clean_ocr = (ocr_text or "").strip()
        if clean_user and clean_ocr:
            if clean_user.lower() == clean_ocr.lower():
                combined_query = clean_user
            else:
                combined_query = f"{clean_user}\n{clean_ocr}"
        elif clean_ocr:
            combined_query = clean_ocr
        else:
            combined_query = clean_user

        # 1c. Emergency Pre-Generation Fast-Path Check (Phase 1.2.d / 1.2.d.2)
        if self.guardrail is not None and self.settings.EMERGENCY_GUARDRAIL_FAST_PATH and combined_query:
            _t_guard_pre = time.perf_counter()
            pre_decision = self.guardrail.detect_emergency(combined_query)
            if pre_decision.is_emergency and pre_decision.severity == "CRITICAL_EMERGENCY":
                guarded_response_str, final_decision = self.guardrail.apply_guardrail(
                    query=combined_query,
                    baseline_response=""
                )
                pipeline_timings["guardrail_fast_path_ms"] = int((time.perf_counter() - _t_guard_pre) * 1000)
                pipeline_timings["pipeline_total_ms"] = int((time.perf_counter() - _t_pipeline_start) * 1000)
                card = build_summary_card(
                    user_text=user_text,
                    ocr_text=ocr_text,
                    retrievals={},
                    llm_output=guarded_response_str.strip()
                )
                card_meta = {
                    "mismatch": None,
                    "mismatch_details": "Immediate emergency fast-path engaged.",
                    "guardrail": final_decision.to_dict(),
                    "fast_path": True,
                }
                if ocr_failed:
                    card_meta["ocr_status"] = "FAILED"
                    card_meta["ocr_error_type"] = ocr_error_type
                elif ocr_text_override is not None:
                    card_meta["ocr_status"] = "SUCCESS" if ocr_text else "EMPTY"
                elif image_path:
                    card_meta["ocr_status"] = "SUCCESS" if ocr_text else "EMPTY"
                else:
                    card_meta["ocr_status"] = "SKIPPED"

                print(f"🚨 [Emergency Guardrail] FAST-PATH ENGAGED: {final_decision.fired_rule_id} in {pipeline_timings['guardrail_fast_path_ms']}ms")
                fast_result = {
                    "card": card,
                    "meta": card_meta,
                    "pipeline_timings": pipeline_timings,
                }
                if return_trace:
                    provider_model_tag = getattr(self.settings, "OLLAMA_MODEL", "llama3.1:8b")
                    fast_result["trace"] = {
                        "prompt": "",
                        "prompt_chars": 0,
                        "prompt_tokens_est": 0,
                        "retrievals_per_channel": {},
                        "retrieved_ids": {},
                        "raw_llm_output": "",
                        "final_output": guarded_response_str.strip(),
                        "fast_path_fired": True,
                        "generation_meta": None,
                        "effective_settings": {
                            "EVIDENCE_FORMAT": getattr(self.settings, "EVIDENCE_FORMAT", "legacy"),
                            "PROMPT_VERSION": getattr(self.settings, "PROMPT_VERSION", "legacy"),
                            "params": asdict(gen_params) if gen_params else None,
                            "top_k": top_k,
                            "llm_mode": llm_mode,
                            "ollama_model": provider_model_tag,
                            "neo4j_enabled": self.settings.NEO4J_ENABLED,
                            "emergency_guardrail_enabled": self.settings.EMERGENCY_GUARDRAIL_ENABLED,
                            "emergency_guardrail_fast_path": self.settings.EMERGENCY_GUARDRAIL_FAST_PATH,
                        }
                    }
                return fast_result


        # 1d. Safe Fallback for Unreadable / Empty Image-Only Queries (Phase 1.2.d.2)
        if image_path and not user_norm:
            from app.guardrail import MANDATORY_HEADER, MANDATORY_TEXT
            if ocr_failed:
                fallback_header = "### 📷 Image Could Not Be Interpreted\n\n"
                fallback_body = (
                    "The uploaded image could not be reliably processed or read. "
                    "No readable medical text or medication labels could be extracted.\n\n"
                    "**Please provide additional information:**\n"
                    "* Type your symptoms, questions, or medication names directly in the text input, or\n"
                    "* Upload a clearer, well-lit, and focused photograph of the packaging or document.\n\n"
                )
                meta_status = "FAILED"
                meta_details = "Image processing failed; requested readable text."
            elif not clean_ocr:
                fallback_header = "### 📷 No Text Detected in Image\n\n"
                fallback_body = (
                    "No text or medication labels were detected in the uploaded image.\n\n"
                    "**Please provide additional information:**\n"
                    "* Type your symptoms, questions, or medication names directly in the text input, or\n"
                    "* Upload a clearer, well-lit, and focused photograph showing the label clearly.\n\n"
                )
                meta_status = "EMPTY"
                meta_details = "No readable text detected in image; requested readable text."
            else:
                fallback_header = ""
                fallback_body = ""
                meta_status = "SUCCESS"
                meta_details = ""

            if fallback_body:
                unreadable_message = (
                    f"{fallback_header}{fallback_body}"
                    "**Important Emergency Guidance:**\n"
                    "If you or the person you are assisting is experiencing an acute medical emergency "
                    "(such as severe chest pain, shortness of breath, sudden weakness, slurred speech, or unresponsiveness), "
                    "do not wait for image processing or online consultation. "
                    "Call **112** (in India), **911** (in the US), or your local emergency services immediately.\n\n"
                    f"{MANDATORY_HEADER}\n"
                    f"{MANDATORY_TEXT}"
                )
                card = build_summary_card(
                    user_text=user_text,
                    ocr_text="",
                    retrievals={},
                    llm_output=unreadable_message.strip()
                )
                card_meta = {
                    "mismatch": None,
                    "mismatch_details": meta_details,
                    "ocr_status": meta_status,
                    "fast_path": False,
                }
                if ocr_failed:
                    card_meta["ocr_error_type"] = ocr_error_type
                pipeline_timings["pipeline_total_ms"] = int((time.perf_counter() - _t_pipeline_start) * 1000)
                return {
                    "card": card,
                    "meta": card_meta,
                    "pipeline_timings": pipeline_timings,
                }

        # 2. Retrievals for Symptom Text
        print(f"🔎 [Retrieval] Running Hybrid Search (FAISS + BM25 + RRF + Cross-Encoder) for symptom query ({len(user_norm)} chars)...")
        _t_ret_symptoms = time.perf_counter()
        _dev_trace_on = bool(getattr(self.settings, "DEV_TRACE_ENABLED", False))
        routing_version = getattr(self.settings, "ROUTING_VERSION", "legacy")
        retrieval_debug: Dict[str, Dict[str, Any]] = {}

        def _search(label: str, index_name: str, text: str):
            if not _dev_trace_on:
                return self.retriever.search_specific(index_name, text, top_k=top_k)
            dbg: Dict[str, Any] = {}
            res = self.retriever.search_specific(index_name, text, top_k=top_k, debug=dbg)
            retrieval_debug[label] = dbg
            return res

        # Under ROUTING_VERSION=v2, if the query is an unanswerable probe or a medicine-label query
        # with no symptoms presented, skip disease retrieval on the generic question text
        skip_disease_search = False
        if routing_version == "v2" and user_norm:
            from app.prompt_v2 import classify_intent_v2
            detected_intent = classify_intent_v2(user_text, ocr_text)
            if detected_intent in ("MEDICINE_ONLY", "UNANSWERABLE"):
                skip_disease_search = True
                print(f"   ℹ️ [Routing v2] Intent detected as '{detected_intent}'. Skipping disease index search for medicine/probe query.")

        if not skip_disease_search:
            diseases_retrieved = _search('diseases', 'diseases', user_norm)
        else:
            diseases_retrieved = []
        pipeline_timings["retrieval_diseases_ms"] = int((time.perf_counter() - _t_ret_symptoms) * 1000)

        _t_ret_drugs = time.perf_counter()
        drugs_retrieved = _search('drugs', 'drugs', user_norm)
        pipeline_timings["retrieval_drugs_ms"] = int((time.perf_counter() - _t_ret_drugs) * 1000)

        print(f"   ↳ Diseases index matches (fused & reranked):")
        for idx, (key, score, obj) in enumerate(diseases_retrieved, 1):
            disease_name = obj.get('chunk', {}).get('disease', key) if isinstance(obj, dict) else key
            print(f"     - Rank #{idx}: {disease_name} (Cross-Encoder score: {score:.4f})")

        print(f"   ↳ Drugs index matches (Symptom query - fused & reranked):")
        for idx, (key, score, obj) in enumerate(drugs_retrieved, 1):
            brand_name = obj.get('brand_name', key) if isinstance(obj, dict) else key
            print(f"     - Rank #{idx}: {brand_name} (Cross-Encoder score: {score:.4f})")

        retrievals_for_user_text = {
            "diseases": diseases_retrieved,
            "drugs": drugs_retrieved,
        }

        # 3. Retrievals for OCR Text
        retrievals_for_ocr_text = {}
        if ocr_text:
            print(f"🔎 [Retrieval] Running Hybrid Search (FAISS + BM25 + RRF + Cross-Encoder) for OCR label ({len(ocr_text)} chars)...")
            _t_ret_drug_dict = time.perf_counter()
            drug_dict_retrieved = _search('drug_dict', 'drug_dict', ocr_text)
            pipeline_timings["retrieval_drug_dict_ms"] = int((time.perf_counter() - _t_ret_drug_dict) * 1000)

            _t_ret_drugs_ocr = time.perf_counter()
            drugs_from_ocr_retrieved = _search('drugs_from_ocr', 'drugs', ocr_text)
            pipeline_timings["retrieval_drugs_from_ocr_ms"] = int((time.perf_counter() - _t_ret_drugs_ocr) * 1000)

            print(f"   ↳ Drug Dictionary index matches (fused & reranked):")
            for idx, (key, score, obj) in enumerate(drug_dict_retrieved, 1):
                drug_name = obj.get('drug_name', key) if isinstance(obj, dict) else key
                print(f"     - Rank #{idx}: {drug_name} (Cross-Encoder score: {score:.4f})")

            print(f"   ↳ Drugs index matches (OCR query - fused & reranked):")
            for idx, (key, score, obj) in enumerate(drugs_from_ocr_retrieved, 1):
                brand_name = obj.get('brand_name', key) if isinstance(obj, dict) else key
                print(f"     - Rank #{idx}: {brand_name} (Cross-Encoder score: {score:.4f})")

            retrievals_for_ocr_text = {
                "drug_dict": drug_dict_retrieved,
                "drugs_from_ocr": drugs_from_ocr_retrieved,
            }

        # 3b. Optional Supplementary Graph Retrieval (Neo4j)
        if self.graph_retriever is not None and self.settings.NEO4J_ENABLED:
            print("🕸️ [Graph] Running Supplementary Neo4j Graph Retrieval...")
            _t_graph = time.perf_counter()

            # A. Disease Graph Retrieval for Symptoms Context
            # Use candidate disease and verified chunk symptoms from existing hybrid retrieval
            graph_diseases_retrieved = []
            seen_disease_names = set()
            if diseases_retrieved:
                top_disease_obj = diseases_retrieved[0][2]
                if isinstance(top_disease_obj, dict):
                    chunk_data = top_disease_obj.get("chunk", {})
                    candidate_disease_name = chunk_data.get("disease")
                    chunk_symptoms = chunk_data.get("symptoms", [])

                    # 1. Neighborhood retrieval for top candidate disease
                    if candidate_disease_name:
                        resp_neigh = self.graph_retriever.get_disease_neighborhood(
                            str(candidate_disease_name), max_chunks=3
                        )
                        if resp_neigh.status == "success":
                            for d in resp_neigh.diseases:
                                if d.disease_name not in seen_disease_names:
                                    seen_disease_names.add(d.disease_name)
                                    key = f"graph_disease_{d.disease_name}"
                                    score = 1.0
                                    obj = {
                                        "disease": d.disease_name,
                                        "symptoms": d.all_symptoms,
                                        "matched_symptoms": d.matched_symptoms,
                                        "overlap_count": d.overlap_count,
                                        "chunks": [{"chunk_id": c.chunk_id, "source_id": c.source_id} for c in d.chunks],
                                        "provenance": d.provenance,
                                    }
                                    graph_diseases_retrieved.append((key, score, obj))
                        elif resp_neigh.status in ("error", "timeout"):
                            logger.warning(
                                "Graph disease neighborhood query returned status '%s' (code: %s); continuing without graph disease context.",
                                resp_neigh.status,
                                resp_neigh.error_code,
                            )

                    # 2. Symptom overlap retrieval if symptoms match query tokens
                    overlapping_symptoms = [
                        str(s).strip() for s in chunk_symptoms
                        if str(s).strip().lower() in user_norm.lower()
                    ]
                    if overlapping_symptoms:
                        resp_syms = self.graph_retriever.find_diseases_by_symptoms(
                            overlapping_symptoms, limit=top_k, max_chunks_per_disease=3
                        )
                        if resp_syms.status == "success":
                            for d in resp_syms.diseases:
                                if d.disease_name not in seen_disease_names:
                                    seen_disease_names.add(d.disease_name)
                                    key = f"graph_disease_{d.disease_name}"
                                    score = float(d.overlap_count)
                                    obj = {
                                        "disease": d.disease_name,
                                        "symptoms": d.all_symptoms,
                                        "matched_symptoms": d.matched_symptoms,
                                        "overlap_count": d.overlap_count,
                                        "chunks": [{"chunk_id": c.chunk_id, "source_id": c.source_id} for c in d.chunks],
                                        "provenance": d.provenance,
                                    }
                                    graph_diseases_retrieved.append((key, score, obj))
                        elif resp_syms.status in ("error", "timeout"):
                            logger.warning(
                                "Graph disease symptom query returned status '%s' (code: %s); continuing without additional graph disease context.",
                                resp_syms.status,
                                resp_syms.error_code,
                            )

            if graph_diseases_retrieved:
                retrievals_for_user_text["graph_diseases"] = graph_diseases_retrieved
                print(f"   ↳ Graph disease matches retrieved: {len(graph_diseases_retrieved)}")

            # B. Drug Graph Retrieval for Medicine/OCR Context
            # Prefer resolved candidate drug names from existing retrieval over raw OCR text
            graph_drugs_retrieved = []
            seen_drug_source_ids = set()
            candidate_drug_names: List[str] = []

            for _, _, obj in retrievals_for_ocr_text.get("drug_dict", [])[:2]:
                if isinstance(obj, dict) and obj.get("drug_name"):
                    name = str(obj["drug_name"]).strip()
                    if name and name not in candidate_drug_names:
                        candidate_drug_names.append(name)

            for _, _, obj in retrievals_for_ocr_text.get("drugs_from_ocr", [])[:2]:
                if isinstance(obj, dict):
                    for field_name in ("brand_name", "generic_name"):
                        val = obj.get(field_name)
                        if val and str(val).strip() and str(val).strip() not in candidate_drug_names:
                            candidate_drug_names.append(str(val).strip())

            for candidate_name in candidate_drug_names[:2]:
                resp_drug = self.graph_retriever.find_drugs_by_name(candidate_name, limit=top_k)
                if resp_drug.status == "success":
                    for drug in resp_drug.drugs:
                        if drug.source_id not in seen_drug_source_ids:
                            seen_drug_source_ids.add(drug.source_id)
                            key = f"graph_drug_{drug.source_id}"
                            score = 1.0
                            obj = {
                                "brand_name": drug.brand_name,
                                "generic_name": drug.generic_name,
                                "active_ingredients": drug.active_ingredients,
                                "indications_and_usage": drug.indications_text,
                                "warnings": drug.warnings_text,
                                "dosage": drug.dosage_text,
                                "adverse_reactions": drug.adverse_reactions_text,
                                "match_field": drug.match_field,
                                "provenance": drug.provenance,
                            }
                            graph_drugs_retrieved.append((key, score, obj))
                elif resp_drug.status in ("error", "timeout"):
                    logger.warning(
                        "Graph drug query for '%s' returned status '%s' (code: %s); continuing without graph drug context.",
                        candidate_name,
                        resp_drug.status,
                        resp_drug.error_code,
                    )

            if graph_drugs_retrieved:
                retrievals_for_ocr_text["graph_drugs"] = graph_drugs_retrieved
                print(f"   ↳ Graph drug matches retrieved: {len(graph_drugs_retrieved)}")

            pipeline_timings["retrieval_graph_ms"] = int((time.perf_counter() - _t_graph) * 1000)

        # 4. Assembling Prompt & generation
        _t_prompt = time.perf_counter()
        token_budget = None

        evidence_trace_data = None
        evidence_format = getattr(self.settings, "EVIDENCE_FORMAT", "legacy")

        if evidence_format == "compact":
            from app.evidence import CompactEvidenceFormatter
            eff_num_ctx = (gen_params.num_ctx if (gen_params and gen_params.num_ctx is not None) else None) or getattr(self.settings, "OLLAMA_NUM_CTX", None) or 8192
            eff_num_predict = (gen_params.num_predict if (gen_params and gen_params.num_predict is not None) else None) or getattr(self.settings, "OLLAMA_NUM_PREDICT", None) or 700
            token_budget = max(200, eff_num_ctx - eff_num_predict - 256 - 500)

            formatter = CompactEvidenceFormatter(
                max_items_per_channel=getattr(self.settings, "EVIDENCE_MAX_ITEMS_PER_CHANNEL", 3),
                drug_fields=getattr(self.settings, "EVIDENCE_DRUG_FIELDS", None),
                field_caps=getattr(self.settings, "EVIDENCE_FIELD_CAPS", None),
            )
            routing_version = getattr(self.settings, "ROUTING_VERSION", "legacy")
            is_med_dir = False
            if routing_version == "v2":
                from app.prompt_v2 import classify_intent_v2
                intent_detected = classify_intent_v2(user_text, ocr_text)
                is_med_dir = intent_detected in ("MEDICINE_ONLY", "UNANSWERABLE")

            combined_retrievals = {**retrievals_for_user_text, **retrievals_for_ocr_text}
            rendered_evidence, evidence_trace_data = formatter.format(
                combined_retrievals,
                token_budget=token_budget,
                query_aware_filtering=(routing_version == "v2"),
                user_text=user_text,
                ocr_text=ocr_text,
                is_medicine_directed=is_med_dir,
            )

            user_chans = set(retrievals_for_user_text.keys())
            ocr_chans = set(retrievals_for_ocr_text.keys())

            blocks = [b for b in rendered_evidence.split("\n") if b.strip()]
            user_blocks = []
            ocr_blocks = []
            for b, itm in zip(blocks, evidence_trace_data["evidence_items"]):
                if itm["channel"] in user_chans:
                    user_blocks.append(b)
                elif itm["channel"] in ocr_chans:
                    ocr_blocks.append(b)
                else:
                    user_blocks.append(b)
            formatted_user_retrievals = "\n".join(user_blocks)
            formatted_ocr_retrievals = "\n".join(ocr_blocks)
        else:
            formatted_user_retrievals = self._format_retrievals(retrievals_for_user_text)
            formatted_ocr_retrievals = self._format_retrievals(retrievals_for_ocr_text)

        prompt_version = getattr(self.settings, "PROMPT_VERSION", "legacy")
        system_prompt = None
        role_separation_mode = "single_user"
        citation_stats = None
        case_type = None

        if prompt_version in ("v2", "v3", "v4"):
            from app.prompt_v2 import SYSTEM_PROMPT, SYSTEM_PROMPT_V3, SYSTEM_PROMPT_V4, build_v2_user_message
            if prompt_version == "v4":
                system_prompt = SYSTEM_PROMPT_V4
            elif prompt_version == "v3":
                system_prompt = SYSTEM_PROMPT_V3
            else:
                system_prompt = SYSTEM_PROMPT
            role_separation_mode = "system_user"

            if evidence_format == "compact":
                v2_evidence_text = rendered_evidence
            else:
                ev_parts = []
                if formatted_user_retrievals.strip():
                    ev_parts.append(formatted_user_retrievals.strip())
                if formatted_ocr_retrievals.strip():
                    ev_parts.append(formatted_ocr_retrievals.strip())
                v2_evidence_text = "\n\n".join(ev_parts)

            routing_version = getattr(self.settings, "ROUTING_VERSION", "legacy")
            full_prompt, case_type = build_v2_user_message(
                user_text=user_text,
                ocr_text=ocr_text,
                evidence_text=v2_evidence_text,
                routing_version=routing_version,
                prompt_version=prompt_version,
            )
        else:
            print("📝 [Prompt] Assembling context-grounded prompt template...")
            full_prompt = ANALYSIS_PROMPT_TEMPLATE.format(
                user_text=user_text,
                ocr_text=ocr_text if ocr_text else "No image provided.",
                retrievals_for_user_text=formatted_user_retrievals,
                retrievals_for_ocr_text=formatted_ocr_retrievals
            )
        pipeline_timings["prompt_assembly_ms"] = int((time.perf_counter() - _t_prompt) * 1000)

        provider_model_tag = getattr(self.settings, "OLLAMA_MODEL", "llama3.1:8b")
        provider_label = "Gemini/Groq (online)" if llm_mode == "online" else f"Ollama/{provider_model_tag}"
        print(f"🤖 [LLM] Requesting clinical analysis via {provider_label}...")
        _t_llm = time.perf_counter()

        if return_trace or _dev_trace_on:
            raw_llm_output, gen_meta = generate_with_mode_meta(
                full_prompt, llm_mode=llm_mode, params=gen_params, system=system_prompt
            )
        else:
            raw_llm_output = generate_with_mode(
                full_prompt, llm_mode=llm_mode, params=gen_params, system=system_prompt
            )
            gen_meta = None

        if prompt_version in ("v2", "v3", "v4"):
            from app.prompt_v2 import finalize_v2_response, compute_citation_stats
            llm_response_str = finalize_v2_response(raw_llm_output)
            evidence_tags = [itm["tag"] for itm in evidence_trace_data["evidence_items"]] if (evidence_trace_data and "evidence_items" in evidence_trace_data) else []
            citation_stats = compute_citation_stats(llm_response_str, evidence_tags=evidence_tags)
        else:
            llm_response_str = raw_llm_output

        pipeline_timings["llm_total_ms"] = int((time.perf_counter() - _t_llm) * 1000)
        print("   ↳ Generation completed successfully.")

        all_retrievals = {**retrievals_for_user_text, **retrievals_for_ocr_text}

        # 4b. Emergency Post-Generation Safeguard Enforcement (Phase 1.2.d)
        guardrail_meta_dict = None
        if self.guardrail is not None:
            _t_guard_post = time.perf_counter()
            evidence_summaries: List[str] = []
            for idx_name, items in all_retrievals.items():
                for key, score, obj in items:
                    if isinstance(obj, dict):
                        evidence_summaries.append(str(obj))
            guarded_response_str, post_decision = self.guardrail.apply_guardrail(
                query=combined_query,
                baseline_response=llm_response_str.strip(),
                retrieved_contexts=evidence_summaries
            )
            pipeline_timings["guardrail_post_gen_ms"] = int((time.perf_counter() - _t_guard_post) * 1000)
            llm_response_str = guarded_response_str
            guardrail_meta_dict = post_decision.to_dict()

        if prompt_version in ("v2", "v3"):
            from app.guardrail import MANDATORY_HEADER, MANDATORY_TEXT
            if llm_response_str.count(MANDATORY_HEADER) > 1:
                parts = llm_response_str.split(MANDATORY_HEADER)
                llm_response_str = f"{parts[0].strip()}\n\n{MANDATORY_HEADER}\n{MANDATORY_TEXT}"
            elif MANDATORY_HEADER not in llm_response_str:
                llm_response_str = f"{llm_response_str.strip()}\n\n{MANDATORY_HEADER}\n{MANDATORY_TEXT}"

        card = build_summary_card(
            user_text=user_text,
            ocr_text=ocr_text,
            retrievals=all_retrievals,
            llm_output=llm_response_str.strip()
        )

        card_meta = {
            "mismatch": None,
            "mismatch_details": "Mismatch check not performed in this pipeline version."
        }
        if ocr_failed:
            card_meta["ocr_status"] = "FAILED"
            card_meta["ocr_error_type"] = ocr_error_type
        elif ocr_text_override is not None:
            card_meta["ocr_status"] = "SUCCESS" if ocr_text else "EMPTY"
        elif image_path:
            card_meta["ocr_status"] = "SUCCESS" if ocr_text else "EMPTY"
        else:
            card_meta["ocr_status"] = "SKIPPED"

        if guardrail_meta_dict is not None:
            card_meta["guardrail"] = guardrail_meta_dict
            card_meta["fast_path"] = False

        pipeline_timings["pipeline_total_ms"] = int((time.perf_counter() - _t_pipeline_start) * 1000)

        # --- Pipeline timing summary ---
        print("\n" + "=" * 60)
        print("[PIPELINE TIMING SUMMARY]")
        if "ocr_total_ms" in pipeline_timings:
            print(f"  OCR (init+infer):           {pipeline_timings['ocr_total_ms']}ms")
        print(f"  Retrieval diseases:          {pipeline_timings.get('retrieval_diseases_ms', 0)}ms")
        print(f"  Retrieval drugs (symptoms):  {pipeline_timings.get('retrieval_drugs_ms', 0)}ms")
        if "retrieval_drug_dict_ms" in pipeline_timings:
            print(f"  Retrieval drug_dict (OCR):   {pipeline_timings['retrieval_drug_dict_ms']}ms")
        if "retrieval_drugs_from_ocr_ms" in pipeline_timings:
            print(f"  Retrieval drugs (OCR):       {pipeline_timings['retrieval_drugs_from_ocr_ms']}ms")
        if "retrieval_graph_ms" in pipeline_timings:
            print(f"  Retrieval graph (Neo4j):     {pipeline_timings['retrieval_graph_ms']}ms")
        print(f"  Prompt assembly:             {pipeline_timings.get('prompt_assembly_ms', 0)}ms")
        print(f"  LLM ({provider_label}): {pipeline_timings.get('llm_total_ms', 0)}ms")
        if "guardrail_fast_path_ms" in pipeline_timings:
            print(f"  Emergency fast-path:         {pipeline_timings['guardrail_fast_path_ms']}ms")
        if "guardrail_post_gen_ms" in pipeline_timings:
            print(f"  Emergency post-guard:        {pipeline_timings['guardrail_post_gen_ms']}ms")
        print(f"  " + "-" * 40)
        print(f"  Pipeline total:              {pipeline_timings['pipeline_total_ms']}ms")
        print("=" * 60 + "\n")

        print("✅ [RAG CORE] Completed execution.\n")
        final_result = {
            "card": card,
            "meta": card_meta,
            "pipeline_timings": pipeline_timings,
        }
        if return_trace:
            try:
                import tiktoken
                enc = tiktoken.get_encoding("cl100k_base")
                prompt_tokens_est = len(enc.encode(full_prompt))
            except Exception:
                prompt_tokens_est = len(full_prompt) // 4

            final_result["trace"] = {
                "prompt": full_prompt,
                "system_prompt": system_prompt,
                "role_separation_mode": role_separation_mode,
                "case_type": case_type,
                "prompt_chars": len(full_prompt),
                "prompt_tokens_est": prompt_tokens_est,
                "evidence_format": evidence_format,
                "prompt_version": prompt_version,
                "evidence_items": evidence_trace_data["evidence_items"] if evidence_trace_data else [],
                "total_evidence_tokens": evidence_trace_data["total_evidence_tokens"] if evidence_trace_data else None,
                "retrieved_but_omitted_ids": evidence_trace_data["retrieved_but_omitted_ids"] if evidence_trace_data else [],
                "evidence_trims": evidence_trace_data["trims"] if evidence_trace_data else [],
                "cap_multiplier": evidence_trace_data["cap_multiplier"] if evidence_trace_data else 1.0,
                "citation_stats": citation_stats,
                "tags_found": citation_stats["tags_found"] if citation_stats else [],
                "invalid_tags": citation_stats["invalid_tags"] if citation_stats else [],
                "citation_pct": citation_stats["citation_pct"] if citation_stats else None,
                "abstained": citation_stats["abstained"] if citation_stats else False,
                "retrievals_per_channel": {
                    "user_text_retrievals": formatted_user_retrievals,
                    "ocr_text_retrievals": formatted_ocr_retrievals,
                    "channels": {
                        chan: self._format_retrievals({chan: items})
                        for chan, items in all_retrievals.items()
                    }
                },
                "retrieved_ids": extract_retrieved_ids_per_channel(all_retrievals),
                "raw_llm_output": raw_llm_output,
                "final_output": llm_response_str.strip(),
                "fast_path_fired": False,
                "generation_meta": gen_meta,
                "effective_settings": {
                    "EVIDENCE_FORMAT": getattr(self.settings, "EVIDENCE_FORMAT", "legacy"),
                    "PROMPT_VERSION": getattr(self.settings, "PROMPT_VERSION", "legacy"),
                    "ROUTING_VERSION": getattr(self.settings, "ROUTING_VERSION", "legacy"),
                    "params": asdict(gen_params) if gen_params else None,
                    "top_k": top_k,
                    "llm_mode": llm_mode,
                    "ollama_model": provider_model_tag,
                    "neo4j_enabled": self.settings.NEO4J_ENABLED,
                    "emergency_guardrail_enabled": self.settings.EMERGENCY_GUARDRAIL_ENABLED,
                    "emergency_guardrail_fast_path": self.settings.EMERGENCY_GUARDRAIL_FAST_PATH,
                }
            }
        if _dev_trace_on:
            from app.dev_trace import build_dev_trace, write_dev_trace
            _eff = {
                "num_ctx": (gen_params.num_ctx if gen_params else None),
                "num_predict": (gen_params.num_predict if gen_params else None),
                "temperature": (gen_params.temperature if gen_params else None),
                "seed": (gen_params.seed if gen_params else None),
                "model": provider_model_tag,
                "llm_mode": llm_mode,
                "top_k": top_k,
                "EVIDENCE_FORMAT": evidence_format,
                "PROMPT_VERSION": prompt_version,
                "evidence_max_items_per_channel": getattr(self.settings, "EVIDENCE_MAX_ITEMS_PER_CHANNEL", 3),
            }
            dev_trace = build_dev_trace(
                user_text=user_text or "",
                ocr_text=ocr_text or "",
                system_prompt=system_prompt,
                full_prompt=full_prompt,
                evidence_trace=evidence_trace_data,
                retrieval_debug=retrieval_debug,
                retrieved_ids=extract_retrieved_ids_per_channel(all_retrievals),
                effective=_eff,
                token_budget=token_budget,
                max_items_per_channel=getattr(self.settings, "EVIDENCE_MAX_ITEMS_PER_CHANNEL", 3),
                case_type=case_type,
                generation_meta=gen_meta,
                include_text=bool(getattr(self.settings, "DEV_TRACE_INCLUDE_TEXT", False)),
            )
            final_result["dev_trace"] = dev_trace
            _trace_dir = getattr(self.settings, "DEV_TRACE_DIR", None)
            if _trace_dir:
                import hashlib as _hl
                write_dev_trace(
                    dev_trace, _trace_dir,
                    _hl.sha256((user_text or "").encode("utf-8") + (ocr_text or "").encode("utf-8")).hexdigest()[:12],
                )
        return final_result


