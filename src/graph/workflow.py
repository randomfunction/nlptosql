from langgraph.graph import StateGraph, END
from .state import AgentState
from .nodes import (
    node_understand_query,
    node_meta_query,
    node_get_schema,
    node_generate_plan,
    node_generate_sql,
    node_execute_validate,
    node_generate_answer,
    node_ask_clarification,
    node_explore_data,
    node_generate_visualization,
    node_reject_irrelevant
)

def route_understand(state: AgentState):
    """Routing logic after Understanding."""
    intent = state.get("intent")
    
    # Reject irrelevant questions
    if intent == "irrelevant":
        return "reject_irrelevant"
    
    if intent == "meta-query":
        return "meta_handler"
    
    if state.get("ambiguity"):
        return "ask_clarification"
        
    return "get_schema"

def route_execution(state: AgentState):
    """Routing logic after Execution."""
    if state.get("error"):
        if state.get("attempts", 0) >= 3:
            return "end_fail"
        return "fix_sql"
    return "generate_visualization"

# Define Graph
workflow = StateGraph(AgentState)

# Add Nodes
workflow.add_node("understand", node_understand_query)
workflow.add_node("meta_handler", node_meta_query)
workflow.add_node("get_schema", node_get_schema)
workflow.add_node("plan", node_generate_plan)
workflow.add_node("explore_data", node_explore_data)
workflow.add_node("generate_sql", node_generate_sql)
workflow.add_node("execute", node_execute_validate)
workflow.add_node("fix_sql", node_generate_sql) # Re-use generation node logic which handles error state
workflow.add_node("generate_visualization", node_generate_visualization)
workflow.add_node("generate_answer", node_generate_answer)
workflow.add_node("ask_clarification", node_ask_clarification)
workflow.add_node("reject_irrelevant", node_reject_irrelevant)

# Set Entry Point
workflow.set_entry_point("understand")

# Add Edges
workflow.add_conditional_edges(
    "understand",
    route_understand,
    {
        "meta_handler": "meta_handler",
        "get_schema": "get_schema",
        "ask_clarification": "ask_clarification",
        "reject_irrelevant": "reject_irrelevant"
    }
)

workflow.add_edge("meta_handler", END)
workflow.add_edge("ask_clarification", END)
workflow.add_edge("reject_irrelevant", END)

workflow.add_edge("get_schema", "explore_data")
workflow.add_edge("explore_data", "plan")
workflow.add_edge("plan", "generate_sql")
workflow.add_edge("generate_sql", "execute")

workflow.add_conditional_edges(
    "execute",
    route_execution,
    {
        "fix_sql": "fix_sql",
        "generate_visualization": "generate_visualization",
        "end_fail": END
    }
)

workflow.add_edge("fix_sql", "execute")
workflow.add_edge("generate_visualization", "generate_answer")
workflow.add_edge("generate_answer", END)

# Compile
app = workflow.compile()
