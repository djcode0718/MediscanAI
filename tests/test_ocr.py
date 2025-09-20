import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# # import os
# # import cv2
# # import matplotlib.pyplot as plt
# # from backend import ocr

# # def test_ocr_preview_and_text():
# #     # Replace with a real pill image path before running
# #     img_path = r"C:\Users\karth\OneDrive\Desktop\ocr_test_img1.jpg"

# #     if not os.path.exists(img_path):
# #         print("⚠️ Sample image not found, skipping OCR test.")
# #         return

# #     # Run OCR
# #     extracted_text, preview_img = ocr.extract_with_preview(img_path)

# #     # Show preview with bounding boxes
# #     plt.figure(figsize=(12, 12))
# #     plt.imshow(cv2.cvtColor(preview_img, cv2.COLOR_BGR2RGB))
# #     plt.axis("off")
# #     plt.title("OCR Preview with Bounding Boxes")
# #     plt.show()

# #     # Print extracted text
# #     print("\n===== Extracted Text =====")
# #     for t in extracted_text:
# #         print(t)

# #     # Assertions (basic check)
# #     assert isinstance(extracted_text, list)
# #     assert all(isinstance(t, str) for t in extracted_text)
# # from backend import ocr 
# # print(ocr.extract_with_preview(r"C:\Users\karth\OneDrive\Desktop\ocr_test_img1.jpg")[0])

# import argparse
# import os
# import cv2
# from backend import ocr

# def run_test(image_path: str, show_preview: bool = False):
#     # Run OCR and get both text + preview image with bounding boxes
#     texts, preview_img = ocr.extract_with_preview(image_path)

#     print("\n=== OCR Extracted Texts ===")
#     for t in texts:
#         print(t)

#     if show_preview:
#         # Save preview for reference
#         save_path = os.path.join("tests", "ocr_preview3.jpg")
#         cv2.imwrite(save_path, preview_img)
#         print(f"\nPreview with bounding boxes saved to: {save_path}")

#         # Show window
#         cv2.imshow("OCR Preview", preview_img)
#         print("Press any key in the preview window to close...")
#         cv2.waitKey(0)
#         cv2.destroyAllWindows()


# if __name__ == "__main__":
#     parser = argparse.ArgumentParser(description="Test OCR Module")
#     parser.add_argument("-i", "--image", type=str, help="Path to input image")
#     parser.add_argument("-s", "--show", action="store_true", help="Show preview window with bounding boxes")
#     args = parser.parse_args()

#     test_folder = "tests/test_data"

#     if args.image:
#         run_test(args.image, args.show)
#     else:
#         # Run OCR on all images in test_data folder
#         for fname in os.listdir(test_folder):
#             if fname.lower().endswith((".jpg", ".jpeg", ".png")):
#                 print(f"\nProcessing: {fname}")
#                 run_test(os.path.join(test_folder, fname), args.show)


import os
import cv2
from backend import ocr

def run_test(image_path: str, show_preview: bool = False):
    # Run OCR and get both text + preview image with bounding boxes
    texts, preview_img = ocr.extract_with_preview(image_path)

    print("\n=== OCR Extracted Texts ===")
    for t in texts:
        print(t)

    # Hardcoded extracted text
    hardcoded_text = "I have skin allergy"
    print(f"\nHardcoded Text: {hardcoded_text}")

    if show_preview:
        # Save preview for reference
        save_path = os.path.join("tests", "ocr_preview3.jpg")
        cv2.imwrite(save_path, preview_img)
        print(f"\nPreview with bounding boxes saved to: {save_path}")

        # Show window
        cv2.imshow("OCR Preview", preview_img)
        print("Press any key in the preview window to close...")
        cv2.waitKey(0)
        cv2.destroyAllWindows()


if __name__ == "__main__":
    # Hardcoded values
    print("starting..")
    # image_path = '/Users/sj/Downloads/WhatsApp Image 2025-09-14 at 14.00.39 (1).jpeg'
    image_path = '/Users/sj/Downloads/WhatsApp Image 2025-09-16 at 22.31.52.jpeg'
    show_preview = True  # Set to False if you do not want to show preview

    run_test(image_path, show_preview)
