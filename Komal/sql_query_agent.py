import streamlit as st
import openai
import os
from dotenv import load_dotenv
import sqlite3
import pandas as pd
import json

# Load environment variables from .env file
load_dotenv()
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_BASE_URL = os.getenv('OPENAI_BASE_URL')

# Configure OpenAI client
openai.api_key = OPENAI_API_KEY
if OPENAI_BASE_URL:
    openai.base_url = OPENAI_BASE_URL

# Set page configuration
st.set_page_config(page_title="SQL Query Generator", layout="wide")
st.header("Database Query Assistant")

# Sample database schema - this would be replaced with your actual schema
SAMPLE_SCHEMA = """
Table: campaign_site_ad_for_ecpm_update
Columns:
  - ga_campaign_id (BigInteger) - Ga Campaign ID
  - pm_ad_id (BigInteger) - Pm Ad ID
  - pm_site_id (BigInteger) - Pm Site ID
  - pub_id (BigInteger) - Pub ID

Table: wrapper_abtest_groupsize
Columns:
  - id (Integer, Primary Key) - ID
  - name (Text) - Name
  - description (Text) - Description
  - display_name (Text) - Display Name

Table: wrapper_abtest_type
Columns:
  - id (Integer, Primary Key) - ID
  - name (Text) - Name
  - description (Text) - Description
  - display_name (Text) - Display Name

Table: wrapper_ad_integration_type
Columns:
  - id (Integer, Primary Key) - ID
  - platform_id (Integer) - Platform ID
  - integration_type (Text) - Integration Type
  - method (Text) - Method
  - endpoint (Text) - Endpoint
  - endpoint_name (Text) - Endpoint Name
  - creation_time (DateTimeWithLocalTZ) - Creation Time
  - last_modified (DateTimeWithLocalTZ) - Last Modified

Table: wrapper_ad_parameter_dependency_map
Columns:
  - id (Integer, Primary Key) - ID
  - parent_object_group (Integer) - Parent Object Group
  - child_object_group (Integer) - Child Object Group

Table: wrapper_ad_parameter_group
Columns:
  - id (Integer, Primary Key) - ID
  - name (Text) - Name

Table: wrapper_ad_parameter_tag_type_mapping
Columns:
  - id (BigInteger, Primary Key) - ID
  - parameter_id (BigInteger) - Parameter ID
  - tag_type_id (Integer) - Tag Type ID

Table: wrapper_ad_pod
Columns:
  - id (BigInteger, Primary Key) - ID
  - version_id (BigInteger) - Version ID
  - pod_type (Text) - Pod Type
  - ad_slots_config (Text) - Ad Slots Config
  - s2s_ad_slots_config (Text) - S2s Ad Slots Config
  - targeting (Text) - Targeting
  - creation_time (DateTimeWithLocalTZ) - Creation Time

Table: wrapper_ad_unit_config
Columns:
  - id (BigInteger, Primary Key) - ID
  - profile_id (BigInteger, Foreign Key to wrapper_profile.id) - Profile ID
  - ad_unit_id (BigInteger) - Ad Unit ID
  - config_id (Integer) - Config ID
  - value (Text) - Value

Table: wrapper_ad_unit_format
Columns:
  - id (Integer, Primary Key) - ID
  - name (Text) - Name
  - description (Text) - Description
  - display_name (Text) - Display Name

Table: wrapper_global_code_version
Columns:
  - id (BigInteger, Primary Key) - ID
  - is_live (Integer) - Is Live
  - prebid_base_version (Text) - Prebid Base Version
  - release_date (DateTimeWithLocalTZ) - Release Date
  - release_name (Text) - Release Name
  - release_notes_url (Text) - Release Notes URL
  - release_summary (Text) - Release Summary (details about this release)
  - release_type_id (Integer) - Release Type ID
  - snapshot_json (Text) - Snapshot Json
  - is_disabled (Integer) - Is Disabled (This column is used for disabling OpenWrap release versions)

Table: wrapper_live_code
Columns:
  - id (BigInteger, Primary Key) - ID
  - status (Text) - Status
  - created_at (DateTimeWithLocalTZ) - Created At
  - updated_at (DateTimeWithLocalTZ) - Updated At
  - version (Text) - Version of the live code
  - author (Text) - The author of the live code
  - is_active (Boolean) - Is Active (Indicates if the code version is currently active)

Table: wrapper_status
Columns:
  - cdn_refresh_id (BigInteger) - Cdn Refresh ID
  - modification_time (DateTimeWithLocalTZ) - Modification Time
  - status (Text) - Status (this shows status of wrapper, it could be live or staging or draft)
  - version_id (BigInteger, Foreign Key to wrapper_version.id) - Version ID

Table: wrapper_profile
Columns:
  - id (BigInteger, Primary Key) - ID
  - is_disabled (Integer) - Is Disabled
  - name (Text) - Name
  - pub_id (BigInteger) - Pub ID
  - type (Boolean) - Type (1 means OpenWrap and 2 means IDhub or identity hub)
  - api_version (Integer) - Api Version
  - platform (Text) - Platform
  - is_action_required (Integer) - Is Action Required

Table: wrapper_version
Columns:
  - id (BigInteger, Primary Key) - ID
  - profile_id (BigInteger, Foreign Key to wrapper_profile.id) - Profile ID
  - comment (Text) - Comment
  - creation_time (DateTimeWithLocalTZ) - Creation Time
  - display_version (BigInteger) - Display Version
  - last_modified (DateTimeWithLocalTZ) - Last Modified
  - script_size (Float) - Script Size

Table: wrapper_version_to_code_map
Columns:
  - version_id (BigInteger, Foreign Key to wrapper_version.id) - Version ID
  - global_code_version_id (BigInteger, Foreign Key to wrapper_global_code_version.id) - Global Code Version ID
  - code (Text) - Code
  - last_modified (DateTimeWithLocalTZ) - Last Modified

Table: wrapper_config_map
Columns:
  - id (BigInteger, Primary Key) - ID
  - config_id (Integer) - Config ID
  - entity_id (BigInteger) - Entity ID
  - entity_type_id (Integer) - Entity Type ID
  - partner_id (BigInteger) - Partner ID
  - value (Text) - Value
  - is_active (Boolean) - Is Active
  - test_config (Boolean) - Test Config
  - creation_time (DateTimeWithLocalTZ) - Creation Time
  - modification_time (DateTimeWithLocalTZ) - Modification Time
"""

# System prompt for the AI agent
SYSTEM_PROMPT = f"""
You are an advanced SQL query generator designed to help users interact with a database using natural language.

Your task is to convert English language instructions into valid SQL queries based on the database schema provided below.

Database Schema:
{SAMPLE_SCHEMA}

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

Examples:

User: "Show me all OpenWrap profiles"
Output: SELECT * FROM wrapper_profile WHERE type = 1;

User: "List the top 5 profiles by ID"
Output: SELECT * FROM wrapper_profile ORDER BY id DESC LIMIT 5;

User: "How many profiles are there for each platform?"
Output: 
SELECT 
    platform, 
    COUNT(id) AS profile_count 
FROM 
    wrapper_profile 
GROUP BY 
    platform;

User: "Show me all versions for a specific profile"
Output:
SELECT 
    wv.* 
FROM 
    wrapper_version wv 
WHERE 
    wv.profile_id = 123;

User: "Find all active configurations"
Output:
SELECT 
    wcm.* 
FROM 
    wrapper_config_map wcm 
WHERE 
    wcm.is_active = TRUE;

User: "Show me the latest version for each profile"
Output:
SELECT 
    wp.id AS profile_id,
    wp.name AS profile_name,
    MAX(wv.id) AS latest_version_id
FROM 
    wrapper_profile wp
JOIN 
    wrapper_version wv ON wp.id = wv.profile_id
GROUP BY 
    wp.id, wp.name;
"""

# Function to generate SQL query using OpenAI
def generate_sql_query(user_instruction, schema=SAMPLE_SCHEMA):
    try:
        # Create custom system prompt with the provided schema
        custom_system_prompt = SYSTEM_PROMPT
        if schema != SAMPLE_SCHEMA:
            custom_system_prompt = custom_system_prompt.replace(SAMPLE_SCHEMA, schema)
        
        # Call OpenAI API
        response = openai.chat.completions.create(
            model="(paid) gpt-4o-mini",  # Use an appropriate model
            messages=[
                {"role": "system", "content": custom_system_prompt},
                {"role": "user", "content": user_instruction}
            ],
            temperature=0.1  # Low temperature for more deterministic outputs
        )
        
        # Extract the generated SQL query
        sql_query = response.choices[0].message.content.strip()
        return sql_query
    
    except Exception as e:
        return f"Error generating SQL query: {str(e)}"

# Function to load custom schema from file
def load_schema_from_file(uploaded_file):
    try:
        content = uploaded_file.read().decode("utf-8")
        return content
    except Exception as e:
        return f"Error loading schema: {str(e)}"

# Function to execute SQL query against a SQLite database
def execute_query(query, db_path):
    try:
        conn = sqlite3.connect(db_path)
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    except Exception as e:
        return f"Error executing query: {str(e)}"

# Sidebar for configuration
with st.sidebar:
    st.title("Configuration")
    
    # Option to upload custom schema
    st.subheader("Database Schema")
    schema_option = st.radio("Schema Source", ["Use Sample Schema", "Upload Schema", "Enter Schema Manually"])
    
    custom_schema = SAMPLE_SCHEMA
    
    if schema_option == "Upload Schema":
        uploaded_schema = st.file_uploader("Upload Schema File", type=["txt", "sql", "json"])
        if uploaded_schema is not None:
            custom_schema = load_schema_from_file(uploaded_schema)
            st.success("Schema loaded successfully!")
    
    elif schema_option == "Enter Schema Manually":
        custom_schema = st.text_area("Enter Database Schema", SAMPLE_SCHEMA, height=300)
    
    # Option to connect to a real database
    st.subheader("Database Connection")
    use_real_db = st.checkbox("Connect to a real database")
    
    db_path = ":memory:"
    if use_real_db:
        db_path = st.text_input("Database Path", "example.db")

# Main content area
st.subheader("Ask your question in plain English")
user_instruction = st.text_area("What would you like to query?", height=100,
                               placeholder="Example: Show me all users who placed orders worth more than $100 last month")

# Generate button
if st.button("Generate SQL Query"):
    if user_instruction:
        with st.spinner("Generating SQL query..."):
            # Generate the SQL query
            sql_query = generate_sql_query(user_instruction, custom_schema)
            
            # Display the generated query
            st.subheader("Generated SQL Query")
            st.code(sql_query, language="sql")
            
            # Execute query if connected to a real database
            if use_real_db and db_path != ":memory:":
                st.subheader("Query Results")
                try:
                    results = execute_query(sql_query, db_path)
                    if isinstance(results, pd.DataFrame):
                        st.dataframe(results)
                    else:
                        st.error(results)  # Display error message
                except Exception as e:
                    st.error(f"Error executing query: {str(e)}")
    else:
        st.warning("Please enter a question or instruction.")

# Explanation section
with st.expander("How it works"):
    st.markdown("""
    This application uses AI to convert your natural language questions into SQL queries:
    
    1. **Input**: You describe what information you want from the database in plain English.
    2. **Processing**: The AI analyzes your request and the database schema.
    3. **Output**: A SQL query is generated that should retrieve the information you requested.
    
    For best results:
    - Be specific about what data you want
    - Mention table and column names if you know them
    - Specify any sorting or filtering criteria clearly
    
    If you have a custom database schema, you can upload it or enter it manually in the sidebar.
    """)

# Example queries section
with st.expander("Example queries"):
    st.markdown("""
    Try these example queries:
    
    - Show all OpenWrap profiles (type = 1)
    - Find all disabled profiles
    - List profiles that require action
    - Show the count of profiles for each platform
    - Find profiles for a specific publisher ID
    - List profiles sorted by name alphabetically
    - Count how many OpenWrap vs IDhub profiles exist
    - Show all versions for a specific profile
    - Find the latest version for each profile
    - List all active configurations
    - Show me all wrapper versions created in the last month
    - Find all global code versions that are currently live
    - List all ad unit configs for a specific profile
    - Show the relationship between wrapper versions and global code versions
    """)
