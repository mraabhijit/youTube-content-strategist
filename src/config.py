from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    mongo_uri: str
    mongo_db_name: str
    youtube_api_key: str

    # Collections
    collection_trends: str = "market_trends"
    collection_configs: str = "video_configs"
    collection_replay: str = "experience_replay"

    # RL Settings
    simulation_episodes: int = 2000
    reward_window_hours: int = 48

    # Youtube secrets
    client_secrets_path: str = "client_secrets.json"
    token_path: str = "token.json"
    youtube_channel_id: str = ""


settings = Settings()
