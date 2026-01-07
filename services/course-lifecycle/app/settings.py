from shared.core.settings import BaseAppSettings

class Settings(BaseAppSettings):
    APP_NAME: str = "Course Lifecycle Service"
    COURSE_SEED_ENABLED: bool = True
    GEMINI_API_KEY: str | None = None
    DEEPSEEK_API_KEY: str | None = None
    EXPORT_DIR: str = "/app/generated_data/exports"
    AI_AUTHORING_URL: str = "http://ai-authoring:8000"
    ENABLE_OCR: bool = False
    OCR_SERVICE_URL: str | None = None
    VERSION: str = "0.1.0"

settings = Settings()
