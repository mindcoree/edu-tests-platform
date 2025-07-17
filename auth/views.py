from fastapi import (
    APIRouter,
    status,
    Form,
    Response,
)
from .schemas import (
    AuthEntityOut,
    AuthEntityIn,
    TokenInfo,
    AuthCredentials,
    RoleRequestCreate,
    RoleRequestOut,
    PasswordResetRequest,
    PasswordResetConfirm,
    PasswordResetResponse,
)
from .dependencies import AuthServiceDep, RoleRequestServiceDep, PayloadEntity
from common.config import settings
from utils import auth
from common.type.jwt import ACCESS_TOKEN_COOKIE_KEY, REFRESH_TOKEN_COOKIE_KEY
from typing import Annotated

router = APIRouter()


@router.post(
    "/register",
    response_model=AuthEntityOut,
    status_code=status.HTTP_201_CREATED,
)
async def register_entity(
    entity_in: Annotated[AuthEntityIn, Form()],
    service: AuthServiceDep,
) -> AuthEntityOut:
    """Ручка для регистрации новой аутентифицируемой сущности."""
    return await service.register_entity(auth_in=entity_in)


@router.post(
    "/login",
    response_model=TokenInfo,
)
async def login(
    credentials: Annotated[AuthCredentials, Form()],
    service: AuthServiceDep,
    response: Response,
) -> TokenInfo:
    """
    Ручка для входа в систему.

    Аутентифицирует сущность, создает access и refresh токены
    и устанавливает их в безопасные http-only cookie.
    """
    auth_entity = await service.authenticate_entity(credentials)
    access_token = await auth.create_access_token(auth_info=auth_entity)
    refresh_token = await auth.create_refresh_token(auth_info=auth_entity)
    await auth.set_token_cookie(
        response=response,
        key=ACCESS_TOKEN_COOKIE_KEY,
        value=access_token,
        max_age=settings.auth.access_expire_min * 60,
    )
    await auth.set_token_cookie(
        response=response,
        key=REFRESH_TOKEN_COOKIE_KEY,
        value=refresh_token,
        max_age=settings.auth.refresh_expire_days * 24 * 60 * 60,
    )
    return TokenInfo(access=access_token, refresh=refresh_token)


# --- Заявки на роль ---


@router.post(
    "/role-request",
    response_model=RoleRequestOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_role_request(
    data: Annotated[RoleRequestCreate, Form()],
    service: RoleRequestServiceDep,
    payload: PayloadEntity,
) -> RoleRequestOut:
    """
    Создать заявку на смену роли (может вызвать любой аутентифицированный пользователь).
    """
    req = await service.create_request(entity_id=int(payload.sub), data=data)
    return req


@router.post(
    "/password-reset-request",
    response_model=PasswordResetResponse,
    status_code=status.HTTP_200_OK,
)
async def password_reset_request(
    data: PasswordResetRequest,
    service: AuthServiceDep,
) -> PasswordResetResponse:
    return await service.password_reset_request(data)


@router.post(
    "/password-reset-confirm",
    response_model=PasswordResetResponse,
    status_code=status.HTTP_200_OK,
)
async def password_reset_confirm(
    data: PasswordResetConfirm,
    service: AuthServiceDep,
) -> PasswordResetResponse:
    return await service.password_reset_confirm(data)
