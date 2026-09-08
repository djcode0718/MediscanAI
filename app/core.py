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


from typing import Optional, Dict, Any, List
import time
from app.ocr import extract_text_from_image, ocr_text_join
from app.retriever import MultiRetriever
from app.llm import generate_with_mode
from app.utils import normalize_text
from app.prompt import ANALYSIS_PROMPT_TEMPLATE
from app.formatter import build_summary_card



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
    def __init__(self, indexes_config: Dict[str, Dict] = None):
        self.config = indexes_config or DEFAULT_INDEXES
        self.retriever = MultiRetriever(self.config)

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

    def run(self, user_text: str, image_path: Optional[str] = None,
             top_k: int = 5, llm_mode: str = "offline") -> Dict[str, Any]:
        _t_pipeline_start = time.perf_counter()
        pipeline_timings: Dict[str, int] = {}

        print("\n🔍 [RAG CORE] Running MediScanAI Core Pipeline...")
        user_norm = normalize_text(user_text or "")
        ocr_text = ""

        # 1. OCR Extraction
        if image_path:
            print("📷 [Vision] Running PaddleOCR on medicine image...")
            _t_ocr = time.perf_counter()
            ocr_res = extract_text_from_image(image_path)
            ocr_text = ocr_text_join(ocr_res["texts"])
            pipeline_timings["ocr_total_ms"] = int((time.perf_counter() - _t_ocr) * 1000)
            print(f"   ↳ OCR label extraction completed ({len(ocr_text)} characters extracted).")
        else:
            print("📷 [Vision] No image provided. Skipping OCR.")

        # 2. Retrievals for Symptom Text
        print(f"🔎 [Retrieval] Running Hybrid Search (FAISS + BM25 + RRF + Cross-Encoder) for symptom query ({len(user_norm)} chars)...")
        _t_ret_symptoms = time.perf_counter()
        diseases_retrieved = self.retriever.search_specific('diseases', user_norm, top_k=top_k)
        pipeline_timings["retrieval_diseases_ms"] = int((time.perf_counter() - _t_ret_symptoms) * 1000)

        _t_ret_drugs = time.perf_counter()
        drugs_retrieved = self.retriever.search_specific('drugs', user_norm, top_k=top_k)
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
            drug_dict_retrieved = self.retriever.search_specific('drug_dict', ocr_text, top_k=top_k)
            pipeline_timings["retrieval_drug_dict_ms"] = int((time.perf_counter() - _t_ret_drug_dict) * 1000)

            _t_ret_drugs_ocr = time.perf_counter()
            drugs_from_ocr_retrieved = self.retriever.search_specific('drugs', ocr_text, top_k=top_k)
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

        # 4. Assembling Prompt & generation
        _t_prompt = time.perf_counter()
        formatted_user_retrievals = self._format_retrievals(retrievals_for_user_text)
        formatted_ocr_retrievals = self._format_retrievals(retrievals_for_ocr_text)

        print("📝 [Prompt] Assembling context-grounded prompt template...")
        full_prompt = ANALYSIS_PROMPT_TEMPLATE.format(
            user_text=user_text,
            ocr_text=ocr_text if ocr_text else "No image provided.",
            retrievals_for_user_text=formatted_user_retrievals,
            retrievals_for_ocr_text=formatted_ocr_retrievals
        )
        pipeline_timings["prompt_assembly_ms"] = int((time.perf_counter() - _t_prompt) * 1000)

        provider_label = "Gemini/Groq (online)" if llm_mode == "online" else "Ollama/Mistral"
        print(f"🤖 [LLM] Requesting clinical analysis via {provider_label}...")
        _t_llm = time.perf_counter()
        llm_response_str = generate_with_mode(full_prompt, llm_mode=llm_mode)
        pipeline_timings["llm_total_ms"] = int((time.perf_counter() - _t_llm) * 1000)
        print("   ↳ Generation completed successfully.")

        all_retrievals = {**retrievals_for_user_text, **retrievals_for_ocr_text}

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
        print(f"  Prompt assembly:             {pipeline_timings.get('prompt_assembly_ms', 0)}ms")
        print(f"  LLM ({provider_label}): {pipeline_timings.get('llm_total_ms', 0)}ms")
        print(f"  " + "-" * 40)
        print(f"  Pipeline total:              {pipeline_timings['pipeline_total_ms']}ms")
        print("=" * 60 + "\n")

        print("✅ [RAG CORE] Completed execution.\n")
        return {
            "card": card,
            "meta": card_meta,
            "pipeline_timings": pipeline_timings,
        }

