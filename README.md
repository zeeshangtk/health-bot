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

**Recommended: Use Environment Variable**

Set the `TELEGRAM_TOKEN` environment variable:

```bash
export TELEGRAM_TOKEN="your_bot_token_here"
```

To make it persistent, add it to your shell profile (`~/.zshrc` or `~/.bashrc`):

```bash
echo 'export TELEGRAM_TOKEN="your_bot_token_here"' >> ~/.zshrc
source ~/.zshrc
```

**Alternative: Using .env file**

You can also create a `.env` file in the project root (note: you'll need to load it manually or use a package like `python-dotenv`):

```
TELEGRAM_TOKEN=your_bot_token_here
```

**Note:** The token is no longer stored in `config.py` for security. Always use environment variables.

### 4. Run the Bot

Activate the virtual environment and start the bot using polling mode:

```bash
source venv/bin/activate  # On Windows: venv\Scripts\activate
python bot.py
```

Or run both commands in one line:

```bash
source venv/bin/activate && python bot.py
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
