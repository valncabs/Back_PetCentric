from datetime import datetime, timedelta, timezone
from uuid import UUID
import logging

from fastapi import BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.core.config import settings
from app.core.exceptions import BadRequestException, NotFoundException, UnauthorizedException
from app.core.security import create_access_token, generate_opaque_token, hash_opaque_token, hash_password, verify_password
from app.repositories.email_verification_repository import EmailVerificationRepository
from app.repositories.password_reset_repository import PasswordResetRepository
from app.repositories.user import UserRepository
from app.services.email import EmailService
from app.repositories.user_profile_repository import UserProfileRepository
from app.repositories.rol_repository import RoleRepository
from app.repositories.user_rol_repository import UserRoleRepository

_log = logging.getLogger(__name__)


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
        # Se calcula el hash ANTES de verificar existencia para igualar el
        # tiempo de respuesta (bcrypt es la operación cara) y evitar una
        # side-channel que delate si el correo ya está registrado.
        password_hash = hash_password(password)

        existing = await self.user_repo.get_by_email(email)
        if existing is not None:
            # No revelar si el correo ya existe: se responde igual que un
            # registro exitoso, sin enviar ningún correo ni crear cuentas.
            return {"id": "", "email": email, "email_verified": False}

        user = await self.user_repo.create(email=email, password_hash=password_hash)
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

        _log.info("Registro de usuario: id=%s email=%s", user.id, user.email)
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
            _log.warning("Login fallido (credenciales): email=%s", email)
            raise UnauthorizedException("Correo o contraseña incorrectos.")
        if not user.is_active:
            _log.warning("Login bloqueado (inactivo): id=%s email=%s", user.id, user.email)
            raise UnauthorizedException("Usuario inactivo.")
        if not user.email_verified:
            _log.warning("Login bloqueado (email sin verificar): id=%s email=%s", user.id, user.email)
            raise UnauthorizedException("Debes verificar tu correo antes de iniciar sesión.")

        await self.user_repo.update_last_login(user)

        access_token = create_access_token(
            {"sub": str(user.id), "ver": user.token_version}
        )
        raw_refresh_token, refresh_hash = generate_opaque_token()
        refresh_expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        await self.refresh_token_repo.create(user.id, refresh_hash, refresh_expires_at, user_agent, ip_address)

        profile_completed = await self.user_profile_repo.exists_for_user(user.id)

        await self.db.commit()

        roles = [ur.role.name for ur in user.user_roles]
        _log.info("Login exitoso: id=%s email=%s ip=%s", user.id, user.email, ip_address)
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
                "profile_completed": profile_completed,
            },
        }
    # ---------- Renovar token ----------
    async def refresh_token(self, raw_refresh_token: str) -> dict:
        token_hash = hash_opaque_token(raw_refresh_token)
        token = await self.refresh_token_repo.get_valid_by_hash(token_hash)
        if token is None:
            _log.warning("Refresh con token inválido o expirado")
            raise UnauthorizedException("Refresh token inválido o expirado.")

        user = await self.user_repo.get_by_id(token.user_id)
        if user is None or not user.is_active:
            raise UnauthorizedException("Usuario no encontrado o inactivo.")

        # Rotación: se revoca el token usado y se emite uno nuevo.
        await self.refresh_token_repo.revoke(token)
        _log.info("Refresh token rotado: user_id=%s", user.id)

        new_raw_refresh_token, new_hash = generate_opaque_token()
        new_expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        await self.refresh_token_repo.create(user.id, new_hash, new_expires_at, token.user_agent, token.ip_address)

        access_token = create_access_token(
            {"sub": str(user.id), "ver": user.token_version}
        )
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
            _log.info("Logout: user_id=%s", token.user_id)

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
        # Invalida todos los access tokens y refresh tokens vigentes.
        await self.user_repo.bump_token_version(user)
        await self.refresh_token_repo.revoke_all_for_user(user.id)
        await self.password_reset_repo.mark_used(token)
        await self.db.commit()
        _log.info("Contraseña restablecida (token): user_id=%s", user.id)

    # ---------- Cambiar contraseña (usuario autenticado) ----------
    async def change_password(self, user_id: UUID, current_password: str, new_password: str) -> None:
        user = await self.user_repo.get_by_id(user_id)
        if user is None:
            raise NotFoundException("Usuario no encontrado.")

        if not verify_password(current_password, user.password_hash):
            _log.warning("Cambio de contraseña con contraseña actual incorrecta: user_id=%s", user_id)
            raise BadRequestException(
                "La contraseña actual es incorrecta.",
                errors={"current_password": ["Contraseña incorrecta."]},
            )

        await self.user_repo.update_password(user, hash_password(new_password))
        # Invalida todos los access tokens y refresh tokens vigentes.
        await self.user_repo.bump_token_version(user)
        await self.refresh_token_repo.revoke_all_for_user(user.id)
        await self.db.commit()
        _log.info("Contraseña cambiada: user_id=%s", user_id)

    # ---------- Sesión actual (rehidratación tras F5) ----------
    async def me(self, user: User) -> dict:
        """
        Devuelve el estado de sesión actual (roles + profile_completed)
        recalculado desde la BD. Pensado para usarse UNA vez al montar el
        shell del dashboard, no en cada navegación.
        """
        # El User viene cargado por get_current_user: solo se consultan los
        # dos datos que faltan (roles y existencia de perfil), sin re-fetchear
        # toda la entidad.
        roles = await self.user_repo.get_role_names(user.id)
        profile_completed = await self.user_profile_repo.exists_for_user(user.id)

        return {
            "id": str(user.id),
            "email": user.email,
            "email_verified": user.email_verified,
            "roles": roles,
            "profile_completed": profile_completed,
        }

    # ---------- Eliminar cuenta (self-service) ----------
    async def delete_account(self, user_id: UUID, password: str) -> None:
        user = await self.user_repo.get_by_id(user_id)
        if user is None:
            raise NotFoundException("Usuario no encontrado.")

        if not verify_password(password, user.password_hash):
            _log.warning("Borrado de cuenta con contraseña incorrecta: user_id=%s", user_id)
            raise BadRequestException(
                "La contraseña es incorrecta.",
                errors={"password": ["Contraseña incorrecta."]},
            )

        await self.user_repo.soft_delete(user)
        await self.db.commit()
        _log.warning("Cuenta eliminada: user_id=%s email=%s", user_id, user.email)