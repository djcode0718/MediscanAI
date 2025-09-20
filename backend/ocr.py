# backend/ocr.py
from typing import List, Dict
import numpy as np
import cv2

# PaddleOCR import - your environment already has paddleocr installed
from paddleocr import PaddleOCR

# Initialize OCR model once on import to reuse
# Note: you tuned PaddleOCR previously. Keep the flags you used.
ocr_model = PaddleOCR(use_textline_orientation=True, lang='en')

def extract_with_preview(img_path: str):
    """Run OCR on image and return (texts, preview_image_with_boxes)."""
    result = ocr_model.predict(img_path)
    res = result[0]

    image = cv2.imread(img_path)
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    extracted_texts = []

    for box, text in zip(res['dt_polys'], res['rec_texts']):
        pts = box.astype(np.int32).reshape((-1, 1, 2))
        cv2.polylines(image, [pts], isClosed=True, color=(255, 0, 0), thickness=2)
        cv2.putText(image, text, tuple(pts[0][0]), cv2.FONT_HERSHEY_SIMPLEX,
                    0.5, (0, 255, 0), 1, cv2.LINE_AA)
        extracted_texts.append(text)

    return extracted_texts, cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

def extract_text_from_image(image_path: str) -> Dict:
    """
    Extracts text and bounding boxes from an image using PaddleOCR.
    Returns a dict: {
      "texts": [str, ...],
      "boxes": [np.ndarray(...), ...],
      "preview_image": np.ndarray (RGB)  # optional for UI preview
    }
    """
    result = ocr_model.predict(image_path)
    # result is typically a list per-image; we assume single image input
    res = result[0]

    # rec_texts and dt_polys are keys in result element (consistent with your test)
    rec_texts = res.get("rec_texts", [])
    dt_polys = res.get("dt_polys", [])

    # Load image for preview (RGB)
    image_bgr = cv2.imread(image_path)
    if image_bgr is None:
        raise FileNotFoundError(f"Image not found or can't be read: {image_path}")
    image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)

    return {
        "texts": rec_texts,
        "boxes": [np.array(b).astype(np.int32) for b in dt_polys],
        "preview_image": image_rgb
    }

def ocr_text_join(texts: List[str]) -> str:
    """
    Join OCR texts into a single cleaned string for downstream embedding/retrieval.
    """
    # Basic join; keep order. You might add cleaning / normalization here.
    return " ".join([t.strip() for t in texts if t and t.strip()])
