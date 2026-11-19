"""EmailSender por SMTP. En desarrollo apunta a Mailpit (D62-C)."""

import smtplib
from email.message import EmailMessage as MimeMessage

from app.shared.use_cases.ports import EmailDeliveryError, EmailMessage


class SmtpEmailSender:
    def __init__(self, host: str, port: int, sender: str) -> None:
        self._host = host
        self._port = port
        self._sender = sender

    def send(self, message: EmailMessage) -> None:
        mime = MimeMessage()
        mime["From"] = self._sender
        mime["To"] = message.to
        mime["Subject"] = message.subject
        mime.set_content(message.text)
        try:
            with smtplib.SMTP(self._host, self._port, timeout=10) as smtp:
                smtp.send_message(mime)
        except OSError as error:  # smtplib.SMTPException también es OSError
            raise EmailDeliveryError(str(error)) from error
