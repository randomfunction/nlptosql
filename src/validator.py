import sqlparse
import re

def validate_sql(sql: str) -> tuple[bool, str]:
    """
    Validates the SQL query for syntax and safety.
    Returns (is_valid, error_message).
    """
    if not sql:
        return False, "Empty SQL query."
        
    # Syntax check (basic)
    try:
        parsed = sqlparse.parse(sql)
        if not parsed:
            return False, "Failed to parse SQL."
    except Exception as e:
        return False, f"SQL syntax error: {e}"

    # Safety check: Read-only enforcement
    forbidden_keywords = [
        "DELETE", "DROP", "UPDATE", "INSERT", "ALTER", "TRUNCATE", 
        "GRANT", "REVOKE", "CREATE", "EXEC", "REPLACE"
    ]
    
    upper_sql = sql.upper()
    
    # Exact word match for forbidden statements to avoid accidentally blocking valid columns containing substrings
    for keyword in forbidden_keywords:
        if re.search(r'\b' + keyword + r'\b', upper_sql):
             return False, f"Forbidden keyword detected: {keyword}. System is read-only."

    # Must start with SELECT (or WITH CTEs followed by SELECT)
    if not re.search(r'^\s*(WITH[\s\S]+?)?SELECT\b', upper_sql):
         return False, "Query must be a SELECT statement."

    return True, ""

def validate_result(result: list, sql: str, question: str) -> tuple[bool, str]:
    """
    Validates the execution result.
    Returns (is_valid, message).
    """
    if not result:
        return True, "Query returned no results. This might be correct, or the query logic might be too restrictive."
        
    return True, f"Returned {len(result)} rows."

def enforce_limit(sql: str, default_limit: int = 1000) -> str:
    """Safely appends a LIMIT clause to the end of a SELECT query if absent."""
    upper_sql = sql.upper()
    # Check if a sensible LIMIT is already established
    if re.search(r'\bLIMIT\b\s+\d+', upper_sql):
        return sql
    # If not, add trailing limit
    if re.search(r'^\s*(WITH[\s\S]+?)?SELECT\b', upper_sql):
        return f"{sql.strip()} LIMIT {default_limit}"
    return sql
