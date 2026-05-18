from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    # App Config
    APP_NAME: str = "Agentic Text-to-SQL"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Database
    DB_FILE: str = "Chinook_Sqlite.sqlite"
    
    # LLM Settings
    DEFAULT_PROVIDER: str = "gemini"
    GEMINI_API_KEY: Optional[str] = None
    GOOGLE_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-2.5-flash-lite"
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o"
    
    # API Security
    API_KEY: Optional[str] = None
    RATE_LIMIT_PER_MINUTE: int = 60
    
    # Observability
    LOG_LEVEL: str = "INFO"
    ENABLE_TRACING: bool = False
    
    # Caching
    REDIS_URL: Optional[str] = None
    CACHE_TTL_SECONDS: int = 3600
    
    # Query Limits
    MAX_ROWS_LIMIT: int = 1000
    QUERY_TIMEOUT_SEC: int = 15
    MAX_RETRIES: int = 3

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
