import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "AI-Powered Product Intelligence Platform"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "dev_secret_key_change_in_production"

    # Database — SQLite default, override with PostgreSQL URL
    DATABASE_URL: str = "sqlite:///./product_intelligence.db"

    # Storage paths
    STORAGE_BASE_PATH: str = "./data_storage"
    PERMANENT_KNOWLEDGE_PATH: str = "./data_storage/permanent_knowledge"
    TEMP_CACHE_PATH: str = "./data_storage/temp_cache"
    USER_UPLOADS_PATH: str = "./data_storage/user_uploads"
    VECTOR_STORE_PATH: str = "./data_storage/vector_store"

    # Storage Safety Constraints (2 GiB each partition)
    MAX_PERMANENT_SIZE_BYTES: int = 2147483648
    MAX_TEMP_CACHE_SIZE_BYTES: int = 2147483648
    CACHE_RETENTION_DAYS: int = 7

    # Vector Store
    DEFAULT_TOP_K: int = 5

    # AI Provider configuration
    AI_PROVIDER: str = "ollama"          # "ollama" | "gemini" | "freellmapi"
    AI_ENGINE_MODE: str = "ollama"       # "ollama" | "gemini" | "auto" | "freellmapi"
    AI_ENGINE_AGENT1_MODE: str = "freellmapi"    # "freellmapi" | "ollama" | "gemini"
    AI_ENGINE_AGENT2_MODE: str = "freellmapi"    # "freellmapi" | "ollama" | "gemini"
    GEMINI_API_KEY_AGENT1: str = ""
    GEMINI_MODEL_AGENT1: str = "gemini-2.0-flash"
    GEMINI_API_KEY_AGENT2: str = ""
    GEMINI_MODEL_AGENT2: str = "gemini-2.0-flash"

    # xAI configuration
    XAI_API_KEY_AGENT1: str = ""
    XAI_MODEL_AGENT1: str = "grok-4.5"
    XAI_API_KEY_AGENT2: str = ""
    XAI_MODEL_AGENT2: str = "grok-4.5"
    XAI_MAX_RPS: int = 5
    XAI_MAX_TPM: int = 100000

    # FreeLLMAPI configuration
    FREELLMAPI_API_KEY: str = ""
    FREELLMAPI_BASE_URL: str = "https://api.freellmapi.com/v1"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()


def ensure_directories():
    os.makedirs(settings.STORAGE_BASE_PATH, exist_ok=True)
    os.makedirs(settings.PERMANENT_KNOWLEDGE_PATH, exist_ok=True)
    os.makedirs(settings.TEMP_CACHE_PATH, exist_ok=True)
    os.makedirs(settings.USER_UPLOADS_PATH, exist_ok=True)
    os.makedirs(settings.VECTOR_STORE_PATH, exist_ok=True)
