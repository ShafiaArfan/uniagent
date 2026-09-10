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

# Initialize environment variables
load_dotenv()

# Get API key
try:
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
except (KeyError, FileNotFoundError):
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not GOOGLE_API_KEY:
    st.error("Google API Key not found. Please set it in .env or Streamlit Secrets.")
    st.stop()

os.environ["GOOGLE_API_KEY"] = GOOGLE_API_KEY

VECTOR_STORE_PATH = "faiss_index"
DATA_DIR = "data"

st.set_page_config(page_title="UniAgent | Academic Co-Pilot", page_icon="🎓", layout="wide")
st.title("🎓 UniAgent: Your Academic Co-Pilot")
st.markdown("Ask questions about your syllabus, timetable, or reference books.")

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "vector_store" not in st.session_state:
    st.session_state.vector_store = None

@st.cache_resource
def get_embeddings():
    return GoogleGenerativeAIEmbeddings(model="models/embedding-001")

def get_llm():
    return ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.3)

def process_documents(documents):
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = text_splitter.split_documents(documents)
    embeddings = get_embeddings()
    return FAISS.from_documents(chunks, embeddings)

def initialize_baseline_data():
    if os.path.exists(DATA_DIR) and len(os.listdir(DATA_DIR)) > 0:
        with st.spinner("Loading baseline academic data..."):
            loader = DirectoryLoader(DATA_DIR, glob="**/*.pdf", loader_cls=PyPDFLoader)
            documents = loader.load()
            if documents:
                vector_store = process_documents(documents)
                vector_store.save_local(VECTOR_STORE_PATH)
                st.session_state.vector_store = vector_store
                return True
    return False

def load_or_create_vector_store():
    embeddings = get_embeddings()
    if os.path.exists(VECTOR_STORE_PATH):
        try:
            st.session_state.vector_store = FAISS.load_local(
                VECTOR_STORE_PATH, 
                embeddings, 
                allow_dangerous_deserialization=True
            )
        except Exception:
            initialize_baseline_data()
    else:
        if not initialize_baseline_data():
            st.info("No baseline data found. Please upload documents via the sidebar.")

if st.session_state.vector_store is None:
    load_or_create_vector_store()

with st.sidebar:
    st.header("⚙️ Admin Controls")
    uploaded_files = st.file_uploader("Upload PDF Documents", accept_multiple_files=True, type=["pdf"])
    
    if st.button("Process & Update Agent"):
        if uploaded_files:
            with st.spinner("Processing new documents..."):
                all_new_docs = []
                for uploaded_file in uploaded_files:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                        tmp_file.write(uploaded_file.getvalue())
                        tmp_path = tmp_file.name
                    
                    loader = PyPDFLoader(tmp_path)
                    all_new_docs.extend(loader.load())
                    os.remove(tmp_path)
                
                new_vector_store = process_documents(all_new_docs)
                
                if st.session_state.vector_store is None:
                    st.session_state.vector_store = new_vector_store
                else:
                    st.session_state.vector_store.merge_from(new_vector_store)
                
                st.session_state.vector_store.save_local(VECTOR_STORE_PATH)
                st.success(f"Successfully integrated {len(uploaded_files)} new document(s)!")
        else:
            st.warning("Please upload files before processing.")

system_prompt = (
    "You are an academic co-pilot for university students. Use the retrieved context below to answer "
    "the student's question. If the answer is not in the context, explicitly say that you do not "
    "have that information in the current syllabus or schedule.\n\n"
    "Context: {context}"
)
prompt_template = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    ("human", "{input}"),
])

for message in st.session_state.chat_history:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if user_question := st.chat_input("Ask about your schedule or syllabus..."):
    with st.chat_message("user"):
        st.markdown(user_question)
    
    st.session_state.chat_history.append({"role": "user", "content": user_question})
    
    with st.chat_message("assistant"):
        if st.session_state.vector_store is None:
            st.error("The knowledge base is empty. Please upload documents.")
        else:
            with st.spinner("Searching records..."):
                try:
                    llm = get_llm()
                    retriever = st.session_state.vector_store.as_retriever(search_kwargs={"k": 4})
                    question_answer_chain = create_stuff_documents_chain(llm, prompt_template)
                    rag_chain = create_retrieval_chain(retriever, question_answer_chain)
                    
                    response = rag_chain.invoke({"input": user_question})
                    answer = response["answer"]
                    
                    st.markdown(answer)
                    st.session_state.chat_history.append({"role": "assistant", "content": answer})
                except Exception as e:
                    st.error(f"Error: {e}")
