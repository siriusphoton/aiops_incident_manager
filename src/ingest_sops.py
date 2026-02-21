import os
import json
import logging
import psycopg2
from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ingest-sops")

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# Constants
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOP_DIR = os.path.join(BASE_DIR, "docs", "sops")
DB_URL = os.getenv("DB_URL")

def get_db_connection():
    return psycopg2.connect(DB_URL)

def ingest_sops():
    logger.info("Initializing HuggingFace Embeddings (all-MiniLM-L6-v2)...")
    # This will download the model to your local machine on the first run
    embeddings = HuggingFaceEmbeddings(model_name="intfloat/e5-large-v2")
    
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1500,
        chunk_overlap=350,
        separators=["\n## ", "\n### ", "\n", " "]
    )

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Clear existing KB to prevent duplicates if run multiple times
        cursor.execute("TRUNCATE TABLE Knowledge_Base RESTART IDENTITY;")
        
        for filename in os.listdir(SOP_DIR):
            if not filename.endswith(".md"):
                continue
                
            file_path = os.path.join(SOP_DIR, filename)
            logger.info(f"Processing: {filename}")
            
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            chunks = text_splitter.split_text(content)
            
            for index, chunk in enumerate(chunks):
                # Generate 384-dimensional vector locally
                vector = embeddings.embed_query(chunk)
                
                cursor.execute(
                    """
                    INSERT INTO Knowledge_Base (sop_name, chunk_index, content, embedding)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (filename, index, chunk, vector)
                )
        
        conn.commit()
        logger.info("Successfully ingested all SOPs into pgvector.")

    except Exception as e:
        conn.rollback()
        logger.error(f"Ingestion failed: {e}", exc_info=True)
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    ingest_sops()