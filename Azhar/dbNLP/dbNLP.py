import openai
import os
import sys
import time
import threading
import json
import requests
from dotenv import load_dotenv
from system_prompt import SYSTEM_PROMPT

# Load environment variables from .env file
load_dotenv()

# Get environment variables
API_KEY = os.getenv("API_KEY")
BASE_URL = os.getenv("BASE_URL")
MODEL_NAME = os.getenv("MODEL_NAME")
DATABASE_URL = os.getenv("DATABASE_URL")

def show_loading_animation():
    animation = ["Processing.", "Processing..", "Processing..."]
    i = 0
    while loading[0]:
        sys.stdout.write('\r' + animation[i % len(animation)])
        sys.stdout.flush()
        time.sleep(0.5)
        i += 1
    sys.stdout.write('\r')
    sys.stdout.flush()

def process_text(text):
    try:
        # Initialize the client with custom base URL
        client = openai.OpenAI(
            api_key=API_KEY,
            base_url=BASE_URL
        )
        
        # Start loading animation
        global loading
        loading = [True]
        loading_thread = threading.Thread(target=show_loading_animation)
        loading_thread.start()
        
        # Use the imported system prompt
        system_prompt = SYSTEM_PROMPT
        
        # Make API request
        prompt = f"Generate a SQL query for the following request:\n\n{text}"
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]
        )
        
        # Stop loading animation
        loading[0] = False
        loading_thread.join()
        
        result = response.choices[0].message.content.strip()
        query = None
        
        try:
            # Print raw response for debugging
            print("\nRaw API response:")
            print(result)
            
            # Parse the JSON result
            json_result = json.loads(result)
            # Extract and print only the query property
            query = json_result.get("query", "No query found in response")
            print("\n✅ SQL Query generated successfully!")
            print("\nQuery:", query)
            
            # Execute the query if valid
            if query and query != "No query found in response":
                try:
                    print("\nExecuting query on SQL Server...")
                    # Import necessary modules
                    from sqlalchemy import create_engine, text
                    import pandas as pd
                    
                    # Create SQLAlchemy engine
                    engine = create_engine(DATABASE_URL)
                    
                    # Execute the query and fetch results
                    with engine.connect() as connection:
                        result = connection.execute(text(query))
                        # Convert result to DataFrame for better display
                        df = pd.DataFrame(result.fetchall())
                        if not df.empty:
                            # Set column names if available
                            if result.keys():
                                df.columns = result.keys()
                            print("\nQuery Results:")
                            print(df)
                        else:
                            print("Query executed successfully, but returned no results.")
                    
                    print("✅ Query executed successfully!")
                except Exception as e:
                    print(f"❌ Error executing query: {str(e)}")
            
            return True
        
        except json.JSONDecodeError as e:
            print(f"\n⚠️ Could not parse JSON response. Error: {str(e)}")
            print("Raw result:", result)
            
            # Try to extract query with a fallback approach
            if "query" in result:
                try:
                    # Try to find the query part using string manipulation
                    start_idx = result.find('"query":') + 9  # Length of '"query": "'
                    if start_idx > 9:  # Found "query":
                        # Find the closing quote, accounting for escaped quotes
                        end_idx = start_idx
                        in_escape = False
                        for i in range(start_idx, len(result)):
                            if result[i] == '\\':
                                in_escape = not in_escape
                                continue
                            if result[i] == '"' and not in_escape:
                                end_idx = i
                                break
                            in_escape = False
                        
                        if end_idx > start_idx:
                            query = result[start_idx:end_idx]
                            print("\n✅ Extracted query using fallback method:")
                            print("\nQuery:", query)
                except Exception as ex:
                    print(f"Fallback extraction failed: {str(ex)}")
            
            if not query:
                return False
        
        return True
        
    except Exception as e:
        # Stop loading animation in case of error
        loading[0] = False
        loading_thread.join()
        
        print("\n❌ API request failed!")
        print("Error:", str(e))
        return False

if __name__ == "__main__":
    user_text = input("Enter your SQL query request: ")
    if user_text.strip():
        process_text(user_text.strip())
    else:
        print("No text provided. Exiting.")