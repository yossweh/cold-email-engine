"""
Cold Email Engine — Main Dashboard App
Auth, payments, campaigns, leads, verification, sequences
"""
import os
import sys
import json
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session, abort

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.main import ColdEmailEngine, load_leads_csv
from src.leads.lead_manager import LeadManager
from src.verifier.email_verifier import EmailVerifier
from src.sequences.followup import FollowUpSequence, DEFAULT_TEMPLATES
from src.auth.user_manager import UserManager, login_required, get_current_user
from src.payments.lemonsqueezy import LemonSqueezy, PLANS

app = Flask(__name__, template_folder='../dashboard/templates', static_folder='../dashboard/static')
app.secret_key = os.getenv('DASHBOARD_SECRET', 'dev-secret-change-me')

engine = None
lead_manager = LeadManager()
verifier = EmailVerifier()
sequences = FollowUpSequence()
user_manager = UserManager()
payment = LemonSqueezy()


def get_engine():
    global engine
    if engine is None:
        engine = ColdEmailEngine()
    return engine


# ==================== AUTH ROUTES ====================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '')
        password = request.form.get('password', '')

        result = user_manager.login(email, password)
        if result.get('error'):
            flash(result['error'], 'error')
        else:
            session['session_token'] = result['session_token']
            session['user'] = result['user']
            flash('Welcome back!', 'success')
            return redirect(url_for('dashboard'))

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name', '')
        email = request.form.get('email', '')
        password = request.form.get('password', '')
        confirm = request.form.get('confirm', '')

        if password != confirm:
            flash('Passwords do not match', 'error')
        elif len(password) < 8:
            flash('Password must be at least 8 characters', 'error')
        else:
            result = user_manager.register(email, password, name)
            if result.get('error'):
                flash(result['error'], 'error')
            else:
                flash('Account created! Please login.', 'success')
                return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out', 'success')
    return redirect(url_for('index'))


# ==================== MAIN ROUTES ====================

@app.route('/')
def index():
    """Landing page / dashboard."""
    user = get_current_user()
    if user:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard."""
    user = get_current_user()

    campaigns_dir = Path(__file__).parent.parent / 'data' / 'campaigns'
    campaigns = []

    if campaigns_dir.exists():
        for d in sorted(campaigns_dir.iterdir(), reverse=True)[:5]:
            if d.is_dir():
                send_log = d / 'send_log.json'
                stats = {'id': d.name}
                if send_log.exists():
                    with open(send_log) as f:
                        logs = json.load(f)
                    stats['total'] = len(logs)
                    stats['sent'] = sum(1 for l in logs if l.get('status') == 'sent')
                    stats['failed'] = sum(1 for l in logs if l.get('status') == 'failed')
                campaigns.append(stats)

    lead_lists = lead_manager.list_all()
    seq_list = sequences.list_sequences()
    usage = user_manager.check_usage(user['email'])

    return render_template('index.html',
        user=user,
        campaigns=campaigns,
        lead_lists=lead_lists,
        sequences=seq_list,
        usage=usage,
    )


# ==================== CAMPAIGN ROUTES ====================

@app.route('/campaign/new', methods=['GET', 'POST'])
@login_required
def new_campaign():
    user = get_current_user()

    if request.method == 'POST':
        # Check usage
        usage = user_manager.check_usage(user['email'])
        if not usage['can_send']:
            flash('Daily email limit reached. Upgrade your plan!', 'error')
            return redirect(url_for('pricing'))

        leads_text = request.form.get('leads', '')
        product = request.form.get('product', '')
        sender_name = request.form.get('sender_name', '')
        sender_company = request.form.get('sender_company', '')
        tone = request.form.get('tone', 'professional')
        dry_run = 'dry_run' in request.form
        verify_emails = 'verify_emails' in request.form

        leads = [l.strip() for l in leads_text.strip().split('\n') if l.strip()]

        if verify_emails:
            emails = [l for l in leads if '@' in l]
            if emails:
                valid, rejected = verifier.filter_valid_emails(emails)
                leads = [l for l in leads if '@' not in l] + valid

        eng = get_engine()
        result = eng.run_campaign(
            leads=leads,
            product_description=product,
            sender_name=sender_name,
            sender_company=sender_company,
            tone=tone,
            dry_run=dry_run,
        )

        if not dry_run:
            user_manager.increment_usage(user['email'], result.get('emails_sent', 0))

        return render_template('result.html', user=user, result=result)

    return render_template('new_campaign.html', user=user)


@app.route('/campaign/<campaign_id>')
@login_required
def campaign_detail(campaign_id):
    user = get_current_user()
    campaign_dir = Path(__file__).parent.parent / 'data' / 'campaigns' / campaign_id

    if not campaign_dir.exists():
        return "Campaign not found", 404

    generated = []
    gen_file = campaign_dir / 'generated.json'
    if gen_file.exists():
        with open(gen_file) as f:
            generated = json.load(f)

    send_log = []
    log_file = campaign_dir / 'send_log.json'
    if log_file.exists():
        with open(log_file) as f:
            send_log = json.load(f)

    return render_template('campaign.html',
        user=user,
        campaign_id=campaign_id,
        generated=generated,
        send_log=send_log,
    )


# ==================== LEAD ROUTES ====================

@app.route('/leads', methods=['GET', 'POST'])
@login_required
def leads_page():
    user = get_current_user()

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'import_csv':
            file = request.files.get('file')
            list_name = request.form.get('list_name', '')

            if file:
                temp_path = Path('/tmp') / file.filename
                file.save(str(temp_path))
                result = lead_manager.import_csv(str(temp_path), list_name or None)
                temp_path.unlink()

                if 'error' in result:
                    flash(f'Error: {result["error"]}', 'error')
                else:
                    flash(f'Imported {result["total_imported"]} leads!', 'success')

        elif action == 'import_manual':
            entries_text = request.form.get('entries', '')
            list_name = request.form.get('list_name', 'manual')
            entries = [e.strip() for e in entries_text.strip().split('\n') if e.strip()]
            result = lead_manager.import_manual(entries, list_name)
            flash(f'Imported {result["total_imported"]} leads!', 'success')

        elif action == 'deduplicate':
            list_name = request.form.get('list_name')
            if list_name:
                result = lead_manager.deduplicate(list_name)
                flash(f'Removed {result["removed"]} duplicates!', 'success')

        return redirect(url_for('leads_page'))

    lists = lead_manager.list_all()
    return render_template('leads.html', user=user, lead_lists=lists)


@app.route('/leads/<list_name>')
@login_required
def leads_detail(list_name):
    user = get_current_user()
    leads = lead_manager.get_list(list_name)
    return render_template('leads_detail.html', user=user, list_name=list_name, leads=leads)


# ==================== VERIFY ROUTES ====================

@app.route('/verify', methods=['GET', 'POST'])
@login_required
def verify_page():
    user = get_current_user()
    results = []

    if request.method == 'POST':
        emails_text = request.form.get('emails', '')
        emails = [e.strip() for e in emails_text.strip().split('\n') if e.strip()]
        if emails:
            results = verifier.verify_batch(emails)

    return render_template('verify.html', user=user, results=results)


# ==================== SEQUENCE ROUTES ====================

@app.route('/sequences', methods=['GET', 'POST'])
@login_required
def sequences_page():
    user = get_current_user()

    # Check plan
    if user.get('plan') == 'free':
        flash('Follow-up sequences are available on Pro plan', 'error')
        return redirect(url_for('pricing'))

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'create':
            name = request.form.get('name', '')
            subjects = request.form.getlist('subjects[]')
            bodies = request.form.getlist('bodies[]')
            delays = request.form.get('delays', '0,3,7')
            delay_days = [int(d.strip()) for d in delays.split(',')]

            emails = []
            for s, b in zip(subjects, bodies):
                if s.strip() and b.strip():
                    emails.append({'subject': s.strip(), 'body': b.strip()})

            if emails and name:
                result = sequences.create_sequence(name, emails, delay_days)
                flash(f'Sequence "{name}" created!', 'success')

        elif action == 'start':
            seq_name = request.form.get('sequence_name')
            list_name = request.form.get('list_name')

            if seq_name and list_name:
                leads = lead_manager.get_list(list_name)
                if leads:
                    result = sequences.start_sequence(seq_name, leads)
                    flash(f'Sequence started for {result["leads_count"]} leads!', 'success')

        return redirect(url_for('sequences_page'))

    seq_list = sequences.list_sequences()
    lead_lists = lead_manager.list_all()

    return render_template('sequences.html',
        user=user,
        sequences=seq_list,
        lead_lists=lead_lists,
        default_templates=DEFAULT_TEMPLATES,
    )


@app.route('/sequences/<seq_name>')
@login_required
def sequence_detail(seq_name):
    user = get_current_user()
    stats = sequences.get_stats(seq_name)
    pending = sequences.get_pending_sends(seq_name)

    return render_template('sequence_detail.html',
        user=user,
        sequence_name=seq_name,
        stats=stats,
        pending=pending,
    )


# ==================== PRICING & PAYMENT ROUTES ====================

@app.route('/pricing')
def pricing():
    user = get_current_user()
    return render_template('pricing.html', user=user, plans=PLANS)


@app.route('/subscribe/<plan>', methods=['POST'])
@login_required
def subscribe(plan):
    user = get_current_user()

    if plan not in PLANS or plan == 'free':
        flash('Invalid plan', 'error')
        return redirect(url_for('pricing'))

    # Create LemonSqueezy checkout
    variant_id = os.getenv(f'LEMONSQUEEZY_VARIANT_{plan.upper()}', '')
    if not variant_id:
        # Redirect to LemonSqueezy directly
        checkout_url = os.getenv(f'LEMONSQUEEZY_CHECKOUT_{plan.upper()}', '/pricing')
        return redirect(checkout_url)

    result = payment.create_checkout(
        variant_id=variant_id,
        email=user['email'],
        custom_data={'email': user['email'], 'plan': plan}
    )

    checkout_url = result.get('data', {}).get('attributes', {}).get('url')
    if checkout_url:
        return redirect(checkout_url)

    flash('Error creating checkout. Please try again.', 'error')
    return redirect(url_for('pricing'))


@app.route('/webhook/lemonsqueezy', methods=['POST'])
def webhook():
    """Handle LemonSqueezy webhooks."""
    payload = request.get_data()
    signature = request.headers.get('X-Signature', '')

    if not payment.verify_webhook(payload, signature):
        abort(401)

    data = request.get_json()
    result = payment.handle_webhook(data)

    return jsonify(result)


@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    user = get_current_user()

    if request.method == 'POST':
        updates = {
            'settings': {
                'smtp_host': request.form.get('smtp_host', ''),
                'smtp_port': int(request.form.get('smtp_port', 587)),
                'smtp_user': request.form.get('smtp_user', ''),
                'smtp_password': request.form.get('smtp_password', ''),
                'from_name': request.form.get('from_name', ''),
                'from_email': request.form.get('from_email', ''),
                'anthropic_api_key': request.form.get('anthropic_api_key', ''),
            }
        }
        user_manager.update_user(user['email'], updates)
        flash('Settings saved!', 'success')
        return redirect(url_for('settings'))

    return render_template('settings.html', user=user)


# ==================== API ROUTES ====================

@app.route('/api/scrape', methods=['POST'])
def api_scrape():
    url = request.json.get('url', '')
    if not url:
        return jsonify({'error': 'URL required'}), 400

    from src.scraper.lead_scraper import enrich_lead
    data = enrich_lead(url)
    return jsonify(data)


@app.route('/api/generate', methods=['POST'])
def api_generate():
    data = request.json
    eng = get_engine()

    result = eng.generator.generate_email(
        lead_data=data.get('lead', {}),
        product_description=data.get('product', ''),
        sender_name=data.get('sender_name', ''),
        sender_company=data.get('sender_company', ''),
        tone=data.get('tone', 'professional'),
    )
    return jsonify(result)


@app.route('/api/verify', methods=['POST'])
def api_verify():
    data = request.json
    emails = data.get('emails', [])

    if not emails:
        return jsonify({'error': 'No emails provided'}), 400

    results = verifier.verify_batch(emails)
    return jsonify(results)


# ==================== MAIN ====================

if __name__ == '__main__':
    port = int(os.getenv('DASHBOARD_PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
