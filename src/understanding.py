import json
from .llm import LLMService

def analyze_query(question: str, llm: LLMService) -> dict:
    prompt = f"""
    Analyze the following natural language query for a SQL database.
    Query: "{question}"
    
    Provide a JSON response with the following keys:
    - "intent": The type of query (e.g., "aggregation", "filtering", "join", "meta-query").
      * "meta-query": If the user asks about tables, columns, or schema structure (e.g., "Show tables").
    - "entities": A list of potential entities or table names mentioned or implied.
    - "ambiguity": A list of ambiguous terms that might need clarification (e.g., "best", "top", "recent" without specific numbers or criteria).
    - "complexity": "simple", "moderate", or "complex".
    
    Return ONLY valid JSON.
    """
    
    response_text = llm.generate_content(prompt)
    
    # Basic cleanup to ensure JSON parsing
    response_text = response_text.replace("```json", "").replace("```", "").strip()
    
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        # Fallback if specific formatting fails, though with Gemini it's usually good.
        print(f"Failed to parse JSON for query understanding. Response: {response_text}")
        return {
            "intent": "unknown",
            "entities": [],
            "ambiguity": [],
            "complexity": "moderate" # Assume moderate on failure
        }
