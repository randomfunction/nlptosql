from .schema import SchemaManager
import sqlite3

def handle_meta_query(question: str, schema_manager: SchemaManager, llm=None) -> str:
    """
    Handles questions about the database schema using LLM-generated SQL.
    Uses SQLite's PRAGMA commands and sqlite_master for introspection.
    """
    
    # If no LLM provided, use simple fallback
    if llm is None:
        return _simple_meta_response(question, schema_manager)
    
    # Build context about available meta-query capabilities
    meta_context = f"""You are answering a question about the database SCHEMA/STRUCTURE.

Available tables: {', '.join(schema_manager.table_names)}

SQLite introspection you can use:
- SELECT name FROM sqlite_master WHERE type='table' -- lists all tables
- For column counts: SELECT name, (SELECT COUNT(*) FROM pragma_table_info(name)) as col_count FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'

IMPORTANT: 
- Return ONLY a SINGLE SQL SELECT statement
- Do NOT use multiple statements separated by semicolons
- Do NOT use PRAGMA directly (use pragma_table_info as a table)
"""
    
    from langchain_core.prompts import ChatPromptTemplate
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", meta_context),
        ("human", "{question}")
    ])
    
    try:
        chain = prompt | llm
        response = chain.invoke({"question": question})
        sql = response.content.replace("```sql", "").replace("```", "").strip()
        
        # Clean up: take only the first statement if multiple
        if ";" in sql:
            sql = sql.split(";")[0].strip()
        
        # Execute the meta-query
        conn = sqlite3.connect(schema_manager.db_path)
        cursor = conn.cursor()
        cursor.execute(sql)
        results = cursor.fetchall()
        cols = [desc[0] for desc in cursor.description] if cursor.description else []
        conn.close()
        
        # Format results
        if not results:
            return "No results found for your schema query."
        
        # Simple formatting
        output = []
        if cols:
            output.append(" | ".join(cols))
            output.append("-" * len(output[0]))
        for row in results:
            output.append(" | ".join(str(val) for val in row))
        
        return "\n".join(output)
        
    except Exception as e:
        # Fallback to simple response on error
        return f"Error executing meta-query: {e}\n\nFalling back to simple response:\n{_simple_meta_response(question, schema_manager)}"


def _simple_meta_response(question: str, schema_manager: SchemaManager) -> str:
    """Simple fallback when LLM is not available."""
    question_lower = question.lower()
    
    if "table" in question_lower:
        return f"Tables in database: {', '.join(schema_manager.table_names)}"
    
    return f"Database has {len(schema_manager.table_names)} tables: {', '.join(schema_manager.table_names)}"
