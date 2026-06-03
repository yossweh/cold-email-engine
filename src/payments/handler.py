"""
Cold Email Engine — Unified Payment Handler
Handles webhooks from LemonSqueezy + Midtrans, auto-activates plans
"""
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict

logger = logging.getLogger(__name__)


class PaymentHandler:
    """Unified payment handler for all providers."""

    def __init__(self):
        self.data_dir = Path(__file__).parent.parent.parent / 'data'
        self.orders_dir = self.data_dir / 'orders'
        self.orders_dir.mkdir(parents=True, exist_ok=True)
        self.webhook_log = self.data_dir / 'webhooks.json'

    def handle_lemonsqueezy(self, payload: Dict) -> Dict:
        """Handle LemonSqueezy webhook."""
        event_name = payload.get('meta', {}).get('event_name', '')
        data = payload.get('data', {})
        attrs = data.get('attributes', {})

        self._log_webhook('lemonsqueezy', event_name, payload)

        # Extract email from custom data or customer email
        custom = attrs.get('checkout_data', {}).get('custom', {})
        email = custom.get('email') or attrs.get('customer_email', '')
        plan = custom.get('plan', 'pro')

        result = {'provider': 'lemonsqueezy', 'event': event_name}

        if event_name == 'order_created':
            # Payment successful!
            order = {
                'id': data.get('id'),
                'provider': 'lemonsqueezy',
                'email': email,
                'plan': plan,
                'amount': attrs.get('total'),
                'currency': attrs.get('currency', 'USD'),
                'status': 'paid',
                'license_key': attrs.get('license_key'),
                'created': attrs.get('created_at'),
            }
            self._save_order(f'ls_{order["id"]}', order)
            self._activate_plan(email, plan)
            result['action'] = 'activated'
            result['order'] = order

        elif event_name in ['subscription_created', 'subscription_payment_success']:
            email = attrs.get('user_email', email)
            self._activate_plan(email, plan)
            result['action'] = 'activated'

        elif event_name == 'subscription_cancelled':
            email = attrs.get('user_email', email)
            self._downgrade_plan(email)
            result['action'] = 'downgraded'

        else:
            result['action'] = 'ignored'

        return result

    def handle_midtrans(self, notification: Dict) -> Dict:
        """Handle Midtrans webhook/notification."""
        order_id = notification.get('order_id', '')
        transaction_status = notification.get('transaction_status', '')
        fraud_status = notification.get('fraud_status', '')

        self._log_webhook('midtrans', transaction_status, notification)

        # Load order
        order_path = self.orders_dir / f'{order_id}.json'
        if not order_path.exists():
            return {'error': f'Order not found: {order_id}'}

        with open(order_path) as f:
            order = json.load(f)

        result = {'provider': 'midtrans', 'order_id': order_id}

        # Determine if should activate
        should_activate = False

        if transaction_status == 'capture' and fraud_status == 'accept':
            should_activate = True
        elif transaction_status == 'settlement':
            should_activate = True
        elif transaction_status in ['cancel', 'deny']:
            order['status'] = 'failed'
        elif transaction_status == 'expire':
            order['status'] = 'expired'
        else:
            order['status'] = 'pending'

        if should_activate:
            order['status'] = 'paid'
            order['paid_at'] = datetime.now().isoformat()
            self._activate_plan(order['email'], order['plan'])
            result['action'] = 'activated'
        else:
            result['action'] = 'status_updated'

        # Save updated order
        with open(order_path, 'w') as f:
            json.dump(order, f, indent=2)

        result['order'] = order
        return result

    def _activate_plan(self, email: str, plan: str) -> bool:
        """Auto-activate plan for user. This is the key function!"""
        if not email:
            logger.error(f"No email provided for activation")
            return False

        from src.auth.user_manager import UserManager
        user_manager = UserManager()

        # Check if user exists
        user = user_manager.get_user(email)
        if not user:
            # Auto-register user if not exists
            logger.info(f"Auto-registering user: {email}")
            user_manager.register(email, '', email.split('@')[0])

        # Plan limits
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
            'activated_at': datetime.now().isoformat(),
        }

        result = user_manager.update_user(email, updates)
        logger.info(f"Plan activated: {email} -> {plan}")
        return True

    def _downgrade_plan(self, email: str) -> bool:
        """Downgrade user to free plan."""
        if not email:
            return False

        from src.auth.user_manager import UserManager
        user_manager = UserManager()

        updates = {
            'plan': 'free',
            'plan_expires': None,
            'usage': {
                'emails_limit': 10,
            },
        }

        user_manager.update_user(email, updates)
        logger.info(f"Plan downgraded: {email} -> free")
        return True

    def _save_order(self, order_id: str, order: Dict):
        """Save order to file."""
        order_path = self.orders_dir / f'{order_id}.json'
        with open(order_path, 'w') as f:
            json.dump(order, f, indent=2)

    def _log_webhook(self, provider: str, event: str, payload: Dict):
        """Log webhook for debugging."""
        log_entry = {
            'provider': provider,
            'event': event,
            'timestamp': datetime.now().isoformat(),
            'payload_keys': list(payload.keys()),
        }

        logs = []
        if self.webhook_log.exists():
            try:
                with open(self.webhook_log) as f:
                    logs = json.load(f)
            except:
                pass

        logs.append(log_entry)

        # Keep last 1000 entries
        if len(logs) > 1000:
            logs = logs[-1000:]

        with open(self.webhook_log, 'w') as f:
            json.dump(logs, f, indent=2)

    def get_order_status(self, order_id: str) -> Dict:
        """Get order status."""
        order_path = self.orders_dir / f'{order_id}.json'
        if not order_path.exists():
            return {'error': 'Order not found'}

        with open(order_path) as f:
            return json.load(f)

    def get_user_orders(self, email: str) -> list:
        """Get all orders for a user."""
        orders = []
        for f in self.orders_dir.glob('*.json'):
            with open(f) as fh:
                order = json.load(fh)
            if order.get('email', '').lower() == email.lower():
                orders.append(order)
        return orders


# Singleton
payment_handler = PaymentHandler()
