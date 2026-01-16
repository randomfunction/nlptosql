from .llm import LLMService

def generate_plan(question: str, schema_context: str, llm: LLMService) -> str:
    prompt = f"""
    You are a Query Planner for a Text-to-SQL system.
    Your goal is to break down the user's complex question into logical steps before generating SQL.
    
    Database Schema:
    {schema_context}
    
    User Question: "{question}"
    
    Create a step-by-step plan to answer this question.
    Format your response as a numbered list.
    For each step, identify:
    - What data is needed.
    - Which table(s) to access.
    - Any conditions or filters.
    
    Example Plan:
    1. Find the internal ID for the genre "Rock" from the Genre table.
    2. Find all tracks with that GenreId from the Track table.
    3. Count the number of such tracks.
    
    Return ONLY the numbered plan.
    """
    
    return llm.generate_content(prompt)
