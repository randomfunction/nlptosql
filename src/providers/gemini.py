import json
from typing import Any, Dict
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from src.providers.base import BaseLLMProvider
from src.core.config import settings
from src.core.logger import logger

class GeminiProvider(BaseLLMProvider):
    def __init__(self):
        api_key = settings.GEMINI_API_KEY or settings.GOOGLE_API_KEY
        if not api_key:
            raise RuntimeError(
                "Gemini API key is missing. Set GEMINI_API_KEY or GOOGLE_API_KEY."
            )

        self.llm = ChatGoogleGenerativeAI(
            model=settings.GEMINI_MODEL,
            api_key=api_key,
            temperature=0
        )
        
    async def understand_query(self, db_context: str, question: str) -> Dict[str, Any]:
        prompt = ChatPromptTemplate.from_messages([
            ("system", f"""You are a SQL expert AI for a database containing: {db_context}
Analyze the user question and determine if it can be answered using this database.
Return a JSON object with:
- "intent": "aggregation", "filtering", "join", "meta-query", "irrelevant", or "general"
- "complexity": "simple", "moderate", or "complex"
- "entities": list of database entities/tables mentioned
- "ambiguity": list of ambiguous terms
- "rejection_reason": if intent is "irrelevant", explain why
"""),
            ("human", "{question}")
        ])
        
        chain = prompt | self.llm
        try:
            response = await chain.ainvoke({"question": question})
            content = response.content.replace("```json", "").replace("```", "").strip()
            return json.loads(content)
        except Exception as e:
            logger.error(f"Failed to understand query: {str(e)}", exc_info=True)
            return {"intent": "general", "complexity": "moderate", "entities": []}

    async def generate_plan(self, schema: str, question: str) -> str:
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a Query Planner. Create a numbered step-by-step plan to answer the question using the schema."),
            ("human", "Schema:\n{schema}\n\nQuestion: {question}")
        ])
        chain = prompt | self.llm
        response = await chain.ainvoke({"schema": schema, "question": question})
        return response.content

    async def generate_sql(self, schema: str, question: str, plan: str, prev_sql: str = "", error: str = "") -> str:
        if error:
            prompt_template = """You are fixing a broken SQL query.
Schema: {schema}
Question: {question}
Previous Failed SQL: {prev_sql}
Error Message: {error}
Return ONLY the corrected SQL query. No explanations."""
            params = {"schema": schema, "question": question, "prev_sql": prev_sql, "error": error}
        else:
            prompt_template = """Generate a safe, efficient SQLite query.
Schema: {schema}
Question: {question}
Plan: {plan}
Rules:
1. Read-only (SELECT only).
2. LIMIT {limit} unless aggregation.
3. Use CTEs for complex logic.
Return ONLY the SQL query. No explanations."""
            params = {"schema": schema, "question": question, "plan": plan, "limit": settings.MAX_ROWS_LIMIT}

        prompt = ChatPromptTemplate.from_template(prompt_template)
        chain = prompt | self.llm
        
        response = await chain.ainvoke(params)
        return response.content

    async def generate_visualization_config(self, question: str, columns: list, sample_data: list) -> Dict[str, Any]:
        prompt = ChatPromptTemplate.from_messages([
            ("system", """
Identify columns for visualization.
Return JSON: {{ "chart_type": "bar|line|pie", "label_column": "col_name", "value_column": "col_name_or_list" }}
If not suitable, return {{}}.
"""),
            ("human", "Columns: {cols}\nSample Data: {sample}")
        ])
        chain = prompt | self.llm
        try:
            response = await chain.ainvoke({"cols": str(columns), "sample": str(sample_data)})
            clean = response.content.replace("```json", "").replace("```", "").strip()
            return json.loads(clean)
        except Exception as e:
            logger.warning(f"Failed to generate visualization config: {e}")
            return {}
