import streamlit as st
import os
from dotenv import load_dotenv
import glob
import json
import mysql.connector
import pandas as pd
from datetime import datetime
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
import openai
import sys

# Add the knowledgeBase directory to the Python path
knowledgebase_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "knowledgeBase")
if knowledgebase_dir not in sys.path:
    sys.path.append(knowledgebase_dir)

# Import the schema from system_prompt.py
from system_prompt import SAMPLE_SCHEMA

# Load environment variables from .env file
load_dotenv()
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_BASE_URL = os.getenv('OPENAI_BASE_URL')

# Configure OpenAI client
openai.api_key = OPENAI_API_KEY
if OPENAI_BASE_URL:
    openai.base_url = OPENAI_BASE_URL

# Database configuration
DB_CONFIG = {
    'host': '10.172.96.13',
    'user': 'kdbuser',
    'password': 'KdBuSeR12!',
    'database': 'giym'
}

# Set page configuration
st.set_page_config(page_title="RAG Knowledge Base Chat Assistant with DB", layout="wide")
st.header("Knowledge Base Chat Assistant with Database Integration")

# Initialize session state variables
if 'vector_store' not in st.session_state:
    st.session_state.vector_store = None
if 'processing_done' not in st.session_state:
    st.session_state.processing_done = False
if 'db_connected' not in st.session_state:
    st.session_state.db_connected = False
if 'db_schema' not in st.session_state:
    st.session_state.db_schema = None
if 'query_results' not in st.session_state:
    st.session_state.query_results = None

# Function to connect to MySQL database
def connect_to_database():
    try:
        # Connect to the MySQL database
        conn = mysql.connector.connect(**DB_CONFIG)
        st.session_state.db_connected = True
        return conn
    except Exception as e:
        st.error(f"Error connecting to database: {str(e)}")
        return None

# Function to fetch table schema from database
def fetch_database_schema():
    try:
        # First try to use the schema from system_prompt.py
        if SAMPLE_SCHEMA:
            # Convert the schema string to a structured format
            schema_data = []
            current_table = None
            current_columns = []
            
            for line in SAMPLE_SCHEMA.strip().split('\n'):
                if line.startswith('Table:'):
                    # If we were processing a table, add it to the schema data
                    if current_table:
                        schema_data.append({
                            "table_name": current_table,
                            "columns": current_columns
                        })
                    
                    # Start a new table
                    current_table = line.replace('Table:', '').strip()
                    current_columns = []
                
                elif line.strip().startswith('-') and current_table:
                    # This is a column definition
                    col_line = line.strip()[2:].strip()  # Remove the dash and spaces
                    
                    # Parse the column information
                    parts = col_line.split(' - ')
                    if len(parts) >= 2:
                        col_def = parts[0].strip()
                        col_desc = parts[1].strip() if len(parts) > 1 else ""
                        
                        # Extract name and type
                        name_type = col_def.split(' (', 1)
                        if len(name_type) == 2:
                            name = name_type[0].strip()
                            type_info = name_type[1].rstrip(')')
                            
                            # Check if it's a primary key or foreign key
                            is_primary = "Primary Key" in type_info
                            is_foreign = "Foreign Key" in type_info
                            
                            # Clean up the type
                            col_type = type_info.split(',')[0].strip()
                            
                            # Add the column to the current table
                            current_columns.append({
                                "name": name,
                                "type": col_type,
                                "is_primary": is_primary,
                                "is_foreign": is_foreign,
                                "description": col_desc
                            })
            
            # Add the last table if there is one
            if current_table and current_columns:
                schema_data.append({
                    "table_name": current_table,
                    "columns": current_columns
                })
            
            st.session_state.db_schema = schema_data
            return schema_data
            
        # If system_prompt.py schema is not available, try the JSON file
        schema_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "knowledgeBase", "db_schema.json")
        if os.path.exists(schema_path):
            with open(schema_path, 'r', encoding='utf-8') as file:
                schema_data = json.load(file)
                st.session_state.db_schema = schema_data
                return schema_data
        else:
            st.warning("Schema not found in system_prompt.py or db_schema.json. Attempting to fetch schema directly from database.")
            
            # If neither source is available, fetch schema directly from database
            conn = connect_to_database()
            if conn:
                cursor = conn.cursor(dictionary=True)
                
                # Get list of tables
                cursor.execute("SHOW TABLES")
                tables = cursor.fetchall()
                
                schema_data = []
                for table in tables:
                    table_name = list(table.values())[0]
                    
                    # Get columns for each table
                    cursor.execute(f"DESCRIBE {table_name}")
                    columns = cursor.fetchall()
                    
                    table_schema = {
                        "table_name": table_name,
                        "columns": []
                    }
                    
                    for column in columns:
                        col_info = {
                            "name": column["Field"],
                            "type": column["Type"],
                            "is_primary": column["Key"] == "PRI",
                            "is_foreign": column["Key"] == "MUL"
                        }
                        table_schema["columns"].append(col_info)
                    
                    schema_data.append(table_schema)
                
                cursor.close()
                conn.close()
                
                st.session_state.db_schema = schema_data
                return schema_data
            else:
                return None
    except Exception as e:
        st.error(f"Error fetching database schema: {str(e)}")
        return None

# Function to generate SQL query based on natural language input
def generate_sql_query(user_instruction):
    try:
        # Ensure we have the schema data
        schema_data = st.session_state.db_schema
        if not schema_data:
            schema_data = fetch_database_schema()
            if not schema_data:
                return "Error: Could not fetch database schema"
        
        # Format the schema for the prompt
        schema_text = "Database Schema:\n"
        for table in schema_data:
            table_name = table.get("table_name")
            columns = table.get("columns", [])
            
            schema_text += f"Table: {table_name}\nColumns:\n"
            for column in columns:
                name = column.get("name", "")
                col_type = column.get("type", "")
                is_primary = "Primary Key" if column.get("is_primary") else ""
                is_foreign = "Foreign Key" if column.get("is_foreign") else ""
                
                schema_text += f"  - {name} ({col_type}) {is_primary} {is_foreign}\n"
            
            schema_text += "\n"
        
        # Create system prompt for SQL generation
        system_prompt = f"""
        You are an advanced SQL query generator designed to help users interact with a database using natural language.

        Your task is to convert English language instructions into valid SQL queries based on the database schema provided below.

        {schema_text}

        Follow these guidelines:
        1. Generate only the SQL query without any explanations or markdown formatting.
        2. Ensure the query is syntactically correct and optimized.
        3. Use appropriate joins when querying across multiple tables.
        4. Include appropriate WHERE clauses to filter data as requested.
        5. If the user's request is ambiguous, make reasonable assumptions based on the schema.
        6. If the user's request cannot be fulfilled with the given schema, explain why and suggest alternatives.
        7. For aggregation requests (counts, averages, etc.), use appropriate SQL functions.
        8. Format the query with proper indentation for readability.
        9. Always use table aliases for clarity in joins.
        10. If the request involves sorting, use ORDER BY with appropriate direction (ASC/DESC).
        11. Limit results to 100 rows maximum to avoid overwhelming the system.
        """
        
        # Call OpenAI API
        response = openai.chat.completions.create(
            model="(paid) gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_instruction}
            ],
            temperature=0.1  # Low temperature for more deterministic outputs
        )
        
        # Extract the generated SQL query
        sql_query = response.choices[0].message.content.strip()
        return sql_query
    
    except Exception as e:
        return f"Error generating SQL query: {str(e)}"

# Function to execute SQL query and return results
def execute_query(query):
    try:
        conn = connect_to_database()
        if not conn:
            return None, "Could not connect to database"
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query)
        results = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return results, None
    except Exception as e:
        error_message = str(e)
        return None, error_message

# Function to fetch data from specific tables
def fetch_data_from_database():
    try:
        conn = connect_to_database()
        if not conn:
            return None, False
        
        cursor = conn.cursor(dictionary=True)
        
        # List of tables to query - can be customized based on requirements
        tables_to_query = [
            "wrapper_profile",
            "wrapper_config_map",
            "wrapper_global_code_version",
            "wrapper_ad_parameter"
        ]
        
        all_data = {}
        
        for table in tables_to_query:
            try:
                # Limit to 100 rows per table to avoid overwhelming the system
                cursor.execute(f"SELECT * FROM {table} LIMIT 100")
                results = cursor.fetchall()
                all_data[table] = results
            except Exception as e:
                st.warning(f"Error querying table {table}: {str(e)}")
        
        cursor.close()
        conn.close()
        
        # Convert the data to formatted text
        formatted_text = ""
        
        for table, data in all_data.items():
            formatted_text += f"# Table: {table}\n\n"
            
            if data and len(data) > 0:
                # Get column names from the first row
                columns = list(data[0].keys())
                
                # Create markdown table header
                formatted_text += "| " + " | ".join(columns) + " |\n"
                formatted_text += "| " + " | ".join(["---" for _ in columns]) + " |\n"
                
                # Add data rows
                for row in data[:10]:  # Limit to 10 rows in the display
                    formatted_text += "| " + " | ".join([str(row[col]) for col in columns]) + " |\n"
                
                if len(data) > 10:
                    formatted_text += "\n*Table truncated, showing 10 of " + str(len(data)) + " rows*\n"
            else:
                formatted_text += "*No data available for this table*\n"
            
            formatted_text += "\n\n"
        
        # Add schema information
        schema_data = fetch_database_schema()
        if schema_data:
            formatted_text += "# Database Schema\n\n"
            
            for table in schema_data:
                table_name = table.get("table_name")
                columns = table.get("columns", [])
                
                formatted_text += f"## Table: {table_name}\n\n"
                formatted_text += "| Column Name | Data Type | Primary Key | Foreign Key |\n"
                formatted_text += "|------------|-----------|-------------|-------------|\n"
                
                for column in columns[:20]:  # Limit to 20 columns per table
                    name = column.get("name", "")
                    col_type = column.get("type", "")
                    is_primary = "Yes" if column.get("is_primary") else "No"
                    is_foreign = "Yes" if column.get("is_foreign") else "No"
                    
                    formatted_text += f"| {name} | {col_type} | {is_primary} | {is_foreign} |\n"
                
                if "description" in table:
                    formatted_text += f"\n**Description**: {table['description']}\n"
                
                formatted_text += "\n\n"
        
        return formatted_text, True
    
    except Exception as e:
        st.error(f"Error fetching data from database: {str(e)}")
        return None, False

# Function to process knowledge base
def process_knowledge_base():
    try:
        documents = []
        
        # First, process static files from the knowledge base directory
        kb_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "knowledgeBase")
        
        if os.path.exists(kb_dir):
            # Get all files from the knowledge base directory
            all_files = []
            for ext in ["*.md", "*.txt", "*.json"]:
                all_files.extend(glob.glob(os.path.join(kb_dir, ext)))
            
            # Read and combine all files
            for file_path in all_files:
                file_name = os.path.basename(file_path)
                file_ext = os.path.splitext(file_path)[1].lower()
                
                # Skip the db_schema.json file as it's used separately
                if file_name == "db_schema.json":
                    continue
                
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
        
        # Now, fetch and process data from the database
        db_content, success = fetch_data_from_database()
        if success and db_content:
            documents.append(db_content)
            st.session_state.db_connected = True
        
        if not documents:
            st.error("No content was found to process")
            return False
        
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
            st.error("No text chunks were created")
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
        
        # Show success message
        if st.session_state.db_connected:
            st.success(f"Successfully processed knowledge base with real-time database data")
        else:
            st.success(f"Successfully processed knowledge base from static files only")
            
        return True
        
    except Exception as e:
        st.error(f"Error processing knowledge base: {str(e)}")
        return False

# Automatically process knowledge base on startup
with st.spinner("Processing knowledge base and connecting to database..."):
    # Fetch database schema first
    fetch_database_schema()
    # Then process knowledge base
    process_knowledge_base()

# Main interface with only the Query Database tab
(tab2,) = st.tabs(["Query Database"])

with tab2:
    st.subheader("Query Database")
    
    # User input for database query
    user_query = st.text_area("Enter your query in plain English", height=100, 
                           placeholder="Example: Show me all wrapper profiles where type is 1")
    
    # Generate and execute query button
    if st.button("Generate and Execute Query", key="execute_query"):
        if user_query:
            with st.spinner("Generating SQL query..."):
                # Generate SQL query from natural language
                sql_query = generate_sql_query(user_query)
                
                # Display the generated query
                st.subheader("Generated SQL Query")
                st.code(sql_query, language="sql")
                
                # Execute the query if it looks valid
                if sql_query and not sql_query.startswith("Error"):
                    with st.spinner("Executing query..."):
                        results, error = execute_query(sql_query)
                        
                        if error:
                            st.error(f"Error executing query: {error}")
                        elif results:
                            # Store results in session state
                            st.session_state.query_results = results
                            
                            # Display results
                            st.subheader("Query Results")
                            
                            # Convert to DataFrame for better display
                            df = pd.DataFrame(results)
                            st.dataframe(df)
                            
                            # Show number of rows returned
                            st.info(f"Query returned {len(results)} rows")
                        else:
                            st.info("Query executed successfully but returned no results")
                else:
                    st.error(sql_query)  # Display the error message
        else:
            st.warning("Please enter a query in plain English")
    
    # Show previous query results if available
    if st.session_state.query_results and not user_query:
        st.subheader("Previous Query Results")
        df = pd.DataFrame(st.session_state.query_results)
        st.dataframe(df)

# Add information about the implementation
with st.expander("About this RAG Implementation with Database Integration"):
    st.markdown("""
    This chat assistant uses Retrieval Augmented Generation (RAG) to provide answers based on your knowledge base with real-time database integration:
    
    1. **Database Integration**: The system connects to a MySQL database to fetch real-time data about various tables including wrapper profiles, configurations, and parameters.
    
    2. **Schema Understanding**: The system uses the database schema from the db_schema.json file to understand the structure of the database.
    
    3. **Combined Knowledge Sources**: The assistant uses both static files from the knowledgeBase directory and dynamic data from the database.
    
    4. **Retrieval**: When you ask a question, the system searches through the vector embeddings of all content to find the most relevant information.
    
    5. **Augmentation**: The retrieved content is used to augment the language model's knowledge.
    
    6. **Generation**: The language model generates a response based on both the retrieved content and its own knowledge.
    
    7. **Natural Language to SQL**: You can query the database directly using natural language in the "Query Database" tab.
    
    You can refresh the data from the database at any time by clicking the "Refresh Data from Database" button.
    """)
