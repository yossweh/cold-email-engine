"""
Cold Email Engine — Authentication & User Management
"""
import os
import hashlib
import secrets
import json
from datetime import datetime, timedelta
from typing import Optional, Dict
from pathlib import Path
from functools import wraps
from flask import session, redirect, url_for, request, flash


class UserManager:
    """Simple user management with file-based storage."""

    def __init__(self, data_dir: str = None):
        self.data_dir = Path(data_dir or Path(__file__).parent.parent.parent / 'data')
        self.users_dir = self.data_dir / 'users'
        self.users_dir.mkdir(parents=True, exist_ok=True)
        self.sessions_dir = self.data_dir / 'sessions'
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

    def _hash_password(self, password: str, salt: str = None) -> tuple:
        """Hash password with salt."""
        if salt is None:
            salt = secrets.token_hex(16)
        hashed = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return hashed.hex(), salt

    def register(self, email: str, password: str, name: str = '') -> Dict:
        """Register new user."""
        # Check if exists
        user_path = self.users_dir / f'{email.lower().replace("@", "_at_")}.json'
        if user_path.exists():
            return {'error': 'Email already registered'}

        hashed, salt = self._hash_password(password)

        user = {
            'email': email.lower(),
            'name': name or email.split('@')[0],
            'password_hash': hashed,
            'salt': salt,
            'created': datetime.now().isoformat(),
            'plan': 'free',
            'plan_expires': None,
            'trial_expires': None,  # Trial starts after card is added
            'license_key': None,
            'usage': {
                'emails_sent': 0,
                'emails_limit': 10,
                'last_reset': datetime.now().isoformat(),
            },
            'settings': {
                'smtp_host': '',
                'smtp_port': 587,
                'smtp_user': '',
                'smtp_password': '',
                'from_name': name,
                'from_email': email,
                'anthropic_api_key': '',
            }
        }

        with open(user_path, 'w') as f:
            json.dump(user, f, indent=2)

        return {'success': True, 'email': email}

    def login(self, email: str, password: str) -> Dict:
        """Login user."""
        user_path = self.users_dir / f'{email.lower().replace("@", "_at_")}.json'
        if not user_path.exists():
            return {'error': 'Invalid credentials'}

        with open(user_path) as f:
            user = json.load(f)

        hashed, _ = self._hash_password(password, user['salt'])
        if hashed != user['password_hash']:
            return {'error': 'Invalid credentials'}

        # Create session
        session_token = secrets.token_hex(32)
        session_data = {
            'email': user['email'],
            'created': datetime.now().isoformat(),
            'expires': (datetime.now() + timedelta(days=30)).isoformat(),
        }

        session_path = self.sessions_dir / f'{session_token}.json'
        with open(session_path, 'w') as f:
            json.dump(session_data, f, indent=2)

        return {
            'success': True,
            'session_token': session_token,
            'user': {
                'email': user['email'],
                'name': user['name'],
                'plan': user['plan'],
            }
        }

    def create_session(self, email: str) -> Optional[str]:
        """Create session for user (used by OAuth)"""
        user = self.get_user(email)
        if not user:
            return None
        
        session_token = secrets.token_hex(32)
        session_data = {
            'email': email,
            'created': datetime.now().isoformat(),
            'expires': (datetime.now() + timedelta(days=30)).isoformat(),
        }
        
        session_path = self.sessions_dir / f'{session_token}.json'
        with open(session_path, 'w') as f:
            json.dump(session_data, f, indent=2)
        
        return session_token

    def invalidate_all_sessions(self, email: str) -> int:
        """Invalidate all sessions for a user. Returns count of deleted sessions."""
        deleted = 0
        for session_file in self.sessions_dir.glob('*.json'):
            try:
                with open(session_file) as f:
                    data = json.load(f)
                if data.get('email') == email:
                    session_file.unlink()
                    deleted += 1
            except:
                pass
        return deleted

    def get_user(self, email: str) -> Optional[Dict]:
        """Get user by email."""
        user_path = self.users_dir / f'{email.lower().replace("@", "_at_")}.json'
        if not user_path.exists():
            return None

        with open(user_path) as f:
            user = json.load(f)

        # Remove sensitive fields
        user.pop('password_hash', None)
        user.pop('salt', None)
        return user

    def update_user(self, email: str, updates: Dict) -> Dict:
        """Update user data."""
        user_path = self.users_dir / f'{email.lower().replace("@", "_at_")}.json'
        if not user_path.exists():
            return {'error': 'User not found'}

        with open(user_path) as f:
            user = json.load(f)

        # Deep merge
        for key, value in updates.items():
            if isinstance(value, dict) and key in user and isinstance(user[key], dict):
                user[key].update(value)
            else:
                user[key] = value

        with open(user_path, 'w') as f:
            json.dump(user, f, indent=2)

        return {'success': True}

    def verify_session(self, token: str) -> Optional[Dict]:
        """Verify session token."""
        session_path = self.sessions_dir / f'{token}.json'
        if not session_path.exists():
            return None

        with open(session_path) as f:
            session_data = json.load(f)

        # Check expiry
        expires = datetime.fromisoformat(session_data['expires'])
        if datetime.now() > expires:
            session_path.unlink()
            return None

        return session_data

    def check_usage(self, email: str) -> Dict:
        """Check if user can send more emails."""
        user = self.get_user(email)
        if not user:
            return {'error': 'User not found'}

        usage = user.get('usage', {})

        # Reset monthly if needed
        last_reset = datetime.fromisoformat(usage.get('last_reset', datetime.now().isoformat()))
        if datetime.now() - last_reset > timedelta(days=30):
            usage['emails_sent'] = 0
            usage['last_reset'] = datetime.now().isoformat()
            self.update_user(email, {'usage': usage})

        plan = user.get('plan', 'free')
        limits = {
            'free': 10,
            'pro': 500,
            'enterprise': 999999,
        }

        limit = limits.get(plan, 10)
        remaining = max(0, limit - usage.get('emails_sent', 0))

        return {
            'plan': plan,
            'limit': limit,
            'used': usage.get('emails_sent', 0),
            'remaining': remaining,
            'can_send': remaining > 0,
        }

    
    def check_trial(self, email: str) -> Dict:
        """Check if user's trial is still active."""
        user = self.get_user(email)
        if not user:
            return {'error': 'User not found'}

        plan = user.get('plan', 'free')

        # Pro/Enterprise always active
        if plan in ('pro', 'enterprise'):
            plan_expires = user.get('plan_expires')
            if plan_expires:
                expires = datetime.fromisoformat(plan_expires)
                if datetime.now() > expires:
                    # Plan expired, downgrade to free
                    self.update_user(email, {
                        'plan': 'free',
                        'trial_expires': (datetime.now() + timedelta(days=3)).isoformat()
                    })
                    return {'active': False, 'plan': 'free', 'reason': 'plan_expired', 'days_left': 0}
            return {'active': True, 'plan': plan, 'days_left': -1}

        # Free plan — check trial
        trial_expires = user.get('trial_expires')
        if not trial_expires:
            # Old user without trial — give them 7 days
            trial_expires = (datetime.now() + timedelta(days=7)).isoformat()
            self.update_user(email, {'trial_expires': trial_expires})

        expires = datetime.fromisoformat(trial_expires)
        now = datetime.now()

        if now > expires:
            return {'active': False, 'plan': 'free', 'reason': 'trial_expired', 'days_left': 0}

        days_left = (expires - now).days
        return {'active': True, 'plan': 'free', 'reason': 'trial_active', 'days_left': days_left}

    def increment_usage(self, email: str, count: int = 1) -> Dict:
        """Increment email usage."""
        user = self.get_user(email)
        if not user:
            return {'error': 'User not found'}

        usage = user.get('usage', {})
        usage['emails_sent'] = usage.get('emails_sent', 0) + count

        self.update_user(email, {'usage': usage})
        return {'success': True, 'used': usage['emails_sent']}


def login_required(f):
    """Decorator to require login."""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = session.get('session_token')
        if not token:
            flash('Please login first', 'error')
            return redirect(url_for('login'))

        user_manager = UserManager()
        session_data = user_manager.verify_session(token)
        if not session_data:
            session.clear()
            flash('Session expired, please login again', 'error')
            return redirect(url_for('login'))

        return f(*args, **kwargs)
    return decorated



def trial_required(f):
    """Decorator to require active trial or paid plan."""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = session.get('session_token')
        if not token:
            flash('Please login first', 'error')
            return redirect(url_for('login'))

        user_manager = UserManager()
        session_data = user_manager.verify_session(token)
        if not session_data:
            session.clear()
            flash('Session expired, please login again', 'error')
            return redirect(url_for('login'))

        trial = user_manager.check_trial(session_data['email'])
        if not trial.get('active'):
            # Check if user has never started trial
            user = user_manager.get_user(session_data['email'])
            if user and not user.get('trial_expires'):
                flash('Start your free trial to continue.', 'error')
                return redirect(url_for('start_trial'))
            else:
                flash('Your free trial has expired. Upgrade to Pro to continue!', 'error')
                return redirect(url_for('pricing'))

        return f(*args, **kwargs)
    return decorated

def get_current_user() -> Optional[Dict]:
    """Get current logged-in user."""
    token = session.get('session_token')
    if not token:
        return None

    user_manager = UserManager()
    session_data = user_manager.verify_session(token)
    if not session_data:
        return None

    return user_manager.get_user(session_data['email'])
