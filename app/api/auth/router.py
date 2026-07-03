from fastapi import APIRouter, BackgroundTasks, Depends, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.auth.token import LogoutRequest, RefreshTokenRequest
from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.auth.login import LoginRequest
from app.schemas.auth.password import ChangePasswordRequest, ForgotPasswordRequest, ResetPasswordRequest
from app.schemas.auth.register import RegisterRequest
from app.schemas.auth.verify_email import ResendVerificationRequest, VerifyEmailRequest
from app.services.auth import AuthService
from app.utils.response import success_response

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    data = await AuthService(db).register(payload.email, payload.password, background_tasks)
    return success_response(data=data, message="Registro exitoso. Revisa tu correo para verificar tu cuenta.", status_code=201)


@router.post("/verify-email")
async def verify_email(payload: VerifyEmailRequest, db: AsyncSession = Depends(get_db)):
    await AuthService(db).verify_email(payload.token)
    return success_response(message="Correo verificado correctamente.")


@router.post("/resend-verification")
async def resend_verification(payload: ResendVerificationRequest, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    await AuthService(db).resend_verification(payload.email, background_tasks)
    return success_response(message="Si el correo existe y no ha sido verificado, se envió un nuevo enlace.")


@router.post("/login")
async def login(payload: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    data = await AuthService(db).login(
        payload.email,
        payload.password,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )
    return success_response(data=data, message="Inicio de sesión exitoso.")


@router.post("/refresh")
async def refresh_token(payload: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    data = await AuthService(db).refresh_token(payload.refresh_token)
    return success_response(data=data, message="Token renovado correctamente.")


@router.post("/logout")
async def logout(payload: LogoutRequest, db: AsyncSession = Depends(get_db)):
    await AuthService(db).logout(payload.refresh_token)
    return success_response(message="Sesión cerrada correctamente.")


@router.post("/forgot-password")
async def forgot_password(payload: ForgotPasswordRequest, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    await AuthService(db).forgot_password(payload.email, background_tasks)
    return success_response(message="Si el correo existe, se envió un enlace para restablecer la contraseña.")


@router.post("/reset-password")
async def reset_password(payload: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    await AuthService(db).reset_password(payload.token, payload.new_password)
    return success_response(message="Contraseña restablecida correctamente.")


@router.post("/change-password")
async def change_password(payload: ChangePasswordRequest, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await AuthService(db).change_password(current_user.id, payload.current_password, payload.new_password)
    return success_response(message="Contraseña actualizada correctamente.")