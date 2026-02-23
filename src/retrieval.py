import os
import json
import logging
import psycopg2
from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEmbeddings

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("vector-retrieval")

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
DB_URL = os.getenv("DB_URL")

# Initialize embeddings globally so it doesn't reload into memory on every query
logger.info("Loading embedding model into memory...")
embeddings = HuggingFaceEmbeddings(model_name="intfloat/e5-large-v2")

def get_db_connection():
    return psycopg2.connect(DB_URL)

def search_knowledge_base(query: str, k: int = 10) -> str:
    """
    Embeds the query and searches Postgres for the closest k chunks.
    Returns a JSON string array of dicts: [{sop_id, starting_line, text}]
    """
    logger.info(f"Performing vector search for query: '{query}'")
    
    try:
        # Generate the query vector
        query_vector = embeddings.embed_query(query)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # pgvector cosine distance operator is <=>
        # We order by distance ascending (closest first)
        sql = """
            SELECT id, sop_name, content 
            FROM Knowledge_Base 
            ORDER BY embedding <=> %s::vector 
            LIMIT %s;
        """
        cursor.execute(sql, (query_vector, k))
        results = cursor.fetchall()
        
        formatted_results = []
        for row in results:
            # Format requested by you
            formatted_results.append({
                "sop_id": row[1],
                "starting_line": 0, # Note: Chunk starting line logic omitted for brevity, using index 0
                "retrieved_text": row[2]
            })
            
        logger.info(f"Retrieved {len(formatted_results)} relevant chunks.")
        return json.dumps(formatted_results, indent=2)

    except Exception as e:
        logger.error(f"Retrieval failed: {e}", exc_info=True)
        return json.dumps({"error": str(e)})
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

if __name__ == "__main__":
    # Quick local test
    test_query = "my laptop is slow and i need a replacement"
    print(search_knowledge_base(test_query, k=10))