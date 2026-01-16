import sys
import argparse
import os
from dotenv import load_dotenv

# Add current directory to path so we can import src
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.llm import LLMService
from src.understanding import analyze_query
from src.schema import SchemaManager
from src.planner import generate_plan
from src.generator import generate_sql
from src.validator import validate_sql, validate_result
from src.recovery import fix_query
from src.meta_handler import handle_meta_query
import baseline 

MAX_RETRIES = 3

def process_question(question: str, return_steps: bool = False):
    db_file = "Chinook_Sqlite.sqlite"
    steps = []
    
    def log_step(title, content, type="info"):
        steps.append({"title": title, "content": content, "type": type})
        if not return_steps: # Fallback to print if running in CLI mode (implied)
            print(f"\n[{title}]\n{content}")

    # Initial Step
    # log_step("Start", f"Analyzing question: '{question}'") 
    
    try:
        # Initialize Services
        llm = LLMService(model_name='gemini-flash-latest')
        schema_manager = SchemaManager(db_file)
        
        # 1. Understand
        understanding = analyze_query(question, llm)
        log_step("Understanding", 
                 f"Intent: {understanding.get('intent')}\nComplexity: {understanding.get('complexity')}\nEntities: {understanding.get('entities')}",
                 "analysis")
            
        # 1.5 Meta-Query Check
        if understanding.get('intent') == 'meta-query':
            result = handle_meta_query(question, schema_manager)
            log_step("Meta-Query Result", result, "result")
            return {"success": True, "result": result, "steps": steps}
        
        # 2. Schema Reasoning
        relevant_schema = schema_manager.get_relevant_tables(
            question, 
            understanding.get('complexity', 'moderate'), 
            llm
        )
        # Parse table names for display
        lines = relevant_schema.split('\n')
        tables = [l for l in lines if l.startswith('Table:')]
        log_step("Relevant Tables", '\n'.join(tables), "schema")

        # 3. Planning
        plan = None
        if understanding.get('complexity') != 'simple':
            plan = generate_plan(question, relevant_schema, llm)
            log_step("Query Plan", plan, "plan")
        
        # 4. Generation
        sql = generate_sql(question, relevant_schema, plan, llm)
        log_step("Generated SQL", sql, "sql")

        # Recovery Loop
        attempt = 1
        last_error = None
        
        while attempt <= MAX_RETRIES:
            # 5. Pre-Execution Validation
            is_valid, msg = validate_sql(sql)
            if not is_valid:
                log_step(f"Validation Error (Attempt {attempt})", msg, "error")
                
                # Trigger recovery
                step_log = f"Attempting to fix query based on validation error: {msg}"
                # log_step("Recovery", step_log)
                
                sql = fix_query(question, sql, msg, relevant_schema, llm)
                log_step("Fixed SQL", sql, "sql")
                attempt += 1
                continue

            # 6. Execution
            conn = baseline.sqlite3.connect(db_file)
            cursor = conn.cursor()
            results = []
            try:
                cursor.execute(sql)
                results = cursor.fetchall()
                
                # 7. Post-Execution Validation
                valid_res, res_msg = validate_result(results, sql, question)
                # log_step("Result Validation", res_msg)
                
                final_res = []
                # Format results for cleaner display
                if len(results) > 0:
                     # Get column names if possible. Cursor.description works after execute.
                     cols = [description[0] for description in cursor.description]
                     final_res.append(cols)
                     final_res.extend(results)
                
                log_step("Execution Result", f"Query Successful. {res_msg}\nRows: {len(results)}", "success")
                conn.close()
                return {"success": True, "result": final_res, "steps": steps}
                
            except Exception as e:
                log_step(f"Execution Error (Attempt {attempt})", str(e), "error")
                last_error = e
                
                sql = fix_query(question, sql, str(e), relevant_schema, llm)
                log_step("Fixed SQL", sql, "sql")
                attempt += 1
            finally:
                if conn: conn.close()
        
        if attempt > MAX_RETRIES:
            log_step("Failure", f"Failed after {MAX_RETRIES} attempts. Last error: {last_error}", "error")
            return {"success": False, "error": str(last_error), "steps": steps}
        
    except Exception as e:
        import traceback
        trace = traceback.format_exc()
        log_step("System Error", str(e), "error")
        return {"success": False, "error": str(e), "steps": steps}


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description="Agentic Text-to-SQL System")
    parser.add_argument("question", help="The natural language question")
    parser.add_argument("--details", action="store_true", help="Show reasoning details")
    args = parser.parse_args()
    
    # CLI Mode wrapper (simplified)
    res = process_question(args.question, return_steps=False) 
    # Logic above already handled printing if return_steps=False, 
    # but let's just print final result here to be safe if not using details mode in CLI
    if res['success'] and 'result' in res:
        print("\n[Final Result]")
        # Basic serialization for CLI
        for row in res['result']:
            print(row)

if __name__ == "__main__":
    main()
