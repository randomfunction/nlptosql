import os
import sqlite3
import sys
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

DB_FILE = "Chinook_Sqlite.sqlite"

def get_schema():
    conn = sqlite3.connect(DB_FILE)
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
    return schema_str

def generate_sql(question, schema):
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY not found in environment variables.")
        
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.5-flash-lite')
    
    prompt = f"""
    You are a SQL expert. Convert the following natural language question into a SQL query for the Chinook database.
    
    Schema:
    {schema}
    
    Question: {question}
    
    Return ONLY the SQL query, no markdown formatting, no explanations.
    """
    
    response = model.generate_content(prompt)
    sql = response.text.strip().replace("```sql", "").replace("```", "")
    return sql

def execute_query(sql):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute(sql)
        results = cursor.fetchall()
        print(f"\nQuery Executed: {sql}")
        print("Results:")
        for row in results:
            print(row)
    except sqlite3.Error as e:
        print(f"\nSQL Error: {e}")
        print(f"Query: {sql}")
    finally:
        conn.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python baseline.py '<question>'")
    else:
        question = sys.argv[1]
        try:
            schema = get_schema()
            sql = generate_sql(question, schema)
            execute_query(sql)
        except Exception as e:
            print(f"Error: {e}")
