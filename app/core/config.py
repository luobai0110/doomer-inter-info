from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置，从环境变量与 .env 文件加载。"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ---------- 数据库 (PostgreSQL) ----------
    db_host: str = "127.0.0.1"
    db_port: int = 5432
    db_user: str = "postgres"
    db_password: str = "postgres"
    db_name: str = "inter"
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_echo: bool = False

    # ---------- 雪花 ID 服务 ----------
    snowflake_id_url: str = "http://192.168.1.3:8088"

    # ---------- 日志 ----------
    log_level: str = "INFO"

    @property
    def database_url(self) -> str:
        """SQLAlchemy 连接 PostgreSQL 的 URL（psycopg2 驱动）。"""
        return (
            f"postgresql+psycopg2://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


settings = Settings()
