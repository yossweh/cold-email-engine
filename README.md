# 🖤 Obsidian — AI Cold Email Engine

**By Obsidian Labs**

AI-powered cold email automation — scrape leads, generate personalized emails with Claude, send via SMTP, auto follow-ups.

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
- 💳 **Payments** — LemonSqueezy (USD) + Midtrans (IDR)

## Quick Start

```bash
# Install
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your API keys

# Run
python src/dashboard/app.py
```

## Architecture

```
obsidian/
├── src/
│   ├── auth/            # User authentication
│   ├── payments/        # LemonSqueezy + Midtrans
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

## Pricing

| Plan | USD | IDR | Emails/Day |
|------|-----|-----|------------|
| Free | $0 | Gratis | 10 |
| Pro | $29/bln | Rp 450rb/bln | 500 |
| Enterprise | $99/bln | Rp 1.5jt/bln | Unlimited |

## Payment Flow

```
Customer bayar → Webhook → Auto-activate → Langsung Pro
```

- **International:** LemonSqueezy (Visa, Mastercard, PayPal)
- **Indonesia:** Midtrans (QRIS, GoPay, OVO, VA Bank)

## Dashboard

- `/login` — Login
- `/register` — Register
- `/dashboard` — Main dashboard
- `/campaign/new` — Create campaign
- `/leads` — Lead management
- `/verify` — Email verification
- `/sequences` — Follow-up sequences
- `/pricing` — Plans & upgrade
- `/settings` — SMTP & API config

## API

- `POST /api/scrape` — Scrape website
- `POST /api/generate` — Generate email
- `POST /api/verify` — Verify emails

## License

MIT — Obsidian Labs
