from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def send_verification_email(to_email: str, code: str) -> None:
    settings = get_settings()
    if not settings.smtp_host:
        logger.info("SMTP 미설정 - 인증코드 발송 스킵 (email=%s, code=%s)", to_email, code)
        return

    message = EmailMessage()
    message["Subject"] = "[Ding-Dong11] 이메일 인증코드"
    message["From"] = settings.smtp_from or settings.smtp_user
    message["To"] = to_email
    message.set_content(f"인증코드: {code}\n유효 시간: 10분")

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as smtp:
        smtp.starttls()
        if settings.smtp_user:
            smtp.login(settings.smtp_user, settings.smtp_password)
        smtp.send_message(message)
