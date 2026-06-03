"""
Cold Email Engine — Web Dashboard
Manage campaigns, view analytics, configure settings
"""
import os
import sys
import json
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.main import ColdEmailEngine, load_leads_csv
from src.leads.lead_manager import LeadManager
from src.verifier.email_verifier import EmailVerifier
from src.sequences.followup import FollowUpSequence, DEFAULT_TEMPLATES

app = Flask(__name__, template_folder='../dashboard/templates', static_folder='../dashboard/static')
app.secret_key = os.getenv('DASHBOARD_SECRET', 'dev-secret')

engine = None
lead_manager = LeadManager()
verifier = EmailVerifier()
sequences = FollowUpSequence()


def get_engine():
    global engine
    if engine is None:
        engine = ColdEmailEngine()
    return engine


@app.route('/')
def index():
    """Dashboard home — show campaigns."""
    campaigns_dir = Path(__file__).parent.parent / 'data' / 'campaigns'
    campaigns = []

    if campaigns_dir.exists():
        for d in sorted(campaigns_dir.iterdir(), reverse=True):
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

    # Get lead lists
    lead_lists = lead_manager.list_all()

    # Get sequences
    seq_list = sequences.list_sequences()

    return render_template('index.html',
        campaigns=campaigns,
        lead_lists=lead_lists,
        sequences=seq_list,
    )


@app.route('/campaign/new', methods=['GET', 'POST'])
def new_campaign():
    """Create new campaign."""
    if request.method == 'POST':
        leads_text = request.form.get('leads', '')
        product = request.form.get('product', '')
        sender_name = request.form.get('sender_name', '')
        sender_company = request.form.get('sender_company', '')
        tone = request.form.get('tone', 'professional')
        dry_run = 'dry_run' in request.form
        verify_emails = 'verify_emails' in request.form

        # Parse leads (one URL or email per line)
        leads = [l.strip() for l in leads_text.strip().split('\n') if l.strip()]

        # Verify emails if requested
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

        return render_template('result.html', result=result)

    return render_template('new_campaign.html')


@app.route('/leads', methods=['GET', 'POST'])
def leads_page():
    """Lead management page."""
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'import_csv':
            file = request.files.get('file')
            list_name = request.form.get('list_name', '')

            if file:
                # Save uploaded file temporarily
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
    return render_template('leads.html', lead_lists=lists)


@app.route('/leads/<list_name>')
def leads_detail(list_name):
    """View leads in a list."""
    leads = lead_manager.get_list(list_name)
    return render_template('leads_detail.html', list_name=list_name, leads=leads)


@app.route('/verify', methods=['GET', 'POST'])
def verify_page():
    """Email verification page."""
    results = []

    if request.method == 'POST':
        emails_text = request.form.get('emails', '')
        emails = [e.strip() for e in emails_text.strip().split('\n') if e.strip()]

        if emails:
            results = verifier.verify_batch(emails)

    return render_template('verify.html', results=results)


@app.route('/sequences', methods=['GET', 'POST'])
def sequences_page():
    """Follow-up sequences page."""
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
        sequences=seq_list,
        lead_lists=lead_lists,
        default_templates=DEFAULT_TEMPLATES,
    )


@app.route('/sequences/<seq_name>')
def sequence_detail(seq_name):
    """View sequence details and stats."""
    stats = sequences.get_stats(seq_name)
    pending = sequences.get_pending_sends(seq_name)

    return render_template('sequence_detail.html',
        sequence_name=seq_name,
        stats=stats,
        pending=pending,
    )


@app.route('/api/scrape', methods=['POST'])
def api_scrape():
    """API: Scrape a website."""
    url = request.json.get('url', '')
    if not url:
        return jsonify({'error': 'URL required'}), 400

    from src.scraper.lead_scraper import enrich_lead
    data = enrich_lead(url)
    return jsonify(data)


@app.route('/api/generate', methods=['POST'])
def api_generate():
    """API: Generate email for a lead."""
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
    """API: Verify email addresses."""
    data = request.json
    emails = data.get('emails', [])

    if not emails:
        return jsonify({'error': 'No emails provided'}), 400

    results = verifier.verify_batch(emails)
    return jsonify(results)


@app.route('/campaign/<campaign_id>')
def campaign_detail(campaign_id):
    """View campaign details."""
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
        campaign_id=campaign_id,
        generated=generated,
        send_log=send_log,
    )


if __name__ == '__main__':
    port = int(os.getenv('DASHBOARD_PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
