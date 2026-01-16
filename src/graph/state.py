from typing import TypedDict, List, Any, Optional

class AgentState(TypedDict):
    """
    State of the Text-to-SQL Agent.
    """
    question: str
    
    # Understanding
    intent: Optional[str]
    complexity: Optional[str]
    entities: List[str]
    ambiguity: List[str]
    clarification_question: Optional[str] # If set, we stop and ask user
    
    # Schema
    relevant_schema: Optional[str]
    
    # Planning
    plan: Optional[str]
    
    # Generation
    sql: Optional[str]
    
    # Execution
    results: Optional[List[Any]]
    error: Optional[str]
    visualization: Optional[dict] # {type: 'bar', data: {...}}
    
    # Final Output
    final_answer: Optional[str]
    
    # Internal
    attempts: int
    logs: List[dict] # For UI: {title, content, type}
