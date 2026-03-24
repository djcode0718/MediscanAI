# 🏥 MediScanAI – Privacy-First AI Health Copilot

**MediScanAI** is an AI-powered healthcare assistant that analyzes **symptoms, medicine images, and voice inputs** to provide medical insights while keeping all data **fully local and private**.
The system uses a **Retrieval-Augmented Generation (RAG)** pipeline combined with a **local LLM** to generate safe and contextual health guidance.



---

# 📌 Features

## 🔍 Multimodal Input

MediScanAI accepts multiple types of input:

* 📝 Text (Symptoms)
* 📷 Medicine Image (OCR)
* 🎤 Voice Input (Speech-to-Text)

## 🧠 AI Analysis

The system:

* Identifies possible diseases from symptoms
* Extracts medicine names from images
* Checks if the medicine matches the symptoms
* Suggests alternatives if mismatch detected
* Generates medical advice using a local LLM

## 🔒 Privacy First

All processing runs locally:

* Local OCR
* Local Speech Recognition
* Local Vector Database
* Local LLM (Ollama)
* No cloud APIs required

---

# 🏗️ Project Architecture

```
MediScanAI
│
├── backend/
│   ├── core.py
│   ├── core_new.py
│   ├── retriever.py
│   ├── embeddings.py
│   ├── llm.py
│   ├── ocr.py
│   ├── whisper.py
│   └── utils.py
│
├── frontend/
│   ├── app.py
│   └── app_new.py
│
├── data/
├── indexes/
├── tests/
└── copy_codes.py
```

---

# ⚙️ How the System Works

## Step-by-Step Pipeline

1. User enters symptoms (text / voice)
2. User uploads medicine image
3. OCR extracts medicine name
4. Voice converted to text using Whisper
5. Symptoms matched with disease database
6. Medicine matched with drug database
7. System checks **medicine–symptom mismatch**
8. Local LLM generates final medical advice

---

# 🧩 Core Technologies Used

| Component          | Technology                           |
| ------------------ | ------------------------------------ |
| OCR                | PaddleOCR                            |
| Speech Recognition | Faster-Whisper                       |
| Embeddings         | SentenceTransformers                 |
| Vector Search      | FAISS                                |
| LLM                | Ollama (Llama / Phi / Mistral)       |
| Frontend           | Streamlit                            |
| Backend            | Python                               |
| Architecture       | RAG (Retrieval Augmented Generation) |

---

# 🧠 RAG Pipeline Overview

```
User Input
   ↓
OCR / Speech-to-Text
   ↓
Text Normalization
   ↓
Vector Embeddings
   ↓
FAISS Retrieval
   ↓
Context Generation
   ↓
Local LLM (Ollama)
   ↓
Medical Advice Output
```

---

# 🚀 Installation & Setup

## 1. Clone Repository

```bash
git clone https://github.com/yourusername/MediScanAI.git
cd MediScanAI
```

## 2. Install Dependencies

```bash
pip install -r requirements.txt
```

## 3. Install Ollama

Install Ollama and pull model:

```bash
ollama pull llama3.1:8b
```

## 4. Run Streamlit App

```bash
streamlit run frontend/app_new.py
```

---

# 🧪 Running Tests

```bash
python tests/test_retriever.py
python tests/test_ocr.py
python tests/test_utils.py
python tests/test_pipeline_new.py
```

---

# 📊 Key Modules Explained

## utils.py

* Text normalization
* Spell correction
* JSONL data loading

## ocr.py

* Extract text from medicine images
* Draw bounding boxes on detected text

## whisper.py

* Converts speech to text
* Detects language

## embeddings.py

* Converts text to vector embeddings

## retriever.py

* Searches disease & drug databases using FAISS

## llm.py

* Communicates with Ollama LLM

## core_new.py

* Main pipeline
* Performs mismatch check
* Generates final AI response

---

# ⚠️ Important Disclaimer

MediScanAI **does not replace professional medical advice**.
It is intended only for **educational and informational purposes**.

---

# 🎯 Future Improvements

* Mobile App Integration
* Drug Interaction Checker
* Prescription Scanner
* Patient History Tracking
* Emergency Warning System
* Multilingual Support
* Fine-tuned Medical LLM

---

# 👨‍💻 Author

**Sreevedh Jella**

AI + Healthcare + Privacy
MediScanAI Project

---
