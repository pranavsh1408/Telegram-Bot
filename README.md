# PhonePe Voucher Tracker Bot

A Telegram bot that monitors PhonePe gift voucher availability on StanShop and sends instant notifications when stock becomes available.

## Features

- 🔔 **Track Command**: Use `/track` to register for stock alerts
- 📡 **Auto-Check**: Checks every hour automatically
- 🔕 **Smart Notifications**: Notifies once, then stops (no spam!)
- 💰 **Denomination Details**: Shows all available denominations with prices
- 🔄 **Re-enable Tracking**: Use `/track` again after notification

## Prerequisites

- Python 3.8 or higher
- A Telegram account
- Telegram Bot Token (from @BotFather)

## Setup

### 1. Get Bot Token from @BotFather

1. Open Telegram and search for `@BotFather`
2. Send `/newbot` command
3. Follow the prompts to name your bot
4. Copy the token (looks like `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment

Copy the example environment file:

```bash
copy .env.example .env
```

Edit `.env` and add your bot token:

```
TELEGRAM_BOT_TOKEN=your_actual_bot_token
CHECK_INTERVAL=21600
```

### 4. Start the Bot

```bash
python scheduler.py
```

## Deploy to Vercel

### 1. Push to GitHub

Push this repository to GitHub if you haven't already.

### 2. Deploy on Vercel

1. Go to [vercel.com](https://vercel.com) and import your GitHub repository
2. Add environment variable: `TELEGRAM_BOT_TOKEN`
3. Deploy!

### 3. Set Up Storage

1. In Vercel dashboard, go to Storage → Create → KV
2. Link the KV store to your project
3. Environment variables `KV_REST_API_URL` and `KV_REST_API_TOKEN` will be auto-added

### 4. Configure Telegram Webhook

After deployment, set your webhook URL:
```
https://api.telegram.org/bot<YOUR_TOKEN>/setWebhook?url=https://<YOUR_VERCEL_URL>/api/webhook
```

### 5. Verify Cron Job

The stock check runs every 6 hours automatically. View logs in Vercel dashboard to confirm.

### 5. Register for Notifications

1. Open Telegram and search for your bot's username
2. Send `/start` to see available commands
3. Send `/track` to start receiving notifications

## Bot Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome message with bot info |
| `/track` | Start tracking for stock notifications |
| `/untrack` | Stop tracking |
| `/check` | Manually check current stock status |
| `/status` | View your tracking status |
| `/help` | Show available commands |

## Architecture

### System Overview

```
┌──────────────────────────────────────────────────────────────────────────┐
│                           YOUR SYSTEM                                     │
│                                                                          │
│   ┌─────────────┐     ┌─────────────┐     ┌─────────────────────────┐   │
│   │   Webhook   │     │    Cron     │     │       Storage           │   │
│   │  Handler    │     │   Handler   │     │    (Vercel KV)          │   │
│   │             │     │             │     │                         │   │
│   │ • /track    │     │ • Runs 4x   │     │ • Who's tracking?       │   │
│   │ • /check    │     │   per day   │     │ • Who got notified?     │   │
│   │ • /status   │     │ • Checks    │     │                         │   │
│   │             │     │   StanShop  │     │                         │   │
│   └──────┬──────┘     └──────┬──────┘     └───────────┬─────────────┘   │
│          │                   │                        │                  │
└──────────┼───────────────────┼────────────────────────┼──────────────────┘
           │                   │                        │
           ▼                   ▼                        │
    ┌─────────────┐    ┌─────────────┐                 │
    │  Telegram   │    │  StanShop   │◄────────────────┘
    │  Bot API    │    │    API      │   (reads/writes)
    └─────────────┘    └─────────────┘
```

---

### Flow 1: User Interaction (Event-Driven)

**Trigger:** User sends a command in Telegram

```
User types /track
      │
      ▼
[Telegram servers receive message]
      │
      ▼
[Telegram POSTs to your webhook URL]
      │
      ▼
┌─────────────────────────────────────┐
│         api/webhook.py              │
│                                     │
│  1. Parse incoming JSON             │
│  2. Extract command (/track)        │
│  3. Save user to Vercel KV          │
│  4. Send confirmation via API       │
└─────────────────────────────────────┘
      │
      ▼
[User sees "🔔 Tracking Started!"]
```

**Key Design Decisions:**
- **Webhook vs Polling**: Serverless can't do polling (functions timeout after 10s). Webhooks are event-driven and cost-efficient.
- **Stateless Functions**: Each request is independent. Must use external storage (KV) to remember users.

---

### Flow 2: Stock Monitoring (Scheduled)

**Trigger:** Vercel Cron at 00:00, 06:00, 12:00, 18:00 UTC

```
[Vercel Cron triggers /api/cron]
           │
           ▼
┌──────────────────────────────────────────┐
│              api/cron.py                  │
│                                          │
│  1. Call StanShop API                    │
│     └─► GET inventory data               │
│                                          │
│  2. Compare with previous state          │
│     └─► Was nothing, now has stock?      │
│                                          │
│  3. If stock appeared:                   │
│     ├─► Get tracked users from KV        │
│     ├─► Send Telegram notification       │
│     └─► Mark users as "notified"         │
│                                          │
│  4. If no change:                        │
│     └─► Log and exit                     │
└──────────────────────────────────────────┘
```

**Key Design Decisions:**
- **6-hour interval**: Balances between freshness and API rate limits
- **One-time notification**: Users only get 1 alert, then must re-enable (prevents spam)
- **Change detection**: Only notifies when stock *appears* (not every time it's available)

---

### Data Model (Vercel KV)

```json
{
  "tracked_users": {
    "123456789": {
      "username": "pranav",
      "tracked_at": "2026-02-01T14:00:00",
      "notified": false
    },
    "987654321": {
      "username": "someone",
      "tracked_at": "2026-02-01T10:00:00",
      "notified": true
    }
  }
}
```

| Field | Type | Purpose |
|-------|------|---------|
| `username` | string | Telegram username for reference |
| `tracked_at` | ISO date | When user started tracking |
| `notified` | boolean | `false` = will notify, `true` = already notified |

---

### User State Machine

```
         ┌─────────────────────────────────────────┐
         │                                         │
         ▼                                         │
    ┌─────────┐    /track    ┌──────────┐         │
    │   NOT   │ ──────────►  │ TRACKING │         │
    │TRACKING │              │(notified │         │
    └─────────┘              │ = false) │         │
         ▲                   └────┬─────┘         │
         │                        │               │
         │   /untrack             │ Stock found   │
         │                        ▼               │
         │                  ┌──────────┐         │
         └───────────────── │ NOTIFIED │ ────────┘
                            │(notified │   /track
                            │ = true)  │   (resets)
                            └──────────┘
```

---

### Component Details

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Webhook Handler** | `api/webhook.py` | Receives Telegram updates, processes commands |
| **Cron Handler** | `api/cron.py` | Stock checks every 6 hours |
| **Storage** | Vercel KV (Redis) | Persists tracked users |
| **Monitor** | `monitor.py` | Scrapes StanShop API |
| **Config** | `config.py` | Environment variables |

---

### Local vs Vercel Architecture

```
┌─────────────────────────────────┐    ┌─────────────────────────────────┐
│        LOCAL (scheduler.py)     │    │         VERCEL (api/)           │
├─────────────────────────────────┤    ├─────────────────────────────────┤
│                                 │    │                                 │
│  ┌─────────────────────────┐   │    │  ┌─────────────────────────┐   │
│  │     Long Polling        │   │    │  │       Webhooks          │   │
│  │  (bot asks Telegram)    │   │    │  │  (Telegram pushes)      │   │
│  └─────────────────────────┘   │    │  └─────────────────────────┘   │
│                                 │    │                                 │
│  ┌─────────────────────────┐   │    │  ┌─────────────────────────┐   │
│  │     APScheduler         │   │    │  │     Vercel Cron         │   │
│  │  (in-memory scheduler)  │   │    │  │  (managed by Vercel)    │   │
│  └─────────────────────────┘   │    │  └─────────────────────────┘   │
│                                 │    │                                 │
│  ┌─────────────────────────┐   │    │  ┌─────────────────────────┐   │
│  │   tracked_users.json    │   │    │  │      Vercel KV          │   │
│  │   (local file)          │   │    │  │   (cloud database)      │   │
│  └─────────────────────────┘   │    │  └─────────────────────────┘   │
│                                 │    │                                 │
│  ✓ Always running              │    │  ✓ Serverless (pay per use)   │
│  ✓ Simple setup                │    │  ✓ Auto-scales                │
│  ✗ Requires server             │    │  ✓ No server management       │
│                                 │    │                                 │
└─────────────────────────────────┘    └─────────────────────────────────┘
```

---

### Cron Schedule

Schedule: `0 */6 * * *`

| Field | Value | Meaning |
|-------|-------|---------|
| Minute | `0` | At minute 0 |
| Hour | `*/6` | Every 6 hours (0, 6, 12, 18) |
| Day | `*` | Every day |
| Month | `*` | Every month |
| Weekday | `*` | Every day of week |

**Check times (UTC):** 00:00, 06:00, 12:00, 18:00

---

### Why This Design?

| Decision | Reason |
|----------|--------|
| **Webhooks** | Serverless-compatible, only pay when triggered |
| **Vercel KV** | Persistent storage, auto-managed, fast Redis |
| **One-time notify** | Prevents spam, respects user attention |
| **6-hour cron** | Reasonable check frequency without API abuse |

This is a **pub-sub pattern** where:
- Users **subscribe** via `/track`
- Cron job **publishes** notifications when stock changes
- Users **unsubscribe** automatically after notification (or manually via `/untrack`)

## Files

| File | Description |
|------|-------------|
| `scheduler.py` | Local entry point - runs bot with long polling |
| `bot.py` | Telegram bot commands and handlers (local mode) |
| `monitor.py` | API monitoring and stock tracking logic |
| `config.py` | Configuration loader from .env |

### Vercel Files (api/)

| File | Description |
|------|-------------|
| `api/webhook.py` | Serverless webhook handler for Telegram |
| `api/cron.py` | Scheduled stock check (every 6 hours) |
| `api/storage.py` | Vercel KV storage for tracked users |
| `vercel.json` | Cron job configuration |

## Running in Background (Windows)

### Option 1: Task Scheduler
1. Open Task Scheduler
2. Create a new task triggered "At startup"
3. Set action to run `python scheduler.py` in this directory

### Option 2: Using pythonw
```bash
pythonw scheduler.py
```

## Testing

Test the API monitor independently:

```bash
python monitor.py
```

Test configuration:

```bash
python config.py
```

## License

MIT License
