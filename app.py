import os
import datetime
import streamlit as st

if "GEMINI_API_KEY" in st.secrets:
    os.environ["GEMINI_API_KEY"] = st.secrets["GEMINI_API_KEY"]

if not os.getenv("GEMINI_API_KEY"):
    st.error("🚨 GEMINI_API_KEY is missing! Add it to Streamlit Secrets.")
    st.stop()

from backend.conversation import ConversationManager
from backend.document_processor import process_document
from backend.document_store import add_document, get_documents, load_documents

# Load Backend Data
load_documents()

st.set_page_config(page_title="UniAgent | Academic Co-Pilot", page_icon="🎓", layout="wide")

# --- AUTO-CATEGORIZATION LOGIC ---
def categorize_doc(title):
    title_lower = title.lower()
    if any(kw in title_lower for kw in ["oop", "object", "c++"]): return "Object-Oriented Programming"
    if any(kw in title_lower for kw in ["dld", "digital", "logic"]): return "Digital Logic Design"
    if any(kw in title_lower for kw in ["calculus", "math"]): return "Calculus & Mathematics"
    if any(kw in title_lower for kw in ["discrete", "structure"]): return "Discrete Structures"
    if any(kw in title_lower for kw in ["probability", "statistics"]): return "Probability & Statistics"
    if any(kw in title_lower for kw in ["ideology", "pakistan"]): return "Pak Studies"
    if any(kw in title_lower for kw in ["schedule", "timetable", "calendar"]): return "Schedules & Calendars"
    return "General Materials"

if "manager" not in st.session_state:
    st.session_state.manager = ConversationManager()
    st.session_state.current_conv = st.session_state.manager.get_or_create("student_session")

conv = st.session_state.current_conv

# --- SIDEBAR UI ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3176/3176378.png", width=60)
    st.title("My Workspace")
    
    # Portion 1: Schedules & Alerts
    st.markdown("### 📅 Schedules & Alerts")
    with st.expander("📌 Classes Schedule"):
        st.info("**Monday:** OOP & DLD\n\n**Tuesday:** Math-II & Multivariable Calculus\n\n**Wednesday:** Probability & Pak Studies")
    with st.expander("📆 Annual Schedule"):
        st.info("**Spring 2026:** Feb 09 - June 23\n\n**Summer 2026:** June 29 - Sept 18")
    with st.expander("📝 Exams Schedule"):
        st.info("**Mid Terms:** April 06 - 10\n\n**Finals:** June 08 - 12")
    with st.expander("⏰ Deadlines"):
        st.warning("No immediate deadlines uploaded.")

    st.markdown("---")
    
    # Portion 2: Courses & Admin Upload
    st.markdown("### 📚 Courses Hub")
    uploaded_files = st.file_uploader("Admin: Upload PDF Syllabi/Slides", accept_multiple_files=True, type=["pdf"])
    
    if st.button("Process & Categorize Documents"):
        if uploaded_files:
            with st.spinner("Ingesting into RAG..."):
                for uploaded_file in uploaded_files:
                    temp_path = os.path.join(".", uploaded_file.name)
                    with open(temp_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    try:
                        doc = process_document(temp_path)
                        add_document(doc)
                    except Exception as e:
                        st.warning(f"Could not process {uploaded_file.name}: {e}")
                    finally:
                        if os.path.exists(temp_path):
                            os.remove(temp_path)
                st.success("Documents integrated and categorized!")

    # Display Auto-Categorized Documents
    docs = get_documents()
    categorized_docs = {}
    for d in docs:
        cat = categorize_doc(d.title)
        if cat not in categorized_docs: categorized_docs[cat] = []
        categorized_docs[cat].append(d.title)
        
    for cat, titles in categorized_docs.items():
        with st.expander(f"📁 {cat}"):
            for t in titles:
                st.caption(f"📄 {t}")

# --- MAIN CHAT INTERFACE ---
st.title("🎓 UniAgent: Your Academic Co-Pilot")
for message in conv.get_history():
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if user_question := st.chat_input("E.g., Explain the concept of binary digits in DLD..."):
    with st.chat_message("user"):
        st.markdown(user_question)
    
    with st.chat_message("assistant"):
        with st.spinner("Analyzing course materials..."):
            try:
                response = conv.ask(user_question)
                st.markdown(response.answer)
                if response.sources:
                    st.caption("✅ Sources: " + ", ".join([s.document for s in response.sources]))
            except Exception as e:
                st.error(f"Agent Error: {str(e)}")
