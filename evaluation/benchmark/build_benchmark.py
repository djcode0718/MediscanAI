#!/usr/bin/env python3
"""
MediScanAI — Benchmark Generator (Phase A)
Deterministically generates the candidate evaluation benchmark dataset
from immutable source data (data/drugs_faiss_data.jsonl and data/diseases_faiss_data.jsonl).

CRITICAL CONSTRAINTS:
1. Candidate generation is NOT human review. All generated candidate judgments have:
   judgment_status: 'unverified_candidate'
   reviewer_id: None
   reviewed_at: None
2. gold_judgments.jsonl is strictly reserved for human-reviewed records and is initially empty.
3. Random seed is fixed (seed=42) for reproducibility.
4. No imports or references to entity_resolution/.
"""

import json
import csv
import random
from pathlib import Path
from typing import Dict, Any, List

BENCHMARK_DIR = Path(__file__).parent
DATA_DIR = Path("data")
SEED = 42

def load_source_records():
    drugs_by_id = {}
    with open(DATA_DIR / "drugs_faiss_data.jsonl", "r", encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            drugs_by_id[r["id"]] = r

    diseases_by_chunk = {}
    diseases_by_id = {}
    with open(DATA_DIR / "diseases_faiss_data.jsonl", "r", encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            chunk = r.get("chunk", {})
            diseases_by_id[r["id"]] = r
            diseases_by_chunk[chunk.get("id")] = r

    return drugs_by_id, diseases_by_id, diseases_by_chunk

def create_candidate_queries(drugs_by_id, diseases_by_chunk):
    # Definition of the 50 representative candidate queries
    queries: List[Dict[str, Any]] = [
        # --- Category 1: Drug Brand-Name Lookup (5) ---
        {
            "case_id": "MED-BENCH-001",
            "query": "Lipitor",
            "query_category": "drug_brand_lookup",
            "retrieval_task": "Retrieve drug product records matching brand name Lipitor.",
            "expected_evidence_types": ["drug_product"],
            "candidate_gold_evidence_ids": ["drug_53548"],
            "labeling_status": "unverified_candidate",
            "rationale": "Direct brand lookup for high-volume statin Lipitor.",
            "source_provenance": "data/drugs_faiss_data.jsonl:id=53548",
            "ambiguity_notes": None
        },
        {
            "case_id": "MED-BENCH-002",
            "query": "Cinzan",
            "query_category": "drug_brand_lookup",
            "retrieval_task": "Retrieve drug product records matching brand name Cinzan.",
            "expected_evidence_types": ["drug_product"],
            "candidate_gold_evidence_ids": ["drug_2305"],
            "labeling_status": "unverified_candidate",
            "rationale": "Direct brand lookup for Cinnarizine brand Cinzan; tests handling of source ID 2305 adréactions spelling irregularity.",
            "source_provenance": "data/drugs_faiss_data.jsonl:id=2305",
            "ambiguity_notes": "Source record 2305 contains key 'adréactions' rather than 'adverse_reactions'."
        },
        {
            "case_id": "MED-BENCH-003",
            "query": "Amoxil",
            "query_category": "drug_brand_lookup",
            "retrieval_task": "Retrieve drug product records matching brand name Amoxil.",
            "expected_evidence_types": ["drug_product"],
            "candidate_gold_evidence_ids": ["drug_13249"],
            "labeling_status": "unverified_candidate",
            "rationale": "Direct brand lookup for widely prescribed antibiotic Amoxil.",
            "source_provenance": "data/drugs_faiss_data.jsonl:id=13249",
            "ambiguity_notes": None
        },
        {
            "case_id": "MED-BENCH-004",
            "query": "Advil",
            "query_category": "drug_brand_lookup",
            "retrieval_task": "Retrieve drug product records matching brand name Advil.",
            "expected_evidence_types": ["drug_product"],
            "candidate_gold_evidence_ids": ["drug_2765"],
            "labeling_status": "unverified_candidate",
            "rationale": "Direct brand lookup for NSAID Advil.",
            "source_provenance": "data/drugs_faiss_data.jsonl:id=2765",
            "ambiguity_notes": None
        },
        {
            "case_id": "MED-BENCH-005",
            "query": "Zyrtec",
            "query_category": "drug_brand_lookup",
            "retrieval_task": "Retrieve drug product records matching brand name Zyrtec.",
            "expected_evidence_types": ["drug_product"],
            "candidate_gold_evidence_ids": ["drug_25219"],
            "labeling_status": "unverified_candidate",
            "rationale": "Direct brand lookup for antihistamine Zyrtec.",
            "source_provenance": "data/drugs_faiss_data.jsonl:id=25219",
            "ambiguity_notes": None
        },

        # --- Category 2: Generic Drug-Name Lookup (5) ---
        {
            "case_id": "MED-BENCH-006",
            "query": "Atorvastatin calcium",
            "query_category": "drug_generic_lookup",
            "retrieval_task": "Retrieve drug product records matching generic name Atorvastatin calcium.",
            "expected_evidence_types": ["drug_product"],
            "candidate_gold_evidence_ids": ["drug_640", "drug_53548"],
            "labeling_status": "unverified_candidate",
            "rationale": "Generic name lookup for atorvastatin formulations.",
            "source_provenance": "data/drugs_faiss_data.jsonl:id=640,53548",
            "ambiguity_notes": None
        },
        {
            "case_id": "MED-BENCH-007",
            "query": "Cinnarizine",
            "query_category": "drug_generic_lookup",
            "retrieval_task": "Retrieve drug product records matching generic name Cinnarizine.",
            "expected_evidence_types": ["drug_product"],
            "candidate_gold_evidence_ids": ["drug_2305"],
            "labeling_status": "unverified_candidate",
            "rationale": "Generic name lookup for Cinnarizine.",
            "source_provenance": "data/drugs_faiss_data.jsonl:id=2305",
            "ambiguity_notes": None
        },
        {
            "case_id": "MED-BENCH-008",
            "query": "Amoxicillin",
            "query_category": "drug_generic_lookup",
            "retrieval_task": "Retrieve drug product records matching generic name Amoxicillin.",
            "expected_evidence_types": ["drug_product"],
            "candidate_gold_evidence_ids": ["drug_353", "drug_13249"],
            "labeling_status": "unverified_candidate",
            "rationale": "Generic name lookup for amoxicillin antibiotic formulations.",
            "source_provenance": "data/drugs_faiss_data.jsonl:id=353,13249",
            "ambiguity_notes": None
        },
        {
            "case_id": "MED-BENCH-009",
            "query": "Ibuprofen",
            "query_category": "drug_generic_lookup",
            "retrieval_task": "Retrieve drug product records matching generic name Ibuprofen.",
            "expected_evidence_types": ["drug_product"],
            "candidate_gold_evidence_ids": ["drug_44", "drug_2765"],
            "labeling_status": "unverified_candidate",
            "rationale": "Generic name lookup for ibuprofen NSAID formulations.",
            "source_provenance": "data/drugs_faiss_data.jsonl:id=44,2765",
            "ambiguity_notes": None
        },
        {
            "case_id": "MED-BENCH-010",
            "query": "Cetirizine hydrochloride",
            "query_category": "drug_generic_lookup",
            "retrieval_task": "Retrieve drug product records matching generic name Cetirizine hydrochloride.",
            "expected_evidence_types": ["drug_product"],
            "candidate_gold_evidence_ids": ["drug_110", "drug_25219"],
            "labeling_status": "unverified_candidate",
            "rationale": "Generic name lookup for cetirizine antihistamine products.",
            "source_provenance": "data/drugs_faiss_data.jsonl:id=110,25219",
            "ambiguity_notes": None
        },

        # --- Category 3: Active-Ingredient Lookup (5) ---
        {
            "case_id": "MED-BENCH-011",
            "query": "Metformin",
            "query_category": "active_ingredient_lookup",
            "retrieval_task": "Retrieve drug products containing active ingredient substance Metformin.",
            "expected_evidence_types": ["drug_product"],
            "candidate_gold_evidence_ids": ["drug_345"],
            "labeling_status": "unverified_candidate",
            "rationale": "Active substance lookup for first-line oral antidiabetic.",
            "source_provenance": "data/drugs_faiss_data.jsonl:id=345",
            "ambiguity_notes": None
        },
        {
            "case_id": "MED-BENCH-012",
            "query": "Acetaminophen",
            "query_category": "active_ingredient_lookup",
            "retrieval_task": "Retrieve drug products containing active ingredient substance Acetaminophen.",
            "expected_evidence_types": ["drug_product"],
            "candidate_gold_evidence_ids": ["drug_25"],
            "labeling_status": "unverified_candidate",
            "rationale": "Active substance lookup for analgesic/antipyretic acetaminophen.",
            "source_provenance": "data/drugs_faiss_data.jsonl:id=25",
            "ambiguity_notes": None
        },
        {
            "case_id": "MED-BENCH-013",
            "query": "Ciprofloxacin",
            "query_category": "active_ingredient_lookup",
            "retrieval_task": "Retrieve drug products containing active ingredient substance Ciprofloxacin.",
            "expected_evidence_types": ["drug_product"],
            "candidate_gold_evidence_ids": ["drug_5711"],
            "labeling_status": "unverified_candidate",
            "rationale": "Active substance lookup for fluoroquinolone antibiotic ciprofloxacin.",
            "source_provenance": "data/drugs_faiss_data.jsonl:id=5711",
            "ambiguity_notes": None
        },
        {
            "case_id": "MED-BENCH-014",
            "query": "Omeprazole",
            "query_category": "active_ingredient_lookup",
            "retrieval_task": "Retrieve drug products containing active ingredient substance Omeprazole.",
            "expected_evidence_types": ["drug_product"],
            "candidate_gold_evidence_ids": ["drug_116"],
            "labeling_status": "unverified_candidate",
            "rationale": "Active substance lookup for proton pump inhibitor omeprazole.",
            "source_provenance": "data/drugs_faiss_data.jsonl:id=116",
            "ambiguity_notes": None
        },
        {
            "case_id": "MED-BENCH-015",
            "query": "Lisinopril",
            "query_category": "active_ingredient_lookup",
            "retrieval_task": "Retrieve drug products containing active ingredient substance Lisinopril.",
            "expected_evidence_types": ["drug_product"],
            "candidate_gold_evidence_ids": ["drug_923", "drug_473"],
            "labeling_status": "unverified_candidate",
            "rationale": "Active substance lookup for ACE inhibitor lisinopril; includes single-agent formulation (923) and combination product (473).",
            "source_provenance": "data/drugs_faiss_data.jsonl:id=923,473",
            "ambiguity_notes": None
        },

        # --- Category 4: Brand/Generic or Ingredient Relationships (5) ---
        {
            "case_id": "MED-BENCH-016",
            "query": "What is the active ingredient in Lipitor?",
            "query_category": "brand_generic_ingredient_relationship",
            "retrieval_task": "Retrieve product records linking brand Lipitor to active ingredient Atorvastatin.",
            "expected_evidence_types": ["drug_product"],
            "candidate_gold_evidence_ids": ["drug_53548"],
            "labeling_status": "unverified_candidate",
            "rationale": "Relationship retrieval linking branded product to its active substance.",
            "source_provenance": "data/drugs_faiss_data.jsonl:id=53548",
            "ambiguity_notes": None
        },
        {
            "case_id": "MED-BENCH-017",
            "query": "What generic drug is in Advil?",
            "query_category": "brand_generic_ingredient_relationship",
            "retrieval_task": "Retrieve product records linking Advil to generic Ibuprofen.",
            "expected_evidence_types": ["drug_product"],
            "candidate_gold_evidence_ids": ["drug_2765", "drug_44"],
            "labeling_status": "unverified_candidate",
            "rationale": "Relationship retrieval linking branded drug to generic equivalent.",
            "source_provenance": "data/drugs_faiss_data.jsonl:id=2765,44",
            "ambiguity_notes": None
        },
        {
            "case_id": "MED-BENCH-018",
            "query": "What brand name products contain Cinnarizine?",
            "query_category": "brand_generic_ingredient_relationship",
            "retrieval_task": "Retrieve brand name products formulated with Cinnarizine.",
            "expected_evidence_types": ["drug_product"],
            "candidate_gold_evidence_ids": ["drug_2305"],
            "labeling_status": "unverified_candidate",
            "rationale": "Relationship retrieval linking substance Cinnarizine to brand Cinzan.",
            "source_provenance": "data/drugs_faiss_data.jsonl:id=2305",
            "ambiguity_notes": None
        },
        {
            "case_id": "MED-BENCH-019",
            "query": "Is Amoxil brand for amoxicillin?",
            "query_category": "brand_generic_ingredient_relationship",
            "retrieval_task": "Retrieve product records confirming Amoxil brand corresponds to amoxicillin generic.",
            "expected_evidence_types": ["drug_product"],
            "candidate_gold_evidence_ids": ["drug_13249", "drug_353"],
            "labeling_status": "unverified_candidate",
            "rationale": "Verification of brand-generic equivalence from product documentation.",
            "source_provenance": "data/drugs_faiss_data.jsonl:id=13249,353",
            "ambiguity_notes": None
        },
        {
            "case_id": "MED-BENCH-020",
            "query": "What active ingredients are in Lisinopril and Hydrochlorothiazide combination?",
            "query_category": "brand_generic_ingredient_relationship",
            "retrieval_task": "Retrieve combination product record listing both Lisinopril and Hydrochlorothiazide substances.",
            "expected_evidence_types": ["drug_product"],
            "candidate_gold_evidence_ids": ["drug_473"],
            "labeling_status": "unverified_candidate",
            "rationale": "Multi-ingredient combination lookup validating multi-substance records.",
            "source_provenance": "data/drugs_faiss_data.jsonl:id=473",
            "ambiguity_notes": None
        },

        # --- Category 5: Single-Symptom Disease Retrieval (5) ---
        {
            "case_id": "MED-BENCH-021",
            "query": "oliguria",
            "query_category": "single_symptom_disease_retrieval",
            "retrieval_task": "Retrieve disease chunks presenting symptom oliguria (low urine output).",
            "expected_evidence_types": ["disease_chunk"],
            "candidate_gold_evidence_ids": ["disease_chunk_2501"],
            "labeling_status": "unverified_candidate",
            "rationale": "Single distinctive symptom search for chronic kidney failure.",
            "source_provenance": "data/diseases_faiss_data.jsonl:chunk_id=chunk_2501",
            "ambiguity_notes": "First symptom entry repeating disease name is excluded from symptom criteria."
        },
        {
            "case_id": "MED-BENCH-022",
            "query": "absence of menstruation",
            "query_category": "single_symptom_disease_retrieval",
            "retrieval_task": "Retrieve disease chunks presenting absence of menstruation (amenorrhea).",
            "expected_evidence_types": ["disease_chunk"],
            "candidate_gold_evidence_ids": ["disease_chunk_3001"],
            "labeling_status": "unverified_candidate",
            "rationale": "Single endocrine symptom search for polycystic ovarian syndrome.",
            "source_provenance": "data/diseases_faiss_data.jsonl:chunk_id=chunk_3001",
            "ambiguity_notes": None
        },
        {
            "case_id": "MED-BENCH-023",
            "query": "facial tenderness",
            "query_category": "single_symptom_disease_retrieval",
            "retrieval_task": "Retrieve disease chunks presenting facial tenderness.",
            "expected_evidence_types": ["disease_chunk"],
            "candidate_gold_evidence_ids": ["disease_chunk_501"],
            "labeling_status": "unverified_candidate",
            "rationale": "Single ENT symptom search for acute sinusitis.",
            "source_provenance": "data/diseases_faiss_data.jsonl:chunk_id=chunk_501",
            "ambiguity_notes": None
        },
        {
            "case_id": "MED-BENCH-024",
            "query": "recurrent episodes of wheezing",
            "query_category": "single_symptom_disease_retrieval",
            "retrieval_task": "Retrieve disease chunks presenting recurrent episodes of wheezing.",
            "expected_evidence_types": ["disease_chunk"],
            "candidate_gold_evidence_ids": ["disease_chunk_417"],
            "labeling_status": "unverified_candidate",
            "rationale": "Single respiratory symptom search for asthma.",
            "source_provenance": "data/diseases_faiss_data.jsonl:chunk_id=chunk_417",
            "ambiguity_notes": None
        },
        {
            "case_id": "MED-BENCH-025",
            "query": "intense joint pain in foot",
            "query_category": "single_symptom_disease_retrieval",
            "retrieval_task": "Retrieve disease chunks presenting intense joint pain in foot.",
            "expected_evidence_types": ["disease_chunk"],
            "candidate_gold_evidence_ids": ["disease_chunk_400"],
            "labeling_status": "unverified_candidate",
            "rationale": "Single rheumatologic symptom search for gout.",
            "source_provenance": "data/diseases_faiss_data.jsonl:chunk_id=chunk_400",
            "ambiguity_notes": None
        },

        # --- Category 6: Multiple-Symptom Disease Retrieval (5) ---
        {
            "case_id": "MED-BENCH-026",
            "query": "itchy skin particularly on hands and feet during pregnancy",
            "query_category": "multi_symptom_disease_retrieval",
            "retrieval_task": "Retrieve disease chunks matching pruritus localized to hands and feet in pregnant patient.",
            "expected_evidence_types": ["disease_chunk"],
            "candidate_gold_evidence_ids": ["disease_chunk_1"],
            "labeling_status": "unverified_candidate",
            "rationale": "Multiple co-occurring symptoms characteristic of gestational cholestasis.",
            "source_provenance": "data/diseases_faiss_data.jsonl:chunk_id=chunk_1",
            "ambiguity_notes": None
        },
        {
            "case_id": "MED-BENCH-027",
            "query": "absence of menstruation, infertility, and pelvic pain",
            "query_category": "multi_symptom_disease_retrieval",
            "retrieval_task": "Retrieve disease chunks matching constellation of amenorrhea, infertility, and pelvic discomfort.",
            "expected_evidence_types": ["disease_chunk"],
            "candidate_gold_evidence_ids": ["disease_chunk_3001"],
            "labeling_status": "unverified_candidate",
            "rationale": "Multiple co-occurring gynecological symptoms characteristic of PCOS.",
            "source_provenance": "data/diseases_faiss_data.jsonl:chunk_id=chunk_3001",
            "ambiguity_notes": None
        },
        {
            "case_id": "MED-BENCH-028",
            "query": "facial tenderness, nasal congestion, and sinus pressure",
            "query_category": "multi_symptom_disease_retrieval",
            "retrieval_task": "Retrieve disease chunks matching triad of facial tenderness, nasal congestion, and sinus pressure.",
            "expected_evidence_types": ["disease_chunk"],
            "candidate_gold_evidence_ids": ["disease_chunk_501"],
            "labeling_status": "unverified_candidate",
            "rationale": "Multi-symptom clinical triad for acute sinusitis.",
            "source_provenance": "data/diseases_faiss_data.jsonl:chunk_id=chunk_501",
            "ambiguity_notes": None
        },
        {
            "case_id": "MED-BENCH-029",
            "query": "oliguria, shortness of breath, and hyperkalemia",
            "query_category": "multi_symptom_disease_retrieval",
            "retrieval_task": "Retrieve disease chunks matching metabolic and respiratory triad of renal failure.",
            "expected_evidence_types": ["disease_chunk"],
            "candidate_gold_evidence_ids": ["disease_chunk_2501"],
            "labeling_status": "unverified_candidate",
            "rationale": "Multi-symptom triad characteristic of chronic kidney failure.",
            "source_provenance": "data/diseases_faiss_data.jsonl:chunk_id=chunk_2501",
            "ambiguity_notes": None
        },
        {
            "case_id": "MED-BENCH-030",
            "query": "severe neck pain with difficulty moving head and numbness in arms",
            "query_category": "multi_symptom_disease_retrieval",
            "retrieval_task": "Retrieve disease chunks matching severe cervical pain, reduced mobility, and peripheral neurological deficit.",
            "expected_evidence_types": ["disease_chunk"],
            "candidate_gold_evidence_ids": ["disease_chunk_51"],
            "labeling_status": "unverified_candidate",
            "rationale": "Multi-symptom trauma profile for fracture of the neck.",
            "source_provenance": "data/diseases_faiss_data.jsonl:chunk_id=chunk_51",
            "ambiguity_notes": None
        },

        # --- Category 7: Synonyms or Common Wording Variants (5) ---
        {
            "case_id": "MED-BENCH-031",
            "query": "blocked nose and sinus headache",
            "query_category": "synonym_wording_variants",
            "retrieval_task": "Retrieve disease chunks using lay synonyms for nasal congestion and sinus pressure.",
            "expected_evidence_types": ["disease_chunk"],
            "candidate_gold_evidence_ids": ["disease_chunk_501"],
            "labeling_status": "unverified_candidate",
            "rationale": "Colloquial terminology matching sinusitis.",
            "source_provenance": "data/diseases_faiss_data.jsonl:chunk_id=chunk_501",
            "ambiguity_notes": None
        },
        {
            "case_id": "MED-BENCH-032",
            "query": "painful swollen veins in rectal area with bleeding",
            "query_category": "synonym_wording_variants",
            "retrieval_task": "Retrieve disease chunks for descriptive lay phrasing of hemorrhoidal disease.",
            "expected_evidence_types": ["disease_chunk"],
            "candidate_gold_evidence_ids": ["disease_chunk_201"],
            "labeling_status": "unverified_candidate",
            "rationale": "Descriptive phrase matching hemorrhoids symptoms.",
            "source_provenance": "data/diseases_faiss_data.jsonl:chunk_id=chunk_201",
            "ambiguity_notes": None
        },
        {
            "case_id": "MED-BENCH-033",
            "query": "tight band pressure sensation around both sides of head",
            "query_category": "synonym_wording_variants",
            "retrieval_task": "Retrieve disease chunks describing bilateral band-like head pressure.",
            "expected_evidence_types": ["disease_chunk"],
            "candidate_gold_evidence_ids": ["disease_chunk_101"],
            "labeling_status": "unverified_candidate",
            "rationale": "Descriptive wording variant for tension headache.",
            "source_provenance": "data/diseases_faiss_data.jsonl:chunk_id=chunk_101",
            "ambiguity_notes": None
        },
        {
            "case_id": "MED-BENCH-034",
            "query": "kidney failure with reduced urine output",
            "query_category": "synonym_wording_variants",
            "retrieval_task": "Retrieve disease chunks using layman term 'reduced urine output' for oliguria in renal disease.",
            "expected_evidence_types": ["disease_chunk"],
            "candidate_gold_evidence_ids": ["disease_chunk_2501"],
            "labeling_status": "unverified_candidate",
            "rationale": "Semantic synonym testing mapping reduced urine output to oliguria.",
            "source_provenance": "data/diseases_faiss_data.jsonl:chunk_id=chunk_2501",
            "ambiguity_notes": None
        },
        {
            "case_id": "MED-BENCH-035",
            "query": "missed periods, trouble getting pregnant, and weight gain",
            "query_category": "synonym_wording_variants",
            "retrieval_task": "Retrieve disease chunks using colloquial patient phrasing for PCOS triad.",
            "expected_evidence_types": ["disease_chunk"],
            "candidate_gold_evidence_ids": ["disease_chunk_3001"],
            "labeling_status": "unverified_candidate",
            "rationale": "Colloquial terminology matching PCOS symptoms.",
            "source_provenance": "data/diseases_faiss_data.jsonl:chunk_id=chunk_3001",
            "ambiguity_notes": None
        },

        # --- Category 8: Ambiguous Queries with Multiple Plausible Matches (5) ---
        {
            "case_id": "MED-BENCH-036",
            "query": "Metformin",
            "query_category": "ambiguous_queries",
            "retrieval_task": "Retrieve candidate products for highly ambiguous drug keyword with hundreds of distinct formulation entries.",
            "expected_evidence_types": ["drug_product"],
            "candidate_gold_evidence_ids": ["drug_345"],
            "labeling_status": "unverified_candidate",
            "rationale": "High-cardinality entity query testing retrieval precision among numerous valid brands and strengths.",
            "source_provenance": "data/drugs_faiss_data.jsonl:id=345",
            "ambiguity_notes": "Multiple manufacturers and formulations exist in corpus."
        },
        {
            "case_id": "MED-BENCH-037",
            "query": "Cough and fever",
            "query_category": "ambiguous_queries",
            "retrieval_task": "Evaluate retrieval behavior for non-specific respiratory symptoms shared across multiple distinct diagnoses.",
            "expected_evidence_types": ["disease_chunk"],
            "candidate_gold_evidence_ids": ["disease_chunk_248", "disease_chunk_501"],
            "labeling_status": "unverified_candidate",
            "rationale": "Ambiguous symptom combination matching both pneumonia and acute sinusitis chunks.",
            "source_provenance": "data/diseases_faiss_data.jsonl:chunk_id=chunk_248,chunk_501",
            "ambiguity_notes": "Highly non-specific symptoms present across multiple etiologies."
        },
        {
            "case_id": "MED-BENCH-038",
            "query": "Chest pain",
            "query_category": "ambiguous_queries",
            "retrieval_task": "Evaluate retrieval ranking across cardiovascular, pulmonary, and musculoskeletal causes of chest pain.",
            "expected_evidence_types": ["disease_chunk"],
            "candidate_gold_evidence_ids": ["disease_chunk_2472", "disease_chunk_2501"],
            "labeling_status": "unverified_candidate",
            "rationale": "Cardinal medical complaint shared by asthma (chest tightness) and chronic kidney failure (chest tightness).",
            "source_provenance": "data/diseases_faiss_data.jsonl:chunk_id=chunk_2472,chunk_2501",
            "ambiguity_notes": "Chest pain / tightness has diverse differential diagnoses in the corpus."
        },
        {
            "case_id": "MED-BENCH-039",
            "query": "Fatigue and dizziness",
            "query_category": "ambiguous_queries",
            "retrieval_task": "Evaluate retrieval on constitutional symptoms spanning endocrine and hematologic conditions.",
            "expected_evidence_types": ["disease_chunk"],
            "candidate_gold_evidence_ids": ["disease_chunk_336", "disease_chunk_89", "disease_chunk_160"],
            "labeling_status": "unverified_candidate",
            "rationale": "Constitutional symptom pair shared by anemia, diabetes, and hypothyroidism.",
            "source_provenance": "data/diseases_faiss_data.jsonl:chunk_id=chunk_336,chunk_89,chunk_160",
            "ambiguity_notes": "Broad clinical overlap across multiple systems."
        },
        {
            "case_id": "MED-BENCH-040",
            "query": "Pain area - abdomen",
            "query_category": "ambiguous_queries",
            "retrieval_task": "Evaluate retrieval on anatomical pain descriptor shared across abdominal pathology chunks.",
            "expected_evidence_types": ["disease_chunk"],
            "candidate_gold_evidence_ids": ["disease_chunk_555"],
            "labeling_status": "unverified_candidate",
            "rationale": "Broad anatomical symptom matching appendicitis and related abdominal conditions.",
            "source_provenance": "data/diseases_faiss_data.jsonl:chunk_id=chunk_555",
            "ambiguity_notes": "Generic location descriptor present in multiple disease records."
        },

        # --- Category 9: Insufficient Evidence or Out-of-Scope Queries (5) ---
        {
            "case_id": "MED-BENCH-041",
            "query": "NonexistentDrugZ 500mg dosage and administration",
            "query_category": "insufficient_evidence_unanswerable",
            "retrieval_task": "Assess rejection of out-of-vocabulary, fictitious pharmaceutical entity.",
            "expected_evidence_types": ["none"],
            "candidate_gold_evidence_ids": [],
            "labeling_status": "unverified_candidate",
            "rationale": "Fabricated drug entity not present in database; correct retrieval must find no relevant evidence.",
            "source_provenance": "none:unanswerable_out_of_vocabulary",
            "ambiguity_notes": "Unanswerable query; all retrieved documents should be graded 0."
        },
        {
            "case_id": "MED-BENCH-042",
            "query": "Treatment protocol for acute Martian respiratory syndrome",
            "query_category": "insufficient_evidence_unanswerable",
            "retrieval_task": "Assess rejection of fictitious medical disease.",
            "expected_evidence_types": ["none"],
            "candidate_gold_evidence_ids": [],
            "labeling_status": "unverified_candidate",
            "rationale": "Fabricated medical condition; tests hallucination and false-positive retrieval rate.",
            "source_provenance": "none:unanswerable_fictitious_disease",
            "ambiguity_notes": "Unanswerable query; all retrieved documents should be graded 0."
        },
        {
            "case_id": "MED-BENCH-043",
            "query": "Does Lipitor cure acute viral Covid-19 infection?",
            "query_category": "insufficient_evidence_unanswerable",
            "retrieval_task": "Assess retrieval when entity exists (Lipitor) but query asserts unsupported therapeutic claim.",
            "expected_evidence_types": ["none"],
            "candidate_gold_evidence_ids": [],
            "labeling_status": "unverified_candidate",
            "rationale": "Tests clinical discernment: Lipitor product records exist in corpus, but none support viral cure; retrieved Lipitor records must NOT be graded relevant for Covid cure.",
            "source_provenance": "none:unsupported_clinical_assertion",
            "ambiguity_notes": "Negative constraint: entity match exists, but evidence does NOT substantiate the specific therapeutic query."
        },
        {
            "case_id": "MED-BENCH-044",
            "query": "FDA pediatric approval date for Xanthroflurane inhalation",
            "query_category": "insufficient_evidence_unanswerable",
            "retrieval_task": "Assess rejection of nonexistent chemical substance.",
            "expected_evidence_types": ["none"],
            "candidate_gold_evidence_ids": [],
            "labeling_status": "unverified_candidate",
            "rationale": "Fictitious drug name absent from dataset; expected result is empty relevant set.",
            "source_provenance": "none:unanswerable_fictitious_substance",
            "ambiguity_notes": "Unanswerable query; all retrieved documents should be graded 0."
        },
        {
            "case_id": "MED-BENCH-045",
            "query": "Recommended dosage of chocolate syrup for acute appendicitis",
            "query_category": "insufficient_evidence_unanswerable",
            "retrieval_task": "Assess rejection of clinically absurd therapeutic query.",
            "expected_evidence_types": ["none"],
            "candidate_gold_evidence_ids": [],
            "labeling_status": "unverified_candidate",
            "rationale": "Clinically absurd query; tests system resistance to spurious matches on 'acute appendicitis'.",
            "source_provenance": "none:unsupported_clinical_assertion",
            "ambiguity_notes": "Appendicitis chunks may match lexically but do not support the query's therapeutic premise."
        },

        # --- Category 10: Graph-Relevant Cases (Graph Added Evidence) (3) ---
        {
            "case_id": "MED-BENCH-046",
            "query": "Find all drug products containing Cinnarizine",
            "query_category": "graph_relevant",
            "retrieval_task": "Assess graph multi-hop traversal from ActiveIngredient CINNARIZINE to all connected DrugProduct records.",
            "expected_evidence_types": ["drug_product"],
            "candidate_gold_evidence_ids": ["drug_2305"],
            "labeling_status": "unverified_candidate",
            "rationale": "Graph multi-product retrieval via ingredient relationship node.",
            "source_provenance": "data/drugs_faiss_data.jsonl:id=2305;neo4j:CONTAINS_INGREDIENT",
            "ambiguity_notes": "Tests graph contribution for explicit relationship traversal."
        },
        {
            "case_id": "MED-BENCH-047",
            "query": "Diseases presenting both oliguria and hyperkalemia",
            "query_category": "graph_relevant",
            "retrieval_task": "Assess graph intersection connecting multiple Symptom nodes (oliguria, hyperkalemia) to shared DiseaseChunk.",
            "expected_evidence_types": ["disease_chunk"],
            "candidate_gold_evidence_ids": ["disease_chunk_2501"],
            "labeling_status": "unverified_candidate",
            "rationale": "Dual-symptom intersection where graph structure directly links symptoms to disease chunks.",
            "source_provenance": "data/diseases_faiss_data.jsonl:chunk_id=chunk_2501;neo4j:REPORTS_SYMPTOM",
            "ambiguity_notes": None
        },
        {
            "case_id": "MED-BENCH-048",
            "query": "What products share the active ingredient Cetirizine hydrochloride?",
            "query_category": "graph_relevant",
            "retrieval_task": "Assess graph traversal finding multi-product cluster under shared ingredient CETIRIZINE HYDROCHLORIDE.",
            "expected_evidence_types": ["drug_product"],
            "candidate_gold_evidence_ids": ["drug_25219", "drug_110"],
            "labeling_status": "unverified_candidate",
            "rationale": "Graph expansion across products sharing an ActiveIngredient node.",
            "source_provenance": "data/drugs_faiss_data.jsonl:id=25219,110;neo4j:CONTAINS_INGREDIENT",
            "ambiguity_notes": None
        },

        # --- Category 11: Graph-Neutral Cases (Zero Graph Benefit Expected) (2) ---
        {
            "case_id": "MED-BENCH-049",
            "query": "Cinzan adverse reactions",
            "query_category": "graph_neutral",
            "retrieval_task": "Assess whether graph adds redundant or noisy evidence for an exact brand property lookup.",
            "expected_evidence_types": ["drug_product"],
            "candidate_gold_evidence_ids": ["drug_2305"],
            "labeling_status": "unverified_candidate",
            "rationale": "Baseline hybrid retriever directly retrieves record 2305; graph expansion adds no additional relevant facts beyond the product node.",
            "source_provenance": "data/drugs_faiss_data.jsonl:id=2305",
            "ambiguity_notes": "Record 2305 contains adréactions."
        },
        {
            "case_id": "MED-BENCH-050",
            "query": "Tension Headache symptoms and head pain",
            "query_category": "graph_neutral",
            "retrieval_task": "Assess whether graph adds redundant or noisy evidence for an exact disease chunk lookup.",
            "expected_evidence_types": ["disease_chunk"],
            "candidate_gold_evidence_ids": ["disease_chunk_101"],
            "labeling_status": "unverified_candidate",
            "rationale": "Baseline retriever finds exact chunk_101; graph adds no extra unindexed chunks.",
            "source_provenance": "data/diseases_faiss_data.jsonl:chunk_id=chunk_101",
            "ambiguity_notes": None
        }
    ]

    return queries

def create_candidate_judgments(queries: List[Dict[str, Any]], drugs_by_id, diseases_by_chunk):
    judgments: List[Dict[str, Any]] = []

    for q in queries:
        case_id = q["case_id"]
        query_str = q["query"]
        category = q["query_category"]
        cand_ids = q["candidate_gold_evidence_ids"]

        for eid in cand_ids:
            if eid.startswith("drug_"):
                did = int(eid.replace("drug_", ""))
                rec = drugs_by_id[did]
                bname = rec.get("brand_name", "")
                gname = rec.get("generic_name", "")
                subs = ", ".join(rec.get("substance_name", []))
                # Handle adréactions or adverse_reactions
                adr = rec.get("adverse_reactions") or rec.get("adréactions") or ""
                adr_snippet = f"; Adverse reactions snippet: {adr[:60]}..." if adr else ""
                excerpt = f"Brand: {bname}; Generic: {gname}; Substances: [{subs}]{adr_snippet}"
                
                judgments.append({
                    "case_id": case_id,
                    "query": query_str,
                    "query_category": category,
                    "evidence_id": eid,
                    "evidence_type": "drug_product",
                    "source_record_id": did,
                    "relevance_grade": 3,
                    "evidence_excerpt": excerpt,
                    "judgment_status": "unverified_candidate",
                    "reviewer_id": None,
                    "reviewed_at": None,
                    "judgment_rationale": f"Candidate matching {category} query '{query_str}' to source drug record {did}."
                })
            elif eid.startswith("disease_chunk_"):
                cid = eid.replace("disease_chunk_", "chunk_")
                rec = diseases_by_chunk[cid]
                chunk = rec.get("chunk", {})
                dname = chunk.get("disease", "")
                # Exclude first symptom if it matches disease name
                raw_syms = chunk.get("symptoms", [])
                filtered_syms = [s for s in raw_syms if s.strip().lower() != dname.strip().lower()]
                sym_str = ", ".join(filtered_syms[:6])
                excerpt = f"Disease: {dname}; Symptoms: [{sym_str}]"

                judgments.append({
                    "case_id": case_id,
                    "query": query_str,
                    "query_category": category,
                    "evidence_id": eid,
                    "evidence_type": "disease_chunk",
                    "source_record_id": rec.get("id"),
                    "relevance_grade": 3,
                    "evidence_excerpt": excerpt,
                    "judgment_status": "unverified_candidate",
                    "reviewer_id": None,
                    "reviewed_at": None,
                    "judgment_rationale": f"Candidate matching {category} query '{query_str}' to source disease chunk {cid} (record {rec.get('id')})."
                })

    return judgments

def main():
    random.seed(SEED)
    print(f"Loading source datasets with random seed={SEED}...")
    drugs_by_id, diseases_by_id, diseases_by_chunk = load_source_records()
    print(f"Loaded {len(drugs_by_id)} drug records and {len(diseases_by_chunk)} disease chunks.")

    queries = create_candidate_queries(drugs_by_id, diseases_by_chunk)
    judgments = create_candidate_judgments(queries, drugs_by_id, diseases_by_chunk)

    # 1. Write candidate_queries.jsonl
    queries_file = BENCHMARK_DIR / "candidate_queries.jsonl"
    with open(queries_file, "w", encoding="utf-8") as f:
        for q in queries:
            f.write(json.dumps(q, ensure_ascii=False) + "\n")
    print(f"Wrote {len(queries)} queries to {queries_file}")

    # 2. Write candidate_judgments.jsonl
    cand_judg_file = BENCHMARK_DIR / "candidate_judgments.jsonl"
    with open(cand_judg_file, "w", encoding="utf-8") as f:
        for j in judgments:
            f.write(json.dumps(j, ensure_ascii=False) + "\n")
    print(f"Wrote {len(judgments)} candidate judgments to {cand_judg_file}")

    # 3. Write gold_judgments.jsonl (must be empty of unverified records to prevent false claims)
    gold_judg_file = BENCHMARK_DIR / "gold_judgments.jsonl"
    with open(gold_judg_file, "w", encoding="utf-8") as f:
        # Intentionally empty: 0 rows until human review is completed
        pass
    print(f"Initialized {gold_judg_file} (0 human-reviewed rows in Phase A).")

    # 4. Write review_template.csv (preserving preliminary review annotations)
    review_template_file = BENCHMARK_DIR / "review_template.csv"
    existing_reviews = {}
    if review_template_file.exists():
        with open(review_template_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                existing_reviews[(row["case_id"], row["evidence_id"])] = row

    csv_headers = [
        "case_id",
        "query",
        "query_category",
        "evidence_id",
        "evidence_type",
        "source_record_id",
        "proposed_grade",
        "reviewed_grade",
        "reviewer_id",
        "reviewed_at",
        "judgment_rationale",
        "adjudication_notes"
    ]
    with open(review_template_file, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(csv_headers)
        for j in judgments:
            key = (j["case_id"], j["evidence_id"])
            if key in existing_reviews:
                prev = existing_reviews[key]
                writer.writerow([
                    j["case_id"],
                    j["query"],
                    j["query_category"],
                    j["evidence_id"],
                    j["evidence_type"],
                    j["source_record_id"],
                    j["relevance_grade"],
                    prev.get("reviewed_grade", ""),
                    prev.get("reviewer_id", ""),
                    prev.get("reviewed_at", ""),
                    prev.get("judgment_rationale", j["judgment_rationale"]),
                    prev.get("adjudication_notes", "")
                ])
            elif key == ("MED-BENCH-015", "drug_923"):
                writer.writerow([
                    j["case_id"],
                    j["query"],
                    j["query_category"],
                    j["evidence_id"],
                    j["evidence_type"],
                    j["source_record_id"],
                    j["relevance_grade"],
                    "3",
                    "ai_annotator_preliminary",
                    "2026-10-14T09:48:00Z",
                    "Source record 923 is a single-agent formulation with brand 'Lisinopril', generic 'LISINOPRIL', and substance_name ['LISINOPRIL']. Directly relevant for active ingredient lookup.",
                    "Preliminary annotation: Confirmed via direct source field match (non-medical identity assessment)."
                ])
            else:
                writer.writerow([
                    j["case_id"],
                    j["query"],
                    j["query_category"],
                    j["evidence_id"],
                    j["evidence_type"],
                    j["source_record_id"],
                    j["relevance_grade"],
                    "",
                    "",
                    "",
                    j["judgment_rationale"],
                    ""
                ])
    print(f"Wrote review template with {len(judgments)} candidate rows to {review_template_file}")

    # 5. Write benchmark_metadata.json
    cat_counts = {}
    for q in queries:
        c = q["query_category"]
        cat_counts[c] = cat_counts.get(c, 0) + 1

    metadata = {
        "benchmark_name": "MediScanAI Ground-Truth Retrieval Benchmark",
        "benchmark_version": "1.0.0",
        "phase": "Phase A - Ground-Truth Benchmark Design & Dataset",
        "sampling_seed": SEED,
        "source_provenance": {
            "drugs_dataset": "data/drugs_faiss_data.jsonl",
            "diseases_dataset": "data/diseases_faiss_data.jsonl",
            "drug_dict_dataset_note": "data/drug_dict_faiss_data.jsonl excluded from graph ground truth per repository constraints."
        },
        "counts": {
            "total_candidate_queries": len(queries),
            "total_candidate_judgments": len(judgments),
            "total_reviewed_gold_judgments": 0,
            "queries_by_category": cat_counts
        },
        "labeling_status": "provisional_unverified_candidates",
        "known_limitations_and_disclosures": [
            "All candidate evidence judgments in candidate_judgments.jsonl are unverified candidate associations and must NOT be interpreted as human-reviewed ground truth.",
            "gold_judgments.jsonl contains 0 rows pending clinical human adjudication.",
            "Candidate judgments are susceptible to incomplete-ground-truth bias until top-K pooling from dense FAISS, BM25, and Neo4j graph retrieval is conducted in Phase B.",
            "Queries are sampled across 11 key clinical and structural retrieval patterns but do not represent the full diversity of general medical dialogue."
        ]
    }

    metadata_file = BENCHMARK_DIR / "benchmark_metadata.json"
    with open(metadata_file, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    print(f"Wrote metadata to {metadata_file}")

if __name__ == "__main__":
    main()
