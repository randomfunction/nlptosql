from .llm import LLMService

def generate_sql(question: str, schema: str, plan: str, llm: LLMService) -> str:
    prompt = f"""
    You are a SQL expert for SQLite. Generate a safe and efficient SQL query based on the user's question and the provided schema.
    
    Database Schema:
    {schema}
    
    User Question: "{question}"
    
    Query Plan:
    {plan if plan else "No specific plan provided."}
    
    Constraints & Guidelines:
    1. READ-ONLY: Do not use INSERT, UPDATE, DELETE, DROP, or ALTER.
    2. SAFETY: Always add a LIMIT 1000 clause if the query might return many rows, unless an explicit aggregation (COUNT, MAX, etc.) is requested.
    3. CLARITY: Use Common Table Expressions (CTEs) for complex logic.
    4. COLUMN SELECTION: Avoid `SELECT *`. Explicitly select the columns needed.
    
    Return ONLY the SQL query. No markdown formatting (no ```sql).
    """
    
    response = llm.generate_content(prompt)
    # Cleanup
    sql = response.replace("```sql", "").replace("```", "").strip()
    return sql
