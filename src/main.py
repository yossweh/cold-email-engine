"""
Cold Email Engine — Main Pipeline
Scrape → Generate → Send → Track
"""
import json
import csv
import os
import sys
from pathlib import Path
from datetime import datetime

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.scraper.lead_scraper import LeadScraper
from src.generator.email_generator import EmailGenerator
from src.sender.email_sender import EmailSender


class ColdEmailEngine:
    """Main pipeline for cold email campaigns."""

    def __init__(self, config_path: str = None, smtp_config: dict = None):
        self.config = self._load_config(config_path)
        self.scraper = LeadScraper()
        self.generator = EmailGenerator(self.config['anthropic_api_key'])

        # Use custom SMTP config if provided, otherwise use platform defaults
        if smtp_config:
            smtp = smtp_config
        else:
            smtp = self.config

        self.sender = EmailSender(
            smtp_host=smtp.get('smtp_host', self.config['smtp_host']),
            smtp_port=int(smtp.get('smtp_port', self.config['smtp_port'])),
            smtp_user=smtp.get('smtp_user', self.config['smtp_user']),
            smtp_password=smtp.get('smtp_password', self.config['smtp_password']),
            from_name=smtp.get('from_name', self.config['from_name']),
            from_email=smtp.get('from_email', self.config['from_email']),
            max_per_hour=self.config.get('max_per_hour', 30),
            delay_seconds=self.config.get('delay_seconds', 60),
        )
        self.campaigns_dir = Path(__file__).parent.parent / 'data' / 'campaigns'
        self.campaigns_dir.mkdir(parents=True, exist_ok=True)

    def _load_config(self, config_path: str) -> dict:
        """Load config from env or file."""
        from dotenv import load_dotenv
        load_dotenv()

        return {
            'anthropic_api_key': os.getenv('ANTHROPIC_API_KEY', ''),
            'smtp_host': os.getenv('SMTP_HOST', 'smtp.gmail.com'),
            'smtp_port': int(os.getenv('SMTP_PORT', 587)),
            'smtp_user': os.getenv('SMTP_USER', ''),
            'smtp_password': os.getenv('SMTP_PASSWORD', ''),
            'from_name': os.getenv('SMTP_FROM_NAME', ''),
            'from_email': os.getenv('SMTP_FROM_EMAIL', ''),
            'max_per_hour': int(os.getenv('MAX_EMAILS_PER_HOUR', 30)),
            'delay_seconds': int(os.getenv('DELAY_BETWEEN_EMAILS_SEC', 60)),
        }

    def run_campaign(
        self,
        leads: list,
        product_description: str,
        sender_name: str,
        sender_company: str,
        tone: str = "professional",
        dry_run: bool = True
    ) -> dict:
        """Run full campaign pipeline."""

        campaign_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        campaign_dir = self.campaigns_dir / campaign_id
        campaign_dir.mkdir(parents=True, exist_ok=True)

        print(f"🚀 Campaign {campaign_id}")
        print(f"   Leads: {len(leads)}")
        print(f"   Mode: {'DRY RUN' if dry_run else 'LIVE'}")
        print()

        # Step 1: Scrape/Enrich leads
        print("📊 Step 1: Enriching leads...")
        enriched_leads = []
        for i, lead in enumerate(leads):
            if isinstance(lead, str):
                if '@' in lead:
                    # It's an email address
                    data = {'email': lead, 'title': lead.split('@')[1].split('.')[0].title()}
                    # Try to get company info from domain
                    domain = lead.split('@')[1]
                    if domain not in ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com']:
                        try:
                            scraped = self.scraper.scrape_company(f'https://{domain}')
                            data.update({k: v for k, v in scraped.items() if v})
                            if not data.get('title'):
                                data['title'] = domain.split('.')[0].title()
                        except:
                            pass
                else:
                    # It's a URL
                    data = self.scraper.scrape_company(lead)
                    data['email'] = data.get('contact_email', '')
            else:
                data = lead
                if 'url' in data and not data.get('description'):
                    scraped = self.scraper.scrape_company(data['url'])
                    data.update({k: v for k, v in scraped.items() if v})

            enriched_leads.append(data)
            print(f"   [{i+1}/{len(leads)}] {data.get('title', data.get('url', 'Unknown'))}")

        # Step 2: Generate emails
        print("\n✍️ Step 2: Generating emails...")
        generated = self.generator.generate_batch(
            leads=enriched_leads,
            product=product_description,
            sender_name=sender_name,
            sender_company=sender_company,
            tone=tone,
        )

        emails_to_send = []
        for i, gen in enumerate(generated):
            if 'error' in gen:
                print(f"   ❌ [{i+1}] Error: {gen['error']}")
                continue

            lead = gen.get('lead', {})
            to_email = lead.get('email', '')
            if not to_email:
                print(f"   ⚠️ [{i+1}] No email found for {lead.get('title', 'Unknown')}")
                continue

            emails_to_send.append({
                'to': to_email,
                'subject': gen['subject'],
                'body': gen['body'],
                'lead': lead,
                'personalization': gen.get('personalization_note', ''),
            })
            print(f"   ✅ [{i+1}] Generated for {to_email}")

        # Save generated emails
        with open(campaign_dir / 'generated.json', 'w') as f:
            json.dump(generated, f, indent=2)

        # Step 3: Send
        if dry_run:
            print(f"\n🧪 DRY RUN — {len(emails_to_send)} emails ready to send")
            print("   Set dry_run=False to actually send")

            # Preview first email
            if emails_to_send:
                preview = emails_to_send[0]
                print(f"\n📧 Preview:")
                print(f"   To: {preview['to']}")
                print(f"   Subject: {preview['subject']}")
                print(f"   Body:\n{preview['body'][:300]}...")

            return {
                'campaign_id': campaign_id,
                'mode': 'dry_run',
                'leads_enriched': len(enriched_leads),
                'emails_generated': len(generated),
                'emails_ready': len(emails_to_send),
                'campaign_dir': str(campaign_dir),
            }
        else:
            print(f"\n📤 Step 3: Sending {len(emails_to_send)} emails...")
            results = self.sender.send_batch(emails_to_send)
            self.sender.save_log(str(campaign_dir / 'send_log.json'))
            self.sender.export_log_csv(str(campaign_dir / 'send_log.csv'))

            sent = sum(1 for r in results if r['status'] == 'sent')
            failed = sum(1 for r in results if r['status'] == 'failed')

            return {
                'campaign_id': campaign_id,
                'mode': 'live',
                'leads_enriched': len(enriched_leads),
                'emails_generated': len(generated),
                'emails_sent': sent,
                'emails_failed': failed,
                'campaign_dir': str(campaign_dir),
            }


def load_leads_csv(filepath: str) -> list:
    """Load leads from CSV file."""
    leads = []
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            leads.append(dict(row))
    return leads


if __name__ == '__main__':
    # Example usage
    engine = ColdEmailEngine()

    sample_leads = [
        'https://example.com',
        {'url': 'https://example2.com', 'email': 'hi@example2.com'},
    ]

    result = engine.run_campaign(
        leads=sample_leads,
        product_description="We build AI chatbots that increase conversion by 40%",
        sender_name="John",
        sender_company="BotBuilder",
        dry_run=True,
    )

    print(f"\n📋 Result: {json.dumps(result, indent=2)}")
