from .llm import LLMService

def fix_query(question: str, invalid_sql: str, error_msg: str, schema: str, llm: LLMService) -> str:
    prompt = f"""
    The following SQL query failed to execute or validate.
    
    Database Schema:
    {schema}
    
    User Question: "{question}"
    
    Invalid SQL:
    {invalid_sql}
    
    Error Message:
    {error_msg}
    
    Please correct the SQL query to resolve the error. 
    Ensure the logic matches the user's question and the schema.
    
    Return ONLY the corrected SQL query. No markdown formatting.
    """
    
    response = llm.generate_content(prompt)
    return response.replace("```sql", "").replace("```", "").strip()
