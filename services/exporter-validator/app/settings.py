from shared.core.settings import BaseAppSettings

class Settings(BaseAppSettings):
    SERVICE_NAME: str = "exporter-validator"

settings = Settings()
