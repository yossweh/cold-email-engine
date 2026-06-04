"""
Cold Email Engine — Main Dashboard App
All routes: auth, payments, campaigns, leads, verification, sequences
"""
import os
import sys
import json
from pathlib import Path
from datetime import datetime
from datetime import timedelta
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session, abort, Response

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.main import ColdEmailEngine, load_leads_csv
from src.leads.lead_manager import LeadManager
from src.verifier.email_verifier import EmailVerifier, filter_valid_emails
from src.sequences.followup import FollowUpSequence, DEFAULT_TEMPLATES
from src.auth.user_manager import UserManager, login_required, trial_required, get_current_user
from src.auth.oauth import generate_otp, verify_otp, send_otp_email, get_google_auth_url, exchange_google_code
from src.payments.lemonsqueezy import LemonSqueezy, PLANS
from src.payments.handler import payment_handler
from src.templates.email_templates import TEMPLATES as EMAIL_TEMPLATES, get_templates_by_category, get_categories, get_template_by_id

# Import blueprints
from src.dashboard.webhooks import webhook_bp
from src.dashboard.payments import payment_bp

app = Flask(__name__, template_folder='../dashboard/templates', static_folder='../dashboard/static')
app.secret_key = os.getenv('DASHBOARD_SECRET', 'dev-secret-change-me')

# Register blueprints
app.register_blueprint(webhook_bp)
app.register_blueprint(payment_bp)

engine = None
lead_manager = LeadManager()
verifier = EmailVerifier()
sequences = FollowUpSequence()
user_manager = UserManager()


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
            return redirect(url_for('login'))
        else:
            session['session_token'] = result['session_token']
            session['user'] = result['user']
            flash('Welcome back!', 'success')
            return redirect(url_for('dashboard'))

    return render_template('login.html')


# ==================== OTP ROUTES ====================

@app.route('/send-otp', methods=['POST'])
def send_otp():
    """Send OTP to email for registration verification"""
    data = request.get_json() if request.is_json else request.form
    email = data.get('email', '').strip().lower()
    
    if not email:
        return jsonify({'error': 'Email required'}), 400
    
    # Generate and send OTP
    code = generate_otp(email)
    sent = send_otp_email(email, code)
    
    if sent:
        return jsonify({'success': True, 'message': 'OTP sent to your email'})
    else:
        return jsonify({'error': 'Failed to send OTP'}), 500


@app.route('/verify-otp', methods=['POST'])
def verify_otp_route():
    """Verify OTP code"""
    data = request.get_json() if request.is_json else request.form
    email = data.get('email', '').strip().lower()
    code = data.get('code', '').strip()
    
    if not email or not code:
        return jsonify({'error': 'Email and code required'}), 400
    
    if verify_otp(email, code):
        session['otp_verified'] = email
        return jsonify({'success': True, 'message': 'Email verified'})
    else:
        return jsonify({'error': 'Invalid or expired code'}), 400


@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Reset password via OTP"""
    if request.method == 'POST':
        step = request.form.get('step', 'email')
        
        if step == 'email':
            email = request.form.get('email', '').strip().lower()
            if not email:
                flash('Email required', 'error')
                return render_template('forgot_password.html')
            
            # Check if user exists
            user = user_manager.get_user(email)
            if not user:
                flash('Email not found', 'error')
                return render_template('forgot_password.html')
            
            # Send OTP
            code = generate_otp(email)
            sent = send_otp_email(email, code)
            if sent:
                session['reset_email'] = email
                return render_template('forgot_password.html', step='otp', email=email)
            else:
                flash('Failed to send code', 'error')
                return render_template('forgot_password.html')
        
        elif step == 'otp':
            email = session.get('reset_email', '')
            code = request.form.get('code', '').strip()
            
            if verify_otp(email, code):
                session['reset_verified'] = True
                return render_template('forgot_password.html', step='password', email=email)
            else:
                flash('Invalid or expired code', 'error')
                return render_template('forgot_password.html', step='otp', email=email)
        
        elif step == 'password':
            email = session.get('reset_email', '')
            password = request.form.get('password', '')
            confirm = request.form.get('confirm', '')
            
            if not session.get('reset_verified'):
                flash('Please verify your email first', 'error')
                return redirect(url_for('forgot_password'))
            
            if password != confirm:
                flash('Passwords do not match', 'error')
                return render_template('forgot_password.html', step='password', email=email)
            
            if len(password) < 8:
                flash('Password must be at least 8 characters', 'error')
                return render_template('forgot_password.html', step='password', email=email)
            
            # Update password
            import hashlib, secrets
            salt = secrets.token_hex(16)
            hashed = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000).hex()
            
            user_path = user_manager.users_dir / f'{email.lower().replace("@", "_at_")}.json'
            with open(user_path) as f:
                user = json.load(f)
            
            user['password_hash'] = hashed
            user['salt'] = salt
            
            with open(user_path, 'w') as f:
                json.dump(user, f, indent=2)
            
            # Invalidate all existing sessions for this user
            user_manager.invalidate_all_sessions(email)
            
            session.pop('reset_email', None)
            session.pop('reset_verified', None)
            flash('Password updated! Please login.', 'success')
            return redirect(url_for('login'))
    
    return render_template('forgot_password.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name', '')
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm', '')

        # Check OTP verification
        if session.get('otp_verified') != email:
            flash('Please verify your email first', 'error')
            return render_template('register.html', email=email, name=name)

        if password != confirm:
            flash('Passwords do not match', 'error')
        elif len(password) < 8:
            flash('Password must be at least 8 characters', 'error')
        else:
            result = user_manager.register(email, password, name)
            if result.get('error'):
                flash(result['error'], 'error')
            else:
                session.pop('otp_verified', None)
                # Auto login after register
                login_result = user_manager.login(email, password)
                if login_result.get('success'):
                    session['session_token'] = login_result['session_token']
                    session['user'] = login_result['user']
                flash('Account created! Start your free trial.', 'success')
                return redirect(url_for('start_trial'))

    return render_template('register.html')


# ==================== GOOGLE OAUTH ROUTES ====================

@app.route('/auth/google')
def google_auth():
    """Redirect to Google OAuth"""
    auth_url = get_google_auth_url()
    if auth_url:
        return redirect(auth_url)
    else:
        flash('Google login not configured', 'error')
        return redirect(url_for('login'))


@app.route('/auth/google/callback')
def google_callback():
    """Handle Google OAuth callback"""
    code = request.args.get('code')
    if not code:
        flash('Google authentication failed', 'error')
        return redirect(url_for('login'))
    
    # Exchange code for user info
    google_user = exchange_google_code(code)
    if not google_user or not google_user.get('email'):
        flash('Failed to get Google account info', 'error')
        return redirect(url_for('login'))
    
    email = google_user['email']
    name = google_user.get('name', email.split('@')[0])
    
    # Check if user exists
    existing_user = user_manager.get_user(email)
    
    if existing_user:
        # Login existing user
        session_token = user_manager.create_session(email)
        session['session_token'] = session_token
        session['user'] = existing_user
        flash('Welcome back!', 'success')
    else:
        # Create new user with random password
        import secrets
        random_password = secrets.token_urlsafe(16)
        result = user_manager.register(email, random_password, name)
        
        if result.get('error'):
            flash(result['error'], 'error')
            return redirect(url_for('login'))
        
        # Auto login
        session_token = user_manager.create_session(email)
        new_user = user_manager.get_user(email)
        session['session_token'] = session_token
        session['user'] = {
            'email': new_user['email'],
            'name': new_user['name'],
            'plan': new_user['plan'],
        }
        flash('Account created with Google! Start your free trial.', 'success')
        return redirect(url_for('start_trial'))
    
    return redirect(url_for('dashboard'))


@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out', 'success')
    return redirect(url_for('index'))


# ==================== MAIN ROUTES ====================

@app.route('/')
def index():
    """Landing page for visitors, dashboard for authenticated users."""
    user = get_current_user()
    if user:
        return redirect(url_for('dashboard'))
    return render_template('landing.html')


@app.route('/start-trial')
@login_required
def start_trial():
    """Show start trial page with card requirement."""
    user = get_current_user()
    
    # If user already has trial or pro, redirect to dashboard
    if user.get('plan') in ['pro', 'enterprise']:
        return redirect(url_for('dashboard'))
    
    if user.get('trial_expires'):
        from datetime import datetime
        if datetime.fromisoformat(user['trial_expires']) > datetime.now():
            return redirect(url_for('dashboard'))
    
    # LemonSqueezy checkout via API (if ready)
    lemonsqueezy_ready = os.getenv('LEMONSQUEEZY_READY', 'false').lower() == 'true'
    checkout_url = None
    
    if lemonsqueezy_ready:
        import requests as req
        api_key = os.getenv('LEMONSQUEEZY_API_KEY', '')
        store_id = os.getenv('LEMONSQUEEZY_STORE_ID', '')
        variant_id = os.getenv('LEMONSQUEEZY_VARIANT_PRO', '')
        if api_key and store_id and variant_id:
            try:
                resp = req.post('https://api.lemonsqueezy.com/v1/checkouts',
                    headers={'Authorization': f'Bearer {api_key}', 'Accept': 'application/vnd.api+json', 'Content-Type': 'application/vnd.api+json'},
                    json={'data': {'type': 'checkouts', 'attributes': {'checkout_data': {'email': user['email']}}, 'relationships': {'store': {'data': {'type': 'stores', 'id': store_id}}, 'variant': {'data': {'type': 'variants', 'id': variant_id}}}}},
                    timeout=10
                )
                if resp.status_code == 201:
                    checkout_url = resp.json()['data']['attributes']['url']
            except Exception:
                pass
    
    return render_template('start_trial.html', checkout_url=checkout_url, 
                          lemonsqueezy_ready=lemonsqueezy_ready)


@app.route('/activate-trial', methods=['POST'])
@login_required
def activate_trial():
    """Activate free trial directly (temporary until LemonSqueezy is ready)."""
    from src.auth.user_manager import UserManager
    user = get_current_user()
    
    # Check if already has pro/enterprise plan
    if user.get('plan') in ['pro', 'enterprise']:
        flash('You already have an active plan', 'info')
        return redirect(url_for('dashboard'))
    
    if user.get('trial_expires'):
        from datetime import datetime
        if datetime.fromisoformat(user['trial_expires']) > datetime.now():
            flash('You already have an active trial', 'info')
            return redirect(url_for('dashboard'))
    
    # Activate 7-day trial (keep plan as 'free', just set trial_expires)
    from datetime import datetime, timedelta
    trial_expires = (datetime.now() + timedelta(days=7)).isoformat()
    
    um = UserManager()
    um.update_user(user['email'], {
        'plan': 'free',
        'trial_expires': trial_expires,
        'usage': {
            'emails_limit': 500,
            'emails_sent': user.get('usage', {}).get('emails_sent', 0),
            'last_reset': datetime.now().isoformat(),
        }
    })
    
    flash('🎉 Free trial activated! 7 days of Pro features.', 'success')
    return redirect(url_for('dashboard'))


@app.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard."""
    user = get_current_user()

    # Redirect new users to onboarding if not completed
    if not user.get('onboarding_completed'):
        return redirect(url_for('onboarding'))

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

    trial = user_manager.check_trial(user['email'])

    return render_template('index.html',
        user=user,
        campaigns=campaigns,
        lead_lists=lead_lists,
        sequences=seq_list,
        usage=usage,
        trial=trial,
    )


# ==================== CAMPAIGN ROUTES ====================

@app.route('/campaign/new', methods=['GET', 'POST'])
@login_required
@trial_required
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
                valid, rejected = filter_valid_emails(emails)
                leads = [l for l in leads if '@' not in l] + valid

        # Require user SMTP settings — no platform fallback
        user_settings = user.get('settings', {}) or {}
        if not user_settings.get('smtp_host') or not user_settings.get('smtp_user') or not user_settings.get('smtp_password'):
            flash('⚠️ Please configure your SMTP settings first before sending campaigns.', 'error')
            return redirect(url_for('profile'))

        user_smtp = {
            'smtp_host': user_settings['smtp_host'],
            'smtp_port': user_settings.get('smtp_port', 587),
            'smtp_user': user_settings['smtp_user'],
            'smtp_password': user_settings['smtp_password'],
            'from_name': user_settings.get('from_name', sender_name),
            'from_email': user_settings.get('from_email', user.get('email', '')),
        }

        from src.main import ColdEmailEngine
        eng = ColdEmailEngine(smtp_config=user_smtp)

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
        # Log activity
        mode_str = 'DRY RUN' if dry_run else 'LIVE'
        sent_count = result.get('emails_sent', result.get('emails_ready', 0))
        log_activity(user['email'], 'campaign', f'Campaign run ({mode_str})', f'{sent_count} emails processed')

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
@trial_required
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
                    log_activity(user['email'], 'leads', 'Imported leads via CSV', f'{result["total_imported"]} leads in "{list_name or "default"}"')
        elif action == 'import_manual':
            entries_text = request.form.get('entries', '')
            list_name = request.form.get('list_name', 'manual')
            entries = [e.strip() for e in entries_text.strip().split('\n') if e.strip()]
            result = lead_manager.import_manual(entries, list_name)
            flash(f'Imported {result["total_imported"]} leads!', 'success')
            log_activity(user['email'], 'leads', 'Imported leads manually', f'{result["total_imported"]} leads in "{list_name}"')
        elif action == 'deduplicate':
            list_name = request.form.get('list_name')
            if list_name:
                result = lead_manager.deduplicate(list_name)
                flash(f'Removed {result["removed"]} duplicates!', 'success')
                log_activity(user['email'], 'leads', 'Deduplicated leads', f'{result["removed"]} removed from "{list_name}"')

        return redirect(url_for('leads_page'))

    lists = lead_manager.list_all()
    return render_template('leads.html', user=user, lead_lists=lists)


@app.route('/leads/<list_name>')
@login_required
@trial_required
def leads_detail(list_name):
    user = get_current_user()
    leads = lead_manager.get_list(list_name)
    return render_template('leads_detail.html', user=user, list_name=list_name, leads=leads)


# ==================== VERIFY ROUTES ====================

@app.route('/verify', methods=['GET', 'POST'])
@login_required
@trial_required
def verify_page():
    user = get_current_user()
    results = []

    if request.method == 'POST':
        emails_text = request.form.get('emails', '')
        emails = [e.strip() for e in emails_text.strip().split('\n') if e.strip()]
        if emails:
            results = verifier.verify_batch(emails)
            log_activity(user['email'], 'verify', 'Verified emails', f'{len(emails)} emails checked')

    return render_template('verify.html', user=user, results=results)


# ==================== SEQUENCE ROUTES ====================

@app.route('/sequences', methods=['GET', 'POST'])
@login_required
@trial_required
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


# ==================== PRICING & SETTINGS ====================

@app.route('/pricing')
@login_required
def pricing():
    user = get_current_user()
    return render_template('pricing.html', user=user, plans=PLANS)


@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    user = get_current_user()

    if request.method == 'POST':
        updates = {
            'name': request.form.get('name', user.get('name', '')),
            'company': request.form.get('company', user.get('company', '')),
            'timezone': request.form.get('timezone', user.get('timezone', 'Asia/Jakarta')),
            'website': request.form.get('website', user.get('website', '')),
        }
        user_manager.update_user(user['email'], updates)
        flash('Profile updated!', 'success')
        return redirect(url_for('profile'))

    # Calculate stats
    usage = user.get('usage', {})
    emails_sent = usage.get('emails_sent', 0)
    emails_limit = usage.get('emails_limit', 10)

    # Count campaigns
    campaigns_dir = Path(__file__).parent.parent / 'data' / 'campaigns'
    campaigns_count = len(list(campaigns_dir.iterdir())) if campaigns_dir.exists() else 0

    # Count leads
    leads_dir = Path(__file__).parent.parent / 'data' / 'leads'
    leads_count = 0
    if leads_dir.exists():
        for f in leads_dir.glob('*.json'):
            try:
                import json
                data = json.load(open(f))
                leads_count += len(data) if isinstance(data, list) else 1
            except:
                pass

    stats = {
        'emails_sent': emails_sent,
        'emails_limit': emails_limit,
        'campaigns': campaigns_count,
        'leads': leads_count,
    }

    return render_template('profile.html', user=user, stats=stats)


@app.route('/profile/smtp', methods=['POST'])
@login_required
def profile_smtp():
    user = get_current_user()
    updates = {
        'settings': {
            'from_name': request.form.get('from_name', ''),
            'from_email': request.form.get('from_email', ''),
            'smtp_host': request.form.get('smtp_host', ''),
            'smtp_port': int(request.form.get('smtp_port', 587)),
            'smtp_user': request.form.get('smtp_user', ''),
            'smtp_password': request.form.get('smtp_password', ''),
        }
    }
    user_manager.update_user(user['email'], updates)
    flash('SMTP settings saved!', 'success')
    log_activity(user['email'], 'settings', 'Updated SMTP settings', f'Host: {request.form.get("smtp_host", "N/A")}')
    return redirect(url_for('profile'))


@app.route('/settings', methods=['GET', 'POST'])
@login_required
@trial_required
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
        log_activity(user['email'], 'settings', 'Updated settings', 'SMTP and API configuration saved')
        return redirect(url_for('settings'))

    return render_template('settings.html', user=user)


# ==================== API ROUTES ====================

@app.route('/api/scrape', methods=['POST'])
@login_required
def api_scrape():
    url = request.json.get('url', '')
    if not url:
        return jsonify({'error': 'URL required'}), 400

    from src.scraper.lead_scraper import enrich_lead
    data = enrich_lead(url)
    return jsonify(data)


@app.route('/api/generate', methods=['POST'])
@login_required
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
@login_required
def api_verify():
    data = request.json
    emails = data.get('emails', [])

    if not emails:
        return jsonify({'error': 'No emails provided'}), 400

    results = verifier.verify_batch(emails)
    return jsonify(results)




# ==================== SCRAPE ROUTES ====================

@app.route('/scrape', methods=['GET', 'POST'])
@login_required
@trial_required
def scrape_page():
    user = get_current_user()
    results = []
    urls_text = ''

    if request.method == 'POST':
        urls_text = request.form.get('urls', '')
        action = request.form.get('action', 'scrape')
        urls = [u.strip() for u in urls_text.strip().split('\n') if u.strip()]
        
        if urls:
            from src.scraper.lead_scraper import LeadScraper
            scraper = LeadScraper()
            
            for url in urls:
                if not url.startswith('http'):
                    url = 'https://' + url
                data = scraper.scrape_company(url)
                results.append(data)

            # Save to leads if requested
            if action in ('save_to_leads', 'scrape_and_save'):
                successful = [r for r in results if 'error' not in r]
                if successful:
                    entries = []
                    for r in successful:
                        email = r.get('contact_email', '')
                        if email:
                            entries.append(email)
                        else:
                            entries.append(r.get('url', ''))
                    if entries:
                        result = lead_manager.import_manual(entries, 'scraped_' + datetime.now().strftime('%Y%m%d_%H%M'))
                        flash(f'Saved {result["total_imported"]} leads!', 'success')
                        return redirect(url_for('leads_page'))
                    else:
                        flash('No leads to save (no emails found)', 'error')

    return render_template('scrape.html', user=user, results=results, urls_text=urls_text)

# ==================== ACTIVITY LOG ====================

def _activity_dir():
    d = Path(__file__).parent.parent / 'data' / 'activity'
    d.mkdir(parents=True, exist_ok=True)
    return d

def _activity_file(email):
    safe = email.lower().replace('@', '_at_').replace('.', '_')
    return _activity_dir() / f'{safe}.json'

def log_activity(email, action_type, description, detail=''):
    """Log a user action. action_type: campaign|email|leads|verify|settings"""
    entry = {
        'type': action_type,
        'description': description,
        'detail': detail,
        'timestamp': datetime.now().isoformat(),
    }
    fp = _activity_file(email)
    activities = []
    if fp.exists():
        try:
            with open(fp) as f:
                activities = json.load(f)
        except Exception:
            pass
    activities.insert(0, entry)
    activities = activities[:500]  # keep last 500
    with open(fp, 'w') as f:
        json.dump(activities, f, indent=2)

def get_activities(email, filter_type=None, limit=100):
    fp = _activity_file(email)
    if not fp.exists():
        return []
    with open(fp) as f:
        activities = json.load(f)
    if filter_type:
        activities = [a for a in activities if a.get('type') == filter_type]
    return activities[:limit]

ACTIVITY_ICONS = {
    'campaign': '🚀',
    'email': '📧',
    'leads': '📋',
    'verify': '✅',
    'settings': '⚙️',
}

def _time_ago(iso_str):
    try:
        dt = datetime.fromisoformat(iso_str)
        diff = datetime.now() - dt
        seconds = int(diff.total_seconds())
        if seconds < 60:
            return 'just now'
        elif seconds < 3600:
            m = seconds // 60
            return f'{m}m ago'
        elif seconds < 86400:
            h = seconds // 3600
            return f'{h}h ago'
        else:
            d = seconds // 86400
            return f'{d}d ago'
    except Exception:
        return ''


# ==================== ANALYTICS ROUTES ====================

@app.route('/analytics')
@login_required
def analytics():
    user = get_current_user()
    campaigns_dir = Path(__file__).parent.parent / 'data' / 'campaigns'

    # Aggregate data from all campaigns
    total_emails = 0
    total_sent = 0
    total_failed = 0
    total_campaigns = 0
    daily_counts = {}  # date_str -> count
    status_counts = {'Sent': 0, 'Failed': 0}

    if campaigns_dir.exists():
        for d in campaigns_dir.iterdir():
            if d.is_dir():
                total_campaigns += 1
                send_log_path = d / 'send_log.json'
                if send_log_path.exists():
                    try:
                        with open(send_log_path) as f:
                            logs = json.load(f)
                        for entry in logs:
                            total_emails += 1
                            if entry.get('status') == 'sent':
                                total_sent += 1
                                status_counts['Sent'] += 1
                            else:
                                total_failed += 1
                                status_counts['Failed'] += 1
                            ts = entry.get('timestamp', '')
                            if ts:
                                try:
                                    day = datetime.fromisoformat(ts).strftime('%Y-%m-%d')
                                    daily_counts[day] = daily_counts.get(day, 0) + 1
                                except Exception:
                                    pass
                    except Exception:
                        pass

    # Build last 30 days labels and data
    today = datetime.now().date()
    daily_labels = []
    daily_data = []
    for i in range(29, -1, -1):
        day = today - timedelta(days=i)
        day_str = day.strftime('%Y-%m-%d')
        daily_labels.append(day.strftime('%b %d'))
        daily_data.append(daily_counts.get(day_str, 0))

    # Success rate
    success_rate = round((total_sent / total_emails * 100), 1) if total_emails > 0 else 0

    # Avg per day (over active days, or 30)
    days_with_data = len([v for v in daily_counts.values() if v > 0]) or 1
    active_days = max(1, min(30, days_with_data))
    avg_per_day = round(sum(daily_data) / active_days, 1)

    # Status chart (only include non-zero)
    status_labels = [k for k, v in status_counts.items() if v > 0] or ['No Data']
    status_data = [v for v in status_counts.values() if v > 0] or [1]

    # Recent activity (latest 10)
    raw_activities = get_activities(user['email'], limit=10)
    recent_activity = []
    for a in raw_activities:
        recent_activity.append({
            'icon': ACTIVITY_ICONS.get(a.get('type', ''), '📌'),
            'description': a.get('description', ''),
            'time_ago': _time_ago(a.get('timestamp', '')),
        })

    return render_template('analytics.html',
        user=user,
        total_emails=total_emails,
        total_campaigns=total_campaigns,
        avg_per_day=avg_per_day,
        success_rate=success_rate,
        daily_labels=daily_labels,
        daily_data=daily_data,
        status_labels=status_labels,
        status_data=status_data,
        recent_activity=recent_activity,
    )


@app.route('/activity')
@login_required
def activity():
    user = get_current_user()
    filter_type = request.args.get('type')

    raw = get_activities(user['email'], filter_type=filter_type)
    activities = []
    for a in raw:
        activities.append({
            'type': a.get('type', 'settings'),
            'icon': ACTIVITY_ICONS.get(a.get('type', ''), '📌'),
            'description': a.get('description', ''),
            'detail': a.get('detail', ''),
            'time_ago': _time_ago(a.get('timestamp', '')),
        })

    return render_template('activity.html',
        user=user,
        activities=activities,
        filter_type=filter_type,
    )


# ==================== TEMPLATE LIBRARY ROUTES ====================

@app.route('/templates')
@login_required
def template_library():
    """Display the email template library."""
    user = get_current_user()
    templates_by_cat = get_templates_by_category()
    categories = get_categories()
    import json
    templates_json = json.dumps(EMAIL_TEMPLATES)
    return render_template('template_library.html',
        user=user,
        templates_by_category=templates_by_cat,
        categories=categories,
        templates_json=templates_json,
    )


@app.route('/api/templates/<template_id>')
@login_required
def get_template(template_id):
    """API endpoint to get a single template by ID."""
    tpl = get_template_by_id(template_id)
    if tpl:
        return jsonify(tpl)
    return jsonify({'error': 'Template not found'}), 404


# ==================== MAIN ====================


# ==================== ONBOARDING ROUTES ====================

@app.route('/onboarding', methods=['GET', 'POST'])
@login_required
def onboarding():
    """Onboarding wizard for new users."""
    user = get_current_user()

    if request.method == 'POST':
        step_completed = request.form.get('step_completed', '4')

        # Build updates dict from form data
        updates = {}

        # Step 1: Profile
        display_name = request.form.get('display_name', '').strip()
        company_name = request.form.get('company_name', '').strip()
        user_type = request.form.get('user_type', '')
        if display_name:
            updates['name'] = display_name
        if company_name:
            updates['company'] = company_name
        if user_type:
            updates['user_type'] = user_type

        # Step 2: SMTP
        smtp_host = request.form.get('smtp_host', '').strip()
        smtp_port = int(request.form.get('smtp_port', 587))
        smtp_user = request.form.get('smtp_user', '').strip()
        smtp_password = request.form.get('smtp_password', '').strip()
        from_name_onb = request.form.get('from_name', '').strip()
        from_email_onb = request.form.get('from_email', '').strip()
        if smtp_host or smtp_user:
            updates['settings'] = updates.get('settings', {})
            updates['settings'].update({
                'smtp_host': smtp_host,
                'smtp_port': smtp_port,
                'smtp_user': smtp_user,
                'smtp_password': smtp_password,
                'from_name': from_name_onb or display_name or user.get('name', ''),
                'from_email': from_email_onb or user.get('email', ''),
            })

        # Step 3: CSV import
        leads_option = request.form.get('leads_option', 'skip')
        if leads_option == 'upload':
            csv_file = request.files.get('csv_file')
            if csv_file and csv_file.filename:
                temp_path = Path('/tmp') / csv_file.filename
                csv_file.save(str(temp_path))
                result = lead_manager.import_csv(str(temp_path))
                temp_path.unlink()
                if result.get('total_imported', 0) > 0:
                    flash(f'Imported {result["total_imported"]} leads!', 'success')

        # Step 4: Campaign (optional)
        if step_completed != 'skip_campaign':
            campaign_name = request.form.get('campaign_name', '').strip()
            product_desc = request.form.get('product_description', '').strip()
            if campaign_name and product_desc:
                updates['onboarding_campaign'] = {
                    'name': campaign_name,
                    'product_description': product_desc,
                }

        # Mark onboarding as completed
        updates['onboarding_completed'] = True
        updates['onboarding_completed_at'] = datetime.now().isoformat()

        user_manager.update_user(user['email'], updates)

        # Update session user data
        if 'name' in updates:
            session['user']['name'] = updates['name']

        # If they created a campaign, redirect to new campaign page
        if updates.get('onboarding_campaign'):
            flash('Account set up! Your campaign is ready to configure.', 'success')
            return redirect(url_for('new_campaign'))

        flash('Welcome aboard! Your account is all set up.', 'success')
        return redirect(url_for('dashboard'))

    return render_template('onboarding.html', user=user)


# ==================== ERROR HANDLERS ====================

@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500


# ==================== CSV EXPORT ROUTES ====================

@app.route('/api/export/leads/<list_name>')
@login_required
def export_leads_csv(list_name):
    """Export a lead list as CSV."""
    import csv
    import io
    leads = lead_manager.get_list(list_name)
    if not leads:
        abort(404)

    output = io.StringIO()
    writer = csv.writer(output)
    # Header
    writer.writerow(['email', 'name', 'company', 'website', 'title'])
    for lead in leads:
        writer.writerow([
            lead.get('email', ''),
            lead.get('name', ''),
            lead.get('company', ''),
            lead.get('website', ''),
            lead.get('title', ''),
        ])

    csv_content = output.getvalue()
    return Response(
        csv_content,
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename={list_name}.csv'}
    )


@app.route('/api/export/campaign/<campaign_id>')
@login_required
def export_campaign_csv(campaign_id):
    """Export a campaign send log as CSV."""
    import csv
    import io
    campaign_dir = Path(__file__).parent.parent / 'data' / 'campaigns' / campaign_id

    if not campaign_dir.exists():
        abort(404)

    send_log = []
    log_file = campaign_dir / 'send_log.json'
    if log_file.exists():
        with open(log_file) as f:
            send_log = json.load(f)

    if not send_log:
        abort(404)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['to', 'subject', 'status', 'timestamp'])
    for entry in send_log:
        writer.writerow([
            entry.get('to', ''),
            entry.get('subject', ''),
            entry.get('status', ''),
            entry.get('timestamp', ''),
        ])

    csv_content = output.getvalue()
    return Response(
        csv_content,
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename=campaign_{campaign_id}.csv'}
    )


if __name__ == '__main__':
    port = int(os.getenv('DASHBOARD_PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
