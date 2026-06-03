# 📧 Cold Email Engine

AI-powered cold email automation — scrape leads, generate personalized emails with Claude, send via SMTP.

## Features

- 🕷️ **Lead Scraping** — Auto-extract company info from websites
- 🤖 **AI Generation** — Claude-powered personalized email writing
- 📤 **SMTP Sending** — Rate-limited email delivery
- 📊 **Dashboard** — Web UI for campaign management
- 🧪 **Dry Run** — Preview before sending

## Quick Start

```bash
# Install
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
│   ├── dashboard/       # Web UI
│   │   ├── app.py
│   │   ├── templates/
│   │   └── static/
│   └── main.py          # CLI pipeline
├── data/
│   └── campaigns/       # Campaign outputs
├── templates/           # Email templates
├── config/
├── .env.example
└── requirements.txt
```

## API Endpoints

- `GET /` — Dashboard
- `GET /campaign/new` — New campaign form
- `POST /campaign/new` — Run campaign
- `GET /campaign/<id>` — Campaign details
- `POST /api/scrape` — Scrape website
- `POST /api/generate` — Generate email

## Usage

### CLI
```python
from src.main import ColdEmailEngine

engine = ColdEmailEngine()

result = engine.run_campaign(
    leads=['https://company.com'],
    product_description="We build AI chatbots",
    sender_name="John",
    sender_company="BotBuilder",
    dry_run=True,
)
```

### API
```bash
# Scrape
curl -X POST http://localhost:5000/api/scrape \
  -H "Content-Type: application/json" \
  -d '{"url": "https://company.com"}'

# Generate
curl -X POST http://localhost:5000/api/generate \
  -H "Content-Type: application/json" \
  -d '{"lead": {...}, "product": "...", "sender_name": "...", "sender_company": "..."}'
```

## Monetization

- Free tier: 10 emails/day
- Pro ($29/mo): 500 emails/day + analytics
- Enterprise ($99/mo): Unlimited + API access + custom templates

## License

MIT
