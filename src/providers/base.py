from abc import ABC, abstractmethod
from typing import Any, Dict

class BaseLLMProvider(ABC):
    """Abstract interface for LLM integrations to avoid vendor lock-in."""
    
    @abstractmethod
    async def generate_sql(self, schema: str, question: str, plan: str) -> str:
        pass
        
    @abstractmethod
    async def generate_plan(self, schema: str, question: str) -> str:
        pass
        
    @abstractmethod
    async def understand_query(self, db_context: str, question: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def generate_visualization_config(self, question: str, columns: list, sample_data: list) -> Dict[str, Any]:
        pass
