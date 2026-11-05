"""
Unit test asserting that the string given to the judge equals the user-visible answer text.
"""

from evaluation.e2e.sanitize import answer_full


def test_judge_input_equals_user_visible_text():
    sample_outputs = [
        (
            "**Verdict:** Based on the available sources, the symptoms you describe overlap with the conditions listed below. This is not a diagnosis.\n\n"
            "Explanation: Coronary Atherosclerosis lists these symptoms: dizziness, fatigue. [E1]\n\n"
            "### ⚠️ Important Warning\n"
            "This analysis is for informational purposes only and is generated based on the data you provided. "
            "It is not a substitute for professional medical advice."
        ),
        (
            "**Verdict:** The label text identifies Metformin. [E1]\n"
            "Explanation: Metformin label evidence lists indications for type 2 diabetes. [E1]\n\n"
            "### ⚠️ Important Warning\n"
            "This analysis is for informational purposes only and is generated based on the data you provided. "
            "It is not a substitute for professional medical advice."
        ),
        (
            "**Verdict:** The available sources do not state the specific information requested in this inquiry.\n\n"
            "Explanation: The available sources do not state the requested information.\n\n"
            "### ⚠️ Important Warning\n"
            "This analysis is for informational purposes only and is generated based on the data you provided. "
            "It is not a substitute for professional medical advice."
        ),
    ]

    for user_visible_output in sample_outputs:
        judge_input_str = answer_full(user_visible_output)
        assert judge_input_str == user_visible_output.strip(), (
            f"Judge input string mismatch with user-visible text:\n"
            f"Judge input: {repr(judge_input_str)}\n"
            f"User visible: {repr(user_visible_output.strip())}"
        )
