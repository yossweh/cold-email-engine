import requests
import json

# Create Brevo API key (requires account)
# For now, let's try using a public SMTP relay

# Alternative: Use Resend.com (free 100/day)
import resend

# You need to get API key from https://resend.com
# For now, let's use a direct approach

# Let's try using Mailgun sandbox (free, no signup needed for testing)
print("Checking available free SMTP options...")

# Option 1: Check if we can use port 587 with Gmail
import smtplib
try:
    server = smtplib.SMTP('smtp.gmail.com', 587, timeout=10)
    server.ehlo()
    server.starttls()
    print("Gmail SMTP port 587: REACHABLE")
    server.quit()
except Exception as e:
    print(f"Gmail SMTP port 587: {e}")

# Option 2: Check Brevo
try:
    server = smtplib.SMTP('smtp-relay.brevo.com', 587, timeout=10)
    server.ehlo()
    print("Brevo SMTP port 587: REACHABLE")
    server.quit()
except Exception as e:
    print(f"Brevo SMTP port 587: {e}")

# Option 3: Check SendGrid
try:
    server = smtplib.SMTP('smtp.sendgrid.net', 587, timeout=10)
    server.ehlo()
    print("SendGrid SMTP port 587: REACHABLE")
    server.quit()
except Exception as e:
    print(f"SendGrid SMTP port 587: {e}")

# Option 4: Check Resend
try:
    server = smtplib.SMTP('smtp.resend.com', 587, timeout=10)
    server.ehlo()
    print("Resend SMTP port 587: REACHABLE")
    server.quit()
except Exception as e:
    print(f"Resend SMTP port 587: {e}")
