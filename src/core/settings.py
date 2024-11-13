from pydantic import BaseSettings, Field
from typing import List, Optional
from pathlib import Path

class Settings(BaseSettings):
    """Application settings for VRP Optimizer."""
    
    # General settings
    APP_NAME: str = "VRP Optimizer"
    ENVIRONMENT: str = "development"
    
    # Database settings
    DATABASE_URL: str = "sqlite:///./vrp_optimizer.db"
    
    # Optimization settings
    MAX_VEHICLES: int = 10
    MAX_DISTANCE: int = 500  # in miles
    MAX_PALLETS: int = 20
    MAX_SHIPMENTS: int = 1000
    MAX_COMPUTATION_TIME: int = 300  # in seconds
    
    # Geocoding settings
    GEOCODING_API_KEY: Optional[str] = None
    MAX_RETRIES: int = 3
    
    # Monitoring settings
    MONITORING_ENABLED: bool = True
    MONITORING_URL: Optional[str] = None
    
    # Security settings
    JWT_SECRET_KEY: str = Field(..., env="JWT_SECRET_KEY")
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # File upload settings
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS: List[str] = ['xlsx', 'xls', 'csv']
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

# Load settings
settings = Settings()
