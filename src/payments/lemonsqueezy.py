"""
Cold Email Engine — LemonSqueezy Payment Integration
Auto license key, subscription management, webhook handling
"""
import os
import json
import hmac
import hashlib
import requests
from typing import Dict, Optional
from pathlib import Path
from datetime import datetime, timedelta


class LemonSqueezy:
    """LemonSqueezy payment integration."""

    def __init__(self, api_key: str = None, webhook_secret: str = None):
        self.api_key = api_key or os.getenv('LEMONSQUEEZY_API_KEY', '')
        self.webhook_secret = webhook_secret or os.getenv('LEMONSQUEEZY_WEBHOOK_SECRET', '')
        self.base_url = 'https://api.lemonsqueezy.com/v1'
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Accept': 'application/vnd.api+json',
            'Content-Type': 'application/vnd.api+json',
        }

        # Store path
        self.data_dir = Path(__file__).parent.parent.parent / 'data'
        self.orders_dir = self.data_dir / 'orders'
        self.orders_dir.mkdir(parents=True, exist_ok=True)

    def get_products(self) -> Dict:
        """List all products."""
        resp = requests.get(f'{self.base_url}/products', headers=self.headers)
        return resp.json()

    def get_variants(self, product_id: str) -> Dict:
        """Get variants (pricing options) for a product."""
        resp = requests.get(f'{self.base_url}/variants', headers=self.headers, params={'filter[product_id]': product_id})
        return resp.json()

    def create_checkout(self, variant_id: str, email: str = None, custom_data: Dict = None) -> Dict:
        """Create a checkout URL for a product variant."""
        payload = {
            'data': {
                'type': 'checkouts',
                'attributes': {
                    'checkout_data': {
                        'email': email,
                        'custom': custom_data or {},
                    },
                    'product_options': {
                        'redirect_url': os.getenv('LEMONSQUEEZY_REDIRECT_URL', 'http://localhost:5000/dashboard'),
                    },
                },
                'relationships': {
                    'store': {
                        'data': {
                            'type': 'stores',
                            'id': os.getenv('LEMONSQUEEZY_STORE_ID', ''),
                        }
                    },
                    'variant': {
                        'data': {
                            'type': 'variants',
                            'id': variant_id,
                        }
                    }
                }
            }
        }

        resp = requests.post(f'{self.base_url}/checkouts', headers=self.headers, json=payload)
        return resp.json()

    def verify_webhook(self, payload: bytes, signature: str) -> bool:
        """Verify webhook signature."""
        if not self.webhook_secret:
            return True  # Skip verification if no secret set

        expected = hmac.new(
            self.webhook_secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(expected, signature)

    def handle_webhook(self, payload: Dict) -> Dict:
        """Handle webhook event."""
        event_name = payload.get('meta', {}).get('event_name', '')
        data = payload.get('data', {})

        handlers = {
            'order_created': self._handle_order_created,
            'subscription_created': self._handle_subscription_created,
            'subscription_updated': self._handle_subscription_updated,
            'subscription_cancelled': self._handle_subscription_cancelled,
            'subscription_payment_success': self._handle_payment_success,
        }

        handler = handlers.get(event_name)
        if handler:
            return handler(data)

        return {'status': 'ignored', 'event': event_name}

    def _handle_order_created(self, data: Dict) -> Dict:
        """Handle new order."""
        attrs = data.get('attributes', {})
        custom = attrs.get('checkout_data', {}).get('custom', {})
        email = attrs.get('customer_email', '')

        order = {
            'id': data.get('id'),
            'email': email,
            'product_id': attrs.get('product_id'),
            'variant_id': attrs.get('variant_id'),
            'total': attrs.get('total'),
            'currency': attrs.get('currency'),
            'license_key': attrs.get('license_key'),
            'status': attrs.get('status'),
            'created': attrs.get('created_at'),
        }

        # Save order
        order_path = self.orders_dir / f'{order["id"]}.json'
        with open(order_path, 'w') as f:
            json.dump(order, f, indent=2)

        # Update user plan
        if email:
            from src.auth.user_manager import UserManager
            user_manager = UserManager()
            user_manager.update_user(email, {
                'plan': 'pro',
                'license_key': order['license_key'],
                'plan_expires': (datetime.now() + timedelta(days=30)).isoformat(),
                'usage': {'emails_limit': 500},
            })

        return {'status': 'processed', 'order': order}

    def _handle_subscription_created(self, data: Dict) -> Dict:
        """Handle new subscription."""
        attrs = data.get('attributes', {})
        email = attrs.get('user_email', '')

        subscription = {
            'id': data.get('id'),
            'email': email,
            'product_id': attrs.get('product_id'),
            'variant_id': attrs.get('variant_id'),
            'status': attrs.get('status'),
            'renews_at': attrs.get('renews_at'),
            'ends_at': attrs.get('ends_at'),
            'created': attrs.get('created_at'),
        }

        # Save subscription
        sub_path = self.orders_dir / f'sub_{subscription["id"]}.json'
        with open(sub_path, 'w') as f:
            json.dump(subscription, f, indent=2)

        # Update user
        if email:
            from src.auth.user_manager import UserManager
            user_manager = UserManager()
            user_manager.update_user(email, {
                'plan': 'pro',
                'subscription_id': subscription['id'],
                'plan_expires': subscription['renews_at'],
            })

        return {'status': 'processed', 'subscription': subscription}

    def _handle_subscription_updated(self, data: Dict) -> Dict:
        """Handle subscription update."""
        attrs = data.get('attributes', {})
        email = attrs.get('user_email', '')

        if email:
            from src.auth.user_manager import UserManager
            user_manager = UserManager()
            user_manager.update_user(email, {
                'plan_expires': attrs.get('renews_at'),
            })

        return {'status': 'updated'}

    def _handle_subscription_cancelled(self, data: Dict) -> Dict:
        """Handle subscription cancellation."""
        attrs = data.get('attributes', {})
        email = attrs.get('user_email', '')

        if email:
            from src.auth.user_manager import UserManager
            user_manager = UserManager()
            user_manager.update_user(email, {
                'plan': 'free',
                'plan_expires': attrs.get('ends_at'),
                'usage': {'emails_limit': 10},
            })

        return {'status': 'cancelled'}

    def _handle_payment_success(self, data: Dict) -> Dict:
        """Handle successful payment."""
        attrs = data.get('attributes', {})
        email = attrs.get('user_email', '')

        if email:
            from src.auth.user_manager import UserManager
            user_manager = UserManager()
            user_manager.update_user(email, {
                'plan_expires': attrs.get('renews_at'),
            })

        return {'status': 'payment_processed'}

    def verify_license(self, license_key: str, instance_id: str = None) -> Dict:
        """Verify a license key."""
        payload = {
            'license_key': license_key,
        }
        if instance_id:
            payload['instance_id'] = instance_id

        resp = requests.post(
            'https://api.lemonsqueezy.com/v1/licenses/validate',
            json=payload
        )
        return resp.json()

    def activate_license(self, license_key: str, instance_name: str = 'default') -> Dict:
        """Activate a license key for an instance."""
        resp = requests.post(
            'https://api.lemonsqueezy.com/v1/licenses/activate',
            json={
                'license_key': license_key,
                'instance_name': instance_name,
            }
        )
        return resp.json()


# Plan configurations
PLANS = {
    'free': {
        'name': 'Free',
        'price': 0,
        'emails_per_day': 10,
        'features': ['Basic email generation', 'CSV import', 'Email verification'],
    },
    'pro': {
        'name': 'Pro',
        'price': 29,
        'emails_per_day': 500,
        'features': [
            'Everything in Free',
            '500 emails/day',
            'Follow-up sequences',
            'Priority support',
            'API access',
        ],
    },
    'enterprise': {
        'name': 'Enterprise',
        'price': 99,
        'emails_per_day': 999999,
        'features': [
            'Everything in Pro',
            'Unlimited emails',
            'Custom templates',
            'Dedicated support',
            'White-label',
        ],
    },
}


if __name__ == '__main__':
    # Test
    ls = LemonSqueezy()
    print("LemonSqueezy integration ready")
    print(f"Plans: {list(PLANS.keys())}")
