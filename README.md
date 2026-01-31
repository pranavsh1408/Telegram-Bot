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

## How It Works

1. Users send `/track` to register for notifications
2. Bot checks StanShop API every hour
3. When vouchers become available, all tracked users get notified
4. After notification, tracking stops for that user (prevents spam)
5. Users can send `/track` again to re-enable notifications

## Files

| File | Description |
|------|-------------|
| `scheduler.py` | Main entry point - runs bot with hourly checks |
| `bot.py` | Telegram bot commands and handlers |
| `monitor.py` | API monitoring and stock tracking logic |
| `config.py` | Configuration loader from .env |
| `tracked_users.json` | Stores registered users (auto-created) |

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
