from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://dbuser:Zeniusit123@10.16.7.95/freeswitchcore"

settings = Settings()
