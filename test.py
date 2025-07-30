import asyncio
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import aiosmtplib


async def send_email():
    """Отправить email."""
    smtp_hostname = "smtp-relay.brevo.com"
    port = 2525  # Используем открытый порт
    username="7e2789001@smtp-brevo.com"
    password="6ZwhH1IzfvTULPax"
    # username = settings.SMTP_USERNAME
    # password = settings.SMTP_PASSWORD
    to_email = "opendoor200179@gmail.com"
    body = "Test"
    html_body = f"""
<html>
<body>
    <p>Here is your verification code: <strong>52</strong></p>
</body>
</html>
"""
    message = MIMEMultipart("alternative")
    message["From"] = "noreply@quam.cc"
    message["To"] = to_email
    message["Subject"] = "TEST"

    html_part = MIMEText(html_body, "html")
    message.attach(html_part)

    await aiosmtplib.send(
        message,
        hostname=smtp_hostname,
        port=port,
        username=username,
        password=password,
        start_tls=True,
        recipients=[to_email.lower()],
        timeout=30
    )

asyncio.run(send_email())