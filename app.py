import os
import streamlit as st

# Bridge Streamlit Secrets into standard environment variables for Zayem's backend
if "GEMINI_API_KEY" in st.secrets:
    os.environ["GEMINI_API_KEY"] = st.secrets["GEMINI_API_KEY"]import streamlit as st
import os
from backend.conversation import ConversationManager
from backend.document_processor import process_document
from backend.document_store import add_document, get_documents, load_documents
from backend.config import Config

# Validate and load stored documents into memory
Config.validate()
load_documents()

st.set_page_config(page_title="UniAgent | Academic Co-Pilot", page_icon="🎓", layout="wide")
st.title("🎓 UniAgent: Academic Co-Pilot")
st.markdown("Your AI assistant for BS program syllabi, reference books, and schedules.")

# Initialize Conversation Manager in Session State
if "manager" not in st.session_state:
    st.session_state.manager = ConversationManager()
    st.session_state.current_conv = st.session_state.manager.get_or_create("student_session")

conv = st.session_state.current_conv

# --- SIDEBAR: Admin & CR Controls ---
with st.sidebar:
    st.header("⚙️ Admin & CR Controls")
    uploaded_files = st.file_uploader("Upload PDF Documents", accept_multiple_files=True, type=["pdf"])
    
    if st.button("Process & Update Agent"):
        if uploaded_files:
            with st.spinner("Processing documents..."):
                for uploaded_file in uploaded_files:
                    temp_path = os.path.join(".", uploaded_file.name)
                    with open(temp_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    
                    doc = process_document(temp_path)
                    add_document(doc)
                    os.remove(temp_path)
                
                st.success(f"Successfully integrated {len(uploaded_files)} document(s)!")
        else:
            st.warning("Please upload files before processing.")
            
    st.markdown("---")
    st.subheader("📚 Loaded Documents")
    stored_docs = get_documents()
    if stored_docs:
        for d in stored_docs:
            st.text(f"• {d.title} ({len(d.pages)} pages)")
    else:
        st.text("No documents loaded yet.")

# --- MAIN CHAT INTERFACE ---
for message in conv.get_history():
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if user_question := st.chat_input("Ask about your schedule, references, or syllabus..."):
    with st.chat_message("user"):
        st.markdown(user_question)
    
    with st.chat_message("assistant"):
        with st.spinner("Searching academic records..."):
            try:
                response = conv.ask(user_question)
                st.markdown(response.answer)
                
                if response.sources:
                    source_text = ", ".join([f"{s.document} (Pages: {s.pages})" for s in response.sources])
                    st.caption(f"📖 Sources: {source_text}")
            except Exception as e:
                st.error(f"An error occurred: {e}")
