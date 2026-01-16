import sqlparse

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
    forbidden_keywords = ["DELETE", "DROP", "UPDATE", "INSERT", "ALTER", "TRUNCATE", "GRANT", "REVOKE"]
    stmt = parsed[0]
    
    # Check token types is a bit complex with sqlparse, let's do a simpler keyword check first
    # referencing the flattened tokens or just string check for now as a robust first line of defense.
    # A better way is checking stmt.get_type()
    
    if stmt.get_type() not in ["SELECT", "UNKNOWN"]: # UNKNOWN might happen for CTEs sometimes depending on sqlparse version
        # Let's inspect tokens more closely if UNKNOWN
        # But for strictly read-only, we mainly want to ban DML/DDL.
        pass

    upper_sql = sql.upper()
    for keyword in forbidden_keywords:
        # Simple word boundary check would be better, but let's start simple
        if keyword in upper_sql.split():
             return False, f"Forbidden keyword detected: {keyword}"

    return True, ""

def validate_result(result: list, sql: str, question: str) -> tuple[bool, str]:
    """
    Validates the execution result.
    Returns (is_valid, message).
    """
    if not result:
        return True, "Query returned no results. This might be correct, or the query logic might be too restrictive."
        
    # Heuristics for reasonableness could go here. 
    # For now, just a pass-through.
    return True, f"Returned {len(result)} rows."
