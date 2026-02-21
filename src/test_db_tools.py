import os
import logging
from dotenv import load_dotenv
import psycopg2
from db_tools import (
    get_active_parents,
    insert_new_parent,
    increment_child_count,
    close_active_parent,
    get_db_connection
)

# Setup basic logging for the test
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger("test-db")

# Dummy Data Constants
DUMMY_SYS_ID = "1234567890abcdef1234567890abcdef" # 32-char hex
DUMMY_INC_NUM = "INC9999999"
DUMMY_SUMMARY = "Test SAP Outage Hypothesis"

def run_db_tests():
    print("\n--- STARTING DB TOOLS TEST ---\n")

    # TEST 1: Insert New Parent
    print("1. Testing insert_new_parent()...")
    success = insert_new_parent(DUMMY_SYS_ID, DUMMY_INC_NUM, DUMMY_SUMMARY)
    if success:
        print("✅ Successfully inserted dummy parent.")
    else:
        print("❌ Failed to insert dummy parent.")
        return

    # TEST 2: Fetch Active Parents
    print("\n2. Testing get_active_parents()...")
    active_parents = get_active_parents()
    found = any(p['parent_id'] == DUMMY_SYS_ID for p in active_parents)
    if found:
        print(f"✅ Successfully fetched active parents. Found our dummy: {DUMMY_INC_NUM}")
    else:
        print("❌ Dummy parent not found in active list!")

    # TEST 3: Increment Child Count
    print("\n3. Testing increment_child_count()...")
    new_count = increment_child_count(DUMMY_SYS_ID)
    if new_count == 1:
        print(f"✅ Successfully incremented child count. New count is: {new_count}")
    else:
        print(f"❌ Failed to increment child count. Got: {new_count}")

    # TEST 4: Close Active Parent
    print("\n4. Testing close_active_parent()...")
    closed = close_active_parent(DUMMY_SYS_ID)
    if closed:
        print("✅ Successfully marked parent as 'Resolved'.")
    else:
        print("❌ Failed to close parent.")

    # TEST 5: Verify it's no longer 'Active'
    print("\n5. Verifying parent is removed from active list...")
    active_parents_post = get_active_parents()
    found_post = any(p['parent_id'] == DUMMY_SYS_ID for p in active_parents_post)
    if not found_post:
        print("✅ Success! Dummy parent is no longer in the active queries.")
    else:
        print("❌ Error: Dummy parent is still showing as active.")

    # CLEANUP: Remove dummy data from DB entirely
    print("\n--- CLEANING UP DUMMY DATA ---")
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM Active_Problems WHERE parent_id = %s;", (DUMMY_SYS_ID,))
            conn.commit()
        print("✅ Dummy data wiped. Database is pristine.")
    except Exception as e:
        print(f"❌ Cleanup failed: {e}")

    print("\n--- DB TOOLS TEST COMPLETE ---")

if __name__ == "__main__":
    run_db_tests()