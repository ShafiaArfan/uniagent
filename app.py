import os
import datetime
import streamlit as st

# 1. Secure API Key Loading
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

# 2. Page Configuration
st.set_page_config(page_title="UniAgent | Academic Co-Pilot", page_icon="🎓", layout="wide")

# 3. Hackathon Mock Schedule (For "What's Next" feature)
mock_schedule = {
    "Monday": "10:00 AM - Data Structures (Room 302)\n2:00 PM - Calculus (Room 101)",
    "Tuesday": "11:00 AM - Artificial Intelligence (Lab 2)",
    "Wednesday": "9:00 AM - Object-Oriented Programming (Room 405)",
    "Thursday": "1:00 PM - Digital Logic Design (Lab 1)",
    "Friday": "10:00 AM - Multi-variable Calculus (Room 101)"
}

# 4. Session State Initialization
if "manager" not in st.session_state:
    st.session_state.manager = ConversationManager()
    st.session_state.current_conv = st.session_state.manager.get_or_create("student_session")

conv = st.session_state.current_conv

# --- SIDEBAR: COURSERA-STYLE NAVIGATION ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3176/3176378.png", width=60)
    st.title("My Workspace")
    
    # Calendar Integration Demo
    st.markdown("### 📅 Schedule & Alerts")
    today = datetime.datetime.now().strftime("%A")
    st.info(f"**Today ({today}):**\n\n{mock_schedule.get(today, 'No classes today!')}")
    if st.button("🔔 What is my next class?"):
        conv.add_user_message("Based on my schedule, what is my next class?")
        conv.add_assistant_message(f"Your schedule for {today} is:\n{mock_schedule.get(today, 'Clear')}. Make sure to prepare your notes!")

    st.markdown("---")
    
    # Course Hub
    st.markdown("### 📚 Course Hub")
    course_selection = st.selectbox("Filter materials by course:", ["All Courses", "Calculus", "OOP", "AI", "Digital Logic"])
    
    # Admin Uploads
    with st.expander("⚙️ Admin: Upload Course Materials"):
        uploaded_files = st.file_uploader("Upload PDF Syllabi/Slides", accept_multiple_files=True, type=["pdf"])
        if st.button("Process Documents"):
            if uploaded_files:
                with st.spinner("Processing..."):
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
                    st.success("Documents integrated!")
    
    # Loaded Docs List
    st.markdown("**Currently Loaded Docs:**")
    stored_docs = get_documents()
    if stored_docs:
        for d in stored_docs:
            st.caption(f"📄 {d.title}")
    else:
        st.caption("No documents loaded.")

# --- MAIN CHAT INTERFACE ---
st.title("🎓 UniAgent: Your Academic Co-Pilot")
st.markdown("Ask anything about your syllabus, deadlines, or upcoming lectures.")

# Render Chat History
for message in conv.get_history():
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat Input & AI Processing
if user_question := st.chat_input("E.g., What are the midterm topics for Calculus?"):
    with st.chat_message("user"):
        st.markdown(user_question)
    
    with st.chat_message("assistant"):
        with st.spinner("Analyzing course materials..."):
            try:
                response = conv.ask(user_question)
                st.markdown(response.answer)
                
                # Source Citation Guardrail
                if response.sources:
                    source_text = ", ".join([f"{s.document} (Pgs: {s.pages[:3]})" for s in response.sources])
                    st.caption(f"✅ Grounded in: {source_text}")
                elif response.grounded == False:
                    st.warning("⚠️ This answer could not be verified against uploaded course materials.")
            except Exception as e:
                st.error(f"Agent Error: {str(e)}")
