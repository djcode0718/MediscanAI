#!/usr/bin/env python3
"""
MediScanAI — End-to-End Evaluation Dataset Generator (Phase 01 / Step 3)

Generates:
  - evaluation/e2e/dataset/e2e_v1.jsonl (~110 RAGAS cases + 10 emergency cases = 120 total)
  - evaluation/e2e/dataset/dataset_stats.json
  - evaluation/e2e/dataset/README.md

Deterministic sampling with seed 42 from real JSONLs in data/.
"""

import json
import random
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Any, Tuple, Set

SEED = 42

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = Path(__file__).resolve().parent / "dataset"
DATASET_PATH = OUTPUT_DIR / "e2e_v1.jsonl"
STATS_PATH = OUTPUT_DIR / "dataset_stats.json"
README_PATH = OUTPUT_DIR / "README.md"


def clean_text(s: str) -> str:
    """Normalize whitespace and remove control characters."""
    if not s:
        return ""
    return re.sub(r"\s+", " ", str(s)).strip()


def build_noisy_ocr(brand: str, generic: str, strength: str, rng: random.Random) -> str:
    """Synthesizes realistic noisy OCR text with batch/mfg/exp noise and char confusions."""
    templates = [
        "{brand} {strength}\n{generic}\nRx On1y\nLot: 4892A\nExp: 11/27\nDistributed by Apex Pharma Inc, Austin TX 78701",
        "{brand}® ({generic})\nEach tablet contains {strength}\nDosage: As directed by physician\nBatch: B9201-C\nMfg: 03/24 Exp: 09/27\nKeep out of reach of children",
        "NDC 0498-1204-01\n{brand}\n({generic})\nStrength: {strength}\nStore at 20° to 25°C (68° to 77°F)\nRx only\nNovartis Pharmaceuticals Corp, Hanover NJ",
        "{brand} {strength} Capsules\n{generic}\nUsual Dosage: See package insert\nMfg Date: 05/2023 Exp: 04/2026\nLot # 771029\nMylan Pharmaceuticals Inc, Morgantown WV",
    ]
    raw = rng.choice(templates).format(brand=brand, generic=generic, strength=strength)
    # Apply realistic OCR character confusions: O -> 0, l -> 1, m -> rn
    chars = list(raw)
    for i in range(len(chars)):
        c = chars[i]
        if c == 'O' and rng.random() < 0.25:
            chars[i] = '0'
        elif c == 'o' and rng.random() < 0.15:
            chars[i] = '0'
        elif c == 'l' and rng.random() < 0.20:
            chars[i] = '1'
        elif c == 'I' and rng.random() < 0.15:
            chars[i] = '1'
        elif c == 'm' and rng.random() < 0.15:
            chars[i] = 'rn'
    return "".join(chars)


def generate_dataset():
    rng = random.Random(SEED)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("📖 Loading corpus JSONLs...")
    # 1. Diseases
    diseases = []
    with open(DATA_DIR / "diseases_faiss_data.jsonl", "r", encoding="utf-8") as f:
        for line in f:
            diseases.append(json.loads(line))
    print(f"Loaded {len(diseases)} disease chunks.")

    # 2. Drugs and equivalence map
    drugs = []
    eq_map = defaultdict(list)
    with open(DATA_DIR / "drugs_faiss_data.jsonl", "r", encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            drugs.append(d)
            did = f"drug_{d['id']}"
            gen = (d.get("generic_name") or "").strip().lower()
            subs = tuple(sorted(s.strip().lower() for s in (d.get("substance_name") or [])))
            if gen or subs:
                eq_map[(gen, subs)].append(did)
    print(f"Loaded {len(drugs)} drugs across {len(eq_map)} equivalence clusters.")

    # Filter rich drugs
    rich_drugs = [
        d for d in drugs
        if (d.get("indications_and_usage") or "").strip()
        and len(d.get("indications_and_usage", "").strip()) >= 120
        and d.get("substance_name")
        and d.get("brand_name")
        and d.get("generic_name")
    ]
    # Group by generic to diversify selection
    generic_to_drugs = defaultdict(list)
    for d in rich_drugs:
        gen = (d.get("generic_name") or "").strip().lower()
        generic_to_drugs[gen].append(d)

    sorted_generics = sorted(generic_to_drugs.keys())
    rng.shuffle(sorted_generics)
    used_drug_ids: Set[int] = set()

    def get_diverse_drug() -> Dict[str, Any]:
        """Picks a drug with a fresh generic to ensure maximum diversity."""
        for gen in sorted_generics:
            candidates = [d for d in generic_to_drugs[gen] if d["id"] not in used_drug_ids]
            if candidates:
                chosen = rng.choice(candidates)
                used_drug_ids.add(chosen["id"])
                return chosen
        # Fallback if exhausted
        candidate = rng.choice(rich_drugs)
        used_drug_ids.add(candidate["id"])
        return candidate

    cases = []
    case_counter = 1

    # -------------------------------------------------------------
    # Category 1: symptom_only (25 cases)
    # -------------------------------------------------------------
    print("Generating Category 1: symptom_only (25 cases)...")
    disease_indices = list(range(len(diseases)))
    rng.shuffle(disease_indices)
    chosen_disease_indices = disease_indices[:25]

    symptom_inquiry_templates = [
        "I have been suffering from {symptoms} for the past several days. What condition could this indicate, and what should I know?",
        "Doctor, I recently developed {symptoms}. What medical illness might be causing this?",
        "For the last 3 days I've been feeling sick with {symptoms}. Can you explain what this could be?",
        "I am experiencing {symptoms} and getting concerned. What disease matches these symptoms?",
        "Could you tell me what condition is associated with symptoms like {symptoms}?",
    ]

    for idx in chosen_disease_indices:
        d_rec = diseases[idx]
        chunk = d_rec.get("chunk", {})
        d_name = chunk.get("disease", "Unknown Condition")
        symptoms = chunk.get("symptoms", [])
        if not symptoms:
            symptoms = ["fever", "fatigue", "malaise"]
        raw_chunk_id = chunk.get("id", f"chunk_{idx + 1}")
        chunk_num = re.search(r"\d+", str(raw_chunk_id))
        chunk_id = f"disease_chunk_{chunk_num.group(0)}" if chunk_num else f"disease_chunk_{idx + 1}"

        sym_str = ", ".join(symptoms[:8])
        prompt_template = rng.choice(symptom_inquiry_templates)
        user_query = prompt_template.format(symptoms=", ".join(symptoms[:4]))
        ref_text = f"{d_name} lists symptoms: {sym_str}."

        cases.append({
            "case_id": f"E2E-{case_counter:03d}",
            "category": "symptom_only",
            "user_text": user_query,
            "ocr_text": "",
            "reference": ref_text,
            "reference_context_ids": [chunk_id],
            "equivalent_ids": [],
            "expected_behavior": "answer",
            "reference_status": "auto_from_source",
        })
        case_counter += 1

    # -------------------------------------------------------------
    # Category 2: medicine_only_clean_ocr (15 cases)
    # -------------------------------------------------------------
    print("Generating Category 2: medicine_only_clean_ocr (15 cases)...")
    clean_user_templates = [
        "I was prescribed this medicine. What is it used for, and what are its key warnings and dosage instructions?",
        "Can you explain what this medication is indicated for, its common precautions, and how it should be taken?",
        "Please provide the therapeutic indications, active ingredients, and important warnings for this scanned drug label.",
        "What condition does this medicine treat, and what safety warnings should I be aware of?",
    ]
    strengths = ["10mg", "20mg", "25mg", "50mg", "100mg", "250mg", "500mg", "5mg/mL"]

    for _ in range(15):
        drug = get_diverse_drug()
        did = f"drug_{drug['id']}"
        bname = clean_text(drug.get("brand_name", "Unknown Brand"))
        gname = clean_text(drug.get("generic_name", "Unknown Generic"))
        subs = [clean_text(s) for s in drug.get("substance_name", [])]
        indications = clean_text(drug.get("indications_and_usage", ""))
        strength = rng.choice(strengths)

        ocr = f"{bname}\n({gname})\nStrength: {strength} Tablets\nRx Only\nDistributed by US Pharmaceuticals LLC"
        user_q = rng.choice(clean_user_templates)
        ref_text = f"{bname} ({gname}) contains {', '.join(subs)}; its label lists: {indications[:400]}"

        gen_key = (gname.lower(), tuple(sorted(s.lower() for s in subs)))
        eq_ids = [x for x in eq_map.get(gen_key, []) if x != did]

        cases.append({
            "case_id": f"E2E-{case_counter:03d}",
            "category": "medicine_only_clean_ocr",
            "user_text": user_q,
            "ocr_text": ocr,
            "reference": ref_text,
            "reference_context_ids": [did],
            "equivalent_ids": eq_ids,
            "expected_behavior": "answer",
            "reference_status": "auto_from_source",
        })
        case_counter += 1

    # -------------------------------------------------------------
    # Category 3: medicine_only_noisy_ocr (15 cases)
    # -------------------------------------------------------------
    print("Generating Category 3: medicine_only_noisy_ocr (15 cases)...")
    noisy_user_templates = [
        "I scanned my pill container label. Can you identify this medication and explain what it treats and its precautions?",
        "Please read this scanned medicine bottle label and explain its therapeutic uses and warnings.",
        "What is this medicine indicated for, and what are the main precautions according to the package label?",
    ]

    for _ in range(15):
        drug = get_diverse_drug()
        did = f"drug_{drug['id']}"
        bname = clean_text(drug.get("brand_name", "Unknown Brand"))
        gname = clean_text(drug.get("generic_name", "Unknown Generic"))
        subs = [clean_text(s) for s in drug.get("substance_name", [])]
        indications = clean_text(drug.get("indications_and_usage", ""))
        strength = rng.choice(strengths)

        ocr = build_noisy_ocr(bname, gname, strength, rng)
        user_q = rng.choice(noisy_user_templates)
        ref_text = f"{bname} ({gname}) contains {', '.join(subs)}; its label lists: {indications[:400]}"

        gen_key = (gname.lower(), tuple(sorted(s.lower() for s in subs)))
        eq_ids = [x for x in eq_map.get(gen_key, []) if x != did]

        cases.append({
            "case_id": f"E2E-{case_counter:03d}",
            "category": "medicine_only_noisy_ocr",
            "user_text": user_q,
            "ocr_text": ocr,
            "reference": ref_text,
            "reference_context_ids": [did],
            "equivalent_ids": eq_ids,
            "expected_behavior": "answer",
            "reference_status": "auto_from_source",
        })
        case_counter += 1

    # -------------------------------------------------------------
    # Category 4: symptom_plus_medicine_match (20 cases)
    # -------------------------------------------------------------
    print("Generating Category 4: symptom_plus_medicine_match (20 cases)...")
    matched_pairs: List[Tuple[Dict, Dict]] = []
    # Search for disease chunks whose disease name or key symptoms appear in drug indications
    shuffled_diseases = list(diseases)
    rng.shuffle(shuffled_diseases)

    for d_rec in shuffled_diseases:
        if len(matched_pairs) >= 20:
            break
        chunk = d_rec.get("chunk", {})
        d_name = chunk.get("disease", "").strip()
        if len(d_name) < 4:
            continue
        d_name_clean = re.sub(r"[^\w\s]", "", d_name).lower()
        # Find candidate drugs whose indications mention disease name
        pattern = re.compile(rf"\b{re.escape(d_name_clean)}\b", re.IGNORECASE)
        matching_drugs = [
            d for d in rich_drugs
            if d["id"] not in used_drug_ids
            and pattern.search(d.get("indications_and_usage", ""))
        ]
        if matching_drugs:
            chosen_drug = rng.choice(matching_drugs)
            used_drug_ids.add(chosen_drug["id"])
            matched_pairs.append((d_rec, chosen_drug))

    print(f"Found {len(matched_pairs)} disease-drug matched pairs.")
    for d_rec, drug in matched_pairs:
        chunk = d_rec.get("chunk", {})
        d_name = chunk.get("disease", "Unknown Condition")
        symptoms = chunk.get("symptoms", ["fever", "pain"])
        raw_chunk_id = chunk.get("id", "chunk_1")
        chunk_num = re.search(r"\d+", str(raw_chunk_id))
        chunk_id = f"disease_chunk_{chunk_num.group(0)}" if chunk_num else "disease_chunk_1"

        did = f"drug_{drug['id']}"
        bname = clean_text(drug.get("brand_name", ""))
        gname = clean_text(drug.get("generic_name", ""))
        subs = [clean_text(s) for s in drug.get("substance_name", [])]
        indications = clean_text(drug.get("indications_and_usage", ""))
        strength = rng.choice(strengths)

        ocr = f"{bname} ({gname}) {strength}\nIndications: See package insert\nRx Only"
        sym_str = ", ".join(symptoms[:5])
        user_q = f"I am experiencing symptoms of {sym_str}. I found this medication at home; is it appropriate for my condition?"
        ref_text = f"{d_name} lists symptoms: {', '.join(symptoms[:8])}. {bname} ({gname}) contains {', '.join(subs)}; its label lists: {indications[:400]}"

        gen_key = (gname.lower(), tuple(sorted(s.lower() for s in subs)))
        eq_ids = [x for x in eq_map.get(gen_key, []) if x != did]

        cases.append({
            "case_id": f"E2E-{case_counter:03d}",
            "category": "symptom_plus_medicine_match",
            "user_text": user_q,
            "ocr_text": ocr,
            "reference": ref_text,
            "reference_context_ids": [chunk_id, did],
            "equivalent_ids": eq_ids,
            "expected_behavior": "answer",
            "reference_status": "auto_from_source",
        })
        case_counter += 1

    # -------------------------------------------------------------
    # Category 5: symptom_plus_medicine_mismatch (15 cases)
    # -------------------------------------------------------------
    print("Generating Category 5: symptom_plus_medicine_mismatch (15 cases)...")
    mismatched_pairs: List[Tuple[Dict, Dict]] = []
    shuffled_diseases = list(diseases)
    rng.shuffle(shuffled_diseases)

    for d_rec in shuffled_diseases:
        if len(mismatched_pairs) >= 15:
            break
        chunk = d_rec.get("chunk", {})
        d_name = chunk.get("disease", "")
        symptoms = chunk.get("symptoms", [])
        disease_words = set(re.findall(r"\b[a-zA-Z]{4,}\b", (d_name + " " + " ".join(symptoms)).lower()))
        
        # Pick candidate drugs that share NO words with disease/symptoms
        for drug in rich_drugs:
            if drug["id"] in used_drug_ids:
                continue
            ind_words = set(re.findall(r"\b[a-zA-Z]{4,}\b", drug.get("indications_and_usage", "").lower()))
            overlap = disease_words.intersection(ind_words)
            if not overlap:
                used_drug_ids.add(drug["id"])
                mismatched_pairs.append((d_rec, drug))
                break

    print(f"Found {len(mismatched_pairs)} disease-drug mismatched pairs.")
    for d_rec, drug in mismatched_pairs:
        chunk = d_rec.get("chunk", {})
        d_name = chunk.get("disease", "Unknown Condition")
        symptoms = chunk.get("symptoms", ["cough", "headache"])
        raw_chunk_id = chunk.get("id", "chunk_1")
        chunk_num = re.search(r"\d+", str(raw_chunk_id))
        chunk_id = f"disease_chunk_{chunk_num.group(0)}" if chunk_num else "disease_chunk_1"

        did = f"drug_{drug['id']}"
        bname = clean_text(drug.get("brand_name", ""))
        gname = clean_text(drug.get("generic_name", ""))
        subs = [clean_text(s) for s in drug.get("substance_name", [])]
        indications = clean_text(drug.get("indications_and_usage", ""))
        strength = rng.choice(strengths)

        ocr = f"{bname} ({gname}) {strength}\nRx Only\nDistributed by Apex Care"
        sym_str = ", ".join(symptoms[:4])
        user_q = f"I have {sym_str}. Can I take this medicine to treat my symptoms?"
        ref_text = (
            f"Patient presents symptoms associated with {d_name}: {', '.join(symptoms[:8])}. "
            f"Scanned medicine {bname} ({gname}) contains {', '.join(subs)}; its label lists indications: {indications[:400]}, "
            f"which do not correspond to the patient's symptoms."
        )

        gen_key = (gname.lower(), tuple(sorted(s.lower() for s in subs)))
        eq_ids = [x for x in eq_map.get(gen_key, []) if x != did]

        cases.append({
            "case_id": f"E2E-{case_counter:03d}",
            "category": "symptom_plus_medicine_mismatch",
            "user_text": user_q,
            "ocr_text": ocr,
            "reference": ref_text,
            "reference_context_ids": [chunk_id, did],
            "equivalent_ids": eq_ids,
            "expected_behavior": "answer",
            "reference_status": "auto_from_source",
            "heuristic": True,
        })
        case_counter += 1

    # -------------------------------------------------------------
    # Category 6: unanswerable (10 cases)
    # -------------------------------------------------------------
    print("Generating Category 6: unanswerable (10 cases)...")
    unanswerable_defs = [
        # 5 benchmark insufficient_evidence cases
        {
            "user": "What is the recommended dosage and administration schedule for NonexistentDrugZ 500mg tablets?",
            "ocr": "NonexistentDrugZ 500mg Tablets\nRx Only\nBatch: 00921",
            "name": "NonexistentDrugZ",
        },
        {
            "user": "What is the clinical treatment protocol and first-line therapy for acute Martian respiratory syndrome?",
            "ocr": "",
            "name": "acute Martian respiratory syndrome",
        },
        {
            "user": "Does taking Lipitor cure acute viral Covid-19 infection according to verified clinical evidence?",
            "ocr": "Lipitor 20mg Tablets\natorvastatin calcium\nPfizer Inc.",
            "name": "Lipitor for Covid-19 cure",
        },
        {
            "user": "What is the official FDA pediatric approval date for Xanthroflurane inhalation?",
            "ocr": "Xanthroflurane Inhalation Solution\nRx Only",
            "name": "Xanthroflurane",
        },
        {
            "user": "What is the recommended clinical dosage of chocolate syrup for treating acute appendicitis?",
            "ocr": "",
            "name": "chocolate syrup for appendicitis",
        },
        # 5 synthetic fictitious drug queries
        {
            "user": "What is the therapeutic indication and maximum daily dose for Zephyroflam 250mg?",
            "ocr": "Zephyroflam 250mg\nZephyropharm Laboratories\nLot: ZP-902",
            "name": "Zephyroflam",
        },
        {
            "user": "Can I take Novaproxin capsules for severe chronic osteoarthritis pain?",
            "ocr": "Novaproxin 100mg\nRx Only\nNovapharma Inc",
            "name": "Novaproxin",
        },
        {
            "user": "What are the common adverse reactions and contraindications of Corvastatine 40mg?",
            "ocr": "Corvastatine 40mg\nCardioPharm Global\nExp: 10/28",
            "name": "Corvastatine",
        },
        {
            "user": "Is Valerionex oral suspension safe for use during pregnancy or lactation?",
            "ocr": "Valerionex Oral Suspension 15mg/5mL\nPediatric & Adult Formulation",
            "name": "Valerionex",
        },
        {
            "user": "What is the pediatric weight-based dosing for Glycozempra 5mg/mL solution?",
            "ocr": "Glycozempra 5mg/mL\nEndoHealth Corp\nRx Only",
            "name": "Glycozempra",
        },
    ]

    for item in unanswerable_defs:
        ref_text = (
            f"Unable to provide clinical indications, dosage, or therapeutic guidance for '{item['name']}' "
            f"because no valid supporting evidence or approved regulatory record exists in the verified database. "
            f"Patients should abstain from unverified substances and consult a licensed healthcare professional."
        )
        cases.append({
            "case_id": f"E2E-{case_counter:03d}",
            "category": "unanswerable",
            "user_text": item["user"],
            "ocr_text": item["ocr"],
            "reference": ref_text,
            "reference_context_ids": [],
            "equivalent_ids": [],
            "expected_behavior": "abstain",
            "reference_status": "auto_from_source",
        })
        case_counter += 1

    # -------------------------------------------------------------
    # Category 7: emergency (10 cases)
    # -------------------------------------------------------------
    print("Generating Category 7: emergency (10 cases)...")
    emergency_defs = [
        "Severe crushing retrosternal chest pain radiating to left arm and jaw, profuse diaphoresis, shortness of breath and dizziness for the last 20 minutes.",
        "My husband suddenly cannot breathe, throat is swelling up rapidly after eating peanuts, lips turning blue.",
        "Sudden weakness and paralysis on the right side of face and arm with slurred speech when trying to talk.",
        "Gasping for air with severe chest tightness and cyanosis, rescue inhaler is completely ineffective.",
        "Massive uncontrolled arterial bleeding from a deep laceration on the upper thigh pulsing with every heartbeat.",
        "Crushing pressure in the center of the chest like an elephant sitting on me, cold clammy skin, impending doom.",
        "Sudden catastrophic thunderclap headache, worst headache of my life, with stiff neck, light sensitivity, and projectile vomiting.",
        "Patient collapsed on the floor, unresponsive and unconscious with shallow gasping respirations.",
        "Severe acute anaphylaxis with rapid facial and laryngeal edema, choking sensation, and full-body urticaria.",
        "Coughing up large quantities of bright red blood with sharp sudden pleuritic chest pain and extreme shortness of breath.",
    ]

    for user_text in emergency_defs:
        ref_text = (
            "Immediate emergency medical attention required. This clinical presentation indicates an acute life-threatening "
            "emergency. Call emergency services (911 or 112) immediately."
        )
        cases.append({
            "case_id": f"E2E-{case_counter:03d}",
            "category": "emergency",
            "user_text": user_text,
            "ocr_text": "",
            "reference": ref_text,
            "reference_context_ids": [],
            "equivalent_ids": [],
            "expected_behavior": "emergency",
            "reference_status": "auto_from_source",
        })
        case_counter += 1

    # Write out JSONL
    print(f"Writing {len(cases)} cases to {DATASET_PATH}...")
    with open(DATASET_PATH, "w", encoding="utf-8") as f:
        for c in cases:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

    # Compute statistics
    category_counts = defaultdict(int)
    expected_behavior_counts = defaultdict(int)
    user_lens = []
    ocr_lens = []
    ref_lens = []

    for c in cases:
        category_counts[c["category"]] += 1
        expected_behavior_counts[c["expected_behavior"]] += 1
        user_lens.append(len(c["user_text"]))
        ocr_lens.append(len(c["ocr_text"]))
        ref_lens.append(len(c["reference"]))

    stats = {
        "total_cases": len(cases),
        "ragas_cases": len([c for c in cases if c["category"] != "emergency"]),
        "emergency_cases": len([c for c in cases if c["category"] == "emergency"]),
        "category_counts": dict(category_counts),
        "expected_behavior_counts": dict(expected_behavior_counts),
        "user_text_char_stats": {
            "min": min(user_lens),
            "mean": round(sum(user_lens) / len(user_lens), 1),
            "max": max(user_lens),
        },
        "ocr_text_char_stats": {
            "min": min(ocr_lens),
            "mean": round(sum(ocr_lens) / len(ocr_lens), 1),
            "max": max(ocr_lens),
        },
        "reference_char_stats": {
            "min": min(ref_lens),
            "mean": round(sum(ref_lens) / len(ref_lens), 1),
            "max": max(ref_lens),
        },
        "random_seed": SEED,
    }

    with open(STATS_PATH, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)
    print(f"Wrote dataset statistics to {STATS_PATH}.")

    # Write README
    readme_content = f"""# MediScanAI End-to-End Evaluation Dataset (v1)

## Overview
This dataset contains {len(cases)} deterministic test cases designed for end-to-end evaluation of the MediScanAI RAG pipeline:
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
4. **Offline Sampling**: Cases are sampled with deterministic seed {SEED} from `data/diseases_faiss_data.jsonl` and `data/drugs_faiss_data.jsonl`.
"""
    with open(README_PATH, "w", encoding="utf-8") as f:
        f.write(readme_content)
    print(f"Wrote README to {README_PATH}.")


if __name__ == "__main__":
    generate_dataset()
