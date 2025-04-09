from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
from typing import Optional
from pydantic import EmailStr

class EmailService:
    def __init__(self):
        self.from_email = "noreply@bristol.ac.uk"
        self.base_url = "https://gpmap.opengwas.io"
        self.contact_url = f"{self.base_url}/contact"

    async def send_results_email(self, to_email: EmailStr, guid: str) -> None:
        """
        Send an email notification that results are ready.
        
        Args:
            to_email: Recipient's email address
            guid: The GUID of the analysis results
        """
        msg = MIMEMultipart('alternative')
        msg['Subject'] = 'Your Genotype-Phenotype Map Results Are Ready'
        msg['From'] = self.from_email
        msg['To'] = to_email

        html = f"""
        <html>
        <body>
            <p>Thanks for using the Genotype-Phenotype Map!</p>
            <p>Your results are ready to view. <a href='{self.base_url}/results/{guid}'>Click here</a> to view your results.</p>
            <p>If you have any questions, please <a href='{self.contact_url}'>contact us here</a>.</p>
            <p>Best regards,<br>The Genotype-Phenotype Map Team</p>
        </body>
        </html>
        """

        msg.attach(MIMEText(html, 'html'))

        try:
            with smtplib.SMTP('localhost') as server:
                server.send_message(msg)
        except Exception as e:
            print(f"Failed to send email: {e}")
            raise
