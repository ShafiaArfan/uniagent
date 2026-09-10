import streamlit as st
import os
import tempfile
from dotenv import load_dotenv

from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_community.document_loaders import PyPDFLoader, DirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate

# Initialize environment variables (for local testing)
load_dotenv()

# Attempt to get API key from Streamlit Secrets (Cloud) or .env (Local)
try:
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
except (KeyError, FileNotFoundError):
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not GOOGLE_API_KEY:
    st.error("Google API Key not found. Please set it in .env or Streamlit Secrets.")
    st.stop()

os.environ["GOOGLE_API_KEY"] = GOOGLE_API_KEY

# --- CONFIGURATION ---
VECTOR_STORE_PATH = "faiss_index"
DATA_DIR = "data"

# Set up page configuration
st.set_page_config(page_title="UniAgent | Academic Co-Pilot", page_icon="🎓", layout="wide")
st.title("🎓 UniAgent: Your Academic Co-Pilot")
st.markdown("Ask questions about your syllabus, timetable, or reference books.")

# Initialize session state variables
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "vector_store" not in st.session_state:
    st.session_state.vector_store = None

# --- CORE FUNCTIONS ---

@st.cache_resource
def get_embeddings():
    """Initialize Google GenAI Embeddings (Cached for speed)"""
    return GoogleGenerativeAIEmbeddings(model="models/embedding-001")

def get_llm():
    """Initialize Gemini Flash for fast generation"""
    return ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.3)

def process_documents(documents):
    """Chunks text and returns a FAISS vector store"""
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = text_splitter.split_documents(documents)
    
    embeddings = get_embeddings()
    vector_store = FAISS.from_documents(chunks, embeddings)
    return vector_store

def initialize_baseline_data():
    """Loads default PDFs from the /data folder if no vector store exists"""
    if os.path.exists(DATA_DIR) and len(os.listdir(DATA_DIR)) > 0:
        with st.spinner("Loading baseline academic data..."):
            loader = DirectoryLoader(DATA_DIR, glob="**/*.pdf", loader_cls=PyPDFLoader)
            documents = loader.load()
            
            if documents:
                vector_store = process_documents(documents)
                # Save locally so we don't have to re-embed on every reload
                vector_store.save_local(VECTOR_STORE_PATH)
                st.session_state.vector_store = vector_store
                return True
    return False

def load_or_create_vector_store():
    """Loads existing FAISS index or creates a new one from the /data folder"""
    embeddings = get_embeddings()
    
    # Try to load existing local index first (saves API limits and time)
    if os.path.exists(VECTOR_STORE_PATH):
        try:
            st.session_state.vector_store = FAISS.load_local(
                VECTOR_STORE_PATH, 
                embeddings, 
                allow_dangerous_deserialization=True # Required for FAISS local loading
            )
        except Exception as e:
            st.warning(f"Could not load local index: {e}. Rebuilding...")
            initialize_baseline_data()
    else:
        # If no index exists, try to build from /data
        if not initialize_baseline_data():
            st.info("No baseline data found. Please upload documents via the sidebar.")

# Run initialization on startup
if st.session_state.vector_store is None:
    load_or_create_vector_store()

# --- SIDEBAR UI (Dynamic Uploads) ---
with st.sidebar:
    st.header("⚙️ Admin & CR Controls")
    st.markdown("Upload new schedules, syllabi, or exam formats here. The agent will learn them instantly.")
    
    uploaded_files = st.file_uploader("Upload PDF Documents", accept_multiple_files=True, type=["pdf"])
    
    if st.button("Process & Update Agent"):
        if uploaded_files:
            with st.spinner("Processing new documents..."):
                all_new_docs = []
                # Use temp files to handle Streamlit's UploadedFile objects with PyPDF
                for uploaded_file in uploaded_files:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                        tmp_file.write(uploaded_file.getvalue())
                        tmp_path = tmp_file.name
                    
                    loader = PyPDFLoader(tmp_path)
                    all_new_docs.extend(loader.load())
                    os.remove(tmp_path) # Clean up temp file
                
                # Create a new vector store for the new docs
                new_vector_store = process_documents(all_new_docs)
                
                if st.session_state.vector_store is None:
                    st.session_state.vector_store = new_vector_store
                else:
                    # Merge new vectors into the existing database
                    st.session_state.vector_store.merge_from(new_vector_store)
                
                # Save the updated store locally
                st.session_state.vector_store.save_local(VECTOR_STORE_PATH)
                st.success(f"Successfully integrated {len(uploaded_files)} new document(s)!")
        else:
            st.warning("Please upload files before processing.")

# --- MAIN CHAT INTERFACE ---

# System Prompt Template
system_prompt = (
    "You are an academic co-pilot for university students. Use the retrieved context below to answer "
    "the student's question. If the answer is not in the context, explicitly say that you do not "
    "have that information in the current syllabus or schedule, rather than guessing. "
    "Keep answers concise, actionable, and formatted clearly (use bullet points if needed).\n\n"
    "Context: {context}"
)
prompt_template = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    ("human", "{input}"),
])

# Display Chat History
for message in st.session_state.chat_history:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# User Input
if user_question := st.chat_input("Ask about your schedule, references, or syllabus..."):
    # Display user message immediately
    with st.chat_message("user"):
        st.markdown(user_question)
    
    # Add to history
    st.session_state.chat_history.append({"role": "user", "content": user_question})
    
    # Generate Response
    with st.chat_message("assistant"):
        if st.session_state.vector_store is None:
            st.error("The knowledge base is empty. Please upload documents in the sidebar first.")
        else:
            with st.spinner("Searching records..."):
                try:
                    llm = get_llm()
                    retriever = st.session_state.vector_store.as_retriever(search_kwargs={"k": 4})
                    
                    # Create the RAG chain
                    question_answer_chain = create_stuff_documents_chain(llm, prompt_template)
                    rag_chain = create_retrieval_chain(retriever, question_answer_chain)
                    
                    response = rag_chain.invoke({"input": user_question})
                    answer = response["answer"]
                    
                    st.markdown(answer)
                    st.session_state.chat_history.append({"role": "assistant", "content": answer})
                
                except Exception as e:
                    st.error(f"An error occurred while generating the response: {e}")
