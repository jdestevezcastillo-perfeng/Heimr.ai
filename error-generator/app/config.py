"""Application configuration using Pydantic settings."""
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Service configuration
    host: str = Field(default="0.0.0.0", description="Service host")
    port: int = Field(default=8000, description="Service port")
    log_level: str = Field(default="info", description="Logging level")
    
    # CORS configuration
    cors_origins: list[str] = Field(default=["*"], description="Allowed CORS origins")
    
    # Metrics configuration
    metrics_enabled: bool = Field(default=True, description="Enable Prometheus metrics")
    
    class Config:
        """Pydantic settings configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()
