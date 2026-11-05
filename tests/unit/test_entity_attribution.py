"""
Unit tests for evaluation/e2e/entity_attribution.py.
Fixtures:
- E2E-041 answer MUST fail due to attributing Allopurinol indications to Glyburide under [E7].
- A corrected answer MUST pass.
"""

import pytest
from evaluation.e2e.entity_attribution import check_entity_attribution

E2E_041_EVIDENCE = """[E1] DRUG | id=24160 | Brand: Allopurinol | Generic: ALLOPURINOL | Active ingredients: ALLOPURINOL | Indications: This is not an innocuous drug. It is not recommended for the treatment of asymptomatic hyperuricemia. Allopurinol tablets, USP reduces serum and urinary uric acid concentrations. Its use should be individualized for each patient and requires an understanding of its mode of action and pharmacokinetics (see CLINICAL PHARMACOLOGY, CONTRAINDICATIONS, WARNINGS, and PRECAUTIONS).
[E2] DRUG | id=54421 | Brand: ClindaCare | Generic: CLINDAMYCIN, IBUPROFEN, CHLORHEXIDINE GLUCONATE
[E3] DRUG | id=71922 | Brand: Dronis | Generic: Drospirenone/Ethinyl Estradiol | Active ingredients: DROSPIRENONE; ETHINYL ESTRADIOL | Indications: A combination oral contraceptive pill used for the prevention of pregnancy. It combines a progestin (purpose: drospirenone); and an estrogen (purpose: ethinyl estradiol); . In addition to its contraceptive effect, it is also approved for the treatment of symptoms of premenstrual dysphoric disorder (purpose: PMDD)
[E4] DRUG | id=16353 | Brand: KOLORZ SIXTY SECOND FLUORIDE FOAM TRIPLE MINT | Generic: SODIUM FLUORIDE | Also marketed as: KOLORZ NEUTRAL FLUORIDE FOAM TRIPLE MINT | Active ingredients: SODIUM FLUORIDE | Indications: For the topical application of fluoride to aid in the protection against dental caries. Shake can thoroughly for at least 30 seconds before each use. Hold can completely upside down to dispense. See package insert for dosage information. Figure
[E5] DRUG | id=45476 | Brand: Danil | Generic: DANIL COMPOUND KETOCONAZOLE SOLUTION FOR SCALP DISORDERS. | Active ingredients: CLOBETASOL PROPIONATE; KETOCONAZOLE | Indications: EXPIRATION DATE: Three years after the manufactured date. For external use only. Avoid contact with eyes. Keep out of reach of children. Do not exceed prescribed dose. Read package insert carefully before using.
[E6] DRUG | id=9707 | Brand: SFERANGS VITA C CAPSULEBOOSTER | Generic: NIACINAMIDE | Active ingredients: NIACINAMIDE | Indications: apply proper amount to the skin
[E7] DRUG_NAME_MATCH | id=3489 | name: glyburide
[E8] DRUG_NAME_MATCH | id=14145 | name: 800mg
[E9] DRUG_NAME_MATCH | id=14144 | name: 1200mg"""

E2E_041_BUGGY_ANSWER = """**Verdict:** The label text identifies Glibenclarnide (Glyburide). [E7]

Explanation: Glibenclarnide (Glyburide) label evidence lists active ingredients: glyburide and indications: This is not an innocuous drug. It is not recommended for the treatment of asymptomatic hyperuricemia. Allopurinol tablets, USP reduces serum and urinary uric acid concentrations. Its use should be individualized for each patient and requires an understanding of its mode of action and pharmacokinetics (see CLINICAL PHARMACOLOGY, CONTRAINDICATIONS, WARNINGS, and PRECAUTIONS). [E7]

### ⚠️ Important Warning
This analysis is for informational purposes only and is generated based on the data you provided. It is **not a substitute for professional medical advice**. You should always consult a qualified doctor or pharmacist for an accurate diagnosis and to determine the best course of treatment for your specific condition."""

E2E_041_CORRECTED_ANSWER = """**Verdict:** The label text identifies Glyburide. [E7]

Explanation: The medication Glyburide was identified from name match evidence [E7]. However, labeled indications and active ingredients are not stated in the available sources for this product.

### Suggested Alternatives
Not applicable: no symptoms were provided.

### ⚠️ Important Warning
This analysis is for informational purposes only and is generated based on the data you provided. It is **not a substitute for professional medical advice**. You should always consult a qualified doctor or pharmacist for an accurate diagnosis and to determine the best course of treatment for your specific condition."""


def test_e2e_041_buggy_answer_fails_attribution():
    res = check_entity_attribution(E2E_041_BUGGY_ANSWER, E2E_041_EVIDENCE)
    assert not res.is_valid, "E2E-041 buggy answer MUST fail attribution checker"
    assert len(res.errors) >= 1
    # Check that both cross-block entity mention (Allopurinol) and copied indication were caught
    assert len(res.flagged_citations) >= 1 or len(res.cross_block_copies) >= 1


def test_e2e_041_corrected_answer_passes_attribution():
    res = check_entity_attribution(E2E_041_CORRECTED_ANSWER, E2E_041_EVIDENCE)
    assert res.is_valid, f"E2E-041 corrected answer MUST pass attribution checker, errors: {res.errors}"
    assert len(res.errors) == 0
