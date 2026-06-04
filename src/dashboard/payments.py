"""
Cold Email Engine — Payment Routes
LemonSqueezy (international) + NOWPayments (crypto)
"""
from flask import Blueprint, request, jsonify, redirect, url_for, flash, session, render_template
from src.auth.user_manager import UserManager, login_required, get_current_user
from src.payments.handler import payment_handler
import os
import requests as req
from datetime import datetime, timedelta
from dotenv import load_dotenv
load_dotenv()

payment_bp = Blueprint('payments', __name__)
user_manager = UserManager()

# Plan pricing (USD)
PLAN_PRICES = {
    'pro': 15.00,
    'enterprise': 49.00,
}


# ==================== CRYPTO PAYMENTS (NOWPayments) ====================

@payment_bp.route('/pay/crypto/<plan>')
@login_required
def crypto_checkout(plan):
    """Create NOWPayments invoice via API for crypto payment (full auto)."""
    if plan not in PLAN_PRICES:
        flash('Invalid plan', 'error')
        return redirect(url_for('pricing'))

    user = get_current_user()
    api_key = os.getenv('NOWPAYMENTS_API_KEY', '')
    price = PLAN_PRICES[plan]

    if not api_key:
        flash('Crypto payment temporarily unavailable. Contact support.', 'error')
        return redirect(url_for('pricing'))

    # Create NOWPayments invoice
    order_id = f"0xchapo_{user['email']}_{plan}_{int(datetime.now().timestamp())}"
    success_url = f"https://0xchapo.xyz/payment/crypto/success?order_id={order_id}"
    cancel_url = "https://0xchapo.xyz/pricing"

    try:
        resp = req.post('https://api.nowpayments.io/v1/invoice',
            headers={
                'x-api-key': api_key,
                'Content-Type': 'application/json'
            },
            json={
                'price_amount': price,
                'price_currency': 'usd',
                'order_id': order_id,
                'order_description': f'0xChapo {plan.capitalize()} Plan - {user["email"]}',
                'success_url': success_url,
                'cancel_url': cancel_url,
                'ipn_callback_url': os.getenv('NOWPAYMENTS_IPN_URL', 'https://0xchapo.xyz/webhook/nowpayments'),
            },
            timeout=10
        )

        if resp.status_code == 200:
            data = resp.json()
            invoice_url = data.get('invoice_url', '')
            if invoice_url:
                # Store pending payment
                user_manager.update_user(user['email'], {
                    'pending_crypto': {
                        'order_id': order_id,
                        'plan': plan,
                        'created_at': datetime.now().isoformat(),
                    }
                })
                return redirect(invoice_url)

        print(f"NOWPayments API error: {resp.status_code} - {resp.text}")
        flash('Failed to create crypto payment. Please try again.', 'error')
    except Exception as e:
        print(f"NOWPayments API exception: {e}")
        flash('Payment service error. Please try again.', 'error')

    return redirect(url_for('pricing'))


@payment_bp.route('/payment/crypto/success')
@login_required
def crypto_success():
    """Crypto payment success callback."""
    order_id = request.args.get('order_id', '')
    flash('Crypto payment submitted! Your plan will be activated once the transaction is confirmed on-chain.', 'info')
    return redirect(url_for('dashboard'))


@payment_bp.route('/webhook/nowpayments', methods=['POST'])
def nowpayments_webhook():
    """NOWPayments webhook for payment confirmation (auto-upgrade)."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data'}), 400

    # Verify IPN signature
    ipn_secret = os.getenv('NOWPAYMENTS_IPN_SECRET', '')
    if ipn_secret:
        import hmac, hashlib
        signature = request.headers.get('x-nowpayments-sig', '')
        if signature:
            # Sort params and create expected signature
            sorted_params = sorted(data.items())
            sorted_json = str(sorted_params).replace("'", '"')
            expected_sig = hmac.new(
                ipn_secret.encode(),
                sorted_json.encode(),
                hashlib.sha512
            ).hexdigest()
            if not hmac.compare_digest(signature, expected_sig):
                print(f"NOWPayments webhook: Invalid signature")
                return jsonify({'error': 'Invalid signature'}), 403

    print(f"NOWPayments webhook: {data}")

    payment_status = data.get('payment_status', '')
    order_id = data.get('order_id', '')
    actually_paid = data.get('actually_paid', 0)

    # Only confirm if payment is finished
    if payment_status in ['finished', 'confirmed', 'sending']:
        # Parse order_id: 0xchapo_{email}_{plan}_{timestamp}
        parts = order_id.split('_')
        if len(parts) >= 4 and parts[0] == '0xchapo':
            email = '_'.join(parts[1:-2])  # Handle emails with underscores
            plan = parts[-2]

            if plan in PLAN_PRICES:
                # Activate plan
                expires = datetime.now() + timedelta(days=30)
                user_manager.update_user(email, {
                    'plan': plan,
                    'plan_expires': expires.isoformat(),
                    'plan_source': 'crypto',
                    'pending_crypto': None,  # Clear pending
                })
                print(f"✅ Crypto payment confirmed: {email} -> {plan}")

    return jsonify({'status': 'ok'}), 200


# ==================== LEMONSQUEEZY (Card Payments) ====================


@payment_bp.route('/subscribe/<plan>', methods=['POST'])
@login_required
def subscribe_international(plan):
    """Subscribe via LemonSqueezy (API checkout)."""
    import requests as req
    user = get_current_user()

    if plan not in ['pro', 'enterprise']:
        flash('Invalid plan', 'error')
        return redirect(url_for('pricing'))

    variant_id = os.getenv(f'LEMONSQUEEZY_VARIANT_{plan.upper()}', '')
    store_id = os.getenv('LEMONSQUEEZY_STORE_ID', '')
    api_key = os.getenv('LEMONSQUEEZY_API_KEY', '')

    if variant_id and store_id and api_key:
        # Create checkout via API
        resp = req.post('https://api.lemonsqueezy.com/v1/checkouts',
            headers={
                'Authorization': f'Bearer {api_key}',
                'Accept': 'application/vnd.api+json',
                'Content-Type': 'application/vnd.api+json'
            },
            json={
                'data': {
                    'type': 'checkouts',
                    'attributes': {
                        'checkout_data': {
                            'email': user['email'],
                            'custom': {'user_email': user['email'], 'plan': plan}
                        }
                    },
                    'relationships': {
                        'store': {'data': {'type': 'stores', 'id': store_id}},
                        'variant': {'data': {'type': 'variants', 'id': variant_id}}
                    }
                }
            }
        )
        if resp.status_code == 201:
            checkout_url = resp.json()['data']['attributes']['url']
            return redirect(checkout_url)

    # Fallback: direct checkout URL
    checkout_url = f'https://0xchapo.lemonsqueezy.com/checkout/buy/{variant_id}?email={user["email"]}&custom[user_email]={user["email"]}&custom[plan]={plan}'
    return redirect(checkout_url)


@payment_bp.route('/payment/success')
@login_required
def payment_success():
    """Payment success callback."""
    flash('Payment successful! Your plan has been upgraded.', 'success')
    return redirect(url_for('dashboard'))


@payment_bp.route('/payment/pending')
@login_required
def payment_pending():
    """Payment pending callback (VA, QRIS)."""
    flash('Payment pending. Your plan will be activated once payment is confirmed.', 'info')
    return redirect(url_for('dashboard'))


@payment_bp.route('/payment/failed')
@login_required
def payment_failed():
    """Payment failed callback."""
    flash('Payment failed. Please try again.', 'error')
    return redirect(url_for('pricing'))


@payment_bp.route('/api/payment/status/<order_id>')
def check_payment_status(order_id):
    """Check payment status (for polling)."""
    result = payment_handler.get_order_status(order_id)
    return jsonify(result)
