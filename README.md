# USCIS WatchBot

USCIS WatchBot is a Python bot that monitors official USCIS and Department of State update pages, classifies new immigration updates by topic, stores them in SQLite, and sends Telegram notifications for priority updates and weekly digests.

## Features

- Monitors only official USCIS and Department of State sources
- Detects new updates and avoids duplicate sends with SQLite
- Sends immediate Telegram alerts for priority immigration topics
- Sends a weekly Telegram digest for non-priority updates
- Uses GitHub Actions for automated daily and weekly runs
- Keeps the code modular and beginner-friendly

## Official sources monitored

- `https://www.uscis.gov/newsroom/alerts`
- `https://www.uscis.gov/newsroom/all-news`
- `https://www.uscis.gov/newsroom/news-releases`
- `https://www.uscis.gov/policy-manual/updates`
- `https://www.uscis.gov/green-card/green-card-processes-and-procedures/visa-availability-priority-dates/adjustment-of-status-filing-charts-from-the-visa-bulletin`
- `https://travel.state.gov/content/travel/en/legal/visa-law0/visa-bulletin.html`

## Priority topics checked daily

- I-130
- I-485
- I-765
- I-864
- I-131
- I-94
- F-1
- H-1B
- OPT
- STEM OPT

## Project structure

```text
uscis-watchbot/
|-- app/
|   |-- __init__.py
|   |-- classifier.py
|   |-- config.py
|   |-- daily.py
|   |-- database.py
|   |-- notifier.py
|   |-- scraper.py
|   `-- weekly.py
|-- .github/
|   `-- workflows/
|       |-- daily.yml
|       `-- weekly.yml
|-- .env.example
|-- .gitignore
|-- README.md
`-- requirements.txt
```

## Setup instructions

1. Install Python 3.11 or newer.
2. Clone this repository.
3. Create and activate a virtual environment.
4. Install the dependencies from `requirements.txt`.
5. Copy `.env.example` to `.env`.
6. Add your Telegram bot token and chat ID to `.env`.

## Create a Telegram bot with BotFather

1. Open Telegram and search for `@BotFather`.
2. Start a chat and send `/newbot`.
3. Follow the prompts to choose a bot name and username.
4. Copy the bot token BotFather gives you.
5. Put that token into `TELEGRAM_BOT_TOKEN` in your `.env` file.

## Get your `TELEGRAM_CHAT_ID`

1. Open a chat with your bot and send it a test message such as `hello`.
2. In your browser, open:

   ```text
   https://api.telegram.org/botYOUR_BOT_TOKEN/getUpdates
   ```

3. Find the `chat` object in the JSON response.
4. Copy the `id` field from that object.
5. Put that value into `TELEGRAM_CHAT_ID` in your `.env` file.

If you want messages to go to a group, add the bot to the group, send a message in the group, and then check `getUpdates` again.

## Run locally

### Daily run

```bash
python -m app.daily
```

This command scrapes all official sources, stores new updates in `updates.db`, classifies them, and sends only new priority-topic alerts.

### Weekly run

```bash
python -m app.weekly
```

This command sends a weekly digest for general immigration updates that have not already been sent in a digest.

## How the database works

The project uses a local SQLite database named `updates.db`. The `updates` table stores:

- title
- url
- source
- category
- matched topics
- update type
- first seen timestamp
- whether the daily alert has been sent
- whether the weekly digest entry has been sent

This prevents duplicate inserts and duplicate Telegram notifications.

## GitHub Actions deployment

Two workflows are included:

- `.github/workflows/daily.yml` runs once every day and supports manual runs
- `.github/workflows/weekly.yml` runs every Sunday and supports manual runs

Both workflows:

- install Python 3.11
- install the project dependencies
- restore `updates.db` from GitHub Actions cache
- run the appropriate Python module
- save the updated SQLite database back to cache

The cache step matters because GitHub Actions runners are temporary. Without cache, the SQLite file would be lost after each run.

## Add GitHub secrets

In your GitHub repository:

1. Go to **Settings**.
2. Open **Secrets and variables** > **Actions**.
3. Add these repository secrets:
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`

After that, you can manually run either workflow from the **Actions** tab or wait for the scheduled jobs.

## Mac local run: step by step

1. Open **Terminal**.
2. Move into the project folder:

   ```bash
   cd /Users/yashashreepatel/Desktop/Projects/uscis-watch-bot
   ```

3. Create a virtual environment:

   ```bash
   python3 -m venv .venv
   ```

4. Activate it:

   ```bash
   source .venv/bin/activate
   ```

5. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

6. Create your environment file:

   ```bash
   cp .env.example .env
   ```

7. Edit `.env` and add your real Telegram bot token and chat ID.

8. Run the daily script:

   ```bash
   python -m app.daily
   ```

9. Run the weekly script when you want to test the digest:

   ```bash
   python -m app.weekly
   ```

10. When you are done, deactivate the virtual environment:

   ```bash
   deactivate
   ```

## Future improvements

- Add retry and backoff logic for temporary HTTP failures
- Add structured logging to a file
- Add tests with mocked HTTP responses and Telegram calls
- Add more source-specific scraping rules for higher precision
- Add message templates with Markdown escaping if needed
- Add optional email or Slack notifications
