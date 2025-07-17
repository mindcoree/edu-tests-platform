import asyncio
import bcrypt
import jwt
from datetime import datetime, timezone, timedelta
from functools import lru_cache
from common.config import settings
from auth.schemas import AuthEntitySchema
from common.type.jwt import TOKEN_TYPE_FIELD, ACCESS_TOKEN_TYPE, REFRESH_TOKEN_TYPE
from fastapi import Response


@lru_cache(maxsize=1)
def get_private_key() -> str:
    """
    Считывает и кэширует приватный ключ для подписи JWT.

    Returns:
        Содержимое приватного ключа в виде строки.
    """
    return settings.auth.private_key.read_text()


@lru_cache(maxsize=1)
def get_public_key() -> str:
    """
    Считывает и кэширует публичный ключ для верификации JWT.

    Returns:
        Содержимое публичного ключа в виде строки.
    """
    return settings.auth.public_key.read_text()


async def encode_jwt(
    payload: dict,
    private_key: str = get_private_key(),
    algorithm: str = settings.auth.algorithm,
    expire_minute: int = settings.auth.access_expire_min,
    expire_timedelta: timedelta | None = None,
) -> str:
    """
    Кодирует данные в JWT.

    Args:
        payload: Данные для кодирования.
        private_key: Приватный ключ для подписи.
        algorithm: Алгоритм подписи.
        expire_minute: Время жизни токена в минутах.
        expire_timedelta: Время жизни токена в виде timedelta.

    Returns:
        Сгенерированный JWT в виде строки.
    """
    now = datetime.now(timezone.utc)
    if expire_timedelta:
        expire = now + expire_timedelta
    else:
        expire = now + timedelta(minutes=expire_minute)

    payload.update(
        exp=int(expire.timestamp()),
        iat=int(now.timestamp()),
    )
    return await asyncio.to_thread(
        jwt.encode,
        payload=payload,
        key=private_key,
        algorithm=algorithm,
    )


async def decode_jwt(
    token: str,
    public_key: str = get_public_key(),
    algorithm: str = settings.auth.algorithm,
) -> dict:
    """
    Декодирует JWT и возвращает его полезную нагрузку.

    Args:
        token: JWT для декодирования.
        public_key: Публичный ключ для верификации.
        algorithm: Алгоритм подписи.

    Returns:
        Полезная нагрузка (payload) токена.
    """
    return await asyncio.to_thread(
        jwt.decode,
        jwt=token,
        key=public_key,
        algorithms=[algorithm],
    )


async def hash_password(password: str) -> str:
    """
    Хеширует пароль с использованием bcrypt.

    Args:
        password: Пароль в открытом виде.

    Returns:
        Хешированный пароль в виде строки.
    """
    salt = bcrypt.gensalt()
    password_bytes: bytes = password.encode()
    hashed_password: bytes = await asyncio.to_thread(
        bcrypt.hashpw, password_bytes, salt
    )
    return hashed_password.decode("utf-8")


async def verify_password(password: str, hashed_password) -> bool:
    """
    Проверяет, соответствует ли пароль хешу.

    Args:
        password: Пароль в открытом виде.
        hashed_password: Хешированный пароль для сравнения.

    Returns:
        True, если пароль верный, иначе False.
    """
    return await asyncio.to_thread(
        bcrypt.checkpw,
        password=password.encode(),
        hashed_password=hashed_password.encode(),
    )


async def create_jwt(
    token_data: dict,
    token_type: str,
    expire_minutes: int = settings.auth.access_expire_min,
    expire_timedelta: timedelta | None = None,
) -> str:
    """
    Создает JWT определенного типа (access или refresh).

    Args:
        token_data: Данные для включения в токен.
        token_type: Тип токена (например, 'access' или 'refresh').
        expire_minutes: Время жизни токена в минутах.
        expire_timedelta: Время жизни токена в виде timedelta.

    Returns:
        Сгенерированный JWT.
    """
    payload = {TOKEN_TYPE_FIELD: token_type}
    payload.update(token_data)
    return await encode_jwt(
        payload=payload,
        expire_minute=expire_minutes,
        expire_timedelta=expire_timedelta,
    )


async def create_access_token(auth_info: AuthEntitySchema) -> str:
    """
    Создает access-токен для аутентифицированной сущности.

    Args:
        auth_info: Данные аутентифицированной сущности.

    Returns:
        Сгенерированный access-токен.
    """
    payload = create_payload(auth_payload=auth_info)
    return await create_jwt(
        token_data=payload,
        token_type=ACCESS_TOKEN_TYPE,
        expire_minutes=settings.auth.access_expire_min,
    )


async def create_refresh_token(auth_info: AuthEntitySchema) -> str:
    """
    Создает refresh-токен для аутентифицированной сущности.

    Args:
        auth_info: Данные аутентифицированной сущности.

    Returns:
        Сгенерированный refresh-токен.
    """
    payload = {"sub": str(auth_info.id)}
    return await create_jwt(
        token_type=REFRESH_TOKEN_TYPE,
        token_data=payload,
        expire_timedelta=timedelta(days=settings.auth.refresh_expire_days),
    )


def create_payload(auth_payload: AuthEntitySchema) -> dict:
    """
    Формирует стандартную полезную нагрузку для access-токена.

    Args:
        auth_payload: Данные аутентифицированной сущности.

    Returns:
        Словарь с данными для JWT.
    """
    return {
        "sub": str(auth_payload.id),
        "login": auth_payload.login,
        "role": auth_payload.role,
    }


async def set_token_cookie(
    response: Response,
    key: str,
    value: str,
    max_age: int,
    # httponly: bool = True,
    # secure: bool = True,
    # samesite: str = "lax",
) -> None:
    """
    Устанавливает токен в http-only cookie.
    Args:
        response: Объект FastAPI Response.
        key: Имя cookie.
        value: Значение cookie (токен).
        max_age: Время жизни cookie в секундах.
        httponly: Флаг, запрещающий доступ к cookie из JavaScript.
        secure: Флаг, требующий HTTPS для передачи cookie.
        samesite: Политика SameSite для защиты от CSRF.
    """
    response.set_cookie(
        key=key,
        value=value,
        max_age=max_age,
        # httponly=httponly,
        # samesite=samesite,
        # secure=secure,
    )
