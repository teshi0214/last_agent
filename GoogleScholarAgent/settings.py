from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # ログに出ていた環境変数に対応するフィールド（必要なら型・必須/任意を調整）
    serpapi_api_key: str | None = None
    google_genai_use_vertexai: bool | None = None
    staging_bucket: str | None = None
    google_cloud_location: str | None = None
    google_cloud_project: str | None = None

    # 未定義フィールドは無視する（extra='ignore'）
    model_config = SettingsConfigDict(extra='ignore')
