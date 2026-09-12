import os
import json
import datetime
import streamlit as st

# --- SECRETS CONFIGURATION ---
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

# Updated Name to GR-Agent
st.set_page_config(page_title="GR-Agent | Academic Co-Pilot", page_icon="🎓", layout="wide")

# --- DATABASE LOGIC (Announcements & Schedules) ---
ANNOUNCEMENT_FILE = "announcements.json"
SCHEDULES_FILE = "schedules.json"

DEFAULT_SCHEDULES = {
    "classes": "**Monday:** OOP & DLD\n\n**Tuesday:** Math-II & Multivariable Calculus\n\n**Wednesday:** Probability & Pak Studies",
    "annual": "**Spring 2026:** Feb 09 - June 23\n\n**Summer 2026:** June 29 - Sept 18",
    "exams": "**Mid Terms:** April 06 - 10\n\n**Finals:** June 08 - 12",
    "deadlines": "No immediate deadlines uploaded."
}

def load_announcements():
    if os.path.exists(ANNOUNCEMENT_FILE):
        with open(ANNOUNCEMENT_FILE, "r") as f:
            return json.load(f)
    return []

def save_announcement(text, link, image_path):
    anns = load_announcements()
    anns.append({"text": text, "link": link, "image": image_path, "date": str(datetime.date.today())})
    with open(ANNOUNCEMENT_FILE, "w") as f:
        json.dump(anns, f)

def load_schedules():
    if os.path.exists(SCHEDULES_FILE):
        with open(SCHEDULES_FILE, "r") as f:
            return json.load(f)
    return DEFAULT_SCHEDULES

def save_schedules(data):
    with open(SCHEDULES_FILE, "w") as f:
        json.dump(data, f)

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
    
    with st.expander("📢 Announcements"):
        anns = load_announcements()
        if not anns:
            st.info("No new announcements at this time.")
        for ann in reversed(anns): 
            st.caption(f"Posted: {ann.get('date', '')}")
            if ann.get("text"):
                st.markdown(f"{ann['text']}")
            if ann.get("link"):
                st.markdown(f"[🔗 Click here for more info]({ann['link']})")
            if ann.get("image") and os.path.exists(ann["image"]):
                st.image(ann["image"])
            st.markdown("---")

    # Load dynamic schedules
    sched_data = load_schedules()

    with st.expander("📌 Classes Schedule"):
        st.info(sched_data["classes"])
    with st.expander("📆 Annual Schedule"):
        st.info(sched_data["annual"])
    with st.expander("📝 Exams Schedule"):
        st.info(sched_data["exams"])
    with st.expander("⏰ Deadlines"):
        st.warning(sched_data["deadlines"])
        
    # Admin: Update Schedules dynamically
    with st.expander("⚙️ Admin: Update Schedules"):
        new_classes = st.text_area("Classes Schedule", sched_data["classes"], height=100)
        new_annual = st.text_area("Annual Schedule", sched_data["annual"], height=100)
        new_exams = st.text_area("Exams Schedule", sched_data["exams"], height=100)
        new_deadlines = st.text_area("Deadlines", sched_data["deadlines"], height=100)
        
        if st.button("Save Schedules"):
            save_schedules({
                "classes": new_classes,
                "annual": new_annual,
                "exams": new_exams,
                "deadlines": new_deadlines
            })
            st.success("Schedules updated successfully!")
            st.rerun()

    with st.expander("⚙️ Admin: Post Announcement"):
        ann_text = st.text_area("Message / Alert Text")
        ann_link = st.text_input("Optional Link (URL)")
        ann_img = st.file_uploader("Optional Image", type=["png", "jpg", "jpeg"])
        
        if st.button("Post Announcement"):
            img_path = ""
            if ann_img:
                img_path = f"uploaded_{ann_img.name}"
                with open(img_path, "wb") as f:
                    f.write(ann_img.getbuffer())
            save_announcement(ann_text, ann_link, img_path)
            st.success("Announcement posted successfully!")
            st.rerun()

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
# Updated Name to GR-Agent
st.title("🎓 GR-Agent: Your Academic Co-Pilot")
for message in conv.get_history():
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if user_question := st.chat_input("Ask a question..."):
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
