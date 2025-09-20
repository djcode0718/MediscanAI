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
from backend.ocr import extract_text_from_image, ocr_text_join
from backend.retriever import MultiRetriever
from backend.llm import generate
from backend.utils import normalize_text
from backend.prompt import ANALYSIS_PROMPT_TEMPLATE
from backend.formatter_new import build_summary_card


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
        user_norm = normalize_text(user_text or "")
        ocr_text = ""
        if image_path:
            ocr_res = extract_text_from_image(image_path)
            ocr_text = ocr_text_join(ocr_res["texts"])

        retrievals_for_user_text = {
            "diseases": self.retriever.search_specific('diseases', user_norm, top_k=top_k),
            "drugs": self.retriever.search_specific('drugs', user_norm, top_k=top_k),
        }

        retrievals_for_ocr_text = {}
        if ocr_text:
            retrievals_for_ocr_text = {
                "drug_dict": self.retriever.search_specific('drug_dict', ocr_text, top_k=top_k),
                "drugs_from_ocr": self.retriever.search_specific('drugs', ocr_text, top_k=top_k),
            }

        formatted_user_retrievals = self._format_retrievals(retrievals_for_user_text)
        formatted_ocr_retrievals = self._format_retrievals(retrievals_for_ocr_text)

        full_prompt = ANALYSIS_PROMPT_TEMPLATE.format(
            user_text=user_text,
            ocr_text=ocr_text if ocr_text else "No image provided.",
            retrievals_for_user_text=formatted_user_retrievals,
            retrievals_for_ocr_text=formatted_ocr_retrievals
        )

        llm_response_str = generate(full_prompt)

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

        return {
            "card": card,
            "meta": card_meta
        }

