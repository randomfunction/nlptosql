from .schema import SchemaManager

def handle_meta_query(question: str, schema_manager: SchemaManager) -> str:
    """
    Handles questions about the database schema itself.
    """
    question_lower = question.lower()
    
    if "table" in question_lower and ("list" in question_lower or "show" in question_lower or "all" in question_lower):
        return f"Here are the tables in the database:\n{', '.join(schema_manager.table_names)}"
    
    if "schema" in question_lower or "structure" in question_lower:
        # If specific table mentioned
        for table in schema_manager.table_names:
            if table.lower() in question_lower:
                return schema_manager._build_schema_subset([table])
        return schema_manager.full_schema

    if "count" in question_lower and "table" in question_lower:
        return f"There are {len(schema_manager.table_names)} tables in the database."

    return "I detected this is a meta-query about the database structure, but I'm not sure specifically what you want to see. Try 'List all tables' or 'Show schema for [Table]'."
