# MediScanAI Narrative Reference Answers — Research Track

**Created:** 2026-10-15  
**Coverage:** 50/50 benchmark cases (`MED-BENCH-001` through `MED-BENCH-050`)  
**Status:** Source-backed research references; not human-reviewed clinical gold.

## Purpose

This dataset provides concise narrative reference answers for downstream Ragas evaluation, particularly reference-based metrics such as Context Recall and Answer Correctness. It is separate from the retrieval relevance labels and must not be copied into `evaluation/benchmark/gold_judgments.jsonl`.

## Files

- `reference_answers.jsonl` — one JSON object per benchmark case, with `reference`/`reference_answer`, key facts, answerability, supporting URLs, source-record context and provenance.
- `reference_answers_review.csv` — compact human-review worksheet with answer, status, source URLs and limitations.
- `README.md` — integration notes and limitations.

## Method

1. Preserved the case IDs, queries, categories, expected evidence types and candidate evidence IDs from the supplied `candidate_queries.jsonl`.
2. Used the uploaded Phase A.3 evidence judgments and source registry as benchmark context, not as infallible authority.
3. Wrote each reference to answer the actual query while avoiding invented dosages, ungrounded indications and symptom-only diagnoses.
4. Used regulatory drug labeling, government/public-health resources and recognized clinical information sources where appropriate.
5. Marked ambiguous symptom queries as ambiguous and deliberately unsupported/fictitious prompts as unanswerable.
6. Included source URLs and an explicit provenance declaration on every record.

## Important scientific limitations

- These references are **AI-assisted, source-backed research outputs**, not independent clinician adjudication. `human_reviewed` and `clinical_reviewed` are `false` for every record.
- A cited authoritative source supports only the claims stated in its scope. A general symptom page does not establish a diagnosis for an individual.
- “Not found in the searched registry” is not proof that a name does not exist in every country or database. Unanswerable controls are phrased conservatively.
- Corpus-scoped results such as “all products” are explicitly limited to the supplied corpus unless a jurisdiction and exhaustive registry are specified.
- The five negative controls must be evaluated for abstention/safety behavior, not treated as ordinary answerable clinical cases.
- Reference-based Ragas scores measure similarity/support against these research references. They do not establish clinical safety, correctness in every patient, or clinical validation.
- Do not promote these records into `gold_judgments.jsonl`. Keep official human gold separate and empty unless the repository's governance policy is satisfied.
- This artifact was assembled from the files supplied in this conversation and source research; it was not executed against or written directly into the user's Git repository.

## Recommended Ragas mapping

For each query:
- `user_input` / `question` <- `query`
- `reference` <- `reference`
- `retrieved_contexts` <- actual retrieved source texts from the baseline/graph runs
- `response` <- the generated model answer

Keep the retrieval-only benchmark metrics and the Ragas generation metrics as separate evaluation tracks.

## Quality checks

- Exactly 50 unique case IDs.
- Every case has a non-empty reference answer, answerability label, key facts, at least one supporting source URL, limitations, and provenance.
- No record is marked human- or clinical-reviewed.
- The file is separate from official gold judgments.
