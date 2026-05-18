import aiosqlite
import asyncio
from typing import Tuple, List, Any
from src.core.config import settings
from src.core.logger import logger

class QueryExecutor:
    """Handles safe database interactions with timeouts and sandboxing."""
    
    def __init__(self, db_path: str = settings.DB_FILE):
        self.db_path = db_path

    @staticmethod
    def _normalize_sql(sql: str) -> str:
        cleaned = sql.strip()
        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            if lines:
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            cleaned = "\n".join(lines).strip()
        if cleaned.lower().startswith("sql\n"):
            cleaned = cleaned[4:].strip()
        return cleaned
        
    async def execute_safe(self, sql: str) -> Tuple[List[str], List[tuple]]:
        """Executes a SQL query asynchronously with timeout and limits."""
        sql = self._normalize_sql(sql)

        # Safety Check: Enforce Read-Only at application layer
        sql_upper = sql.upper()
        dangerous_keywords = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "GRANT", "REVOKE"]
        if any(kw in sql_upper for kw in dangerous_keywords):
            raise ValueError("Unsafe SQL detected. Only SELECT queries are permitted.")

        # Limit enforcement
        if "LIMIT" not in sql_upper and "COUNT" not in sql_upper:
            sql += f" LIMIT {settings.MAX_ROWS_LIMIT}"

        try:
            # We use a timeout to prevent runaway queries
            return await asyncio.wait_for(
                self._run_query(sql),
                timeout=settings.QUERY_TIMEOUT_SEC
            )
        except asyncio.TimeoutError:
            logger.error(f"Query timed out after {settings.QUERY_TIMEOUT_SEC}s: {sql}")
            raise TimeoutError("The database query took too long to execute.")
        except Exception as e:
            logger.error(f"SQL Execution error: {e}")
            raise

    async def _run_query(self, sql: str) -> Tuple[List[str], List[tuple]]:
        # Mode 'ro' enforces read-only connection at SQLite layer
        uri = f"file:{self.db_path}?mode=ro"
        async with aiosqlite.connect(uri, uri=True) as db:
            async with db.execute(sql) as cursor:
                columns = [desc[0] for desc in cursor.description] if cursor.description else []
                rows = await cursor.fetchall()
                return columns, rows
