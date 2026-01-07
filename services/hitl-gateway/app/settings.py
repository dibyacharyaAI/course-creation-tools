from shared.core.settings import BaseAppSettings

class Settings(BaseAppSettings):
    SERVICE_NAME: str = "hitl-gateway"

settings = Settings()
