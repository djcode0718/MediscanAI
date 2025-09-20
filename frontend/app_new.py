# import sys, os
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
# import streamlit as st
# from backend.core_new import Pipeline

# st.set_page_config(page_title="MediScanAI", layout="wide")

# st.title("MediScanAI — RAG healthcare assistant (demo)")

# with st.sidebar:
#     st.header("Inputs")
#     text_input = st.text_area("Describe your symptoms or condition", height=120)
#     uploaded_file = st.file_uploader("Upload pill strap image (optional)", type=["png", "jpg", "jpeg"])
#     run_button = st.button("Analyze")

# @st.cache_resource
# def get_pipeline():
#     return Pipeline()

# pipeline = get_pipeline()

# if run_button:
#     if not text_input and not uploaded_file:
#         st.warning("Please provide symptoms or upload an image.")
#     else:
#         with st.spinner("Processing — this may take a few seconds (embedding + retrieval + LLM)."):
#             image_path = None
#             image_name = "None"
#             if uploaded_file is not None:
#                 with open("tmp_uploaded.jpg", "wb") as f:
#                     f.write(uploaded_file.getvalue())
#                 image_path = "tmp_uploaded.jpg"
#                 image_name = uploaded_file.name

#             st.markdown("---")
#             st.code(
# f"""[TEST] Running pipeline with the following inputs:
#  - Text: '{text_input or 'No text provided.'}'
#  - Image: '{image_name}'

# --- Awaiting response... ---"""
#             )

#             result = pipeline.run(
#                 user_text=(text_input or ""), 
#                 image_path=image_path, 
#                 top_k=5
#             )

#             card = result.get("card", {})
            
#             ocr_text = card.get("ocr_text", "")
#             llm_response = card.get("llm_output", "Error: Could not get LLM response from pipeline result.")
            
#             if ocr_text:
#                 st.markdown("---")
#                 st.code(f"--- OCR Text Extracted ---\n{ocr_text}")

#             st.markdown("---")
#             st.code("[RESULT] Final LLM Analysis:")
#             st.markdown(llm_response)

#             if image_path and os.path.exists(image_path):
#                 os.remove(image_path)




# import sys, os
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
# import streamlit as st
# from backend.core_new import Pipeline

# st.set_page_config(page_title="MediScanAI", layout="wide")

# st.title("MediScanAI — RAG healthcare assistant (demo)")

# with st.sidebar:
#     st.header("Inputs")
#     text_input = st.text_area("Describe your symptoms or condition", height=120)
#     uploaded_file = st.file_uploader("Upload pill strap image (optional)", type=["png", "jpg", "jpeg"])
#     run_button = st.button("Analyze")

# @st.cache_resource
# def get_pipeline():
#     return Pipeline()

# pipeline = get_pipeline()

# if run_button:
#     if not text_input and not uploaded_file:
#         st.warning("Please provide symptoms or upload an image.")
#     else:
#         with st.spinner("Processing — this may take a few seconds..."):
#             image_path = None
#             image_name = "None"
#             if uploaded_file is not None:
#                 with open("tmp_uploaded.jpg", "wb") as f:
#                     f.write(uploaded_file.getvalue())
#                 image_path = "tmp_uploaded.jpg"
#                 image_name = uploaded_file.name

#             result = pipeline.run(
#                 user_text=(text_input or ""), 
#                 image_path=image_path, 
#                 top_k=5
#             )

#             card = result.get("card", {})
#             ocr_text = card.get("ocr_text", "")
#             llm_response = card.get("llm_output", "Error: Could not get LLM response.")
            
#             if ocr_text:
#                 st.code(f"--- OCR Text Extracted ---\n{ocr_text}")
            
#             st.markdown("---")

#             html_template = f"""
#             <style>
#                 .result-box {{
#                     background-color: #262730;
#                     border: 1px solid #3c3f49;
#                     border-radius: 10px;
#                     padding: 25px;
#                     margin-bottom: 20px;
#                     font-family: 'sans serif';
#                     color: #FAFAFA;
#                 }}
#                 .result-box h3 {{
#                     color: #00A67E;
#                     font-size: 22px;
#                     margin-top: 20px;
#                     margin-bottom: 10px;
#                     border-bottom: 2px solid #3c3f49;
#                     padding-bottom: 5px;
#                 }}
#                 .result-box h4 {{
#                     color: #00A67E;
#                     font-size: 18px;
#                     margin-top: 15px;
#                     margin-bottom: 5px;
#                 }}
#                 .result-box p {{
#                     line-height: 1.6;
#                 }}
#                 .result-box strong {{
#                     color: #00C896;
#                 }}
#                 .result-box ul {{
#                     list-style-type: none;
#                     padding-left: 5px;
#                 }}
#                 .result-box li::before {{
#                     content: "•";
#                     color: #00A67E;
#                     font-weight: bold;
#                     display: inline-block; 
#                     width: 1em;
#                     margin-left: -1em;
#                 }}
#                 .result-box li {{
#                     margin-bottom: 10px;
#                     padding-left: 5px;
#                 }}
#             </style>
#             <div class="result-box">
#                 {llm_response}
#             </div>
#             """

#             st.markdown(html_template, unsafe_allow_html=True)

#             if image_path and os.path.exists(image_path):
#                 os.remove(image_path)


# import sys, os
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
# import streamlit as st
# from backend.core_new import Pipeline

# st.set_page_config(page_title="MediScanAI", layout="wide")

# st.title("MediScanAI — RAG healthcare assistant (demo)")

# with st.sidebar:
#     st.header("Inputs")
#     text_input = st.text_area("Describe your symptoms or condition", height=120)
#     uploaded_file = st.file_uploader("Upload pill strap image (optional)", type=["png", "jpg", "jpeg"])
#     run_button = st.button("Analyze")

# @st.cache_resource
# def get_pipeline():
#     return Pipeline()

# pipeline = get_pipeline()

# if run_button:
#     if not text_input and not uploaded_file:
#         st.warning("Please provide symptoms or upload an image.")
#     else:
#         with st.spinner("Processing — this may take a few seconds..."):
#             image_path = None
#             if uploaded_file is not None:
#                 with open("tmp_uploaded.jpg", "wb") as f:
#                     f.write(uploaded_file.getvalue())
#                 image_path = "tmp_uploaded.jpg"

#             result = pipeline.run(
#                 user_text=(text_input or ""),
#                 image_path=image_path,
#                 top_k=5
#             )

#             card = result.get("card", {})
#             ocr_text = card.get("ocr_text", "")
#             llm_response = card.get("llm_output", "Error: Could not get LLM response.")

#             if ocr_text:
#                 st.code(f"--- OCR Text Extracted ---\n{ocr_text}")

#             st.markdown("---")
            
#             full_analysis_text = f"### [RESULT] Final LLM Analysis:\n\n{llm_response}"
            
#             st.warning(full_analysis_text)

#             if image_path and os.path.exists(image_path):
#                 os.remove(image_path)

# import sys, os
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
# import streamlit as st
# from backend.core_new import Pipeline

# st.set_page_config(page_title="MediScanAI", layout="wide")

# st.title("MediScanAI — RAG healthcare assistant (demo)")

# st.markdown("""
# <style>
#     div[data-testid="stAlert"] {
#         background-color: #14213d;
#         color: #e5e5e5;
#     }
# </style>
# """, unsafe_allow_html=True)

# with st.sidebar:
#     st.header("Inputs")
#     text_input = st.text_area("Describe your symptoms or condition", height=120)
#     uploaded_file = st.file_uploader("Upload pill strap image (optional)", type=["png", "jpg", "jpeg"])
#     run_button = st.button("Analyze")

# @st.cache_resource
# def get_pipeline():
#     return Pipeline()

# pipeline = get_pipeline()

# if run_button:
#     if not text_input and not uploaded_file:
#         st.warning("Please provide symptoms or upload an image.")
#     else:
#         with st.spinner("Processing — this may take a few seconds..."):
#             image_path = None
#             if uploaded_file is not None:
#                 with open("tmp_uploaded.jpg", "wb") as f:
#                     f.write(uploaded_file.getvalue())
#                 image_path = "tmp_uploaded.jpg"

#             result = pipeline.run(
#                 user_text=(text_input or ""),
#                 image_path=image_path,
#                 top_k=5
#             )

#             card = result.get("card", {})
#             ocr_text = card.get("ocr_text", "")
#             llm_response = card.get("llm_output", "Error: Could not get LLM response.")

#             if ocr_text:
#                 st.code(f"--- OCR Text Extracted ---\n{ocr_text}")

#             st.markdown("---")
            
#             full_analysis_text = f"### [RESULT] Final LLM Analysis:\n\n{llm_response}"
            
#             st.markdown(full_analysis_text)

#             if image_path and os.path.exists(image_path):
#                 os.remove(image_path)


# import sys, os
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
# import streamlit as st
# from backend.core_new import Pipeline
# from backend.whisper import WhisperTranscriber
# from streamlit_mic_recorder import mic_recorder
# import uuid

# st.set_page_config(page_title="MediScanAI", layout="wide")

# st.title("MediScanAI — Your AI Healthcare Assistant")

# if 'voice_recordings' not in st.session_state:
#     st.session_state.voice_recordings = []

# @st.cache_resource
# def get_pipeline():
#     return Pipeline()

# @st.cache_resource
# def get_transcriber():
#     return WhisperTranscriber(model_size="base")

# pipeline = get_pipeline()
# transcriber = get_transcriber()

# with st.sidebar:
#     st.header("Inputs")
#     text_input = st.text_area("1. Describe your symptoms or condition", height=100)
    
#     st.markdown("---")
    
#     st.markdown("##### 2. Add Voice Input")
    
#     st.markdown("###### Record Live Audio")
#     audio_bytes = mic_recorder(start_prompt="Start Recording 🎙️", stop_prompt="Stop Recording ⏹️", key='recorder')

#     if audio_bytes:
#         recording_id = str(uuid.uuid4())
#         st.session_state.voice_recordings.append({
#             "id": recording_id,
#             "bytes": audio_bytes['bytes'],
#             "source": "live"
#         })
#         # st.rerun()  <- THIS LINE IS REMOVED

#     st.markdown("###### Or Upload Audio File")
#     uploaded_audio_file = st.file_uploader("Select a file", type=["wav", "mp3", "m4a", "ogg"], label_visibility="collapsed")
    
#     if uploaded_audio_file:
#         if st.button("Add Uploaded Audio"):
#             recording_id = str(uuid.uuid4())
#             st.session_state.voice_recordings.append({
#                 "id": recording_id,
#                 "bytes": uploaded_audio_file.getvalue(),
#                 "source": "upload",
#                 "filename": uploaded_audio_file.name
#             })
#             st.rerun()

#     if st.session_state.voice_recordings:
#         st.markdown("##### Your Audio Clips")
#         for i, rec in enumerate(st.session_state.voice_recordings):
#             col1, col2 = st.columns([4, 1])
#             with col1:
#                 if rec['source'] == 'upload':
#                     st.caption(f"Uploaded: `{rec['filename']}`")
#                 st.audio(rec['bytes'])
#             with col2:
#                 if st.button("✖️", key=f"delete_{rec['id']}", help="Delete this clip"):
#                     st.session_state.voice_recordings.pop(i)
#                     st.rerun()
    
#     st.markdown("---")

#     st.markdown("##### 3. Upload Medicine Image")
#     uploaded_file = st.file_uploader("Upload pill strap image (optional)", type=["png", "jpg", "jpeg"], label_visibility="collapsed")
    
#     st.markdown("---")

#     run_button = st.button("Analyze")

# if run_button:
#     combined_user_text = text_input.strip()
#     transcribed_texts = []

#     if not st.session_state.voice_recordings and not text_input and not uploaded_file:
#         st.warning("Please provide symptoms via text/voice or upload an image.")
#         st.stop()

#     with st.spinner("Transcribing audio... Please wait."):
#         for i, rec in enumerate(st.session_state.voice_recordings):
#             temp_audio_path = f"temp_audio_{rec['id']}.wav"
#             with open(temp_audio_path, "wb") as f:
#                 f.write(rec['bytes'])
            
#             transcribed_text = transcriber.transcribe_audio_file(temp_audio_path)
#             transcribed_texts.append(transcribed_text)
            
#             if os.path.exists(temp_audio_path):
#                 os.remove(temp_audio_path)

#     if transcribed_texts:
#         combined_user_text += "\n" + "\n".join(transcribed_texts)
#         combined_user_text = combined_user_text.strip()

#     with st.spinner("Processing — this may take a few seconds..."):
#         image_path = None
#         if uploaded_file is not None:
#             temp_image_path = f"temp_image_{uuid.uuid4()}.jpg"
#             with open(temp_image_path, "wb") as f:
#                 f.write(uploaded_file.getvalue())
#             image_path = temp_image_path

#         result = pipeline.run(
#             user_text=combined_user_text,
#             image_path=image_path,
#             top_k=5
#         )

#         card = result.get("card", {})
#         ocr_text = card.get("ocr_text", "")
#         llm_response = card.get("llm_output", "Error: Could not get LLM response.")

#         if ocr_text:
#             st.code(f"--- OCR Text Extracted ---\n{ocr_text}")
        
#         st.markdown("---")
        
#         st.markdown(f"### Final Analysis\n\n{llm_response}")

#         if image_path and os.path.exists(image_path):
#             os.remove(image_path)


import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import streamlit as st
from backend.core_new import Pipeline
from backend.whisper import WhisperTranscriber
from streamlit_mic_recorder import mic_recorder
import uuid

st.set_page_config(page_title="MediScanAI", layout="wide")

st.title("MediScanAI — Your AI Healthcare Assistant")

if 'voice_recordings' not in st.session_state:
    st.session_state.voice_recordings = []
if 'last_processed_audio_id' not in st.session_state:
    st.session_state.last_processed_audio_id = None

@st.cache_resource
def get_pipeline():
    return Pipeline()

@st.cache_resource
def get_transcriber():
    return WhisperTranscriber(model_size="base")

pipeline = get_pipeline()
transcriber = get_transcriber()

with st.sidebar:
    st.header("Inputs")
    text_input = st.text_area("1. Describe your symptoms or condition", height=100)
    
    st.markdown("---")
    
    st.markdown("##### 2. Add Voice Input")
    
    st.markdown("###### Record Live Audio")
    audio_bytes = mic_recorder(start_prompt="Start Recording 🎙️", stop_prompt="Stop Recording ⏹️", key='recorder')

    if audio_bytes and audio_bytes['id'] != st.session_state.last_processed_audio_id:
        st.session_state.last_processed_audio_id = audio_bytes['id']
        st.session_state.voice_recordings.append({
            "id": audio_bytes['id'],
            "bytes": audio_bytes['bytes'],
            "source": "live"
        })
        st.rerun()

    st.markdown("###### Or Upload Audio File")
    uploaded_audio_file = st.file_uploader("Select a file", type=["wav", "mp3", "m4a", "ogg"], label_visibility="collapsed")
    
    if uploaded_audio_file:
        if st.button("Add Uploaded Audio"):
            recording_id = str(uuid.uuid4())
            st.session_state.voice_recordings.append({
                "id": recording_id,
                "bytes": uploaded_audio_file.getvalue(),
                "source": "upload",
                "filename": uploaded_audio_file.name
            })
            st.rerun()

    if st.session_state.voice_recordings:
        st.markdown("##### Your Audio Clips")
        for i, rec in enumerate(st.session_state.voice_recordings):
            col1, col2 = st.columns([4, 1])
            with col1:
                if rec['source'] == 'upload':
                    st.caption(f"Uploaded: `{rec['filename']}`")
                st.audio(rec['bytes'])
            with col2:
                if st.button("✖️", key=f"delete_{rec['id']}", help="Delete this clip"):
                    st.session_state.voice_recordings.pop(i)
                    st.rerun()
    
    st.markdown("---")

    st.markdown("##### 3. Upload Medicine Image")
    uploaded_file = st.file_uploader("Upload pill strap image (optional)", type=["png", "jpg", "jpeg"], label_visibility="collapsed")
    
    st.markdown("---")

    run_button = st.button("Analyze")

if run_button:
    combined_user_text = text_input.strip()
    transcribed_texts = []

    if not st.session_state.voice_recordings and not text_input and not uploaded_file:
        st.warning("Please provide symptoms via text/voice or upload an image.")
        st.stop()

    with st.spinner("Transcribing audio... Please wait."):
        for i, rec in enumerate(st.session_state.voice_recordings):
            temp_audio_path = f"temp_audio_{rec['id']}.wav"
            with open(temp_audio_path, "wb") as f:
                f.write(rec['bytes'])
            
            transcribed_text = transcriber.transcribe_audio_file(temp_audio_path)
            transcribed_texts.append(transcribed_text)
            
            if os.path.exists(temp_audio_path):
                os.remove(temp_audio_path)

    if transcribed_texts:
        combined_user_text += "\n" + "\n".join(transcribed_texts)
        combined_user_text = combined_user_text.strip()

    with st.spinner("Processing — this may take a few seconds..."):
        image_path = None
        if uploaded_file is not None:
            temp_image_path = f"temp_image_{uuid.uuid4()}.jpg"
            with open(temp_image_path, "wb") as f:
                f.write(uploaded_file.getvalue())
            image_path = temp_image_path

        result = pipeline.run(
            user_text=combined_user_text,
            image_path=image_path,
            top_k=5
        )

        card = result.get("card", {})
        ocr_text = card.get("ocr_text", "")
        llm_response = card.get("llm_output", "Error: Could not get LLM response.")

        if ocr_text:
            st.code(f"--- OCR Text Extracted ---\n{ocr_text}")
        
        st.markdown("---")
        
        st.markdown(f"### Final Analysis\n\n{llm_response}")

        if image_path and os.path.exists(image_path):
            os.remove(image_path)