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
- 🔐 **User Auth** — Register, login, sessions
- 💳 **Payments** — LemonSqueezy integration with license keys

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
```

## Architecture

```
cold-email-engine/
├── src/
│   ├── auth/            # User authentication
│   │   └── user_manager.py
│   ├── payments/        # LemonSqueezy integration
│   │   └── lemonsqueezy.py
│   ├── scraper/         # Lead enrichment
│   ├── generator/       # AI email writer
│   ├── sender/          # SMTP delivery
│   ├── verifier/        # Email verification
│   ├── leads/           # Lead management
│   ├── sequences/       # Follow-up sequences
│   ├── dashboard/       # Web UI
│   └── main.py          # CLI pipeline
├── data/
│   ├── campaigns/       # Campaign outputs
│   ├── leads/           # Saved lead lists
│   ├── sequences/       # Sequence tracking
│   ├── users/           # User data
│   └── orders/          # Payment orders
├── .env.example
└── requirements.txt
```

## Dashboard Pages

- `/login` — User login
- `/register` — New account
- `/dashboard` — Main dashboard
- `/campaign/new` — Create & run campaign
- `/leads` — Lead management (CSV import, manual entry, dedup)
- `/verify` — Email verification
- `/sequences` — Follow-up sequence management
- `/pricing` — Plan comparison & upgrade
- `/settings` — SMTP config, API keys

## Pricing Plans

| Plan | Price | Emails/Day | Features |
|------|-------|------------|----------|
| Free | $0 | 10 | Basic generation, CSV import, verification |
| Pro | $29/mo | 500 | + Sequences, API access, priority support |
| Enterprise | $99/mo | Unlimited | + White-label, custom integrations, SLA |

## LemonSqueezy Setup

1. Create account at [lemonsqueezy.com](https://lemonsqueezy.com)
2. Create products for Pro ($29) and Enterprise ($99)
3. Get API key from Settings > API
4. Set webhook URL: `https://yourdomain.com/webhook/lemonsqueezy`
5. Add to `.env`:
   ```
   LEMONSQUEEZY_API_KEY=your-key
   LEMONSQUEEZY_WEBHOOK_SECRET=your-secret
   LEMONSQUEEZY_STORE_ID=your-store
   LEMONSQUEEZY_VARIANT_PRO=variant-id
   LEMONSQUEEZY_VARIANT_ENTERPRISE=variant-id
   ```

## API Endpoints

- `POST /api/scrape` — Scrape website for lead data
- `POST /api/generate` — Generate personalized email
- `POST /api/verify` — Verify email addresses

## License

MIT
