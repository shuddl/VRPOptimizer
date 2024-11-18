import logging
from pydantic_settings import BaseSettings
from pydantic import Field
from pathlib import Path
from typing import Optional


class Settings(BaseSettings):
    """Application settings for VRP Optimizer."""

    # General settings
    APP_NAME: str = "VRP Optimizer"
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")

    # Debugging and logging
    DEBUG: bool = Field(default=False, env="DEBUG")
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")

    # Worker settings
    MAX_WORKERS: int = Field(default=4, env="MAX_WORKERS")

    # Database settings
    DATABASE_URL: str = Field(..., env="DATABASE_URL")
    DB_POOL_SIZE: int = Field(default=5, env="DB_POOL_SIZE")
    DB_MAX_OVERFLOW: int = Field(default=10, env="DB_MAX_OVERFLOW")
    DB_POOL_TIMEOUT: int = Field(default=30, env="DB_POOL_TIMEOUT")
    DB_POOL_RECYCLE: int = Field(default=1800, env="DB_POOL_RECYCLE")

    # Optimization settings
    MAX_VEHICLES: int = 10
    MAX_DISTANCE: int = 5000  # increased to 5000 miles
    MAX_PALLETS: int = 20
    MAX_SHIPMENTS: int = 1000
    MAX_COMPUTATION_TIME: int = 300  # in seconds

    # Geocoding settings
    GEOCODING_API_KEY: Optional[str] = Field(env="GEOCODING_API_KEY")
    MAX_RETRIES: int = 3

    # Monitoring settings
    MONITORING_ENABLED: bool = Field(default=True, env="MONITORING_ENABLED")
    MEMORY_LIMIT_MB: int = 1024  # Default to 1GB

    # Security settings
    JWT_SECRET_KEY: str = Field(..., env="JWT_SECRET_KEY")
    JWT_ALGORITHM: str = "HS256"

    # Cache directory settings
    CACHE_DIR: Optional[Path] = Field(default=Path("./cache"), env="CACHE_DIR")

    # Redis settings
    REDIS_URL: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    REDIS_PASSWORD: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    REDIS_SSL: bool = Field(default=False, env="REDIS_SSL")
    REDIS_TIMEOUT: int = Field(default=5, env="REDIS_TIMEOUT")
    REDIS_RETRY_COUNT: int = Field(default=3, env="REDIS_RETRY_COUNT")
    REDIS_RETRY_DELAY: int = Field(default=1, env="REDIS_RETRY_DELAY")

    # Cache settings
    CACHE_TTL: int = Field(default=2592000, env="CACHE_TTL")  # 30 days in seconds

    # Visualization settings
    VISUALIZATION_CPU_LIMIT: int = 100  # Example default value (adjust as needed)
    VISUALIZATION_MEMORY_LIMIT: int = (
        32768  # Example default value in MB (adjust as needed)
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "allow"
        case_sensitive = False

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.CACHE_DIR.mkdir(parents=True, exist_ok=True)

    @property
    def database_settings(self):
        """Get database-specific settings as a dictionary."""
        return {
            "pool_size": self.DB_POOL_SIZE,
            "max_overflow": self.DB_MAX_OVERFLOW,
            "pool_timeout": self.DB_POOL_TIMEOUT,
            "pool_recycle": self.DB_POOL_RECYCLE,
        }

    @property
    def redis_settings(self):
        """Get Redis-specific settings as a dictionary."""
        return {
            "url": self.REDIS_URL,
            "password": self.REDIS_PASSWORD,
            "ssl": self.REDIS_SSL,
            "timeout": self.REDIS_TIMEOUT,
            "retry_count": self.REDIS_RETRY_COUNT,
            "retry_delay": self.REDIS_RETRY_DELAY,
        }


# Instantiate settings
settings = Settings()

# Configure logging
logging.basicConfig(level=logging.INFO if not settings.DEBUG else logging.DEBUG)

# Debugging output to confirm settings are loaded
if settings.DEBUG:
    print(f"Loaded settings: {settings.dict()}")
    print(f"DATABASE_URL: {settings.DATABASE_URL}")
