import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from common.config import settings


def send_email(to_email: str, subject: str, body: str) -> None:
    smtp_conf = settings.smtp
    msg = MIMEMultipart()
    msg["From"] = smtp_conf.from_email
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "html"))

    if smtp_conf.use_ssl:
        server = smtplib.SMTP_SSL(smtp_conf.host, smtp_conf.port)
    else:
        server = smtplib.SMTP(smtp_conf.host, smtp_conf.port)
        if smtp_conf.use_tls:
            server.starttls()
    server.login(smtp_conf.user, smtp_conf.password)
    server.sendmail(smtp_conf.from_email, to_email, msg.as_string())
    server.quit() 