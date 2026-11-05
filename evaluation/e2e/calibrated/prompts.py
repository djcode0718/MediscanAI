"""Prompt definitions for MediScanAI Calibrated Evaluator (Revision 2.4)."""

# ---------------------------------------------------------------------------
# 1. B0 Frozen Baseline Prompt (Legacy RAGAS)
# ---------------------------------------------------------------------------
B0_LEGACY_SYSTEM = (
    "Your task is to judge the faithfulness of a series of statements based on a given context. "
    "For each statement you must return verdict as 1 if the statement can be directly inferred based on the context "
    "or 0 if the statement can not be directly inferred based on the context.\n\n"
    "Respond with a JSON object containing a 'statements' list where each item has:\n"
    "- 'statement': the statement text\n"
    "- 'reason': explanation\n"
    "- 'verdict': 1 or 0\n"
)

# ---------------------------------------------------------------------------
# 2. EXP-01: Structural & Reference Validation Prompt (Layer A integration)
# ---------------------------------------------------------------------------
EXP01_SYSTEM = (
    "Your task is to judge the faithfulness of a clinical statement based on retrieved evidence chunks.\n"
    "Return verdict as 1 if the statement is directly entailed by the context, or 0 if it is not.\n"
    "You must cite the supporting chunk ID ('cited_chunk_id') and a verbatim quote ('cited_quote') from that chunk.\n\n"
    "Respond in valid JSON with keys:\n"
    "- 'verdict': 1 or 0\n"
    "- 'reason': concise clinical explanation\n"
    "- 'cited_chunk_id': chunk ID (e.g. E1)\n"
    "- 'cited_quote': verbatim substring from the chunk\n"
    "- 'is_absence_statement': boolean\n"
)

# ---------------------------------------------------------------------------
# 3. EXP-02: Scoped Abstention Semantics Prompt
# ---------------------------------------------------------------------------
EXP02_SYSTEM = (
    "Your task is to judge the faithfulness of a clinical statement based on retrieved evidence chunks.\n"
    "Distinguish between evidence-scoped limitations and global nonexistence claims:\n"
    "1. Evidence-Scoped Limitation (Verdict 1): If the statement asserts that available/retrieved sources do not mention a fact "
    "(e.g. 'Available sources do not mention pediatric dosing'), and the provided chunks indeed do not mention it, verdict is 1 (Supported).\n"
    "2. Global Nonexistence Claim (Verdict 0): If the statement asserts that a medication or condition does not exist in reality "
    "(e.g. 'Drug X does not exist'), context omission does NOT prove nonexistence, so verdict is 0 (Unsupported).\n\n"
    "Respond in valid JSON with keys: 'verdict', 'reason', 'cited_chunk_id', 'cited_quote', 'is_absence_statement'."
)

# ---------------------------------------------------------------------------
# 4. EXP-03: Entity-Attribute Binding Prompt
# ---------------------------------------------------------------------------
EXP03_SYSTEM = (
    "Your task is to judge the faithfulness of a clinical statement based on retrieved evidence chunks.\n"
    "Enforce strict Entity-Attribute Binding:\n"
    "- Verify that clinical attributes (indications, active ingredients, dosages, contraindications) belong specifically to the subject entity defined in that chunk header.\n"
    "- Do not swap attributes between adjacent or co-occurring entities.\n"
    "- Example: If chunk states 'Brand: PROCRIT | Active ingredients: EPOETIN', the statement 'PROCRIT lists EPOETIN as an active ingredient' is SUPPORTED (Verdict 1).\n\n"
    "Respond in valid JSON with keys: 'verdict', 'reason', 'cited_chunk_id', 'cited_quote', 'is_absence_statement'."
)

# ---------------------------------------------------------------------------
# 5. EXP-04: Bounded Clinical & Statutory Synonymy Prompt
# ---------------------------------------------------------------------------
EXP04_SYSTEM = (
    "Your task is to judge the faithfulness of a clinical statement based on retrieved evidence chunks.\n"
    "Apply Bounded Clinical and Statutory Synonymy:\n"
    "- Standard statutory equivalents are faithful: 'Rx Only*' is equivalent to 'requires a prescription' or 'prescription-only'.\n"
    "- Lexical subsets are faithful: 'blurred or distorted vision' entails 'distorted vision'.\n"
    "- Standard pharmacopeia salts are equivalent where context establishes generic equivalence (e.g. EPOETIN and EPOETIN ALFA).\n"
    "- Prohibited substitutions: OTC is NOT equivalent to Rx; Monotherapy is NOT equivalent to Combination Therapy.\n\n"
    "Respond in valid JSON with keys: 'verdict', 'reason', 'cited_chunk_id', 'cited_quote', 'is_absence_statement'."
)

# ---------------------------------------------------------------------------
# 6. EXP-05: Multi-Chunk Evidence Synthesis Prompt
# ---------------------------------------------------------------------------
EXP05_SYSTEM = (
    "Your task is to judge the faithfulness of a clinical statement based on retrieved evidence chunks.\n"
    "Multi-Chunk Evidence Synthesis:\n"
    "- Clinical claims may be jointly supported across multiple chunks (e.g. condition defined in E1, dosage adjustment in E3).\n"
    "- If multiple chunks jointly support the assertion, cite the primary supporting chunk and explain the joint entailment in reason.\n"
    "- Check all relevant chunks to ensure the context as a whole supports the assertion without unresolved contradictions.\n\n"
    "Respond in valid JSON with keys: 'verdict', 'reason', 'cited_chunk_id', 'cited_quote', 'is_absence_statement'."
)

# ---------------------------------------------------------------------------
# 7. EXP-06: Atomic Proposition Decomposition Prompt
# ---------------------------------------------------------------------------
EXP06_SYSTEM = (
    "Your task is to evaluate an atomic proposition derived from a clinical statement against retrieved evidence chunks.\n"
    "Evaluate this single atomic proposition strictly on its own merits.\n"
    "Verdict 1 = Supported by context; Verdict 0 = Unsupported by context.\n\n"
    "Respond in valid JSON with keys: 'verdict', 'reason', 'cited_chunk_id', 'cited_quote', 'is_absence_statement'."
)

# ---------------------------------------------------------------------------
# 8. EXP-07: Dual-Layer Absence & Token Scan Prompt
# ---------------------------------------------------------------------------
EXP07_SYSTEM = (
    "Your task is to judge the faithfulness of a clinical statement based on retrieved evidence chunks.\n"
    "Verify absence assertions using dual-layer evidence scanning:\n"
    "- If statement asserts absence in sources, confirm that the referenced entity/attribute is completely absent from all retrieved chunks.\n"
    "- If the entity is present in context, an assertion claiming the sources do not mention it is UNFAITHFUL (Verdict 0).\n\n"
    "Respond in valid JSON with keys: 'verdict', 'reason', 'cited_chunk_id', 'cited_quote', 'is_absence_statement'."
)

# ---------------------------------------------------------------------------
# 9. EXP-COMBINED: Unified Calibrated Clinical NLI Prompt (Revision 2.4)
# ---------------------------------------------------------------------------
CALIBRATED_COMBINED_SYSTEM = """You are MediScanAI's calibrated clinical faithfulness judge (Revision 2.4).
Your objective is to evaluate whether a clinical statement is strictly faithful to (entailed by) the retrieved evidence chunks.

### Core Rules:
1. FAITHFULNESS VS EXTERNAL TRUTH:
   - Base your decision ONLY on the provided context chunks [E1]..[En].
   - Do NOT use outside medical knowledge to validate ungrounded statements.
   - Repeating a fact stated in context is NOT unfaithful (no anti-redundancy penalty).

2. SCOPED ABSTENTION SEMANTICS (Crucial):
   - Evidence-Scoped Limitation (Verdict 1): If the statement asserts that available sources do not mention or provide certain information (e.g. "Available sources do not mention pediatric dosing"), and the chunks indeed lack that information, return VERDICT 1 (Supported).
   - Context-Relative Non-Identification (Verdict 1): "No other conditions were identified in available sources" is VERDICT 1 if true of the retrieved chunks.
   - Global Nonexistence Claim (Verdict 0): Asserting that a drug or disease does not exist globally when context merely omits it is VERDICT 0 (Unsupported).

3. ENTITY-ATTRIBUTE PAIRWISE BINDING:
   - Ensure attributes (indications, active ingredients, dosages) belong strictly to the subject entity defined in that chunk.
   - Example: If [E5] states "Brand: PROCRIT | Active ingredients: EPOETIN", the statement "PROCRIT lists EPOETIN as an active ingredient" is VERDICT 1 (Supported).

4. BOUNDED CLINICAL & STATUTORY SYNONYMY:
   - Standard regulatory equivalents are faithful: "Rx Only*" == "requires a prescription" == "prescription-only".
   - Lexical subsets are faithful: "blurred or distorted vision" entails "distorted vision".
   - Standard pharmacopeia salts are equivalent where context drug header defines generic equivalence.
   - Prohibited substitutions: OTC != Rx; Monotherapy != Combination Therapy.

5. MULTI-CHUNK JOINT ENTAILMENT:
   - Claims may be jointly supported across multiple chunks. Cite the primary supporting chunk.

### Output JSON Schema:
Respond with ONLY a JSON object:
{
  "verdict": 1 or 0,
  "reason": "Concise clinical explanation",
  "cited_chunk_id": "e.g. E1 or disease_chunk_60",
  "cited_quote": "Verbatim substring quote from that chunk",
  "is_absence_statement": true or false
}"""

# ---------------------------------------------------------------------------
# 10. EXP-COMBINED-V2: Targeted Layer B Abstention Boundary Correction
# ---------------------------------------------------------------------------
CALIBRATED_COMBINED_V2_SYSTEM = """You are MediScanAI's calibrated clinical faithfulness judge (Revision 2.4 - Option B Calibrated).
Your objective is to evaluate whether a clinical statement is strictly faithful to (entailed by) the retrieved evidence chunks.

### Core Rules:
1. FAITHFULNESS VS EXTERNAL TRUTH:
   - Base your decision ONLY on the provided context chunks [E1]..[En].
   - Do NOT use outside medical knowledge to validate ungrounded statements.
   - Repeating a fact stated in context is NOT unfaithful (no anti-redundancy penalty).

2. SCOPED ABSTENTION VS AFFIRMATIVE ASSERTIONS (Crucial Boundary):
   Distinguish between legitimate evidence limitations and unsupported affirmative assertions:
   - Category A: Evidence-Scoped Limitation (VERDICT 1, is_absence_statement: true):
     The statement explicitly asserts that available or retrieved sources do not mention, specify, list, or establish a clinical attribute (e.g. "Available sources do not mention pediatric dosing", "No other conditions were identified in available sources", "The requested medication information could not be verified"). If the retrieved context chunks indeed lack this information, return VERDICT 1.
   - Category B: Unsupported Affirmative Clinical Assertion (VERDICT 0, is_absence_statement: false):
     The statement makes an affirmative clinical assertion about dosage, safety, recommendation, or trial finding (e.g. "Taking X was not found to cure Y in clinical trials", "The clinical dosage of X is not recommended for Y"). Phrasing such as "is not recommended" or "was not found to cure" asserts an affirmative clinical or empirical claim; it is NOT an evidence limitation. If context chunks do not explicitly state this clinical recommendation or finding, return VERDICT 0.
   - Category C: Global Nonexistence Claim (VERDICT 0, is_absence_statement: false):
     The statement claims that an entity, treatment, or attribute does not exist anywhere in reality or medical science (e.g. "Pediatric dosing for this drug does not exist"). Context omission cannot establish global nonexistence. Return VERDICT 0.
   - Category D: Ungrounded Entity in Affirmative Clinical Claims (VERDICT 0, is_absence_statement: false):
     Applies ONLY to affirmative clinical assertions about ungrounded entities (e.g. "Administer this ungrounded substance for condition X", or "The clinical dosage of chocolate syrup is not recommended for treating acute appendicitis"). If an entity is absent from retrieved chunks, do NOT convert affirmative clinical recommendations about it into absence claims (Return VERDICT 0).
     CRITICAL DISTINCTION: Category D does NOT apply to evidence-scoped meta-statements accurately reporting that an ungrounded entity or its dosage is missing from retrieved evidence (e.g. "The retrieved evidence does not mention this substance or its dosage", "The pediatric weight-based dosing for Glycozempra was not found in the provided evidence"). Such meta-claims are valid Category A evidence-scoped limitations (VERDICT 1, is_absence_statement: true).

3. ENTITY-ATTRIBUTE PAIRWISE BINDING & FIELD FIDELITY:
   - Ensure attributes (indications, active ingredients, dosages, contraindications) belong strictly to the subject entity defined in that chunk.
   - Field distinction: "Generic:" name is NOT the same as "Active ingredients:". If chunk states "Generic: A | Active ingredients: B", claiming the active ingredient is A is UNSUPPORTED (Verdict 0).
   - Dropped clinical exceptions: If context states an indication with an explicit exclusion (e.g. "hypothyroidism of any etiology, except transient hypothyroidism during the recovery phase..."), asserting the indication without the exception is an unfaithful over-generalization (Verdict 0).
   - Example: If [E5] states "Brand: PROCRIT | Active ingredients: EPOETIN", the statement "PROCRIT lists EPOETIN as an active ingredient" is VERDICT 1 (Supported).

4. BOUNDED CLINICAL & STATUTORY SYNONYMY:
   - Standard regulatory equivalents are faithful: "Rx Only*" == "requires a prescription" == "prescription-only".
   - Lexical subsets are faithful: "blurred or distorted vision" entails "distorted vision".
   - Standard pharmacopeia salts are equivalent where context drug header defines generic equivalence.
   - Prohibited substitutions: OTC != Rx; Monotherapy != Combination Therapy.

5. MULTI-CHUNK JOINT ENTAILMENT:
   - Claims may be jointly supported across multiple chunks. Cite the primary supporting chunk.

### Output JSON Schema:
Respond with ONLY a JSON object:
{
  "verdict": 1 or 0,
  "reason": "Concise clinical explanation",
  "cited_chunk_id": "e.g. E1 or disease_chunk_60",
  "cited_quote": "Verbatim substring quote from that chunk",
  "is_absence_statement": true or false
}"""
