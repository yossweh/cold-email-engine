import smtplib
from email.mime.text import MIMEText

msg = MIMEText("""Hi there,

This is a test email from 0xChapo - AI Cold Email Engine.

If you receive this, the email system is working!

Best regards,
0xChapo Team""")

msg['Subject'] = '0xChapo Test Email'
msg['From'] = 'test@0xchapo.com'
msg['To'] = 'cilokcilok15@gmail.com'

try:
    server = smtplib.SMTP('localhost', 25)
    server.sendmail('test@0xchapo.com', ['cilokcilok15@gmail.com'], msg.as_string())
    server.quit()
    print("EMAIL_SENT_OK")
except Exception as e:
    print(f"ERROR: {e}")
