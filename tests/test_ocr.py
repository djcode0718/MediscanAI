import sys
import os
import tempfile
import types

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Compatibility shims for paddlex on environments with modern langchain
try:
    import langchain_community.docstore.document
    import langchain_text_splitters
    m1 = types.ModuleType("langchain.docstore")
    m1.document = langchain_community.docstore.document
    sys.modules["langchain.docstore"] = m1
    sys.modules["langchain.docstore.document"] = langchain_community.docstore.document
    sys.modules["langchain.text_splitter"] = langchain_text_splitters
except ImportError:
    pass

import cv2
import numpy as np
from app import ocr


def generate_synthetic_medicine_label(output_path: str) -> str:
    """
    Generates a deterministic, fictitious medicine label image for testing OCR ingestion.
    Contains strictly fictional test text; contains no real patient data or commercial branding.
    """
    img = np.full((400, 800, 3), 255, dtype=np.uint8)

    # Blue header border
    cv2.rectangle(img, (10, 10), (790, 390), (0, 0, 150), 3)
    cv2.putText(img, "FICTIONAL PHARMA - RX SPECIMEN", (40, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (150, 0, 0), 2)
    cv2.putText(img, "MEDISCAN SYNTHETIC RX 500MG", (40, 130), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (0, 0, 0), 3)
    cv2.putText(img, "ACTIVE: FICTITIOUS HYDROCHLORIDE 500 MG", (40, 190), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
    cv2.putText(img, "DOSAGE: TAKE 1 TABLET DAILY WITH WATER", (40, 240), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
    cv2.putText(img, "CAUTION: FOR TESTING PURPOSES ONLY", (40, 300), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 180), 2)
    cv2.putText(img, "LOT: SYN-2026-TEST  EXP: 12/2099", (40, 350), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (80, 80, 80), 1)

    cv2.imwrite(output_path, img)
    return output_path


def run_test(image_path: str, show_preview: bool = False):
    """Runs OCR extraction on the provided image and asserts text was successfully extracted."""
    texts, preview_img = ocr.extract_with_preview(image_path)

    print("\n=== OCR Extracted Texts ===")
    for t in texts:
        print(t)

    assert len(texts) > 0, "OCR extraction failed: 0 text lines extracted from image."
    full_extracted = " ".join(texts).upper()
    assert "MEDISCAN" in full_extracted or "SYNTHETIC" in full_extracted or "500MG" in full_extracted, (
        f"OCR extraction failed to find expected synthetic label tokens: {texts}"
    )

    if show_preview:
        save_path = os.path.join(tempfile.gettempdir(), "ocr_preview_debug.jpg")
        cv2.imwrite(save_path, preview_img)
        print(f"\nPreview with bounding boxes saved to: {save_path}")

    return texts


def test_ocr_synthetic_extraction():
    """Pytest test case verifying OCR extraction on a deterministic synthetic image."""
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        generate_synthetic_medicine_label(tmp_path)
        texts = run_test(tmp_path, show_preview=False)
        assert len(texts) >= 3, f"Expected at least 3 extracted text lines, got {len(texts)}"
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


if __name__ == "__main__":
    print("--- Running OCR Test with Synthetic Fictitious Label ---")
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        generate_synthetic_medicine_label(tmp_path)
        print(f"Created temporary synthetic label at: {tmp_path}")
        extracted = run_test(tmp_path, show_preview=False)
        print(f"\n✅ OCR Test Successfully Extracted {len(extracted)} lines.")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
            print(f"Cleaned up temporary synthetic label at: {tmp_path}")


