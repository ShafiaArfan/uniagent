import streamlit as st
import os
from pypdf import PdfReader
import google.generativeai as genai

st.set_page_config(page_title="UniAgent | Academic Co-Pilot", page_icon="🎓", layout="wide")
st.title("🎓 UniAgent: Academic Co-Pilot")
st.markdown("Your AI assistant for BS program syllabi, reference books, and schedules.")

# API Key Resolution
api_key = st.secrets.get("GOOGLE_API_KEY") or os.getenv("GOOGLE_API_KEY")

with st.sidebar:
    st.header("⚙️ Configuration")
    user_key = st.text_input("Gemini API Key (optional override)", type="password")
    if user_key:
        api_key = user_key
    
    st.header("📄 Upload Documents")
    uploaded_files = st.file_uploader("Upload Syllabus / Notes / Timetable (PDF)", type=["pdf"], accept_multiple_files=True)

if not api_key:
    st.warning("Please provide a Gemini API Key in Streamlit Secrets or via the sidebar.")
    st.stop()

genai.configure(api_key=api_key)

# Session State for Document Context & Chat
if "doc_context" not in st.session_state:
    st.session_state.doc_context = ""
if "messages" not in st.session_state:
    st.session_state.messages = []

# Load Baseline Data from /data directory safely
def load_baseline_data():
    text = ""
    # The isdir check prevents the app from crashing if 'data' is accidentally created as a file
    if os.path.exists("data") and os.path.isdir("data"):
        for fname in os.listdir("data"):
            if fname.endswith(".pdf"):
                path = os.path.join("data", fname)
                try:
                    reader = PdfReader(path)
                    for page in reader.pages:
                        text += (page.extract_text() or "") + "\n"
                except Exception:
                    pass # Skip unreadable PDFs silently
    return text

if not st.session_state.doc_context:
    st.session_state.doc_context = load_baseline_data()

# Ingest Uploaded Documents
if uploaded_files:
    uploaded_text = ""
    for file in uploaded_files:
        try:
            reader = PdfReader(file)
            for page in reader.pages:
                uploaded_text += (page.extract_text() or "") + "\n"
        except Exception:
            st.sidebar.error(f"Could not read {file.name}")
            
    st.session_state.doc_context += "\n" + uploaded_text
    st.sidebar.success(f"Added {len(uploaded_files)} document(s) to knowledge base!")

# Display Conversation History
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Chat Input & Response Generation
if user_query := st.chat_input("Ask about your courses, timetable, or exams..."):
    st.chat_message("user").markdown(user_query)
    st.session_state.messages.append({"role": "user", "content": user_query})
    
    with st.chat_message("assistant"):
        with st.spinner("Analyzing coursework..."):
            try:
                # Updated to the new, active 3.6 Flash model
                model = genai.GenerativeModel("gemini-3.6-flash")
                prompt = f"""You are UniAgent, an academic co-pilot for university students.
Answer the student's question accurately using ONLY the context provided below.
If the information is not in the context, clearly state that it is not covered in the current syllabus or schedule.

ACADEMIC CONTEXT:
{st.session_state.doc_context[:250000]}

STUDENT QUESTION:
{user_query}
"""
                response = model.generate_content(prompt)
                reply = response.text
                st.markdown(reply)
                st.session_state.messages.append({"role": "assistant", "content": reply})
            except Exception as e:
                st.error(f"API Error: {e}. Please check your API key or network connection.")
