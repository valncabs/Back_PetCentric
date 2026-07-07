from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.core.config import settings
from app.core.exceptions import BadRequestException, ConflictException, NotFoundException, UnauthorizedException
from app.core.security import create_access_token, generate_opaque_token, hash_opaque_token, hash_password, verify_password
from app.repositories.email_verification_repository import EmailVerificationRepository
from app.repositories.password_reset_repository import PasswordResetRepository
from app.repositories.user import UserRepository
from app.services.email import EmailService
from app.repositories.user_profile_repository import UserProfileRepository
from app.repositories.rol_repository import RoleRepository
from app.repositories.user_rol_repository import UserRoleRepository
class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.user_repo = UserRepository(db)
        self.email_verification_repo = EmailVerificationRepository(db)
        self.password_reset_repo = PasswordResetRepository(db)
        self.refresh_token_repo = RefreshTokenRepository(db) 
        self.user_profile_repo = UserProfileRepository(db)
        self.role_repo = RoleRepository(db)
        self.user_role_repo = UserRoleRepository(db)
    # ---------- Registro ----------
    async def register(self, email: str, password: str, background_tasks: BackgroundTasks) -> dict:
        if await self.user_repo.get_by_email(email) is not None:
            raise ConflictException(
                "El correo ya está registrado.",
                errors={"email": ["Este correo ya está en uso."]},
            )

        user = await self.user_repo.create(email=email, password_hash=hash_password(password))
        role = await self.role_repo.get_by_name("USER")

        if role is None:
            raise NotFoundException(
                "El rol USER no existe. Ejecute los seeds del sistema."
            )

        await self.user_role_repo.assign_role(
            user_id=user.id,
            role_id=role.id,
        )
        
        await self._issue_verification_token(user.id, user.email, background_tasks)
        await self.db.commit()

        return {"id": str(user.id), "email": user.email, "email_verified": user.email_verified}
    # ---------- Verificación de correo ----------
    async def verify_email(self, raw_token: str) -> None:
        token = await self.email_verification_repo.get_valid_by_hash(hash_opaque_token(raw_token))
        if token is None:
            raise BadRequestException("El enlace de verificación es inválido o expiró.")

        user = await self.user_repo.get_by_id(token.user_id)
        if user is None:
            raise NotFoundException("Usuario no encontrado.")

        await self.user_repo.mark_email_verified(user)
        await self.email_verification_repo.mark_used(token)
        await self.db.commit()

    async def resend_verification(self, email: str, background_tasks: BackgroundTasks) -> None:
        user = await self.user_repo.get_by_email(email)
        if user is None or user.email_verified:
            return  # No revelar si el correo existe o ya está verificado.

        last_token = await self.email_verification_repo.get_last_for_user(user.id)
        if last_token is not None:
            cooldown_end = last_token.created_at + timedelta(seconds=settings.RESEND_VERIFICATION_COOLDOWN_SECONDS)
            if datetime.now(timezone.utc) < cooldown_end:
                raise BadRequestException("Debes esperar antes de solicitar otro correo de verificación.")

        await self._issue_verification_token(user.id, user.email, background_tasks)
        await self.db.commit()

    async def _issue_verification_token(self, user_id: UUID, email: str, background_tasks: BackgroundTasks) -> None:
        raw_token, token_hash = generate_opaque_token()
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.EMAIL_VERIFICATION_EXPIRE_MINUTES)
        await self.email_verification_repo.create(user_id, token_hash, expires_at)
        EmailService.send_verification_email(background_tasks, email, raw_token)

    # ---------- Login ----------
    async def login(
        self, email: str, password: str, user_agent: str | None = None, ip_address: str | None = None
    ) -> dict:
        user = await self.user_repo.get_by_email_with_roles(email)
        if user is None or not verify_password(password, user.password_hash):
            raise UnauthorizedException("Correo o contraseña incorrectos.")
        if not user.is_active:
            raise UnauthorizedException("Usuario inactivo.")
        if not user.email_verified:
            raise UnauthorizedException("Debes verificar tu correo antes de iniciar sesión.")

        await self.user_repo.update_last_login(user)

        access_token = create_access_token({"sub": str(user.id)})
        raw_refresh_token, refresh_hash = generate_opaque_token()
        refresh_expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        await self.refresh_token_repo.create(user.id, refresh_hash, refresh_expires_at, user_agent, ip_address)

        await self.db.commit()

        roles = [ur.role.name for ur in user.user_roles]
        return {
            "access_token": access_token,
            "refresh_token": raw_refresh_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "user": {
                "id": str(user.id),
                "email": user.email,
                "email_verified": user.email_verified,
                "roles": roles,
            },
        }

    # ---------- Renovar token ----------
    async def refresh_token(self, raw_refresh_token: str) -> dict:
        token_hash = hash_opaque_token(raw_refresh_token)
        token = await self.refresh_token_repo.get_valid_by_hash(token_hash)
        if token is None:
            raise UnauthorizedException("Refresh token inválido o expirado.")

        user = await self.user_repo.get_by_id(token.user_id)
        if user is None or not user.is_active:
            raise UnauthorizedException("Usuario no encontrado o inactivo.")

        # Rotación: se revoca el token usado y se emite uno nuevo.
        await self.refresh_token_repo.revoke(token)

        new_raw_refresh_token, new_hash = generate_opaque_token()
        new_expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        await self.refresh_token_repo.create(user.id, new_hash, new_expires_at, token.user_agent, token.ip_address)

        access_token = create_access_token({"sub": str(user.id)})
        await self.db.commit()

        return {
            "access_token": access_token,
            "refresh_token": new_raw_refresh_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        }

    # ---------- Logout ----------
    async def logout(self, raw_refresh_token: str) -> None:
        token_hash = hash_opaque_token(raw_refresh_token)
        token = await self.refresh_token_repo.get_valid_by_hash(token_hash)
        if token is not None:
            await self.refresh_token_repo.revoke(token)
            await self.db.commit()

    # ---------- Olvidé mi contraseña ----------
    async def forgot_password(self, email: str, background_tasks: BackgroundTasks) -> None:
        user = await self.user_repo.get_by_email(email)
        if user is None:
            return  # No revelar existencia del correo.

        raw_token, token_hash = generate_opaque_token()
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.PASSWORD_RESET_EXPIRE_MINUTES)
        await self.password_reset_repo.create(user.id, token_hash, expires_at)
        await self.db.commit()

        EmailService.send_password_reset_email(background_tasks, user.email, raw_token)

    async def reset_password(self, raw_token: str, new_password: str) -> None:
        token = await self.password_reset_repo.get_valid_by_hash(hash_opaque_token(raw_token))
        if token is None:
            raise BadRequestException("El enlace de restablecimiento es inválido o expiró.")

        user = await self.user_repo.get_by_id(token.user_id)
        if user is None:
            raise NotFoundException("Usuario no encontrado.")

        await self.user_repo.update_password(user, hash_password(new_password))
        await self.password_reset_repo.mark_used(token)
        await self.db.commit()

    # ---------- Cambiar contraseña (usuario autenticado) ----------
    async def change_password(self, user_id: UUID, current_password: str, new_password: str) -> None:
        user = await self.user_repo.get_by_id(user_id)
        if user is None:
            raise NotFoundException("Usuario no encontrado.")

        if not verify_password(current_password, user.password_hash):
            raise BadRequestException(
                "La contraseña actual es incorrecta.",
                errors={"current_password": ["Contraseña incorrecta."]},
            )

        await self.user_repo.update_password(user, hash_password(new_password))
        await self.db.commit()