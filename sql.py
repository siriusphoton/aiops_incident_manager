import os
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

load_dotenv()
DB_URL = os.getenv("DB_URL")

def get_db_connection():
    """Helper to get a database connection."""
    return psycopg2.connect(DB_URL)

while(True):
    user_query = input("Query:").strip()
    if not user_query:
        continue
        
    with get_db_connection() as conn:
        conn.autocommit = True 
        
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            try:
                cursor.execute(user_query)
                
                if cursor.description:
                    for row in cursor:
                        print(row)
                else:
                    print(f"OK. Rows affected: {cursor.rowcount}")
                    
            except Exception as e:
                print(f"Error: {e}")