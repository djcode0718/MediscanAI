# RAGAS Optimization: Step 1-3 Diagnosis (no code changed)

Branch `eval/phase01` @ `5e5a10a`, working tree clean. All judge numbers: SELF-JUDGED (llama3.1:8b).
Baseline verified from saved `scored_results.jsonl` (not re-run; judge cache is content-keyed).

## Verified baseline (saved artifacts)
- A2 mean faithfulness 0.5282 (39 valid / 40; E2E-035 NaN). 15/39 cases < 0.5, only 3 cases == 1.0.
- A2 per category (n valid): medicine_clean 0.567 (5), medicine_noisy 0.487 (5), symptom_only 0.654 (8),
  match 0.464 (8), mismatch 0.647 (6), unanswerable 0.360 (7).

## Top three bottlenecks (evidence from artifacts)
1. **Evidence composition: disease symptom lists dominate the context.**
   DISEASE blocks are 27-54% of shown evidence items in every category. Blocks such as
   `Condition: Chest Pain | Listed symptoms: Chest Pain; Coxsackievirus Infections; Cystic Fibrosis; ...`
   are alphabetical co-occurrence lists, not clinical evidence. Any sentence the model builds on them
   is likely to be judged unsupported (taxonomy_auto: 15 ENTITY_NOT_IN_EVIDENCE, 14 TEMPLATE_VERDICT).
2. **Prompt routing: medicine-only cases are routed to the SYMPTOM_AND_MEDICINE task.**
   `determine_case_type` keys on `user_text` being non-empty. In the dataset every medicine-only case
   (11/11) carries a generic instruction in `user_text`, so the "symptoms match" verdict template is used
   and the model must invent the "user's symptoms" (E2E-035: "Your symptoms are not explicitly stated...
   it appears you are looking for relief from asthma"). Unanswerable cases (6/7) are routed the same way.
   This is a code/dataset-contract issue, to be confirmed before fixing.
3. **Generation shape vs. RAGAS decomposition (evaluator is fixed).**
   A2 answers are 57-80 words yet decompose into 11-27 atomic statements. The fixed template
   verdict sentence ("label evidence for X lists uses that match your symptoms") is emitted even
   when the cited block does not support it. Also, `answer_core` strips `[E#]` tags in 35/40 cases,
   leaving fragments such as "EVIDENCE block  state ..." that the judge sees. Note: this is how the
   existing evaluator prepares input; it is flagged, NOT modified.

## Retrieval observation (reference_context_ids only exist for medicine/match/mismatch cases)
Reference drug present in shown evidence: clean 4/6, noisy 3/5, match 5/8, mismatch 5/6.
Missing references are a recall issue (e.g., E2E-035's reference `drug_1275` is raw rank 16 of 20, and
was shown only after dedupe/budgeting). symptom_only and unanswerable have no reference ids, so
retrieval hit@k cannot be computed for them.

## Limits that must be stated up front
- Generator and judge are both llama3.1:8b; the judge itself yields NaN/unparseable output on some inputs
  (valid rate 39/40) and its per-case scores are noisy. Reaching a mean > 0.90 under this judge may not be
  achievable by honest changes; this will be reported as measured, not assumed.
- Each 40-case scoring pass took roughly 1 h in the earlier gate, so the retrieval-depth x top-k x
  granularity matrix cannot be fully crossed with judge scoring. Plan: deterministic metrics
  (hit@k, MRR, tokens, duplicates) for the full matrix, judge scoring only for finalists.

## Proposed next steps
- Step 4: add opt-in dev-mode trace (exact prompt, token budget, dropped-block reasons), no behavior change.
- Step 5: deterministic retrieval-depth/top-k matrix on the 40 cases (no LLM judge).
- Step 6: (a) route case type by presence of OCR text, not `user_text` (opt-in flag); (b) demote or
  drop alphabetical disease-symptom lists unless they overlap the user's tokens; (c) tighten the template
  verdict to require overlap evidence. Then judge-score finalists only.
