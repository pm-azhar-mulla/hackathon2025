import os
from dotenv import load_dotenv
import pymysql

# Load environment variables from .env file
load_dotenv()

# Database configuration - using the same config from the reference file
DB_CONFIG = {
    'host': '10.172.96.13',
    'user': 'kdbuser',
    'password': 'KdBuSeR12!',
    'database': 'giym',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

def connect_to_database():
    """Connect to the GIYM server database and return the connection object"""
    try:
        # Connect to the MySQL database
        conn = pymysql.connect(**DB_CONFIG)
        print(f"Successfully connected to GIYM server database at {DB_CONFIG['host']}!")
        return conn
    except Exception as e:
        print(f"Error connecting to database: {str(e)}")
        return None

def get_tables():
    """Get all tables from the GIYM database and print them"""
    conn = connect_to_database()
    if conn:
        try:
            with conn.cursor() as cursor:
                # Get list of tables
                cursor.execute("SHOW TABLES")
                tables = cursor.fetchall()
                
                print("\nTables in GIYM database:")
                print("------------------------")
                if tables:
                    for i, table in enumerate(tables, 1):
                        # The key is the first column name from SHOW TABLES
                        table_name = list(table.values())[0]
                        print(f"{i}. {table_name}")
                else:
                    print("No tables found in the database.")
        except Exception as e:
            print(f"Error fetching tables: {str(e)}")
        finally:
            conn.close()
            print("\nDatabase connection closed.")

if __name__ == "__main__":
    get_tables()
