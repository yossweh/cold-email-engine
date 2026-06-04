import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

msg = MIMEMultipart('alternative')
msg['Subject'] = '0xChapo - Test Email berhasil! 🚀'
msg['From'] = '0xChapo <cilokcilok15@gmail.com>'
msg['To'] = 'cilokcilok15@gmail.com'

text = """Hi!

Ini test email dari 0xChapo - AI Cold Email Engine.

Kalau lo baca ini, berarti SMTP udah jalan! ✅

Fitur yang udah ready:
- AI email generation
- Lead scraping dari website
- Email verification
- Follow-up sequences
- Payment integration (LemonSqueezy + Midtrans)

Next: Deploy production & mulai jual!

Best,
0xChapo Team"""

html = """<html>
<body style="font-family: Arial, sans-serif; background: #0a0a0a; color: #e0e0e0; padding: 40px;">
<div style="max-width: 600px; margin: 0 auto; background: #1a1a1a; border-radius: 12px; padding: 30px; border: 1px solid #333;">
<h1 style="color: #00ff88;">◆ 0xChapo</h1>
<p>Ini test email dari <strong>0xChapo - AI Cold Email Engine</strong>.</p>
<p>Kalau lo baca ini, berarti SMTP udah jalan! ✅</p>
<h2 style="color: #888;">Fitur yang udah ready:</h2>
<ul>
<li>AI email generation</li>
<li>Lead scraping dari website</li>
<li>Email verification</li>
<li>Follow-up sequences</li>
<li>Payment integration (LemonSqueezy + Midtrans)</li>
</ul>
<p><strong>Next:</strong> Deploy production & mulai jual!</p>
<p style="color: #666;">Best,<br>0xChapo Team</p>
</div>
</body>
</html>"""

msg.attach(MIMEText(text, 'plain'))
msg.attach(MIMEText(html, 'html'))

try:
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.ehlo()
    server.starttls()
    server.ehlo()
    server.login('cilokcilok15@gmail.com', 'nmyr eydj stjx dswp')
    server.sendmail('cilokcilok15@gmail.com', ['cilokcilok15@gmail.com'], msg.as_string())
    server.quit()
    print("EMAIL_SENT_OK")
except Exception as e:
    print(f"ERROR: {e}")
