from fastapi import BackgroundTasks

from app.core.config import settings
from app.utils.mailer import send_email


class EmailService:
    """Construye el contenido de los correos transaccionales del sistema."""

    @staticmethod
    def send_verification_email(background_tasks: BackgroundTasks, to_email: str, raw_token: str) -> None:
        link = f"{settings.FRONTEND_URL}/verify-email?token={raw_token}"
        html = (
            "<p>Bienvenido a Pet-Centric.</p>"
            f"<p>Confirma tu correo: <a href='{link}'>Verificar correo</a></p>"
            f"<p>Este enlace expira en {settings.EMAIL_VERIFICATION_EXPIRE_MINUTES // 60} horas.</p>"
        )
        background_tasks.add_task(send_email, to_email, "Verifica tu correo - Pet-Centric", html)

    @staticmethod
    def send_password_reset_email(background_tasks: BackgroundTasks, to_email: str, raw_token: str) -> None:
        link = f"{settings.FRONTEND_URL}/reset-password?token={raw_token}"
        html = (
            "<p>Solicitaste restablecer tu contraseña.</p>"
            f"<p><a href='{link}'>Restablecer contraseña</a></p>"
            f"<p>Expira en {settings.PASSWORD_RESET_EXPIRE_MINUTES} minutos. "
            "Si no fuiste tú, ignora este correo.</p>"
        )
        background_tasks.add_task(send_email, to_email, "Restablece tu contraseña - Pet-Centric", html)