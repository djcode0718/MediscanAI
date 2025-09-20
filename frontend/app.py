# # frontend/app.py

# import sys, os
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# import streamlit as st
# from backend.core import Pipeline

# st.set_page_config(page_title="MediScanAI", layout="wide")

# st.title("MediScanAI — RAG healthcare assistant (demo)")

# with st.sidebar:
#     st.header("Inputs")
#     text_input = st.text_area("Describe your symptoms or condition", height=120)
#     uploaded_file = st.file_uploader("Upload pill strap image (optional)", type=["png", "jpg", "jpeg"])
#     run_button = st.button("Analyze")

# # Initialize pipeline once
# pipeline = Pipeline()

# if run_button:
#     st.info("Processing — this may take a few seconds (embedding + retrieval + LLM).")
#     image_path = None
#     if uploaded_file is not None:
#         # Save temporarily to disk for OCR
#         with open("tmp_uploaded.jpg", "wb") as f:
#             f.write(uploaded_file.getvalue())
#         image_path = "tmp_uploaded.jpg"

#     result = pipeline.run(text_input or "", image_path=image_path, top_k=5)
#     card = result["card"]
#     meta = result["meta"]

#     # Pretty output
#     st.subheader("Result")
#     st.markdown("**LLM Response**")
#     st.text_area("Assistant", value=card["llm_output"], height=240)

#     st.markdown("**Retrieved (short preview)**")
#     for idx, items in card["retrieved"].items():
#         st.markdown(f"**{idx}**")
#         for it in items:
#             st.write(f"- {it['key']} (score: {it['score']:.4f})")
#             st.write(it["preview"])

#     if meta.get("mismatch"):
#         st.warning("Potential mismatch detected between detected drug and condition. See LLM response for alternatives and next steps.")
#     else:
#         st.success("No obvious mismatch detected (based on KB retrieval).")

#     st.markdown("---")
#     st.markdown("**Full JSON card**")
#     st.json(card)
