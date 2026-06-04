# 🖤 0xChapo — AI Cold Email Engine

<p align="center">
  <strong>AI-powered cold email automation for modern outreach teams</strong>
</p>

<p align="center">
  <a href="https://0xchapo.xyz">🌐 Live Demo</a> •
  <a href="#features">✨ Features</a> •
  <a href="#quick-start">🚀 Quick Start</a> •
  <a href="#pricing">💰 Pricing</a> •
  <a href="#api">📡 API</a>
</p>

---

## ✨ Features

- 🕷️ **Lead Scraping** — Auto-extract company info from websites
- 🤖 **AI Email Generation** — Claude-powered personalized email writing
- 📤 **SMTP Sending** — Rate-limited email delivery with your own SMTP
- 📊 **Analytics Dashboard** — Track opens, replies, and conversions
- 🧪 **Dry Run Mode** — Preview emails before sending
- 📋 **CSV Import/Export** — Import leads from spreadsheets
- 📧 **Email Verification** — Check email validity (syntax, domain, MX, disposable)
- 🔄 **Follow-up Sequences** — Multi-step auto follow-ups with custom delays
- 🔐 **User Authentication** — Email + OTP, Google OAuth
- 💳 **Payments** — Crypto (NOWPayments, 365+ coins) + Card (LemonSqueezy)
- 📱 **Responsive UI** — Dark theme, works on mobile
- 🔌 **API Access** — RESTful API for developers

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- SMTP credentials (Gmail, SendGrid, etc.)
- Anthropic API key (for AI generation)

### Installation

```bash
# Clone repo
git clone https://github.com/yossweh/cold-email-engine.git
cd cold-email-engine

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Run development server
python src/dashboard/app.py
```

### Production Deployment

```bash
# Install gunicorn
pip install gunicorn

# Run with gunicorn
gunicorn --workers 2 --bind 0.0.0.0:5050 wsgi:app

# Or use systemd (recommended)
sudo cp 0xchapo.service /etc/systemd/system/
sudo systemctl enable 0xchapo
sudo systemctl start 0xchapo
```

---

## 🏗️ Architecture

```
0xchapo/
├── src/
│   ├── auth/              # User authentication (email+OTP, Google OAuth)
│   ├── payments/          # Payment processing (NOWPayments + LemonSqueezy)
│   ├── scraper/           # Lead enrichment & scraping
│   ├── generator/         # AI email writer (Claude)
│   ├── sender/            # SMTP delivery engine
│   ├── verifier/          # Email verification (syntax, MX, disposable)
│   ├── leads/             # Lead management & storage
│   ├── sequences/         # Follow-up sequence engine
│   ├── dashboard/         # Web UI (Flask + Jinja2)
│   │   ├── static/        # CSS, favicon
│   │   └── templates/     # HTML templates (17 pages)
│   └── main.py            # CLI pipeline
├── data/                  # Runtime data (gitignored)
├── .env.example           # Environment template
├── requirements.txt       # Python dependencies
└── wsgi.py                # WSGI entry point
```

---

## 💰 Pricing

| Plan | Price | Emails/Day | Features |
|------|-------|------------|----------|
| **Free** | $0 | 10 | Basic scraping, AI generation, CSV import |
| **Pro** | $15/mo | 500 | + Follow-ups, API access, Priority support |
| **Enterprise** | $49/mo | Unlimited | + White-label, Custom domain, Team management |

### Payment Methods
- 🪙 **Crypto** — BTC, ETH, USDC, SOL, DOGE, +360 coins (via NOWPayments)
- 💳 **Card** — Visa, Mastercard (via LemonSqueezy)

---

## 📡 API

### Authentication
All API endpoints require authentication via session cookie.

### Endpoints

```bash
# Lead Scraping
POST /api/scrape
{
  "url": "https://example.com",
  "depth": 2
}

# Email Generation
POST /api/generate
{
  "lead_name": "John Doe",
  "company": "Acme Inc",
  "context": "SaaS product launch"
}

# Email Verification
POST /api/verify
{
  "emails": ["test@example.com", "invalid@domain.com"]
}
```

---

## ⚙️ Environment Variables

```bash
# Required
ANTHROPIC_API_KEY=your-claude-api-key
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your@email.com
SMTP_PASSWORD=your-app-password

# Optional
DASHBOARD_PORT=5050
DASHBOARD_SECRET=your-secret-key
MAX_EMAILS_PER_HOUR=30
DELAY_BETWEEN_EMAILS_SEC=60

# Payments (NOWPayments)
NOWPAYMENTS_API_KEY=your-api-key
NOWPAYMENTS_IPN_SECRET=your-ipn-secret
NOWPAYMENTS_IPN_URL=https://yourdomain.com/webhook/nowpayments

# Payments (LemonSqueezy)
LEMONSQUEEZY_API_KEY=your-api-key
LEMONSQUEEZY_WEBHOOK_SECRET=your-webhook-secret
LEMONSQUEEZY_STORE_ID=your-store-id
```

---

## 🛠️ Tech Stack

- **Backend:** Python 3.11, Flask, Gunicorn
- **AI:** Anthropic Claude API
- **Database:** JSON file storage
- **Email:** SMTP (Gmail, SendGrid, custom)
- **Payments:** NOWPayments (crypto), LemonSqueezy (card)
- **Frontend:** HTML, CSS (dark theme), Chart.js
- **Deployment:** Nginx, Systemd, Ubuntu 24.04

---

## 📦 Dependencies

```
flask==3.1.1
anthropic==0.42.0
requests==2.32.3
beautifulsoup4==4.12.3
python-dotenv==1.0.1
gunicorn==23.0.0
```

---

## 🔒 Security

- ✅ Environment variables for secrets (`.env` gitignored)
- ✅ Session-based authentication
- ✅ OTP verification for email
- ✅ IPN signature verification (HMAC-SHA512)
- ✅ Rate limiting on API endpoints
- ✅ SQL injection prevention (JSON storage)
- ✅ XSS protection (Jinja2 auto-escaping)

---

## 📄 License

MIT License — [0xChapo Labs](https://0xchapo.xyz)

---

<p align="center">
  Made with 🖤 by <a href="https://0xchapo.xyz">0xChapo Labs</a>
</p>
