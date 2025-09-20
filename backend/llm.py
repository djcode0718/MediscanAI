# # backend/llm.py
# import requests
# import subprocess
# import json
# import shutil
# from typing import Dict, Any, Optional

# OLLAMA_API_URL = "http://localhost:11434/api/generate"
# OLLAMA_CHAT_URL = "http://localhost:11434/api/chat"
# DEFAULT_MODEL = "mistral"  # assumes you have this model downloaded in Ollama

# class OllamaError(Exception):
#     pass

# def call_ollama_api_generate(prompt: str, model: str = DEFAULT_MODEL, stream: bool = False, options: Optional[Dict] = None) -> str:
#     """
#     Call local Ollama REST generate endpoint. Returns the text response.
#     """
#     payload = {
#         "model": model,
#         "prompt": prompt,
#         "stream": stream
#     }
#     if options:
#         payload["options"] = options
#     try:
#         r = requests.post(OLLAMA_API_URL, json=payload, timeout=60)
#         r.raise_for_status()
#     except Exception as e:
#         raise OllamaError(f"HTTP call to Ollama failed: {e}")
#     try:
#         j = r.json()
#     except Exception:
#         # fallback to raw text
#         return r.text
#     # Ollama returns a structured output; try to extract the text
#     # Typical: j may include 'results' or 'output' fields
#     if isinstance(j, dict):
#         # many docs show 'text' in results or direct string
#         if 'text' in j:
#             return j['text']
#         if 'output' in j:
#             return j['output']
#         # sometimes a list of tokens
#         if 'results' in j and isinstance(j['results'], list) and len(j['results']) > 0:
#             first = j['results'][0]
#             if isinstance(first, dict) and 'content' in first:
#                 return first['content']
#         # fallback: stringified json
#         return json.dumps(j)
#     return str(j)

# def call_ollama_cli_generate(prompt: str, model: str = DEFAULT_MODEL) -> str:
#     """
#     Fallback: call 'ollama' CLI if installed.
#     Example: ollama run mistral "Your prompt"
#     """
#     if shutil.which("ollama") is None:
#         raise OllamaError("ollama CLI not found and REST API failed.")
#     try:
#         # Use ollama run <model> "<prompt>"
#         proc = subprocess.run(["ollama", "run", model, prompt], capture_output=True, text=True, timeout=120)
#         if proc.returncode != 0:
#             raise OllamaError(f"ollama CLI returned non-zero code: {proc.stderr}")
#         return proc.stdout.strip()
#     except Exception as e:
#         raise OllamaError(f"ollama CLI invocation failed: {e}")

# def generate(prompt: str, model: str = DEFAULT_MODEL, options: Optional[Dict] = None) -> str:
#     """
#     High-level wrapper. Try REST API first, then CLI.
#     """
#     try:
#         return call_ollama_api_generate(prompt, model=model, options=options)
#     except OllamaError:
#         # fallback to CLI
#         return call_ollama_cli_generate(prompt, model=model)


# import requests
# import subprocess
# import json
# import shutil
# from typing import Dict, Any, Optional

# OLLAMA_API_URL = "http://localhost:11434/api/generate"
# OLLAMA_CHAT_URL = "http://localhost:11434/api/chat"
# DEFAULT_MODEL = "phi3:mini"

# class OllamaError(Exception):
#     pass

# def call_ollama_api_generate(prompt: str, model: str = DEFAULT_MODEL, stream: bool = False, options: Optional[Dict] = None) -> str:
#     """
#     Call local Ollama REST generate endpoint. Returns the text response.
#     """
#     payload = {
#         "model": model,
#         "prompt": prompt,
#         "stream": stream
#     }
#     if options:
#         payload["options"] = options
#     try:
#         r = requests.post(OLLAMA_API_URL, json=payload, timeout=60)
#         r.raise_for_status()
#     except Exception as e:
#         raise OllamaError(f"HTTP call to Ollama failed: {e}")
#     try:
#         j = r.json()
#     except Exception:
#         return r.text

#     if isinstance(j, dict):
#         if 'response' in j:
#             return j['response']
#         if 'text' in j:
#             return j['text']
#         if 'output' in j:
#             return j['output']
#         if 'results' in j and isinstance(j['results'], list) and len(j['results']) > 0:
#             first = j['results'][0]
#             if isinstance(first, dict) and 'content' in first:
#                 return first['content']
#         return json.dumps(j)
#     return str(j)

# def call_ollama_cli_generate(prompt: str, model: str = DEFAULT_MODEL) -> str:
#     """
#     Fallback: call 'ollama' CLI if installed.
#     Example: ollama run mistral "Your prompt"
#     """
#     if shutil.which("ollama") is None:
#         raise OllamaError("ollama CLI not found and REST API failed.")
#     try:
#         proc = subprocess.run(["ollama", "run", model, prompt], capture_output=True, text=True, timeout=120)
#         if proc.returncode != 0:
#             raise OllamaError(f"ollama CLI returned non-zero code: {proc.stderr}")
#         return proc.stdout.strip()
#     except Exception as e:
#         raise OllamaError(f"ollama CLI invocation failed: {e}")

# def generate(prompt: str, model: str = DEFAULT_MODEL, options: Optional[Dict] = None) -> str:
#     """
#     High-level wrapper. Try REST API first, then CLI.
#     """
#     try:
#         return call_ollama_api_generate(prompt, model=model, options=options)
#     except OllamaError:
#         return call_ollama_cli_generate(prompt, model=model)

#llm.py


import requests
import subprocess
import json
import shutil
from typing import Dict, Any, Optional

OLLAMA_API_URL = "http://localhost:11434/api/generate"
OLLAMA_CHAT_URL = "http://localhost:11434/api/chat"
# DEFAULT_MODEL = "phi3:mini"
DEFAULT_MODEL = "llama3.1:8b"

class OllamaError(Exception):
    pass

def call_ollama_api_generate(prompt: str, model: str = DEFAULT_MODEL, stream: bool = False, options: Optional[Dict] = None) -> str:
    """
    Call local Ollama REST generate endpoint. Returns the text response.
    """
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": stream
    }
    if options:
        payload["options"] = options
    try:
        r = requests.post(OLLAMA_API_URL, json=payload, timeout=120)
        r.raise_for_status()
    except Exception as e:
        raise OllamaError(f"HTTP call to Ollama failed: {e}")
    try:
        j = r.json()
    except Exception:
        return r.text

    if isinstance(j, dict):
        if 'response' in j:
            return j['response']
        if 'text' in j:
            return j['text']
        if 'output' in j:
            return j['output']
        if 'results' in j and isinstance(j['results'], list) and len(j['results']) > 0:
            first = j['results'][0]
            if isinstance(first, dict) and 'content' in first:
                return first['content']
        return json.dumps(j)
    return str(j)

def call_ollama_cli_generate(prompt: str, model: str = DEFAULT_MODEL) -> str:
    """
    Fallback: call 'ollama' CLI if installed.
    Example: ollama run mistral "Your prompt"
    """
    if shutil.which("ollama") is None:
        raise OllamaError("ollama CLI not found and REST API failed.")
    try:
        proc = subprocess.run(
            ["ollama", "run", model, prompt],
            capture_output=True,
            text=True,
            timeout=120,
            encoding='utf-8'
        )
        if proc.returncode != 0:
            raise OllamaError(f"ollama CLI returned non-zero code: {proc.stderr}")
        return proc.stdout.strip()
    except Exception as e:
        raise OllamaError(f"ollama CLI invocation failed: {e}")

def generate(prompt: str, model: str = DEFAULT_MODEL, options: Optional[Dict] = None) -> str:
    """
    High-level wrapper. Try REST API first, then CLI.
    """
    try:
        return call_ollama_api_generate(prompt, model=model, options=options)
    except OllamaError:
        return call_ollama_cli_generate(prompt, model=model)