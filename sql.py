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
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(input("Query:"))
            for row in cursor:
                print(row)
