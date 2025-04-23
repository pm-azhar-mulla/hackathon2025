import streamlit as st
import os
from dotenv import load_dotenv
import glob
import json
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory

# Load environment variables from .env file
load_dotenv()
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_BASE_URL = os.getenv('OPENAI_BASE_URL')

# Set page configuration
st.set_page_config(page_title="RAG Knowledge Base Chat Assistant", layout="wide")
st.header("Knowledge Base Chat Assistant")

# Initialize session state variables
if 'vector_store' not in st.session_state:
    st.session_state.vector_store = None
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'processing_done' not in st.session_state:
    st.session_state.processing_done = False

# Function to process knowledge base
def process_knowledge_base():
    try:
        # Path to the knowledge base folder
        kb_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "knowledgeBase")
        
        if not os.path.exists(kb_dir):
            st.error(f"Knowledge base directory not found: {kb_dir}")
            return False
        
        # Get all files from the knowledge base directory
        all_files = []
        for ext in ["*.md", "*.txt", "*.json"]:
            all_files.extend(glob.glob(os.path.join(kb_dir, ext)))
        
        if not all_files:
            st.error("No files found in the knowledge base directory")
            return False
        
        # Read and combine all files
        documents = []
        for file_path in all_files:
            file_name = os.path.basename(file_path)
            file_ext = os.path.splitext(file_path)[1].lower()
            
            try:
                if file_ext == ".json":
                    # Process JSON files
                    with open(file_path, 'r', encoding='utf-8') as file:
                        json_data = json.load(file)
                        # Convert JSON to formatted text
                        if isinstance(json_data, dict) or isinstance(json_data, list):
                            content = f"# {file_name}\n\n```json\n{json.dumps(json_data, indent=2)}\n```\n"
                            documents.append(content)
                else:
                    # Process text and markdown files
                    with open(file_path, 'r', encoding='utf-8') as file:
                        content = file.read()
                        documents.append(f"# {file_name}\n\n{content}")
            except Exception as e:
                st.warning(f"Error processing file {file_name}: {str(e)}")
                continue
        
        # Combine all documents
        text = "\n\n".join(documents)
        
        # Split text into chunks
        text_splitter = RecursiveCharacterTextSplitter(
            separators=["\n## ", "\n### ", "\n#### ", "\n", " "],
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len
        )
        
        chunks = text_splitter.split_text(text)
        
        if not chunks:
            st.error("No text chunks were created from the knowledge base")
            return False
        
        # Create embeddings
        embeddings = OpenAIEmbeddings(
            openai_api_key=OPENAI_API_KEY,
            base_url=OPENAI_BASE_URL,
            model="(paid) text-embedding-3-large"
        )
        
        # Create vector store
        st.session_state.vector_store = FAISS.from_texts(chunks, embeddings)
        st.session_state.processing_done = True
        st.success(f"Successfully processed {len(all_files)} files into {len(chunks)} chunks")
        return True
        
    except Exception as e:
        st.error(f"Error processing knowledge base: {str(e)}")
        return False

# Automatically process knowledge base on startup if not already done
if not st.session_state.processing_done:
    with st.spinner("Processing knowledge base..."):
        process_knowledge_base()

# Main chat interface
st.subheader("Chat with your Knowledge Base")

# Display chat history
for message in st.session_state.chat_history:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("Ask a question about your knowledge base"):
    # Add user message to chat history
    st.session_state.chat_history.append({"role": "user", "content": prompt})
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Generate and display assistant response
    with st.chat_message("assistant"):
        if not st.session_state.vector_store:
            response = "The knowledge base could not be processed. Please check the error messages above."
            st.markdown(response)
            st.session_state.chat_history.append({"role": "assistant", "content": response})
        else:
            with st.spinner("Thinking..."):
                try:
                    # Create memory for conversation history
                    memory = ConversationBufferMemory(
                        memory_key="chat_history",
                        return_messages=True,
                        output_key="answer"
                    )
                    
                    # Convert chat history to the format expected by memory
                    for i in range(0, len(st.session_state.chat_history) - 1, 2):
                        if i + 1 < len(st.session_state.chat_history):
                            user_msg = st.session_state.chat_history[i]["content"]
                            assistant_msg = st.session_state.chat_history[i + 1]["content"]
                            memory.chat_memory.add_user_message(user_msg)
                            memory.chat_memory.add_ai_message(assistant_msg)
                    
                    # Create LLM
                    llm = ChatOpenAI(
                        openai_api_key=OPENAI_API_KEY,
                        base_url=OPENAI_BASE_URL,
                        model="(paid) gpt-4o-mini",
                        temperature=0.2
                    )
                    
                    # Create retrieval chain
                    retriever = st.session_state.vector_store.as_retriever(
                        search_type="similarity",
                        search_kwargs={"k": 5}
                    )
                    
                    qa_chain = ConversationalRetrievalChain.from_llm(
                        llm=llm,
                        retriever=retriever,
                        memory=memory,
                        return_source_documents=True,
                        verbose=True
                    )
                    
                    # Get response
                    result = qa_chain({"question": prompt})
                    response = result["answer"]
                    
                    # Display the response
                    st.markdown(response)
                    
                    # Add assistant response to chat history
                    st.session_state.chat_history.append({"role": "assistant", "content": response})
                    
                except Exception as e:
                    error_msg = f"Error generating response: {str(e)}"
                    st.error(error_msg)
                    st.session_state.chat_history.append({"role": "assistant", "content": error_msg})

# Add information about the implementation
with st.expander("About this RAG Implementation"):
    st.markdown("""
    This chat assistant uses Retrieval Augmented Generation (RAG) to provide answers based on your knowledge base:
    
    1. **Retrieval**: When you ask a question, the system searches through the vector embeddings of your markdown files to find the most relevant content.
    2. **Augmentation**: The retrieved content is used to augment the language model's knowledge.
    3. **Generation**: The language model generates a response based on both the retrieved content and its own knowledge.
    """)
