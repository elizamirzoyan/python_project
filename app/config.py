from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Central configuration for DataSnoop.
    All values can be overridden via environment variables or a .env file.
    """

    APP_NAME: str = "DataSnoop"
    APP_VERSION: str = "2.0.0"
    APP_DESCRIPTION: str = (
        "Your friendly data detective — upload a CSV or fetch live web data "
        "and DataSnoop breaks it all down for you in plain English."
    )
    API_V1_PREFIX: str = "/api/v1"

    HOST: str = "127.0.0.1"
    PORT: int = 8000
    RELOAD: bool = True

    CHUNK_SIZE: int = 10_000
    MAX_FILE_SIZE_MB: int = 500
    MAX_COLUMNS: int = 1_000

    MAX_CONCURRENT_REQUESTS: int = 10
    REQUEST_TIMEOUT: int = 30

    ANOMALY_CONTAMINATION: float = 0.1
    RANDOM_SEED: int = 42

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()

APP_NAME = settings.APP_NAME
APP_VERSION = settings.APP_VERSION
APP_DESCRIPTION = settings.APP_DESCRIPTION
API_V1_PREFIX = settings.API_V1_PREFIX
HOST = settings.HOST
PORT = settings.PORT
