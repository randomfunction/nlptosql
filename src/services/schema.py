import aiosqlite
from typing import List, Dict, Any
from src.core.config import settings
from src.core.logger import logger
from src.services.cache import cache_service

class SchemaService:
    def __init__(self, db_path: str = settings.DB_FILE):
        self.db_path = db_path

    async def get_table_names(self) -> List[str]:
        async with aiosqlite.connect(f"file:{self.db_path}?mode=ro", uri=True) as db:
            async with db.execute("SELECT name FROM sqlite_master WHERE type='table';") as cursor:
                rows = await cursor.fetchall()
                return [row[0] for row in rows if not row[0].startswith("sqlite_")]

    async def get_database_summary(self) -> str:
        cached_summary = await cache_service.get_schema_summary()
        if cached_summary:
            return cached_summary

        tables = await self.get_table_names()
        summary = f"This database contains the following tables: {', '.join(tables)}."
        await cache_service.set_schema_summary(summary)
        return summary

    async def get_structured_schema(self) -> Dict[str, List[Dict[str, str]]]:
        schema = {}
        tables = await self.get_table_names()
        async with aiosqlite.connect(f"file:{self.db_path}?mode=ro", uri=True) as db:
            for table in tables:
                async with db.execute(f"PRAGMA table_info({table})") as cursor:
                    rows = await cursor.fetchall()
                    schema[table] = [{"name": row[1], "type": row[2]} for row in rows]
        return schema

    async def get_schema_for_tables(self, tables: List[str]) -> str:
        schema_str = ""
        async with aiosqlite.connect(f"file:{self.db_path}?mode=ro", uri=True) as db:
            for table_name in tables:
                async with db.execute(f"PRAGMA table_info({table_name})") as cursor:
                    columns = await cursor.fetchall()
                    schema_str += f"Table: {table_name}\n"
                    for col in columns:
                        schema_str += f"  - {col[1]} ({col[2]})\n"
                    schema_str += "\n"
        return schema_str

    async def get_relevant_tables(self, question: str, complexity: str, llm_provider: Any) -> str:
        tables = await self.get_table_names()
        
        if complexity == "simple":
            relevant_tables = [t for t in tables if t.lower() in question.lower()]
            if not relevant_tables:
                 return await self._get_relevant_tables_llm(question, tables, llm_provider)
            return await self.get_schema_for_tables(relevant_tables)
        else:
            return await self._get_relevant_tables_llm(question, tables, llm_provider)

    async def _get_relevant_tables_llm(self, question: str, tables: List[str], llm_provider: Any) -> str:
        # Dynamic dispatch to LLM via Provider
        # We can simulate this using the provider's generate_plan/understand_query or similar.
        # But a more direct method is required for extracting tables. We will fetch everything for simplicity
        # if the provider lacks a specific method, or implement a specific method.
        # For now, let's just fetch full schema to avoid another LLM hop, or just a subset.
        full_schema = await self.get_schema_for_tables(tables)
        return full_schema

schema_service = SchemaService()
