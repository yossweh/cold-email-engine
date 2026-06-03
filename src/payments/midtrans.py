"""
Cold Email Engine — Midtrans Payment Integration
Indonesian payment methods: QRIS, GoPay, OVO, VA, Credit Card
"""
import os
import json
import base64
import requests
from typing import Dict, Optional
from pathlib import Path
from datetime import datetime, timedelta


class Midtrans:
    """Midtrans payment integration for Indonesian market."""

    def __init__(self, server_key: str = None, client_key: str = None, is_production: bool = False):
        self.server_key = server_key or os.getenv('MIDTRANS_SERVER_KEY', '')
        self.client_key = client_key or os.getenv('MIDTRANS_CLIENT_KEY', '')
        self.is_production = is_production

        if is_production:
            self.base_url = 'https://api.midtrans.com/v2'
            self.snap_url = 'https://app.midtrans.com/snap/v1'
        else:
            self.base_url = 'https://api.sandbox.midtrans.com/v2'
            self.snap_url = 'https://app.sandbox.midtrans.com/snap/v1'

        # Auth header
        auth_string = base64.b64encode(f'{self.server_key}:'.encode()).decode()
        self.headers = {
            'Authorization': f'Basic {auth_string}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }

        # Storage
        self.data_dir = Path(__file__).parent.parent.parent / 'data'
        self.orders_dir = self.data_dir / 'orders'
        self.orders_dir.mkdir(parents=True, exist_ok=True)

    def create_transaction(self, order_id: str, amount: int, email: str, plan: str) -> Dict:
        """Create Snap transaction for checkout."""
        payload = {
            'transaction_details': {
                'order_id': order_id,
                'gross_amount': amount,
            },
            'customer_details': {
                'email': email,
            },
            'item_details': [{
                'id': plan,
                'price': amount,
                'quantity': 1,
                'name': f'Cold Email Engine - {plan.title()} Plan',
            }],
            'callbacks': {
                'finish': os.getenv('MIDTRANS_REDIRECT_URL', 'http://localhost:5000/dashboard'),
            },
            'expiry': {
                'unit': 'hours',
                'duration': 24,
            },
        }

        # Enabled payments
        if os.getenv('MIDTRANS_ENABLED_PAYMENTS'):
            payload['enabled_payments'] = os.getenv('MIDTRANS_ENABLED_PAYMENTS').split(',')
        else:
            payload['enabled_payments'] = [
                'qris', 'gopay', 'ovo', 'shopeepay',
                'bca_va', 'bni_va', 'bri_va', 'mandiri_va',
                'credit_card',
            ]

        resp = requests.post(
            f'{self.snap_url}/transactions',
            headers=self.headers,
            json=payload
        )

        data = resp.json()

        # Save order
        order = {
            'order_id': order_id,
            'email': email,
            'plan': plan,
            'amount': amount,
            'currency': 'IDR',
            'status': 'pending',
            'snap_token': data.get('token'),
            'redirect_url': data.get('redirect_url'),
            'created': datetime.now().isoformat(),
        }

        order_path = self.orders_dir / f'{order_id}.json'
        with open(order_path, 'w') as f:
            json.dump(order, f, indent=2)

        return order

    def handle_notification(self, notification: Dict) -> Dict:
        """Handle Midtrans payment notification (webhook)."""
        order_id = notification.get('order_id', '')
        transaction_status = notification.get('transaction_status', '')
        fraud_status = notification.get('fraud_status', '')
        payment_type = notification.get('payment_type', '')
        gross_amount = notification.get('gross_amount', '')

        # Load order
        order_path = self.orders_dir / f'{order_id}.json'
        if not order_path.exists():
            return {'error': f'Order not found: {order_id}'}

        with open(order_path) as f:
            order = json.load(f)

        # Determine status
        status = 'pending'
        should_activate = False

        if transaction_status == 'capture':
            if fraud_status == 'accept':
                status = 'paid'
                should_activate = True
        elif transaction_status == 'settlement':
            status = 'paid'
            should_activate = True
        elif transaction_status == 'cancel' or transaction_status == 'deny':
            status = 'failed'
        elif transaction_status == 'expire':
            status = 'expired'
        elif transaction_status == 'pending':
            status = 'pending'

        # Update order
        order['status'] = status
        order['payment_type'] = payment_type
        order['transaction_status'] = transaction_status
        order['fraud_status'] = fraud_status
        order['updated'] = datetime.now().isoformat()

        with open(order_path, 'w') as f:
            json.dump(order, f, indent=2)

        # Auto-activate if paid
        if should_activate:
            self._activate_plan(order['email'], order['plan'])

        return {
            'status': status,
            'should_activate': should_activate,
            'order': order,
        }

    def _activate_plan(self, email: str, plan: str) -> Dict:
        """Auto-activate plan for user after payment."""
        from src.auth.user_manager import UserManager
        user_manager = UserManager()

        limits = {
            'pro': 500,
            'enterprise': 999999,
        }

        updates = {
            'plan': plan,
            'plan_expires': (datetime.now() + timedelta(days=30)).isoformat(),
            'usage': {
                'emails_limit': limits.get(plan, 10),
                'emails_sent': 0,
                'last_reset': datetime.now().isoformat(),
            },
            'payment': {
                'provider': 'midtrans',
                'activated_at': datetime.now().isoformat(),
                'plan': plan,
            }
        }

        result = user_manager.update_user(email, updates)
        return result

    def check_status(self, order_id: str) -> Dict:
        """Check transaction status."""
        resp = requests.get(
            f'{self.base_url}/{order_id}/status',
            headers=self.headers
        )
        return resp.json()

    def cancel(self, order_id: str) -> Dict:
        """Cancel a transaction."""
        resp = requests.post(
            f'{self.base_url}/{order_id}/cancel',
            headers=self.headers
        )
        return resp.json()

    def generate_order_id(self, email: str, plan: str) -> str:
        """Generate unique order ID."""
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        email_hash = hash(email) % 10000
        return f'CEE-{plan.upper()}-{email_hash}-{timestamp}'


# Pricing in IDR
PLANS_IDR = {
    'pro': 450000,        # ~$29
    'enterprise': 1550000, # ~$99
}


if __name__ == '__main__':
    midtrans = Midtrans()
    print("Midtrans integration ready")
    print(f"Plans (IDR): {PLANS_IDR}")
