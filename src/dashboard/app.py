"""
Cold Email Engine — Web Dashboard
Manage campaigns, view analytics, configure settings
"""
import os
import sys
import json
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.main import ColdEmailEngine, load_leads_csv

app = Flask(__name__, template_folder='../dashboard/templates', static_folder='../dashboard/static')
app.secret_key = os.getenv('DASHBOARD_SECRET', 'dev-secret')

engine = None


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

    return render_template('index.html', campaigns=campaigns)


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

        # Parse leads (one URL or email per line)
        leads = [l.strip() for l in leads_text.strip().split('\n') if l.strip()]

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
