from typing import TypedDict, Optional, List, Dict, Any

class AgentState(TypedDict):
    # --- Input Data ---
    incident_number: str                # e.g., "INC0000015"
    incident_json: Dict[str, Any]       # The full payload from ServiceNow
    reassignment_count: int             # Extracted for the Bounce Router
    
    # --- Database Context ---
    active_parents: List[Dict[str, Any]] # List of current outages from Postgres
    
    # --- LLM Outputs (Node 2B & 4B) ---
    llm_classification: Optional[Dict[str, Any]] # {MATCH, CATEGORY, MISSING_ASSET, IS_BLOCKER}
    root_cause_hypothesis: Optional[str]         # Generated during Triangulation
    
    # --- Execution Tracking ---
    action_taken: str                   # A human-readable log of what the graph actually did