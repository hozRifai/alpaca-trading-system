import os

from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database settings
    DB_HOST: str = os.getenv('DB_HOST', 'timescaledb')
    DB_PORT: int = int(os.getenv('DB_PORT', 5432))
    DB_USER: str = os.getenv('DB_USER', 'postgres')
    DB_PASSWORD: str = os.getenv('DB_PASSWORD', '')
    DB_NAME: str = os.getenv('DB_NAME', 'market_data')

    # Polygon.io settings
    POLYGON_API_KEY: str = os.getenv('POLYGON_API_KEY', '')
    POLYGON_BASE_URL: str = 'https://api.polygon.io/v2'
    POLYGON_MARKET_STATUS_URL: str = 'https://api.polygon.io/v1/marketstatus'
    POLYGON_AGGREGATES_URL: str = 'https://api.polygon.io/v2/aggs/ticker'
    POLYGON_REQUEST_LIMIT: str = '500000000'
    
    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

settings = Settings()

print("Loaded settings:")
print(f"DB_USER: {settings.DB_USER}")
print(f"DB_HOST: {settings.DB_HOST}")
print(f"DB_NAME: {settings.DB_NAME}")