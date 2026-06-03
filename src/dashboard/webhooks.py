"""
Cold Email Engine — Webhook Routes
Handle payment webhooks from LemonSqueezy + Midtrans
"""
import json
import hmac
from flask import Blueprint, request, jsonify, abort
from src.payments.handler import payment_handler

webhook_bp = Blueprint('webhooks', __name__)


@webhook_bp.route('/webhook/lemonsqueezy', methods=['POST'])
def lemonsqueezy_webhook():
    """Handle LemonSqueezy webhook."""
    from src.payments.lemonsqueezy import LemonSqueezy

    payload = request.get_data()
    signature = request.headers.get('X-Signature', '')

    ls = LemonSqueezy()
    if not ls.verify_webhook(payload, signature):
        abort(401)

    data = request.get_json()
    result = payment_handler.handle_lemonsqueezy(data)

    return jsonify(result)


@webhook_bp.route('/webhook/midtrans', methods=['POST'])
def midtrans_webhook():
    """Handle Midtrans notification/webhook."""
    notification = request.get_json()

    if not notification:
        return jsonify({'error': 'No payload'}), 400

    result = payment_handler.handle_midtrans(notification)

    if 'error' in result:
        return jsonify(result), 404

    return jsonify(result)


@webhook_bp.route('/payment/status/<order_id>', methods=['GET'])
def payment_status(order_id):
    """Check payment status."""
    result = payment_handler.get_order_status(order_id)
    return jsonify(result)
