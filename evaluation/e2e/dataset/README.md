# MediScanAI End-to-End Evaluation Dataset (v1)

## Overview
This dataset contains 110 deterministic test cases designed for end-to-end evaluation of the MediScanAI RAG pipeline:
- **110 RAGAS evaluation cases** (covering symptom presentation, multimodal clean/noisy OCR, disease-drug matches and mismatches, and negative unanswerable controls).
- **10 Emergency fast-path cases** (acute red-flag conditions tested against deterministic emergency guardrails, evaluated separately from RAGAS).

## Distribution
| Category | Cases | Expected Behavior | Description |
| :--- | :--- | :--- | :--- |
| `symptom_only` | 25 | `answer` | Real traffic symptom presentations mapped to disease chunks |
| `medicine_only_clean_ocr` | 15 | `answer` | Medicine inquiries with clean drug label OCR text |
| `medicine_only_noisy_ocr` | 15 | `answer` | Medicine inquiries with noisy OCR (batch/lot/confusions) |
| `symptom_plus_medicine_match` | 20 | `answer` | Matching clinical symptoms paired with appropriate medication OCR |
| `symptom_plus_medicine_mismatch` | 15 | `answer` | Unrelated symptoms and medications (0 token overlap; marked heuristic) |
| `unanswerable` | 10 | `abstain` | Negative controls (5 benchmark controls + 5 fictitious pharmaceuticals) |
| `emergency` | 10 | `emergency` | Acute life-threatening red-flag presentations (tested separately) |
| **Total** | **120** | — | — |

## Schema
Each record in `e2e_v1.jsonl` follows this exact JSON structure:
- `case_id` (str): e.g. `E2E-001`
- `category` (str): Category identifier
- `user_text` (str): Real-world patient query
- `ocr_text` (str): Scanned label text or OCR synthesis
- `reference` (str): Programmatically constructed reference fact string from source records (never LLM-generated)
- `reference_context_ids` (List[str]): Ground truth document IDs (`disease_chunk_X`, `drug_Y`)
- `equivalent_ids` (List[str]): Other drug IDs sharing identical `(generic_name, sorted substance_name)`
- `expected_behavior` (str): `answer` | `abstain` | `emergency`
- `reference_status` (str): `auto_from_source`
- `heuristic` (bool, optional): Present on heuristic mismatch pairings

## Known Limitations & Biases
1. **Synthetic OCR Text**: The OCR text for medication packaging is generated synthetically to model real-world PaddleOCR noise patterns (character confusions like O/0, l/1, m/rn and packaging noise like lot numbers and expiration dates).
2. **Programmatic References**: Reference answers are assembled directly from authoritative fields (`indications_and_usage`, `substance_name`, disease symptoms) using deterministic formatting rules rather than human expert clinician annotations.
3. **Unreviewed Mismatches**: Symptom-drug mismatch cases are verified via zero-token lexical overlap between disease/symptom vocabularies and drug indication texts.
4. **Offline Sampling**: Cases are sampled with deterministic seed 42 from `data/diseases_faiss_data.jsonl` and `data/drugs_faiss_data.jsonl`.
