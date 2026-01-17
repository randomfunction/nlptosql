import sqlite3
from typing import Any

class SchemaManager:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.full_schema = self._load_schema()
        self.table_names = self._load_table_names()
        self._database_summary = None  # Lazy-loaded

    def _load_table_names(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall() if not row[0].startswith("sqlite_")]
        conn.close()
        return tables

    def get_database_summary(self) -> str:
        """Returns a human-readable summary of what the database contains."""
        if self._database_summary:
            return self._database_summary
        
        # Build summary from table names
        tables_list = ", ".join(self.table_names)
        summary = f"This database contains the following tables: {tables_list}."
        
        # Cache it
        self._database_summary = summary
        return summary

    def _load_schema(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        schema_str = ""
        for table in tables:
            table_name = table[0]
            if table_name.startswith("sqlite_"):
                continue
                
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            schema_str += f"Table: {table_name}\n"
            for col in columns:
                schema_str += f"  - {col[1]} ({col[2]})\n"
            schema_str += "\n"
        
        conn.close()
    
    def get_structured_schema(self):
        """Returns schema as a dict: {table_name: [{'name': col, 'type': type}, ...]}"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall() if not row[0].startswith("sqlite_")]
        
        schema = {}
        for table in tables:
            cursor.execute(f"PRAGMA table_info({table})")
            # cid, name, type, notnull, dflt_value, pk
            columns = [{"name": col[1], "type": col[2]} for col in cursor.fetchall()]
            schema[table] = columns
            
        conn.close()
        return schema

    def get_relevant_tables(self, question: str, complexity: str, llm: Any) -> str:
        # For simple queries, we might just return the whole schema if it's small,
        # but for this exercise, let's try to be smart even for simple ones if we can,
        # or stick to the plan: Keyword match for simple, LLM for complex.
        
        if complexity == "simple":
            # Very naive keyword matching
            relevant_tables = []
            lower_q = question.lower()
            for table in self.table_names:
                if table.lower() in lower_q:
                    relevant_tables.append(table)
            
            # If no match found, fall back to LLM or return all (let's use LLM to be safe if empty)
            if not relevant_tables:
                 return self._get_relevant_tables_llm(question, llm)
            
            return self._build_schema_subset(relevant_tables)
        else:
            return self._get_relevant_tables_llm(question, llm)

    def _get_relevant_tables_llm(self, question: str, llm: Any) -> str:
        prompt = f"""
        Given the following list of table names, identify which tables are likely relevant to answer the question.
        
        Table Names: {', '.join(self.table_names)}
        
        Question: "{question}"
        
        Return a JSON list of relevant table names only. Example: ["TableA", "TableB"]
        """
        
        response = llm.generate_content(prompt)
        try:
            cleaned = response.replace("```json", "").replace("```", "").strip()
            import json
            relevant_tables = json.loads(cleaned)
            # Filter to ensure they actually exist
            valid_tables = [t for t in relevant_tables if t in self.table_names]
            return self._build_schema_subset(valid_tables)
        except Exception as e:
            print(f"Error determining relevant tables: {e}")
            return self.full_schema # Fallback to everything

    def _build_schema_subset(self, table_names):
        # Re-query schema just for these tables or parse self.full_schema. 
        # Re-querying is cleaner for this POC.
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        schema_str = ""
        for table_name in table_names:
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            schema_str += f"Table: {table_name}\n"
            for col in columns:
                schema_str += f"  - {col[1]} ({col[2]})\n"
            schema_str += "\n"
        
        conn.close()
        return schema_str

    def lookup_values(self, table: str, column: str, search_term: str = None, limit: int = 10) -> list:
        """
        Looks up distinct values in a column, optionally filtering by a search term.
        Useful for correcting entity names (e.g. 'Brazil' vs 'Brasil').
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if search_term:
                # Safe parameter substitution
                query = f"SELECT DISTINCT {column} FROM {table} WHERE {column} LIKE ? LIMIT ?"
                cursor.execute(query, (f"%{search_term}%", limit))
            else:
                query = f"SELECT DISTINCT {column} FROM {table} LIMIT ?"
                cursor.execute(query, (limit,))
                
            values = [row[0] for row in cursor.fetchall()]
            conn.close()
            return values
        except Exception as e:
            print(f"Error looking up values: {e}")
            return []
