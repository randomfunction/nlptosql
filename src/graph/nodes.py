import os
import json
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
from .state import AgentState
from ..schema import SchemaManager
from ..validator import validate_sql, validate_result
import sqlite3

# Initialize LLM
# Note: Switching to gemini-flash-latest to avoid 404/429 issues
llm = ChatGoogleGenerativeAI(model="gemini-flash-latest", temperature=0)

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
        try:
            response = chain.invoke({
                "schema": schema, 
                "question": question, 
                "plan": plan
            })
            sql = response.content.replace("```sql", "").replace("```", "").strip()
        except Exception as e:
            # Fallback for LLM errors
            return {"error": f"LLM Generation Error: {e}", "logs": logs + [{"title": "Generation Error", "content": str(e), "type": "error"}]}
        
    sql = response.content.replace("```sql", "").replace("```", "").strip()
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
