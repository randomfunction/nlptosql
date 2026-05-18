import asyncio
from typing import Dict, Any
from src.graph.state import AgentState
from src.providers.gemini import GeminiProvider
from src.services.schema import schema_service
from src.services.executor import QueryExecutor
from src.services.cache import cache_service
from src.core.logger import logger

provider = None
executor = QueryExecutor()


def get_provider() -> GeminiProvider:
    global provider
    if provider is None:
        provider = GeminiProvider()
    return provider

async def node_understand_query(state: AgentState) -> AgentState:
    logger.info("Node: Understanding Query...")
    question = state["question"]
    logs = state.get("logs", [])
    
    db_summary = await schema_service.get_database_summary()
    analysis = await get_provider().understand_query(db_summary, question)
    
    log_entry = {
        "title": "Understanding", 
        "content": f"Intent: {analysis.get('intent')}\nComplexity: {analysis.get('complexity')}", 
        "type": "analysis"
    }
    
    return {
        "intent": analysis.get("intent", "general"),
        "complexity": analysis.get("complexity", "moderate"),
        "entities": analysis.get("entities", []),
        "ambiguity": analysis.get("ambiguity", []),
        "rejection_reason": analysis.get("rejection_reason"),
        "logs": logs + [log_entry]
    }

async def node_get_schema(state: AgentState) -> AgentState:
    logger.info("Node: Retrieving Schema...")
    question = state["question"]
    logs = state.get("logs", [])
    
    relevant_schema = await schema_service.get_relevant_tables(
        question,
        state.get("complexity", "moderate"),
        get_provider(),
    )
    
    lines = relevant_schema.split('\n')
    tables = [l for l in lines if l.startswith('Table:')]
    
    return {
        "relevant_schema": relevant_schema,
        "logs": logs + [{"title": "Relevant Schema", "content": '\n'.join(tables), "type": "schema"}]
    }

async def node_generate_plan(state: AgentState) -> AgentState:
    logger.info("Node: Generating Plan...")
    if state.get("complexity") == "simple":
        return {"plan": None}
        
    question = state["question"]
    schema = state["relevant_schema"]
    
    plan = await get_provider().generate_plan(schema, question)
    
    return {
        "plan": plan,
        "logs": state.get("logs", []) + [{"title": "Query Plan", "content": plan, "type": "plan"}]
    }

async def node_generate_sql(state: AgentState) -> AgentState:
    logger.info("Node: Generating SQL...")
    question = state["question"]
    schema = state["relevant_schema"]
    plan = state.get("plan", "")
    error = state.get("error")
    prev_sql = state.get("sql", "")
    logs = state.get("logs", [])

    # Check Cache first (if not in error recovery)
    if not error:
        cached_sql = await cache_service.get_cached_query(question)
        if cached_sql:
            logger.info("Cache HIT for SQL Generation")
            return {
                "sql": cached_sql,
                "logs": logs + [{"title": "Generated SQL (Cached)", "content": cached_sql, "type": "sql"}]
            }
            
    sql = await get_provider().generate_sql(
        schema,
        question,
        plan,
        prev_sql=prev_sql,
        error=error,
    )
    
    if not error:
        await cache_service.set_cached_query(question, sql)
        
    return {
        "sql": sql, 
        "error": None,
        "logs": logs + [{"title": "Generated SQL", "content": sql, "type": "sql"}]
    }

async def node_execute_validate(state: AgentState) -> AgentState:
    logger.info("Node: Executing Query...")
    sql = state["sql"]
    logs = state.get("logs", [])
    
    try:
        cols, rows = await executor.execute_safe(sql)
        results = [cols] + rows if cols else []
        
        return {
            "results": results, 
            "error": None,
            "logs": logs + [{"title": "Execution Success", "content": f"Rows: {len(rows)}", "type": "success"}]
        }
    except Exception as e:
        err_msg = str(e)
        logger.warning(f"Execution failed: {err_msg}")
        return {"error": err_msg, "attempts": state.get("attempts", 0) + 1}

async def node_generate_visualization(state: AgentState) -> AgentState:
    results = state.get("results")
    if not results or len(results) < 2:
        return {}
        
    cols = results[0]
    data = results[1:]
    sample = [cols] + data[:5]
    
    config = await get_provider().generate_visualization_config(state["question"], cols, sample)
    if not config or "chart_type" not in config:
        return {}
        
    chart_type = config["chart_type"]
    label_col = config.get("label_column")
    val_col = config.get("value_column")
    
    try:
        label_idx = cols.index(label_col)
        val_idx = cols.index(val_col)
    except:
         return {}
         
    labels = [row[label_idx] for row in data[:20]]
    values = [row[val_idx] for row in data[:20]]
    
    viz_data = {
        "type": chart_type,
        "data": {
            "labels": labels,
            "datasets": [{"label": val_col, "data": values, "backgroundColor": "rgba(54, 162, 235, 0.6)"}]
        },
        "options": {"responsive": True, "plugins": {"title": {"display": True, "text": state["question"]}}}
    }
    
    return {
        "visualization": viz_data,
        "logs": state.get("logs", []) + [{"title": "Visualization Generated", "content": f"Type: {chart_type}", "type": "viz"}]
    }

async def node_generate_answer(state: AgentState) -> AgentState:
    results = state.get("results")
    if not results or len(results) <= 1: 
         return {"final_answer": "No results found."}
    
    num_data_rows = len(results) - 1
    if num_data_rows > 2:
        return {}  # Skip summary when the table itself is the useful output
         
    return {"final_answer": "Here are your exact results based on the query."}

async def node_reject_irrelevant(state: AgentState) -> AgentState:
    reason = state.get("rejection_reason", "This question is not related to the database.")
    logs = state.get("logs", [])
    response = f"I'm sorry, I can only answer questions about the database. {reason}"
    return {
        "final_answer": response,
        "logs": logs + [{"title": "Query Rejected", "content": reason, "type": "warning"}]
    }

async def node_explore_data(state: AgentState) -> AgentState:
    return {"logs": state.get("logs", []) + [{"title": "Data Exploration", "content": "Skipped for latency optimization", "type": "info"}]}

async def node_ask_clarification(state: AgentState) -> AgentState:
    return {
        "clarification_question": "Can you please be more specific?",
        "final_answer": "Can you please be more specific?",
        "logs": state.get("logs", []) + [{"title": "Clarification Requested", "content": "Please be specific", "type": "clarification"}]
    }

async def node_meta_query(state: AgentState) -> AgentState:
    return {"final_answer": "Meta querying is supported via LLM reasoning.", "logs": state.get("logs", [])}
