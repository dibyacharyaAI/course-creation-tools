from shared.core.settings import BaseAppSettings

class Settings(BaseAppSettings):
    SERVICE_NAME: str = "ai-authoring"

settings = Settings()
