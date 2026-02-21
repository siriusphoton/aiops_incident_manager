import os
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('db-tools')

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
DB_URL = os.getenv("DB_URL")

def get_db_connection():
    """Helper to get a database connection."""
    return psycopg2.connect(DB_URL)

# ============================================================================
# PHASE 1 TOOL: FETCH CONTEXT
# ============================================================================
def get_active_parents() -> list:
    """
    Fetches all currently active parent problems from the database.
    Used in Node 1 to provide context to the LLM.
    """
    logger.info("Fetching active parent problems from local database.")
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT parent_id, incident_number, summary, child_count 
                    FROM Active_Problems 
                    WHERE status = 'Active';
                """)
                results = cursor.fetchall()
                logger.info(f"Retrieved {len(results)} active problems.")
                return [dict(row) for row in results]
    except Exception as e:
        logger.error(f"Failed to fetch active parents: {e}", exc_info=True)
        return []

# ============================================================================
# PHASE 3 TOOLS: STATE UPDATES
# ============================================================================
def insert_new_parent(parent_sys_id: str, incident_number: str, summary: str) -> bool:
    """
    Inserts a newly discovered novel issue into the Active_Problems table.
    Used in Node 3B (Novel RAG Fixer).
    """
    logger.info(f"Inserting new parent {incident_number} ({parent_sys_id}) into database.")
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO Active_Problems (parent_id, incident_number, summary, status, child_count)
                    VALUES (%s, %s, %s, 'Active', 0)
                    ON CONFLICT (parent_id) DO NOTHING;
                """, (parent_sys_id, incident_number, summary))
            conn.commit()
            logger.info("Successfully inserted new parent problem.")
            return True
    except Exception as e:
        logger.error(f"Failed to insert new parent: {e}", exc_info=True)
        return False

def increment_child_count(parent_sys_id: str) -> int:
    """
    Increments the child count when a duplicate ticket is linked.
    Used in Node 3C (Group & Link) to trigger Phase 4 thresholds.
    Returns the new child count.
    """
    logger.info(f"Incrementing child count for parent {parent_sys_id}.")
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE Active_Problems
                    SET child_count = child_count + 1, updated_at = CURRENT_TIMESTAMP
                    WHERE parent_id = %s
                    RETURNING child_count;
                """, (parent_sys_id,))
                
                new_count = cursor.fetchone()
                if new_count:
                    logger.info(f"New child count for {parent_sys_id} is {new_count[0]}.")
                    return new_count[0]
                else:
                    logger.warning(f"Parent {parent_sys_id} not found in database.")
                    return 0
    except Exception as e:
        logger.error(f"Failed to increment child count: {e}", exc_info=True)
        return 0

# ============================================================================
# PRE-ROUTING SYNC TOOL
# ============================================================================
def close_active_parent(parent_sys_id: str) -> bool:
    """
    Marks a problem as 'Resolved' in the local DB if it was closed in ServiceNow.
    Used in Node 1 to prevent the 'Zombie Parent' flaw.
    """
    logger.info(f"Marking parent {parent_sys_id} as Resolved in local database.")
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE Active_Problems
                    SET status = 'Resolved', updated_at = CURRENT_TIMESTAMP
                    WHERE parent_id = %s;
                """, (parent_sys_id,))
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"Failed to close parent {parent_sys_id}: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    # Quick visual test
    print("Testing DB connection...")
    parents = get_active_parents()
    print(f"Active parents found: {len(parents)}")