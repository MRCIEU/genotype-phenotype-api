from app.config import get_settings
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from pydantic import EmailStr
from loguru import logger

settings = get_settings()


class EmailService:
    def __init__(self):
        self.from_email = settings.EMAIL_FROM
        self.contact_email = settings.EMAIL_FROM
        self.contact_url = f"{settings.WEBSITE_URL}/contact.html"

        self.conf = ConnectionConfig(
            MAIL_USERNAME=settings.EMAIL_USERNAME,
            MAIL_PASSWORD=settings.EMAIL_PASSWORD,
            MAIL_FROM=self.from_email,
            MAIL_PORT=settings.EMAIL_PORT,
            MAIL_SERVER=settings.EMAIL_SERVER,
            MAIL_STARTTLS=settings.EMAIL_TLS,
            MAIL_SSL_TLS=False,
            USE_CREDENTIALS=True,
        )

    async def send_contact_email(self, email: EmailStr, reason: str, message: str) -> None:
        """
        Send an email to the contact email address from the contact form.
        """

        send_to = "andrew.elmore@bristol.ac.uk"

        subject = f"Contact Form Submission: {reason}"
        html = f"""
        <html>
        <body>
            <p><b>From:</b> {email}</p>
            <p><b>Reason:</b> {reason}</p>
            <p><b>Message:</b><br>{message}</p>
        </body>
        </html>
        """
        msg = MessageSchema(subject=subject, recipients=[send_to], body=html, subtype="html")
        fm = FastMail(self.conf)
        try:
            await fm.send_message(msg)
        except Exception as e:
            logger.error(f"Failed to send contact email: {e}")
            raise

    async def send_results_email(self, to_email: EmailStr, guid: str) -> None:
        """
        Send an email notification that results are ready.
        """
        subject = "Your Genotype-Phenotype Map Results Are Ready"
        html = f"""
        <html>
        <body>
            <p>Thanks for using the Genotype-Phenotype Map!</p>
            <p>Your results are ready to view. <a href='{settings.WEBSITE_URL}/trait.html?id={guid}'>Click here</a> to view your results.</p>
            <p>If you have any questions, please <a href='{self.contact_url}'>contact us here</a>.</p>
            <p>Best regards,<br>The Genotype-Phenotype Map Team</p>
        </body>
        </html>
        """
        msg = MessageSchema(subject=subject, recipients=[to_email], body=html, subtype="html")
        fm = FastMail(self.conf)
        try:
            await fm.send_message(msg)
        except Exception as e:
            logger.error(f"Failed to send results email: {e}")
            raise

    async def send_failure_email(self, to_email: EmailStr, guid: str) -> None:
        """
        Send an email notification that the GWAS upload failed.
        """
        subject = "Your Genotype-Phenotype Map Upload Failed"
        html = f"""
        <html>
        <body>
            <p>Sorry, your Genotype-Phenotype Map <a href='{settings.WEBSITE_URL}/trait.html?id={guid}'>upload failed</a>.</p>
            <p>If you have any questions, please <a href='{self.contact_url}'>contact us here</a>.</p>
            <p>Best regards,<br>The Genotype-Phenotype Map Team</p>
        </body>
        </html>
        """
        msg = MessageSchema(subject=subject, recipients=[to_email], body=html, subtype="html")
        fm = FastMail(self.conf)
        try:
            await fm.send_message(msg)
        except Exception as e:
            logger.error(f"Failed to send failure email: {e}")
            raise
