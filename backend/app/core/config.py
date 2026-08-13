from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Tutor Personal Edition"
    app_env: str = "development"
    admin_api_key: str = "change-me"

    database_url: str = "postgresql+asyncpg://aitutors:change-me@localhost:5432/aitutors"
    redis_url: str = "redis://localhost:6379/0"

    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "aitutors"
    minio_secret_key: str = "change-me"
    minio_bucket: str = "aitutors"
    minio_secure: bool = False

    llm_gateway_mode: str = "mock"
    deepseek_api_key: str | None = None
    mimo_api_key: str | None = None
    qwen_vl_api_key: str | None = None
    paddleocr_vl_token: str | None = None
    deepseek_base_url: str = ""
    deepseek_model: str = ""
    mimo_base_url: str = ""
    mimo_model: str = ""
    qwen_vl_base_url: str = ""
    qwen_vl_model: str = ""
    ollama_base_url: str = ""
    ollama_model: str = ""
    llm_request_timeout_seconds: float = 60.0

    paddleocr_api_base_url: str = "https://paddleocr.aistudio-app.com/api/v2/ocr/jobs"
    paddleocr_poll_interval_seconds: float = 5.0
    paddleocr_job_timeout_seconds: float = 600.0

    embedding_provider: str = "ollama"
    embedding_model: str = "qwen3-embedding:4b"
    embedding_dimension: int = 2560

    ocr_mock_mode: bool = True
    embedding_mock_mode: bool = True

    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://localhost:8080",
    ]

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
