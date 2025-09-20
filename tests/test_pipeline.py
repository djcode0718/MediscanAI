# test_pipeline.py

import sys
import os
import json

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
        result = pipeline.run(user_text=text, image_path=image_path)
        
        print("\n[RESULT] Pipeline Output:\n")
        
        # Pretty-print the JSON card
        if isinstance(result.get("card"), dict):
            print(json.dumps(result["card"], indent=2))
        else:
            print(result)

    except OllamaError as e:
        print(f"\n[ERROR] The LLM call failed: {e}")
    except FileNotFoundError as e:
        print(f"\n[ERROR] File not found: {e}")
    except Exception as e:
        print(f"\n[ERROR] An unexpected error occurred in the pipeline: {e}")

if __name__ == "__main__":
    # Hardcoded values
    # text = "I got mouth ulcers, can i use this medicine?"
    # text = "I have these symptoms, vomiting, fever, excessive sweating, dehydration."
    # text = "I have these symptoms cough and mild fever."
    text = "I’ve been coughing for about a week now. It started with a sore throat, then turned into a dry cough. The last two days I’ve had mild fever in the evenings. I tried paracetamol and ginger tea, which helped a bit, but the cough still comes back. I think it started after I got drenched in the rain."
    # image_path = '/Users/sj/Downloads/WhatsApp Image 2025-09-14 at 14.00.39.jpeg'
    # image_path = '/Users/sj/Downloads/WhatsApp Image 2025-09-07 at 15.21.16 (1).jpeg'
    image_path = '/Users/sj/Downloads/WhatsApp Image 2025-09-07 at 15.21.16.jpeg'

    # Run the test with the hardcoded inputs
    run_pipeline_test(text=text, image_path=image_path)

