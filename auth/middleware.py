from typing import Callable, Awaitable

from fastapi import Request, Response, HTTPException, status
from jwt import ExpiredSignatureError, InvalidTokenError

from main import main_app
from common.type.jwt import ACCESS_TOKEN_TYPE, TOKEN_TYPE_FIELD
from utils import auth


@main_app.middleware("http")
async def verify_jwt_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
):
    """
    Проверяет JWT access-токен из cookie для каждого входящего запроса.

    Пропускает публичные ручки. Если токен валиден, его полезная
    нагрузка (payload) сохраняется в `request.state.auth_payload` для
    дальнейшего использования в защищенных ручках.
    """
    public_paths = {
        "/login",
        "/register",
        "/refresh",
        "/docs",
        "/openapi.json",
        "/",
    }
    if request.url.path in public_paths or request.url.path.startswith("/static"):
        return await call_next(request)

    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    request.state.auth_payload = None
    try:
        payload = await auth.decode_jwt(token=token)
        current_token_type = payload.get(TOKEN_TYPE_FIELD)
        if current_token_type != ACCESS_TOKEN_TYPE:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
            )
        request.state.auth_payload = payload
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        )
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    return await call_next(request)
