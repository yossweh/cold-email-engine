"""
Google OAuth + Email OTP authentication
"""
import os
import secrets
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from typing import Optional, Dict
import json
import requests

# OTP storage (in-memory, reset on restart)
_otp_store = {}  # email -> {code, expires, attempts}

def generate_otp(email: str) -> str:
    """Generate 6-digit OTP and store it"""
    email = email.strip().lower()
    code = f"{secrets.randbelow(900000) + 100000}"  # 6 digits
    _otp_store[email] = {
        'code': code,
        'expires': datetime.now() + timedelta(minutes=10),
        'attempts': 0
    }
    return code

def verify_otp(email: str, code: str) -> bool:
    """Verify OTP code"""
    email = email.strip().lower()
    code = code.strip()
    
    if email not in _otp_store:
        return False
    
    otp_data = _otp_store[email]
    
    # Check expiry
    if datetime.now() > otp_data['expires']:
        del _otp_store[email]
        return False
    
    # Check attempts
    if otp_data['attempts'] >= 5:
        del _otp_store[email]
        return False
    
    # Check code
    if otp_data['code'] != code:
        otp_data['attempts'] += 1
        return False
    
    # Success - remove OTP
    del _otp_store[email]
    return True

def send_otp_email(email: str, code: str) -> bool:
    """Send OTP via SendGrid"""
    api_key = os.getenv('SENDGRID_API_KEY')
    sender = os.getenv('OTP_FROM_EMAIL', os.getenv('SMTP_FROM_EMAIL', 'noreply@0xchapo.xyz'))
    
    if not api_key:
        print("❌ No SENDGRID_API_KEY")
        return False
    
    html_content = f"""
    <div style="font-family: Arial, sans-serif; max-width: 500px; margin: 0 auto; padding: 30px; background: #0a0a0a; border-radius: 12px;">
        <div style="text-align: center; margin-bottom: 30px;">
            <h1 style="color: #e0e0e0; font-size: 28px; letter-spacing: 3px;">◆ 0XCHAPO</h1>
        </div>
        <div style="background: #111; border: 1px solid #2a2a2a; border-radius: 12px; padding: 30px; text-align: center;">
            <p style="color: #888; font-size: 14px; margin-bottom: 10px;">Your verification code</p>
            <h2 style="color: #e0e0e0; font-size: 42px; letter-spacing: 8px; margin: 20px 0;">{code}</h2>
            <p style="color: #666; font-size: 12px;">Valid for 10 minutes</p>
        </div>
        <p style="color: #444; font-size: 11px; text-align: center; margin-top: 20px;">If you didn't request this, ignore this email.</p>
    </div>
    """
    
    try:
        response = requests.post(
            'https://api.sendgrid.com/v3/mail/send',
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            },
            json={
                'personalizations': [{'to': [{'email': email}]}],
                'from': {'email': sender, 'name': '0xChapo'},
                'subject': f'Your 0xChapo Code: {code}',
                'content': [
                    {'type': 'text/plain', 'value': f'Your 0xChapo verification code: {code}'},
                    {'type': 'text/html', 'value': html_content}
                ]
            }
        )
        return response.status_code in [200, 202]
    except Exception as e:
        print(f"❌ SendGrid error: {e}")
        return False

def get_google_auth_url() -> Optional[str]:
    """Get Google OAuth URL"""
    client_id = os.getenv('GOOGLE_CLIENT_ID')
    redirect_uri = os.getenv('GOOGLE_REDIRECT_URI', 'http://localhost:5000/auth/google/callback')
    
    if not client_id:
        return None
    
    return (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={client_id}"
        f"&redirect_uri={redirect_uri}"
        f"&response_type=code"
        f"&scope=openid%20email%20profile"
        f"&access_type=offline"
    )

def exchange_google_code(code: str) -> Optional[Dict]:
    """Exchange Google auth code for user info"""
    client_id = os.getenv('GOOGLE_CLIENT_ID')
    client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
    redirect_uri = os.getenv('GOOGLE_REDIRECT_URI', 'http://localhost:5000/auth/google/callback')
    
    if not client_id or not client_secret:
        return None
    
    try:
        # Exchange code for tokens
        token_response = requests.post(
            'https://oauth2.googleapis.com/token',
            data={
                'code': code,
                'client_id': client_id,
                'client_secret': client_secret,
                'redirect_uri': redirect_uri,
                'grant_type': 'authorization_code'
            }
        )
        
        if token_response.status_code != 200:
            print(f"❌ Token exchange failed: {token_response.text}")
            return None
        
        tokens = token_response.json()
        
        # Get user info
        user_response = requests.get(
            'https://www.googleapis.com/oauth2/v2/userinfo',
            headers={'Authorization': f"Bearer {tokens['access_token']}"}
        )
        
        if user_response.status_code != 200:
            print(f"❌ User info failed: {user_response.text}")
            return None
        
        return user_response.json()
    except Exception as e:
        print(f"❌ Google OAuth error: {e}")
        return None
