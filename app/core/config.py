from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "SINCOV"
    PROJECT_VERSION: str = "0.1.0"
    DATABASE_URL: str

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()
