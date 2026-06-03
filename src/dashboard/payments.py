"""
Cold Email Engine — Payment Routes
LemonSqueezy (international) + Midtrans (Indonesia)
"""
from flask import Blueprint, request, jsonify, redirect, url_for, flash, session, render_template
from src.auth.user_manager import UserManager, login_required, get_current_user
from src.payments.handler import payment_handler
import os

payment_bp = Blueprint('payments', __name__)
user_manager = UserManager()


@payment_bp.route('/subscribe/<plan>', methods=['POST'])
@login_required
def subscribe_international(plan):
    """Subscribe via LemonSqueezy (international payments)."""
    user = get_current_user()

    if plan not in ['pro', 'enterprise']:
        flash('Invalid plan', 'error')
        return redirect(url_for('pricing'))

    # Create LemonSqueezy checkout
    from src.payments.lemonsqueezy import LemonSqueezy
    ls = LemonSqueezy()

    variant_id = os.getenv(f'LEMONSQUEEZY_VARIANT_{plan.upper()}', '')
    if variant_id:
        result = ls.create_checkout(
            variant_id=variant_id,
            email=user['email'],
            custom_data={'email': user['email'], 'plan': plan}
        )
        checkout_url = result.get('data', {}).get('attributes', {}).get('url')
        if checkout_url:
            return redirect(checkout_url)

    # Fallback: direct checkout URL from env
    checkout_url = os.getenv(f'LEMONSQUEEZY_CHECKOUT_{plan.upper()}')
    if checkout_url:
        return redirect(checkout_url)

    flash('Payment not configured. Contact support.', 'error')
    return redirect(url_for('pricing'))


@payment_bp.route('/subscribe/<plan>/idr', methods=['POST'])
@login_required
def subscribe_indonesia(plan):
    """Subscribe via Midtrans (Indonesian payments)."""
    user = get_current_user()

    if plan not in ['pro', 'enterprise']:
        flash('Invalid plan', 'error')
        return redirect(url_for('pricing'))

    from src.payments.midtrans import Midtrans, PLANS_IDR
    midtrans = Midtrans()

    amount = PLANS_IDR.get(plan)
    if not amount:
        flash('Invalid plan', 'error')
        return redirect(url_for('pricing'))

    # Generate order ID
    order_id = midtrans.generate_order_id(user['email'], plan)

    # Create Snap transaction
    order = midtrans.create_transaction(
        order_id=order_id,
        amount=amount,
        email=user['email'],
        plan=plan,
    )

    if order.get('snap_token'):
        # Redirect to Midtrans Snap payment page
        snap_url = os.getenv('MIDTRANS_SNAP_URL', 'https://app.sandbox.midtrans.com/snap/v2/vtweb')
        return redirect(f'{snap_url}/{order["snap_token"]}')

    flash('Error creating payment. Please try again.', 'error')
    return redirect(url_for('pricing'))


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
