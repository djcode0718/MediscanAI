# # test_pipeline_new.py

# import sys
# import os

# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# from backend.core_new import Pipeline
# from backend.llm import OllamaError

# def run_pipeline_test(text: str, image_path: str = None):
#     """
#     Initializes and runs the full backend pipeline with the given inputs.
#     """
#     print("--- Initializing Pipeline ---")
#     pipeline = Pipeline()

#     print("\n[TEST] Running pipeline with the following inputs:")
#     print(f"  - Text: '{text}'")
#     if image_path:
#         print(f"  - Image: '{image_path}'")
    
#     print("\n--- Awaiting response... ---")

#     try:
#         # The 'result' variable is now the final markdown string from the LLM
#         result = pipeline.run(user_text=text, image_path=image_path)
        
#         print("\n[RESULT] Pipeline Output:\n")
        
#         # --- THIS IS THE FIX ---
#         # We no longer need to parse a dictionary. Just print the string result.
#         print(result)

#     except OllamaError as e:
#         print(f"\n[ERROR] The LLM call failed: {e}")
#     except FileNotFoundError as e:
#         print(f"\n[ERROR] File not found: {e}")
#     except Exception as e:
#         print(f"\n[ERROR] An unexpected error occurred in the pipeline: {e}")

# if __name__ == "__main__":
#     # Hardcoded values
#     text = "I’ve been coughing for about a week now. It started with a sore throat, then turned into a dry cough. The last two days I’ve had mild fever in the evenings. I tried paracetamol and ginger tea, which helped a bit, but the cough still comes back. I think it started after I got drenched in the rain."
#     # image_path = '/Users/sj/Downloads/WhatsApp Image 2025-09-14 at 14.00.39 (1).jpeg'
#     image_path = '/Users/sj/Downloads/WhatsApp Image 2025-09-16 at 22.31.52.jpeg'

#     # Run the test with the hardcoded inputs
#     run_pipeline_test(text=text, image_path=image_path)


# test_pipeline_new.py

import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.core_new import Pipeline
from backend.llm import OllamaError

def run_pipeline_test(text: str, image_path: str = None):
    """
    Initializes and runs the full backend pipeline with the given inputs.
    """
    print("--- Initializing Pipeline ---")
    pipeline = Pipeline()

    print("\n[TEST] Running pipeline with the following inputs:")
    print(f"  - Text: '{text}'")
    if image_path:
        print(f"  - Image: '{image_path}'")
    
    print("\n--- Awaiting response... ---")

    try:
        # --- CHANGE 1: Receive two values from the pipeline ---
        llm_result, ocr_text = pipeline.run(user_text=text, image_path=image_path)
        
        # --- CHANGE 2: Display the extracted OCR text ---
        print("\n--- OCR Text Extracted ---")
        print(ocr_text if ocr_text else "No text was extracted from the image.")
        
        print("\n[RESULT] Final LLM Analysis:\n")
        
        # --- CHANGE 3: Print the LLM result ---
        print(llm_result)

    except OllamaError as e:
        print(f"\n[ERROR] The LLM call failed: {e}")
    except FileNotFoundError as e:
        print(f"\n[ERROR] File not found: {e}")
    except Exception as e:
        print(f"\n[ERROR] An unexpected error occurred in the pipeline: {e}")

if __name__ == "__main__":
    text = "I’ve been coughing for about a week now. It started with a sore throat, then turned into a dry cough. The last two days I’ve had mild fever in the evenings. I tried paracetamol and ginger tea, which helped a bit, but the cough still comes back. I think it started after I got drenched in the rain."
    image_path = '/Users/sj/Downloads/WhatsApp Image 2025-09-16 at 22.31.52.jpeg'

    run_pipeline_test(text=text, image_path=image_path)