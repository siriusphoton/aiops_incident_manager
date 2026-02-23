import logging
from langgraph.graph import StateGraph, END
from .state import AgentState
from .nodes import (
    node_1_context_and_sync,
    node_2a_escalation,
    node_2b_llm_triage,
    node_3a_pushback,
    node_3b_novel_rag_fixer,
    node_3c_group_and_link,
    node_4a_dynamic_escalation,
    node_4b_root_cause_triangulation
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

def route_after_node_3c(state: AgentState) -> str:
    """Condition C: Problem Threshold Check"""
    count = state.get("parent_child_count", 0)
    if count >= 3:
        logger.info(f"ROUTING: Volume threshold reached ({count}). Escalating to Phase 4.")
        return "node_4a_dynamic_escalation"
    
    logger.info(f"ROUTING: Linked to parent. Volume below threshold ({count}). Ending graph.")
    return END

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
    workflow.add_node("node_4a_dynamic_escalation", node_4a_dynamic_escalation)
    workflow.add_node("node_4b_root_cause_triangulation", node_4b_root_cause_triangulation)

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
    workflow.add_conditional_edges(
        "node_3c_group_and_link",
        route_after_node_3c,
        {
            "node_4a_dynamic_escalation": "node_4a_dynamic_escalation",
            END: END
        }
    )
    
    # Wire 4A directly to 4B, and 4B to END
    workflow.add_edge("node_4a_dynamic_escalation", "node_4b_root_cause_triangulation")
    workflow.add_edge("node_4b_root_cause_triangulation", END)
    # Compile the graph
    return workflow.compile()