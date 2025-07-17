from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import BaseModel, PostgresDsn
from pathlib import Path


BASE_DIR = Path(__file__).parent.parent


class RunConfig(BaseModel):
    port: int = 8000
    host: str = "127.0.0.1"


class DatabaseConfig(BaseModel):
    url: PostgresDsn
    echo: bool = False
    echo_pool: bool = False
    pool_size: int = 50  # кол-во соединений в пуле
    max_overflow: int = 10  # кол-во дополнительных соединений
    naming_convertion: dict[str, str] = {
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    }


class AuthJWT(BaseModel):
    private_key: Path = BASE_DIR / "certs" / "private_key.pem"
    public_key: Path = BASE_DIR / "certs" / "public_key.pem"
    algorithm: str = "RS256"
    access_expire_min: int = 15
    refresh_expire_days: int = 2


class SMTPConfig(BaseModel):
    host: str = "smtp.example.com"
    port: int = 587
    user: str = "..."
    password: str = "..."
    from_email: str = "..."
    use_tls: bool = True
    use_ssl: bool = False


class S3Config(BaseModel):
    host: str
    port: int
    access_key: str
    secret_key: str
    bucket: str

    @property
    def endpoint(self) -> str:
        return f"{self.host}:{self.port}"

    @property
    def secure(self) -> bool:
        return False


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        case_sensitive=False,  # чувствительность к регистрам
        env_nested_delimiter="__",  # это деления как путь будет
        env_prefix="CONFIG__",
    )
    run: RunConfig = RunConfig()
    db: DatabaseConfig
    auth: AuthJWT = AuthJWT()
    smtp: SMTPConfig
    s3: S3Config


settings = Settings()
