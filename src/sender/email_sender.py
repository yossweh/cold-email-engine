"""
Cold Email Engine — Email Sender
Send emails via SMTP with rate limiting and tracking
"""
import smtplib
import time
import json
import csv
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Optional
from pathlib import Path
from datetime import datetime


class EmailSender:
    """Send cold emails via SMTP with rate limiting."""

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        smtp_user: str,
        smtp_password: str,
        from_name: str,
        from_email: str,
        max_per_hour: int = 30,
        delay_seconds: int = 60
    ):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.from_name = from_name
        self.from_email = from_email
        self.max_per_hour = max_per_hour
        self.delay_seconds = delay_seconds
        self.sent_log = []

    def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        reply_to: Optional[str] = None
    ) -> Dict:
        """Send a single email."""
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = to_email
            if reply_to:
                msg['Reply-To'] = reply_to

            # Plain text
            msg.attach(MIMEText(body, 'plain'))

            # HTML version
            html_body = body.replace('\n', '<br>')
            html = f"""
            <html>
            <body style="font-family: Arial, sans-serif; font-size: 14px; line-height: 1.6;">
            {html_body}
            </body>
            </html>
            """
            msg.attach(MIMEText(html, 'html'))

            # Send
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)

            log_entry = {
                'to': to_email,
                'subject': subject,
                'status': 'sent',
                'timestamp': datetime.now().isoformat(),
            }
            self.sent_log.append(log_entry)
            return {'status': 'sent', 'to': to_email}

        except Exception as e:
            log_entry = {
                'to': to_email,
                'subject': subject,
                'status': 'failed',
                'error': str(e),
                'timestamp': datetime.now().isoformat(),
            }
            self.sent_log.append(log_entry)
            return {'status': 'failed', 'error': str(e)}

    def send_batch(self, emails: List[Dict]) -> List[Dict]:
        """Send multiple emails with rate limiting."""
        results = []
        sent_count = 0

        for i, email in enumerate(emails):
            # Rate limiting
            if sent_count >= self.max_per_hour:
                print(f"⏳ Hourly limit reached ({self.max_per_hour}). Waiting 1 hour...")
                time.sleep(3600)
                sent_count = 0

            if i > 0:
                print(f"⏳ Waiting {self.delay_seconds}s between emails...")
                time.sleep(self.delay_seconds)

            result = self.send_email(
                to_email=email['to'],
                subject=email['subject'],
                body=email['body']
            )
            results.append(result)
            sent_count += 1

            status = '✅' if result['status'] == 'sent' else '❌'
            print(f"{status} [{i+1}/{len(emails)}] {email['to']}")

        return results

    def save_log(self, filepath: str):
        """Save send log to JSON."""
        with open(filepath, 'w') as f:
            json.dump(self.sent_log, f, indent=2)

    def export_log_csv(self, filepath: str):
        """Export send log to CSV."""
        if not self.sent_log:
            return
        with open(filepath, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=self.sent_log[0].keys())
            writer.writeheader()
            writer.writerows(self.sent_log)


if __name__ == '__main__':
    import os
    from dotenv import load_dotenv
    load_dotenv()

    sender = EmailSender(
        smtp_host=os.getenv('SMTP_HOST'),
        smtp_port=int(os.getenv('SMTP_PORT', 587)),
        smtp_user=os.getenv('SMTP_USER'),
        smtp_password=os.getenv('SMTP_PASSWORD'),
        from_name=os.getenv('SMTP_FROM_NAME'),
        from_email=os.getenv('SMTP_FROM_EMAIL'),
    )

    # Test single email
    result = sender.send_email(
        to_email='test@example.com',
        subject='Test Email',
        body='This is a test email from Cold Email Engine.'
    )
    print(json.dumps(result, indent=2))
