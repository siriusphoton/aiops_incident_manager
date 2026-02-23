import logging
from langgraph.graph import StateGraph, END
from .state import AgentState
from .nodes import (
    node_1_context_and_sync,
    node_2a_escalation,
    node_2b_llm_triage,
    node_3a_pushback,
    node_3b_novel_rag_fixer,
    node_3c_group_and_link
)

logger = logging.getLogger('agent-graph')

# ============================================================================
# ROUTING LOGIC (CONDITIONAL EDGES)
# ============================================================================

def route_after_node_1(state: AgentState) -> str:
    """Condition A: The Bounce Router"""
    if state["reassignment_count"] >= 3:
        logger.info("ROUTING: Ticket is bouncing. Routing to Node 2A (Escalation).")
        return "node_2a_escalation"
    
    logger.info("ROUTING: Normal ticket. Routing to Node 2B (LLM Triage).")
    return "node_2b_llm_triage"

def route_after_node_2b(state: AgentState) -> str:
    """Condition B: The Execution Router based on LLM JSON output"""
    llm_class = state.get("llm_classification", {})
    
    match_id = llm_class.get("MATCH")
    missing_asset = llm_class.get("MISSING_ASSET", False)
    
    if match_id and match_id != "None" and match_id != "null":
        logger.info(f"ROUTING: Semantic match found ({match_id}). Routing to Node 3C (Group & Link).")
        return "node_3c_group_and_link"
        
    if missing_asset:
        logger.info("ROUTING: Missing Hardware Asset. Routing to Node 3A (Pushback).")
        return "node_3a_pushback"
        
    logger.info("ROUTING: Novel issue detected. Routing to Node 3B (RAG Fixer).")
    return "node_3b_novel_rag_fixer"

# ============================================================================
# BUILD THE GRAPH
# ============================================================================

def build_incident_graph():
    logger.info("Building the LangGraph workflow...")
    
    # 1. Initialize the Graph with our State schema
    workflow = StateGraph(AgentState)
    
    # 2. Add all our Phase 1, 2, and 3 Nodes
    workflow.add_node("node_1", node_1_context_and_sync)
    workflow.add_node("node_2a_escalation", node_2a_escalation)
    workflow.add_node("node_2b_llm_triage", node_2b_llm_triage)
    workflow.add_node("node_3a_pushback", node_3a_pushback)
    workflow.add_node("node_3b_novel_rag_fixer", node_3b_novel_rag_fixer)
    workflow.add_node("node_3c_group_and_link", node_3c_group_and_link)
    
    # 3. Define the Entry Point
    workflow.set_entry_point("node_1")
    
    # 4. Define the Conditional Edges
    workflow.add_conditional_edges(
        "node_1",
        route_after_node_1,
        {
            "node_2a_escalation": "node_2a_escalation",
            "node_2b_llm_triage": "node_2b_llm_triage"
        }
    )
    
    workflow.add_conditional_edges(
        "node_2b_llm_triage",
        route_after_node_2b,
        {
            "node_3a_pushback": "node_3a_pushback",
            "node_3b_novel_rag_fixer": "node_3b_novel_rag_fixer",
            "node_3c_group_and_link": "node_3c_group_and_link"
        }
    )
    
    # 5. Define Terminal Edges (For now, Phase 3 nodes just End)
    workflow.add_edge("node_2a_escalation", END)
    workflow.add_edge("node_3a_pushback", END)
    workflow.add_edge("node_3b_novel_rag_fixer", END)
    workflow.add_edge("node_3c_group_and_link", END) # We will change this to condition C in Phase 4
    
    # Compile the graph
    return workflow.compile()