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
from app.ocr import extract_text_from_image, ocr_text_join
from app.retriever import MultiRetriever
from app.llm import generate
from app.utils import normalize_text
from app.prompt import ANALYSIS_PROMPT_TEMPLATE
from app.formatter_new import build_summary_card



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

    def run(self, user_text: str, image_path: Optional[str] = None, top_k: int = 5) -> Dict[str, Any]:
        print("\n🔍 [RAG CORE] Running MediScanAI Core Pipeline...")
        user_norm = normalize_text(user_text or "")
        ocr_text = ""
        
        # 1. OCR Extraction
        if image_path:
            print(f"📷 [Vision] Running PaddleOCR on medicine image: {image_path}")
            ocr_res = extract_text_from_image(image_path)
            ocr_text = ocr_text_join(ocr_res["texts"])
            print(f"   ↳ Extracted label text: '{ocr_text}'")
        else:
            print("📷 [Vision] No image provided. Skipping OCR.")

        # 2. Retrievals for Symptom Text
        print(f"🔎 [Retrieval] Searching FAISS databases for symptom: '{user_norm[:60]}...'")
        diseases_retrieved = self.retriever.search_specific('diseases', user_norm, top_k=top_k)
        drugs_retrieved = self.retriever.search_specific('drugs', user_norm, top_k=top_k)
        
        print(f"   ↳ Diseases index: Found {len(diseases_retrieved)} matching chunks")
        for idx, (key, score, obj) in enumerate(diseases_retrieved, 1):
            disease_name = obj.get('chunk', {}).get('disease', key) if isinstance(obj, dict) else key
            print(f"     - Match #{idx}: {disease_name} (Score: {score:.4f})")

        print(f"   ↳ Drugs index (Symptom query): Found {len(drugs_retrieved)} matching chunks")
        for idx, (key, score, obj) in enumerate(drugs_retrieved, 1):
            brand_name = obj.get('brand_name', key) if isinstance(obj, dict) else key
            print(f"     - Match #{idx}: {brand_name} (Score: {score:.4f})")

        retrievals_for_user_text = {
            "diseases": diseases_retrieved,
            "drugs": drugs_retrieved,
        }

        # 3. Retrievals for OCR Text
        retrievals_for_ocr_text = {}
        if ocr_text:
            print(f"🔎 [Retrieval] Searching FAISS databases for OCR label: '{ocr_text[:60]}...'")
            drug_dict_retrieved = self.retriever.search_specific('drug_dict', ocr_text, top_k=top_k)
            drugs_from_ocr_retrieved = self.retriever.search_specific('drugs', ocr_text, top_k=top_k)
            
            print(f"   ↳ Drug Dictionary index: Found {len(drug_dict_retrieved)} matching chunks")
            for idx, (key, score, obj) in enumerate(drug_dict_retrieved, 1):
                drug_name = obj.get('drug_name', key) if isinstance(obj, dict) else key
                print(f"     - Match #{idx}: {drug_name} (Score: {score:.4f})")

            print(f"   ↳ Drugs index (OCR query): Found {len(drugs_from_ocr_retrieved)} matching chunks")
            for idx, (key, score, obj) in enumerate(drugs_from_ocr_retrieved, 1):
                brand_name = obj.get('brand_name', key) if isinstance(obj, dict) else key
                print(f"     - Match #{idx}: {brand_name} (Score: {score:.4f})")

            retrievals_for_ocr_text = {
                "drug_dict": drug_dict_retrieved,
                "drugs_from_ocr": drugs_from_ocr_retrieved,
            }

        # 4. Assembling Prompt & generation
        formatted_user_retrievals = self._format_retrievals(retrievals_for_user_text)
        formatted_ocr_retrievals = self._format_retrievals(retrievals_for_ocr_text)

        print("📝 [Prompt] Assembling context-grounded prompt template...")
        full_prompt = ANALYSIS_PROMPT_TEMPLATE.format(
            user_text=user_text,
            ocr_text=ocr_text if ocr_text else "No image provided.",
            retrievals_for_user_text=formatted_user_retrievals,
            retrievals_for_ocr_text=formatted_ocr_retrievals
        )

        print("🤖 [LLM] Requesting clinical analysis from local model (Mistral)...")
        llm_response_str = generate(full_prompt)
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

        print("✅ [RAG CORE] Completed execution.\n")
        return {
            "card": card,
            "meta": card_meta
        }

