import streamlit as st
import json
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
import os
from dotenv import load_dotenv
from langchain.chains.question_answering import load_qa_chain
from langchain_openai import ChatOpenAI

# Load environment variables from .env file
load_dotenv()
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_BASE_URL = os.getenv('OPENAI_BASE_URL')

st.header("OpenWrap Query Assistant")
st.markdown("""
### Sample Questions:
- Show me all winning bids (wb=1)
- What are the CPM values for each partner?
- Which partners placed bids?
- Show bid details for a specific ad unit
""")

# Initialize session state
if 'vector_store' not in st.session_state:
    st.session_state.vector_store = None

with st.sidebar:
    st.title("Upload JSON Data")
    file = st.file_uploader("Upload a JSON file", type="json")

# Always show the input field
user_question = st.text_input("Ask a question about your document")

if file is not None:
    try:
        # Read and parse JSON data
        content = file.read().decode('utf-8')
        
        # Try to parse as a single JSON array first
        try:
            json_data = json.loads(content)
            if isinstance(json_data, list):
                json_objects = json_data
            else:
                json_objects = [json_data]
        except json.JSONDecodeError:
            # If that fails, try parsing line by line
            json_objects = [json.loads(line) for line in content.strip().split('\n') if line.strip()]
        
        if not json_objects:
            st.error("No valid JSON objects found in the file")
            st.stop()
            
        # Process and format JSON objects for better querying
        formatted_texts = []
        for obj in json_objects:
            # Create a more readable format for each impression
            formatted_text = f"Ad Impression Data:\n"
            formatted_text += f"Publisher ID: {obj.get('pubid')}\n"
            formatted_text += f"Page URL: {obj.get('purl')}\n"
            formatted_text += f"Timestamp: {obj.get('tst')}\n"
            formatted_text += f"Impression ID: {obj.get('iid')}\n"
            formatted_text += f"Country: {obj.get('geo', {}).get('cc')}\n"
            
            # Format slot information
            for idx, slot in enumerate(obj.get('s', [])):
                formatted_text += f"\nSlot {idx + 1}:\n"
                formatted_text += f"Ad Unit: {slot.get('au')}\n"
                formatted_text += f"Sizes: {', '.join(map(str, slot.get('sz', [])))}\n"
                
                # Format partner information
                for partner in slot.get('ps', []):
                    formatted_text += f"Partner: {partner.get('pn')}\n"
                    formatted_text += f"Bid ID: {partner.get('bidid')}\n"
                    formatted_text += f"Status: {'Bid' if partner.get('db') == 1 else 'No Bid'}\n"
                    formatted_text += f"Won Bid: {'Yes' if partner.get('wb') == 1 else 'No'}\n"
                    formatted_text += f"External CPM: {partner.get('eg', 0)}\n"
                    formatted_text += f"Net CPM: {partner.get('en', 0)}\n"
                    formatted_text += f"Currency: {partner.get('ocry', 'USD')}\n"
            
            formatted_texts.append(formatted_text)
        
        # Join all formatted texts
        text = '\n\n'.join(formatted_texts)
        st.success(f"Successfully processed {len(json_objects)} ad impressions")
        
    except json.JSONDecodeError as e:
        st.error(f"Error parsing JSON: {str(e)}")
        st.stop()
    except Exception as e:
        st.error(f"Error processing file: {str(e)}")
        st.stop()

    text_splitter = RecursiveCharacterTextSplitter(
        separators=["\n\n", "\n", " "],  # Split on double newline first to keep related info together
        chunk_size=1500,  # Increased chunk size to keep more context
        chunk_overlap=200,  # Increased overlap for better context preservation
        length_function=len
    )

    chunks = text_splitter.split_text(text)
    
    embeddings = OpenAIEmbeddings(
        openai_api_key=OPENAI_API_KEY,
        base_url=OPENAI_BASE_URL,
        model="(paid) text-embedding-3-large"  # Try a different free model
    )

    try:
        # Create embeddings and store them
        if not chunks:
            st.error("No text chunks were created from the JSON data")
            st.stop()
            
        st.session_state.vector_store = FAISS.from_texts(chunks, embeddings)
        st.success("JSON data processed successfully! You can now ask questions about it.")
    except Exception as e:
        st.error(f"Error creating embeddings: {str(e)}")
        st.session_state.vector_store = None
        st.stop()

# Handle questions
if user_question:
    if st.session_state.vector_store is not None:
        matches = st.session_state.vector_store.similarity_search(user_question)
        #st.write(matches)
        
        # Define the LLM
        llm = ChatOpenAI(
            openai_api_key=OPENAI_API_KEY,
            base_url=OPENAI_BASE_URL,
            model="(paid) gpt-4o-mini"
        )
        
        # Define the chain
        chain = load_qa_chain(llm, chain_type="stuff")
        response = chain.invoke({"input_documents": matches, "question": user_question})  # Using invoke instead of run
        st.write(response["output_text"])
    else:
        st.warning("Please upload a JSON file containing ad impression data first.")