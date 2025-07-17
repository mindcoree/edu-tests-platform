from typing import Optional
from jwt.exceptions import InvalidTokenError
from .repository import AuthRepository, RoleRequestRepository
from utils import auth
from common.type.jwt import ACCESS_TOKEN_COOKIE_KEY, REFRESH_TOKEN_COOKIE_KEY
from sqlalchemy.exc import IntegrityError
from .models import AuthEntity, RoleRequestStatus
from fastapi import HTTPException, status, Response, Request
from common.config import settings
from .schemas import (
    AccessTokenPayload,
    RoleRequestCreate,
    AuthEntityIn,
    AuthCredentials,
    PasswordResetRequest,
    PasswordResetConfirm,
    PasswordResetResponse,
)
from common.enums import Role
from utils.email import send_email
from datetime import timedelta


class AuthServices:
    """
    Сервисный слой для логики аутентификации и управления сущностями.
    """

    def __init__(
        self,
        repository: AuthRepository,
        role_request_repo: RoleRequestRepository = None,
    ):
        self.repo = repository
        self.role_request_repo = role_request_repo

    async def register_entity(self, auth_in: AuthEntityIn) -> AuthEntity:
        """
        Регистрирует новую аутентифицируемую сущность в системе.
        Если выбрана не базовая роль, создаёт заявку на роль, а роль пользователя остаётся student.
        """
        hashed_password = await auth.hash_password(auth_in.password)
        entity_data = auth_in.model_dump(exclude={"password", "desired_role"})
        entity_data["hash_password"] = hashed_password
        # По умолчанию роль student
        try:
            entity = await self.repo.create_entity(entity_data)
        except IntegrityError:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Пользователь с таким email или login уже существует",
            )
        # Если пользователь выбрал не student, создаём заявку
        desired_role = auth_in.desired_role
        if desired_role and desired_role != Role.STUDENT and self.role_request_repo:
            await self.role_request_repo.create(
                entity_id=entity.id, requested_role=desired_role
            )

        return entity

    async def authenticate_entity(self, credentials: AuthCredentials) -> AuthEntity:
        """
        Аутентифицирует сущность по логину и паролю.
        Если у пользователя есть активная заявка на роль, login запрещён.
        """
        auth_entity = await self.repo.get_auth_entity_for_verify(
            login=credentials.login
        )
        # Проверка на активную заявку
        if self.role_request_repo:
            pending = await self.role_request_repo.list_requests(
                status=RoleRequestStatus.PENDING
            )
            if any(r.entity_id == auth_entity.id for r in pending[1]):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Ваша заявка на роль ещё не обработана администратором. Вход невозможен.",
                )
        if not auth_entity or not await auth.verify_password(
            password=credentials.password,
            hashed_password=auth_entity.hash_password,
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid login or password",
            )
        return auth_entity

    async def refresh_authentication(
        self,
        response: Response,
        refresh_token: str,
    ) -> AuthEntity:
        """
        Обновляет access-токен, используя refresh-токен.

        Декодирует refresh-токен, находит соответствующую сущность,
        создает новый access-токен и устанавливает его в cookie.

        Args:
            response: Объект FastAPI Response для установки cookie.
            refresh_token: Refresh-токен, полученный из cookie.

        Raises:
            HTTPException: Если refresh-токен невалиден или сущность не найдена.

        Returns:
            Объект AuthEntitySchema, для которого был обновлен токен.
        """
        try:
            refresh_payload = await auth.decode_jwt(token=refresh_token)
        except InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )

        id_entity = int(refresh_payload.get("sub"))
        auth_entity = await self.repo.get_auth_entity_by_id(id_entity)
        if not auth_entity:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{AuthEntity.__name__} not found by id: {id_entity}",
            )

        access_token = await auth.create_access_token(auth_info=auth_entity)
        await auth.set_token_cookie(
            response=response,
            key=ACCESS_TOKEN_COOKIE_KEY,
            value=access_token,
            max_age=settings.auth.access_expire_min * 60,
        )

        return auth_entity

    async def access_token_payload(
        self, request: Request, response: Response
    ) -> AccessTokenPayload:
        """
        Извлекает полезную нагрузку из access-токена.

        Сначала пытается получить данные из состояния запроса (state).
        Если их там нет, пытается обновить access-токен с помощью refresh-токена.

        Args:
            request: Объект FastAPI Request.
            response: Объект FastAPI Response.

        Raises:
            HTTPException: Если токены отсутствуют или невалидны.

        Returns:
            Полезная нагрузка (payload) access-токена.
        """
        payload = getattr(request.state, "auth_payload", None)
        if payload:
            return AccessTokenPayload(**payload)

        refresh_token = request.cookies.get(REFRESH_TOKEN_COOKIE_KEY)
        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token not provided",
            )

        auth_entity = await self.refresh_authentication(
            response=response, refresh_token=refresh_token
        )
        payload = auth.create_payload(auth_payload=auth_entity)
        return AccessTokenPayload(**payload)

    async def password_reset_request(
        self, data: PasswordResetRequest
    ) -> PasswordResetResponse:
        entity = await self.repo.get_auth_entity_by_email(data.email)
        if not entity:
            # Не раскрываем, что пользователя нет
            return PasswordResetResponse(
                detail="Если email зарегистрирован, инструкция отправлена."
            )
        # Генерируем токен сброса (JWT, TTL 30 мин)
        token = await auth.encode_jwt(
            payload={
                "sub": str(entity.id),
                "email": entity.email,
                "type": "password_reset",
            },
            expire_timedelta=timedelta(minutes=30),
        )
        reset_link = f"https://your-frontend-domain/reset-password?token={token}"
        subject = "Сброс пароля"
        body = f"""
        <p>Для сброса пароля перейдите по ссылке:</p>
        <p><a href='{reset_link}'>{reset_link}</a></p>
        <p>Ссылка действительна 30 минут.</p>
        """
        send_email(entity.email, subject, body)
        return PasswordResetResponse(
            detail="Если email зарегистрирован, инструкция отправлена."
        )

    async def password_reset_confirm(
        self, data: PasswordResetConfirm
    ) -> PasswordResetResponse:
        if data.new_password != data.repeat_password:
            raise HTTPException(status_code=400, detail="Пароли не совпадают")
        try:
            payload = await auth.decode_jwt(data.token)
        except Exception:
            raise HTTPException(
                status_code=400, detail="Некорректный или просроченный токен"
            )
        if payload.get("type") != "password_reset":
            raise HTTPException(status_code=400, detail="Некорректный токен")
        entity_id = int(payload.get("sub"))
        entity = await self.repo.get_auth_entity_by_id(entity_id)
        if not entity:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден"
            )
        new_hash = await auth.hash_password(data.new_password)
        await self.repo.update_password(entity_id, new_hash)
        return PasswordResetResponse(detail="Пароль успешно изменён")


class RoleRequestService:
    def __init__(self, repo: RoleRequestRepository, entity_repo: AuthRepository):
        self.repo = repo
        self.entity_repo = entity_repo

    async def create_request(self, entity_id: int, data: RoleRequestCreate):
        # Проверка: нет ли уже активной заявки (только pending)
        total, requests = await self.repo.list_requests(
            status=RoleRequestStatus.PENDING
        )
        if any(r.entity_id == entity_id for r in requests):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Active request already exists",
            )
        # Если нет pending — разрешаем создать новую заявку, даже если были rejected/approved
        return await self.repo.create(
            entity_id=entity_id, requested_role=data.requested__desired_role
        )

    async def get_request(self, request_id: int):
        req = await self.repo.get_by_id(request_id)
        if not req:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Request not found",
            )
        return req

    async def list_requests(
        self, status_: Optional[RoleRequestStatus], offset: int, limit: int
    ):
        return await self.repo.list_requests(status=status_, offset=offset, limit=limit)

    async def approve_request(self, request_id: int):
        req = await self.get_request(request_id)
        if req.status != RoleRequestStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Request already processed",
            )
        # Меняем роль у сущности
        await self.repo.update_role(
            entity_id=req.entity_id, new_role=req.requested_role
        )
        return await self.repo.update_status(request_id, RoleRequestStatus.APPROVED)

    async def reject_request(self, request_id: int):
        req = await self.get_request(request_id)
        if req.status != RoleRequestStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Request already processed",
            )
        return await self.repo.update_status(request_id, RoleRequestStatus.REJECTED)
