# 📧 Cold Email Engine

AI-powered cold email automation — scrape leads, generate personalized emails with Claude, send via SMTP.

## Features

- 🕷️ **Lead Scraping** — Auto-extract company info from websites
- 🤖 **AI Generation** — Claude-powered personalized email writing
- 📤 **SMTP Sending** — Rate-limited email delivery
- 📊 **Dashboard** — Web UI for campaign management
- 🧪 **Dry Run** — Preview before sending
- 📋 **CSV Import** — Import leads from spreadsheets
- 📧 **Email Verification** — Check email validity (syntax, domain, MX, disposable)
- 🔄 **Follow-up Sequences** — Multi-step auto follow-ups with delays

## Quick Start

```bash
# Install
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your API keys

# Run dashboard
python src/dashboard/app.py

# Or run CLI
python src/main.py
```

## Architecture

```
cold-email-engine/
├── src/
│   ├── scraper/         # Lead enrichment
│   │   └── lead_scraper.py
│   ├── generator/       # AI email writer
│   │   └── email_generator.py
│   ├── sender/          # SMTP delivery
│   │   └── email_sender.py
│   ├── verifier/        # Email verification
│   │   └── email_verifier.py
│   ├── leads/           # Lead management
│   │   └── lead_manager.py
│   ├── sequences/       # Follow-up sequences
│   │   └── followup.py
│   ├── dashboard/       # Web UI
│   │   ├── app.py
│   │   ├── templates/
│   │   └── static/
│   └── main.py          # CLI pipeline
├── data/
│   ├── campaigns/       # Campaign outputs
│   ├── leads/           # Saved lead lists
│   └── sequences/       # Sequence tracking
├── .env.example
└── requirements.txt
```

## Dashboard Pages

- `/` — Dashboard home (campaigns, lead lists, sequences)
- `/campaign/new` — Create & run campaign
- `/leads` — Lead management (CSV import, manual entry, dedup)
- `/verify` — Email verification
- `/sequences` — Follow-up sequence management
- `/campaign/<id>` — Campaign details
- `/leads/<name>` — View leads in list
- `/sequences/<name>` — Sequence stats & pending sends

## API Endpoints

- `POST /api/scrape` — Scrape website for lead data
- `POST /api/generate` — Generate personalized email
- `POST /api/verify` — Verify email addresses

## Email Verification

Checks performed:
1. **Syntax** — RFC-compliant email format
2. **Domain** — Domain exists and resolves
3. **MX Records** — Mail server configured
4. **Disposable** — Temporary email detection
5. **Role-based** — info@, support@ detection

## Follow-up Sequences

- Create multi-step sequences with custom delays
- Personalization with `{{name}}`, `{{company}}` placeholders
- Auto-stop on reply
- Track sent, replied, bounced, completed

## Monetization

- Free tier: 10 emails/day
- Pro ($29/mo): 500 emails/day + sequences + verification
- Enterprise ($99/mo): Unlimited + API + custom templates

## License

MIT
