# Health Bot - Family Medical Measurements Tracker

A Telegram bot for recording and tracking family medical measurements (blood pressure, weight, temperature, etc.).

## Setup Instructions

### 1. Create a Telegram Bot Token

1. Open Telegram and search for [@BotFather](https://t.me/botfather)
2. Send `/newbot` command
3. Follow the prompts to name your bot
4. Copy the bot token (format: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

### 2. Install Dependencies

Create a virtual environment and install packages:

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure the Bot

Create a `.env` file in the project root (or modify `config.py`):

```
TELEGRAM_BOT_TOKEN=your_bot_token_here
```

Or edit `config.py` directly to set your token.

### 4. Run the Bot

Start the bot using polling mode:

```bash
python bot.py
```

The bot will start and wait for messages. Send `/start` to your bot in Telegram to begin.

## Data Storage

- **SQLite**: Data is stored in `health_data.db` in the project root directory
- **JSON**: If using JSON storage, data is stored in `health_data.json` in the project root directory

## Project Structure

```
health-bot/
├── bot.py              # Bot entrypoint
├── config.py           # Configuration (token, settings)
├── requirements.txt    # Python dependencies
├── README.md          # This file
├── handlers/          # Command and message handlers
│   ├── __init__.py
│   ├── start.py       # /start command
│   ├── measurements.py # Record measurements
│   └── view.py        # View records
├── storage/           # Data storage layer
│   ├── __init__.py
│   ├── database.py    # SQLite/JSON storage implementation
│   └── models.py      # Data models
└── utils/             # Utility functions
    ├── __init__.py
    └── validators.py  # Input validation
```
