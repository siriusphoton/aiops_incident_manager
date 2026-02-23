import os
import json
import logging
from dotenv import load_dotenv

# Import our custom tools
from servicenow_tools import ServiceNowClient, get_single_servicenow_record, create_servicenow_record, query_servicenow_records
from db_tools import get_active_parents, close_active_parent

from .state import AgentState


from pydantic import BaseModel, Field
from typing import Optional
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate

# Import our custom RAG and DB tools
from retrieval import search_knowledge_base
from db_tools import insert_new_parent, increment_child_count
from servicenow_tools import update_servicenow_record



from langchain_core.output_parsers import PydanticOutputParser

logger = logging.getLogger('agent-nodes')
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

# We initialize a global SN client for the nodes to share
sn_client = ServiceNowClient(
    instance=os.getenv("SN_INSTANCE"),
    username=os.getenv("SN_USERNAME"),
    password=os.getenv("SN_PASSWORD")
)

async def node_1_context_and_sync(state: AgentState) -> AgentState:
    """
    NODE 1: The Preparer.
    - Fetches the full incident payload from ServiceNow.
    - Checks Postgres for active parents, verifies them in SN, and closes resolved ones.
    - Loads the clean active parents list into the state.
    """
    logger.info(f"--- ENTERING NODE 1: Context & Sync for {state['incident_number']} ---")
    
    # 1. Fetch the incoming incident from ServiceNow
    inc_resp = await get_single_servicenow_record(sn_client, "incident", state["incident_number"])
    
    # Handle the dictionary response (remember we removed json.loads earlier!)
    if not inc_resp.get("success") or inc_resp.get("count", 0) == 0:
        raise ValueError(f"Could not fetch incident {state['incident_number']} from ServiceNow.")
    
    incident_data = inc_resp["data"][0]
    
    # Extract the reassignment count safely (defaults to 0 if empty)
    reassign_val = incident_data.get("reassignment_count", {}).get("value", "0")
    try:
        reassignment_count = int(reassign_val)
    except ValueError:
        reassignment_count = 0

    # 2. Prevent "Zombie Parents" (State Sync)
    current_active_parents = get_active_parents()
    cleaned_active_parents = []
    
    for parent in current_active_parents:
        parent_num = parent["incident_number"]
        parent_sys_id = parent["parent_id"]
        
        # Check SN to see if this parent is still active
        check_resp = await get_single_servicenow_record(sn_client, "incident", parent_num)
        if check_resp.get("success") and check_resp.get("count", 0) > 0:
            sn_state = check_resp["data"][0].get("state", {}).get("value", "")
            
            # In SN, state 7 is usually "Closed" and 6 is "Resolved"
            if sn_state in ["6", "7"]:
                logger.info(f"Zombie Parent detected! {parent_num} is closed in SN. Updating local DB.")
                close_active_parent(parent_sys_id)
            else:
                cleaned_active_parents.append(parent)
        else:
             # If we can't find it in SN, assume it's gone and keep our DB clean
             close_active_parent(parent_sys_id)

    # 3. Update the State
    logger.info(f"Node 1 Complete. Found {len(cleaned_active_parents)} true active parents.")
    
    return {
        "incident_json": incident_data,
        "reassignment_count": reassignment_count,
        "active_parents": cleaned_active_parents,
        "action_taken": "Synced state and fetched context."
    }

# ============================================================================
# PHASE 2: THE AGENTIC BRAIN
# ============================================================================

# Define the exact JSON structure we want Ollama to output
class TriageOutput(BaseModel):
    MATCH: Optional[str] = Field(description="The parent_id (sys_id) of the matching active incident from the provided list, or None if no match.")
    CATEGORY: str = Field(description="Predicted ITIL category (e.g., Network, Hardware, Software, Database, Inquiry).")
    MISSING_ASSET: bool = Field(description="True ONLY if CATEGORY is Hardware AND the cmdb_ci field is empty in the incident JSON.")
    IS_BLOCKER: bool = Field(description="True if the user's text indicates a complete inability to work or a severe business stoppage.")

async def node_2a_escalation(state: AgentState) -> AgentState:
    """
    NODE 2A: The Bounce Preventer.
    Triggers if a ticket has bounced between teams too many times.
    """
    logger.info(f"--- ENTERING NODE 2A: Bounce Escalation for {state['incident_number']} ---")
    inc_sys_id = state["incident_json"]["sys_id"]["value"]
    
    payload = {
        "urgency": "1", 
        # In a real environment, you'd put the sys_id of the Major Incident Team here. 
        # We will just escalate urgency and add a note for the PoC.
        "work_notes": "Automated Escalation: Ticket has bounced between assignment groups multiple times. Upgrading urgency and requesting supervisor triage."
    }
    await update_servicenow_record(sn_client, "incident", inc_sys_id, payload)
    
    state["action_taken"] = "Escalated due to high reassignment count."
    return state

async def node_2b_llm_triage(state: AgentState) -> AgentState:
    """
    NODE 2B: The Brain.
    Analyzes the novel incident against active parents and extracts meta-data.
    """
    logger.info(f"--- ENTERING NODE 2B: LLM Triage for {state['incident_number']} ---")
    
    # 1. Initialize the Parser
    parser = PydanticOutputParser(pydantic_object=TriageOutput)
    
    # 2. Tell Ollama to strictly output JSON
    llm=ChatOllama(
    model="gpt-oss:120b-cloud",
    temperature=0.1,
    format="json",
    base_url=os.getenv("OLLAMA_BASE_URL"),
    headers={"Authorization": f"Bearer {os.getenv('OLLAMA_API_KEY')}"},
    )
    
    # 3. Explicitly inject the format instructions into the prompt
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an expert ITIL Service Desk triage agent. Analyze the incoming incident JSON and compare it to the list of Active Parent Incidents.\n\n{format_instructions}\n\nYou must output ONLY valid JSON matching this exact schema."),
        ("human", "Incoming Incident:\n{incident}\n\nActive Parents:\n{active_parents}")
    ])
    print(prompt)
    # 4. Chain the prompt -> llm -> parser
    chain = prompt | llm | parser
    
    inc_subset = {
        "number": state["incident_number"],
        "short_description": state["incident_json"].get("short_description", {}).get("display_value", ""),
        "description": state["incident_json"].get("description", {}).get("display_value", ""),
        "cmdb_ci": state["incident_json"].get("cmdb_ci", {}).get("display_value", "")
    }

    # 5. Invoke the chain
    try:
        result = chain.invoke({
            "incident": json.dumps(inc_subset),
            "active_parents": json.dumps(state["active_parents"]),
            "format_instructions": parser.get_format_instructions()
        })
        
        # Store the parsed Pydantic object as a dictionary in our state
        state["llm_classification"] = result.dict()
        logger.info(f"LLM Classification Result: {state['llm_classification']}")
        
    except Exception as e:
        logger.error(f"Failed to parse LLM output: {e}")
        # Fallback mechanism if the LLM completely fails
        state["llm_classification"] = {
            "MATCH": None, 
            "CATEGORY": "Inquiry", 
            "MISSING_ASSET": False, 
            "IS_BLOCKER": False
        }

    state["action_taken"] = "Completed LLM Semantic Triage."
    return state

# ============================================================================
# PHASE 3: THE TERMINAL NODES (ACTION EXECUTION)
# ============================================================================

async def node_3a_pushback(state: AgentState) -> AgentState:
    """
    NODE 3A: Data Hygiene.
    Halts the process to ask the user for missing hardware information.
    """
    logger.info(f"--- ENTERING NODE 3A: Pushback for {state['incident_number']} ---")
    inc_sys_id = state["incident_json"]["sys_id"]["value"]
    
    payload = {
        "state": "3", # Standard SN code for 'On Hold' / 'Awaiting Caller'
        "comments": "Automated Triage: To properly diagnose this hardware issue, we need your Machine Asset Tag or PC Name. Please reply to this ticket with that information."
    }
    await update_servicenow_record(sn_client, "incident", inc_sys_id, payload)
    
    state["action_taken"] = "Placed on hold pending asset tag."
    return state

async def node_3b_novel_rag_fixer(state: AgentState) -> AgentState:
    """
    NODE 3B: The Solo Diagnostician.
    Creates a new Parent DB record, fetches SOPs via pgvector,
    and uses the LLM to synthesize a tailored response for the user.
    """
    logger.info(f"--- ENTERING NODE 3B: RAG Fixer (with Synthesis) for {state['incident_number']} ---")
    inc_sys_id = state["incident_json"]["sys_id"]["value"]
    summary = state["incident_json"].get("short_description", {}).get("display_value", "")
    description = state["incident_json"].get("description", {}).get("display_value", "")
    llm_class = state["llm_classification"]
    
    # 1. Register as a new Active Problem in our Postgres DB
    insert_new_parent(inc_sys_id, state["incident_number"], summary)
    
    # 2. Perform Vector Search (Combine summary + description for richer vector match)
    search_query = f"{summary} {description}"
    sop_results_str = search_knowledge_base(search_query)
    sop_results = json.loads(sop_results_str)
    
    # 3. LLM Synthesis of the SOP
    work_note = "Automated Triage: Novel issue detected.\n\n"
    
    if isinstance(sop_results, list) and len(sop_results) > 0:
        raw_sop_text = sop_results[0].get('retrieved_text', '')
        sop_id = sop_results[0].get('sop_id', 'Unknown')
        
        logger.info(f"Synthesizing instructions from SOP: {sop_id}")
        
        # Initialize LLM for synthesis (Slightly higher temperature for natural language generation)
        synth_llm = ChatOllama(
            model="gpt-oss:20b-cloud",
            temperature=0.1,
            base_url=os.getenv("OLLAMA_BASE_URL"),
            headers={"Authorization": f"Bearer {os.getenv('OLLAMA_API_KEY')}"},
        )
        
        synth_prompt = ChatPromptTemplate.from_messages([
            ("system", 
             "You are an expert ITIL Service Desk agent. Your role is to diagnose IT incidents and provide clear, actionable steps to the user.\n"
             "You will be provided with the user's incident description and an official Standard Operating Procedure (SOP) document retrieved from the IT Knowledge Base.\n\n"
             "CONTEXT RULES:\n"
             "1. The provided SOP contains the exact, approved enterprise steps to resolve this specific class of issue.\n"
             "2. Do NOT invent, guess, or hallucinate any technical commands or steps that are not present in the SOP.\n\n"
             "YOUR TASK:\n"
             "Write a professional, empathetic, and concise response to the user. Acknowledge their specific issue (from their summary), "
             "and then seamlessly provide them with the exact troubleshooting steps extracted from the SOP. Use clean formatting."
            ),
            ("human", "User's Incident Summary: {summary}\nUser's Incident Description: {description}\n\nRetrieved Official SOP ({sop_id}):\n{sop_text}")
        ])
        
        chain = synth_prompt | synth_llm
        
        try:
            synth_result = chain.invoke({
                "summary": summary,
                "description": description,
                "sop_id": sop_id,
                "sop_text": raw_sop_text
            })
            # Extract the generated text from the AIMessage object
            synthesized_instructions = synth_result.content
            work_note += f"--- Agent Diagnosis (Source: {sop_id}) ---\n{synthesized_instructions}"
            
        except Exception as e:
            logger.error(f"LLM Synthesis failed: {e}")
            # Graceful degradation: Fallback to raw text if synthesis fails
            work_note += f"Suggested SOP ({sop_id}) [Raw Extraction]:\n{raw_sop_text}"
            
    else:
        work_note += "No relevant SOP found in the Knowledge Base. Routing to Level 2 for investigation."

    # 4. Construct the ServiceNow Update Payload
    payload = {
        "category": llm_class["CATEGORY"].lower(),
        "work_notes": work_note
    }
    
    if llm_class["IS_BLOCKER"]:
        payload["urgency"] = "1"
        payload["work_notes"] = "Elevated urgency to 1: Blocker detected.\n\n" + payload["work_notes"]
        
    await update_servicenow_record(sn_client, "incident", inc_sys_id, payload)
    
    state["action_taken"] = "Registered as new Parent, retrieved SOP, and synthesized instructions."
    return state

async def node_3c_group_and_link(state: AgentState) -> AgentState:
    """
    NODE 3C: The Deduplicator.
    Links the ticket to its semantic match and increments the DB counter.
    """
    logger.info(f"--- ENTERING NODE 3C: Group & Link for {state['incident_number']} ---")
    inc_sys_id = state["incident_json"]["sys_id"]["value"]
    parent_sys_id = state["llm_classification"]["MATCH"]
    
    # 1. Update ServiceNow to link the ticket
    payload = {
        "parent_incident": parent_sys_id,
        "work_notes": "Automated Triage: This incident is a duplicate/child of an active Major Incident. Linking to Parent."
    }
    await update_servicenow_record(sn_client, "incident", inc_sys_id, payload)
    
    # 2. Update Postgres database child count (crucial for Phase 4)
    # 2. Update Postgres database child count and save to state
    new_count = increment_child_count(parent_sys_id)
    state["parent_child_count"] = new_count
    
    state["action_taken"] = f"Linked to Parent Incident {parent_sys_id}."
    return state

# ============================================================================
# PHASE 4: ADVANCED ITIL ANALYSIS (POST-GROUPING)
# ============================================================================

async def node_4a_dynamic_escalation(state: AgentState) -> AgentState:
    """
    NODE 4A: The "Impact" Upgrader.
    Upgrades the Parent Ticket to 'Enterprise Impact' because volume is high.
    """
    logger.info(f"--- ENTERING NODE 4A: Dynamic Escalation for Parent {state['llm_classification']['MATCH']} ---")
    parent_sys_id = state["llm_classification"]["MATCH"]
    
    payload = {
        "impact": "1", # ITIL Code 1 = High/Enterprise Impact
        "work_notes": f"Volume threshold breached ({state.get('parent_child_count')} related incidents). Automated escalation: Upgraded Impact to 1 (Enterprise-wide)."
    }
    await update_servicenow_record(sn_client, "incident", parent_sys_id, payload)
    
    state["action_taken"] = "Escalated Parent Impact to Enterprise."
    return state

async def node_4b_root_cause_triangulation(state: AgentState) -> AgentState:
    """
    NODE 4B: The Core Service Detector.
    Analyzes all grouped tickets, deduces the root infrastructure failure, 
    creates a Problem Record, and links it.
    """
    logger.info("--- ENTERING NODE 4B: Root Cause Triangulation ---")
    parent_sys_id = state["llm_classification"]["MATCH"]
    
    # 1. Fetch all children of this parent from ServiceNow to get their descriptions
    query_str = f"parent_incident={parent_sys_id}"
    children_resp = await query_servicenow_records(sn_client, "incident", query=query_str, limit=10)
    children_data = children_resp.get("data", []) if isinstance(children_resp, dict) else json.loads(children_resp).get("data", [])
    
    ticket_texts = [f"- {state['incident_json'].get('short_description', {}).get('display_value', '')}"] # Start with the trigger ticket
    for child in children_data:
        summary = child.get("short_description", {}).get("display_value", "")
        if summary:
            ticket_texts.append(f"- {summary}")
            
    ticket_list_str = "\n".join(ticket_texts)
    logger.info(f"Triangulating across {len(ticket_texts)} grouped tickets.")
    
    # 2. Ask the LLM to hypothesize the Root Cause
    triangulation_llm = ChatOllama(
        model="gpt-oss:20b-cloud",
        temperature=0.1,
        base_url=os.getenv("OLLAMA_BASE_URL"),
        headers={"Authorization": f"Bearer {os.getenv('OLLAMA_API_KEY')}"},
    )
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an expert AIOps Root Cause Analyzer. Analyze these related IT incidents which have been grouped together by semantic similarity. What is the likely shared underlying infrastructure or database failure? Output STRICTLY a 2 to 3 sentence diagnostic hypothesis. Do not include pleasantries."),
        ("human", "Grouped Incidents:\n{tickets}")
    ])
    chain = prompt | triangulation_llm
    
    hypothesis = chain.invoke({"tickets": ticket_list_str}).content
    
    # 3. Create the Problem Record in ServiceNow
    prob_payload = {
        "short_description": "Automated Triangulation: Systemic Failure Detected",
        "description": f"Automated Triangulation Hypothesis:\n{hypothesis}\n\nBased on a volume spike of {state.get('parent_child_count')} linked incidents."
    }
    prob_resp = await create_servicenow_record(sn_client, "problem", prob_payload)
    
    # Safely parse the response
    prob_data = prob_resp if isinstance(prob_resp, dict) else json.loads(prob_resp)
    
    # --- CRITICAL FIX ---
    # POST responses return flat strings for fields, not nested dicts.
    prob_sys_id = prob_data.get("data", {}).get("sys_id", "")
    prob_number = prob_data.get("data", {}).get("number", "")
    
    # 4. Link the Parent Incident to the new Problem Record
    if prob_sys_id:
        await update_servicenow_record(sn_client, "incident", parent_sys_id, {"problem_id": prob_sys_id})
        logger.info(f"Successfully linked Parent Incident to new Problem {prob_number}")
    
    state["root_cause_hypothesis"] = hypothesis
    state["action_taken"] = f"Generated Problem Record {prob_number} and linked to Parent."
    return state