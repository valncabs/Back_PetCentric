import aiosmtplib
from email.message import EmailMessage

from app.core.config import settings


async def send_email(to_email: str, subject: str, html_body: str) -> None:
    """Envía un correo vía Mailtrap. Se invoca dentro de una BackgroundTask,
    nunca de forma bloqueante en el request."""
    message = EmailMessage()
    message["From"] = f"{settings.MAILTRAP_SENDER_NAME} <{settings.MAILTRAP_SENDER_EMAIL}>"
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content("Este correo requiere un cliente compatible con HTML.")
    message.add_alternative(html_body, subtype="html")

    await aiosmtplib.send(
        message,
        hostname=settings.MAILTRAP_HOST,
        port=settings.MAILTRAP_PORT,
        username=settings.MAILTRAP_USERNAME,
        password=settings.MAILTRAP_PASSWORD,
        start_tls=True,
    )