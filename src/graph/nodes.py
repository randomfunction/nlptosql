import os
import json
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
from .state import AgentState
from ..schema import SchemaManager
from ..validator import validate_sql, validate_result
import sqlite3

# Initialize LLM
# Note: Switching to gemini-flash-latest to avoid 404/429 issues
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite", temperature=0)

DB_FILE = "Chinook_Sqlite.sqlite"
schema_manager = SchemaManager(DB_FILE)

def node_understand_query(state: AgentState) -> AgentState:
    """Classifies intent and complexity."""
    print("🔍 [Node] Understanding Query...")
    question = state["question"]
    logs = state.get("logs", [])
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a SQL expert AI. Analyze the user question.
        Return a JSON object with:
        - "intent": "aggregation", "filtering", "join", "meta-query", or "general"
        - "complexity": "simple", "moderate", or "complex"
        - "entities": list of table names or entities mentioned
        - "ambiguity": list of ambiguous terms
        """),
        ("human", "{question}")
    ])
    
    chain = prompt | llm
    try:
        response = chain.invoke({"question": question})
        content = response.content.replace("```json", "").replace("```", "").strip()
        data = json.loads(content)
        
        log_entry = {
            "title": "Understanding", 
            "content": f"Intent: {data.get('intent')}\nComplexity: {data.get('complexity')}", 
            "type": "analysis"
        }
        
        return {
            "intent": data.get("intent"),
            "complexity": data.get("complexity"),
            "entities": data.get("entities", []),
            "ambiguity": data.get("ambiguity", []),
            "logs": logs + [log_entry]
        }
    except Exception as e:
        return {
            "intent": "general", "complexity": "moderate", 
            "logs": logs + [{"title": "Understanding Error", "content": str(e), "type": "error"}]
        }

def node_meta_query(state: AgentState) -> AgentState:
    from ..meta_handler import handle_meta_query as get_meta_response
    response = get_meta_response(state["question"], schema_manager)
    return {
        "final_answer": response,
        "logs": state.get("logs", []) + [{"title": "Meta-Query Result", "content": response, "type": "result"}]
    }

def node_generate_visualization(state: AgentState) -> AgentState:
    """Generates a Chart.js config if appropriate."""
    results = state.get("results")
    if not results or len(results) < 2:
        return {}
        
    cols = results[0]
    data = results[1:]
    
    # Simple heuristic: 2 columns, one string, one number -> Bar Chart
    # Or LLM can decide. Let's use LLM for flexible "Wow".
    
    # We pass a sample
    sample = [cols] + data[:5]
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """
        You are a Data Visualization Expert.
        Given the query and data, decide if a chart is useful.
        Supported types: 'bar', 'line', 'pie', 'doughnut'.
        
        Return JSON compatible with Chart.js:
        {{
            "type": "bar",
            "data": {{ "labels": [...], "datasets": [{{ "label": "...", "data": [...] }}] }},
            "title": "Chart Title"
        }}
        
        If no chart is suitable, return {{}}.
        """),
        ("human", "Question: {question}\nData (sample): {sample}")
    ])
    
    # We need to reshape full data for the chart, not just sample.
    # So we ask LLM for CONFIG structure, then we populate it with full data in Python?
    # Or just let LLM handle it if data is small (LIMIT 1000 is small enough context usually).
    # But passing 1000 rows to LLM is slow/expensive.
    
    # Hybrid approach:
    # Ask LLM for mapping: "label_column": "Name", "value_column": "Sales"
    # Then Python helper builds the JSON.
    
    mapper_prompt = ChatPromptTemplate.from_messages([
        ("system", """
        Identify columns for visualization.
        Return JSON: {{ "chart_type": "bar|line|pie", "label_column": "col_name", "value_column": "col_name_or_list" }}
        If not suitable, return {{}}.
        """),
        ("human", "Columns: {cols}\nSample Data: {sample}")
    ])
    
    chain = mapper_prompt | llm
    try:
        response = chain.invoke({"cols": str(cols), "sample": str(sample)})
        clean = response.content.replace("```json", "").replace("```", "").strip()
        config = json.loads(clean)
        
        if not config or "chart_type" not in config:
            return {}
            
        chart_type = config["chart_type"]
        label_col = config.get("label_column")
        val_col = config.get("value_column")
        
        # Find indices
        try:
            label_idx = cols.index(label_col)
            val_idx = cols.index(val_col)
        except:
             return {}
             
        # Build Data
        labels = [row[label_idx] for row in data]
        values = [row[val_idx] for row in data]
        
        # Limit to top 20 for chart clarity if too many
        if len(labels) > 20:
             labels = labels[:20]
             values = values[:20]
             
        viz_data = {
            "type": chart_type,
            "data": {
                "labels": labels,
                "datasets": [{
                    "label": val_col,
                    "data": values,
                    "backgroundColor": "rgba(54, 162, 235, 0.6)"
                }]
            },
            "options": {
                "responsive": True,
                "plugins": {
                    "title": {
                        "display": True,
                        "text": state["question"]
                    }
                }
            }
        }
        
        return {
            "visualization": viz_data,
             "logs": state.get("logs", []) + [{"title": "Visualization Generated", "content": f"Type: {chart_type}", "type": "viz"}]
        }
        
    except Exception as e:
        return {"logs": state.get("logs", []) + [{"title": "Viz Error", "content": str(e), "type": "warning"}]}

def node_get_schema(state: AgentState) -> AgentState:
    class Adapter:
        def generate_content(self, prompt):
            return llm.invoke(prompt).content

    relevant_schema = schema_manager.get_relevant_tables(
        state["question"], 
        state.get("complexity", "moderate"), 
        Adapter()
    )
    
    # Parse for log
    lines = relevant_schema.split('\n')
    tables = [l for l in lines if l.startswith('Table:')]
    
    return {
        "relevant_schema": relevant_schema,
        "logs": state.get("logs", []) + [{"title": "Relevant Schema", "content": '\n'.join(tables), "type": "schema"}]
    }

def node_generate_plan(state: AgentState) -> AgentState:
    if state.get("complexity") == "simple":
        return {"plan": None}
        
    question = state["question"]
    schema = state["relevant_schema"]
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a Query Planner. Create a numbered step-by-step plan to answer the question using the schema."),
        ("human", "Schema:\n{schema}\n\nQuestion: {question}")
    ])
    
    chain = prompt | llm
    response = chain.invoke({"schema": schema, "question": question})
    return {
        "plan": response.content,
        "logs": state.get("logs", []) + [{"title": "Query Plan", "content": response.content, "type": "plan"}]
    }

def node_generate_sql(state: AgentState) -> AgentState:
    question = state["question"]
    schema = state["relevant_schema"]
    plan = state.get("plan", "")
    error = state.get("error")
    logs = state.get("logs", [])
    
    if error:
        # Recovery Mode
        logs.append({"title": f"Validation Error (Attempt {state.get('attempts',0)})", "content": error, "type": "error"})
        
        prompt_template = """
        You are fixing a broken SQL query.
        Schema: {schema}
        Question: {question}
        Previous Failed SQL: {prev_sql}
        Error Message: {error}
        
        Return ONLY the corrected SQL.
        """
        prompt = ChatPromptTemplate.from_template(prompt_template)
        chain = prompt | llm
        response = chain.invoke({
            "schema": schema, 
            "question": question, 
            "prev_sql": state.get("sql"), 
            "error": error
        })
    else:
        # Normal Mode
        prompt_template = """
        Generate a safe, efficient SQLite query.
        Schema: {schema}
        Question: {question}
        Plan: {plan}
        
        Rules:
        1. Read-only (SELECT only).
        2. LIMIT 1000 unless aggregation.
        3. Use CTEs for complex logic.
        
        Return ONLY the SQL.
        """
    prompt = ChatPromptTemplate.from_template(prompt_template)
    chain = prompt | llm
    
    def clean_sql(text: str) -> str:
        import re
        # 1. Try to find markdown block
        match = re.search(r"```(?:sql)?(.*?)```", text, re.DOTALL | re.IGNORECASE)
        if match:
             return match.group(1).strip()
        
        # 2. If no markdown, try to find the start of the query
        # Look for SELECT or WITH (common starts)
        match = re.search(r"^\s*(WITH|SELECT)\s", text, re.IGNORECASE | re.MULTILINE)
        if match:
             start_index = match.start()
             return text[start_index:].strip()
             
        # 3. Fallback: just strip
        return text.strip()

    try:
        response = chain.invoke({
            "schema": schema, 
            "question": question, 
            "plan": plan
        })
        sql = clean_sql(response.content)
    except Exception as e:
        # Fallback for LLM errors
        return {"error": f"LLM Generation Error: {e}", "logs": logs + [{"title": "Generation Error", "content": str(e), "type": "error"}]}
    
    return {
        "sql": sql, 
        "error": None,
        "logs": logs + [{"title": "Generated SQL", "content": sql, "type": "sql"}]
    }

def node_execute_validate(state: AgentState) -> AgentState:
    sql = state["sql"]
    logs = state.get("logs", [])
    
    # 1. Syntax/Safety Validation
    is_valid, msg = validate_sql(sql)
    if not is_valid:
        return {"error": f"Validation Failed: {msg}", "attempts": state.get("attempts", 0) + 1}
        
    # 2. Execution
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute(sql)
        cols = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        conn.close()
        
        results = [cols] + rows
        
        return {
            "results": results, 
            "error": None,
            "logs": logs + [{"title": "Execution Success", "content": f"Rows: {len(rows)}", "type": "success"}]
        }
        
    except Exception as e:
        return {"error": str(e), "attempts": state.get("attempts", 0) + 1}

def node_generate_answer(state: AgentState) -> AgentState:
    question = state["question"]
    results = state["results"]
    logs = state.get("logs", [])
    
    if not results or len(results) <= 1: 
         ans = "No results found."
         return {"final_answer": ans, "logs": logs}
    
    # Smart Summarization Logic
    # If we have only a few rows (headers + 1 or 2 rows), provide natural language.
    # Otherwise, rely on the table view.
    num_data_rows = len(results) - 1
    if num_data_rows > 2:
        return {
            "final_answer": None, # Skip LLM Summary
            "logs": logs
        }
         
    preview = results[:5] 
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Summarize the SQL results for the user in a natural sentence."),
        ("human", "Question: {question}\nResults (preview): {results}")
    ])
    
    chain = prompt | llm
    try:
        response = chain.invoke({"question": question, "results": str(preview)})
        return {
            "final_answer": response.content,
        }
    except Exception as e:
        return {"final_answer": "Here are the results (AI summary unavailable)."}

def node_ask_clarification(state: AgentState) -> AgentState:
    """Generates a clarification question."""
    ambiguity = state.get("ambiguity", [])
    question = state["question"]
    logs = state.get("logs", [])
    schema = state.get("relevant_schema", "")
    
    # Get dynamic database context
    db_summary = schema_manager.get_database_summary()
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", f"""You are a helpful assistant for a database.
{db_summary}

When the user asks an ambiguous question, ask a clarifying question that is RELEVANT to the data available in this database.
Do NOT suggest options that are not represented in the database tables.

Use the schema below to understand what data is available:
{{schema}}
"""),
        ("human", "Question: {question}\nAmbiguity detected: {ambiguity}")
    ])
    
    chain = prompt | llm
    response = chain.invoke({"question": question, "ambiguity": str(ambiguity), "schema": schema})
    
    return {
        "clarification_question": response.content,
        "final_answer": response.content,  # Expose as answer so UI shows it
        "logs": logs + [{"title": "Clarification Requested", "content": response.content, "type": "clarification"}]
    }

def node_explore_data(state: AgentState) -> AgentState:
    """
    Checks if entities mentioned in the question actually exist in the DB.
    Matches them to table columns and looks up valid values.
    """
    question = state["question"]
    entities = state.get("entities", [])
    relevant_schema = state.get("relevant_schema", "")
    logs = state.get("logs", [])
    
    if not entities:
        return {"logs": logs}
        
    print(f"🔍 [Node] Exploring Data for entities: {entities}")
    
    # 1. Map entities to table/column using LLM
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a Database Analyst. 
        For each entity mentioned, identify the most likely Table and Column in the schema where it would be found.
        Schema:
        {schema}
        
        Return a JSON list of objects: {{"entity": "entity_name", "table": "TableName", "column": "ColumnName"}}
        If you can't determine, skip it.
        """),
        ("human", "Entities: {entities}")
    ])
    
    chain = prompt | llm
    try:
        response = chain.invoke({"schema": relevant_schema, "entities": str(entities)})
        mapping_str = response.content.replace("```json", "").replace("```", "").strip()
        mappings = json.loads(mapping_str)
    except Exception as e:
        return {"logs": logs + [{"title": "Exploration Error", "content": f"Mapping failed: {e}", "type": "warning"}]}
    
    # 2. Verify values
    updates = []
    run_logs = []
    
    for item in mappings:
        entity = item.get("entity")
        table = item.get("table")
        col = item.get("column")
        
        if table and col:
            # Try exact match first (case-insensitive done by DB usually, or we search)
            # We use our lookup tool
            matches = schema_manager.lookup_values(table, col, search_term=entity, limit=5)
            
            if matches:
                # If we found matches, great. 
                # If the match is not identical to entity, we might want to suggest it?
                # For now, let's just log it.
                run_logs.append(f"Found '{entity}' in {table}.{col} -> {matches}")
            else:
                # If no match, try looser search?
                # For now, just report.
                 run_logs.append(f"'{entity}' NOT found in {table}.{col}")
        
    return {
        "logs": logs + [{"title": "Data Exploration", "content": "\n".join(run_logs), "type": "info"}]
    }
