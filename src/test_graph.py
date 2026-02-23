import asyncio
import logging
from agent_logic.graph import build_incident_graph

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

async def run_graph_test(incident_number: str):
    print(f"\n{'='*60}")
    print(f"🚀 INITIATING AIOPS PIPELINE FOR: {incident_number}")
    print(f"{'='*60}\n")

    # 1. Compile the graph
    app = build_incident_graph()
    
    # 2. Define our initial state (Just the incident number is enough to start)
    initial_state = {
        "incident_number": incident_number,
        "incident_json": {},
        "reassignment_count": 0,
        "active_parents": [],
        "llm_classification": None,
        "root_cause_hypothesis": None,
        "action_taken": "Initialized"
    }

    # 3. Stream the graph execution so we can watch it think
    print("--- EXECUTION TRACE ---")
    async for output in app.astream(initial_state):
        for node_name, state_update in output.items():
            print(f"\n✅ COMPLETED NODE: {node_name}")
            print(f"   Action Taken: {state_update.get('action_taken', 'N/A')}")
            
            # Print LLM reasoning if it just ran the triage node
            if node_name == "node_2b_llm_triage":
                print(f"   LLM Decision: {state_update.get('llm_classification')}")

    print(f"\n{'='*60}")
    print("🏁 GRAPH EXECUTION COMPLETE")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    # Simulating an Alert Storm!
    tickets = ["INC0000054"] 
    for ticket in tickets:
        asyncio.run(run_graph_test(ticket))