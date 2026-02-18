# Shekkle Predictions Bot

A Telegram bot for betting and predictions using Shekkles (or any custom currency).

## Features

- **Economy System**: Users start with an initial balance and can claim daily rewards.
- **Betting**: Users can create bets with deadlines and two outcomes.
- **Wagering**: Users can place wagers on open bets.
- **Bet Resolution**: Admins can resolve bets, distributing winnings to the correct side.
- **Refunds**: Automatically refunds wagers if no one bet on the winning side.
- **Deadlines**: Background job automatically closes bets and notifies admins when deadlines pass.
- **Inline Buttons**: Quick wagering directly from chat.

## Setup

1.  **Clone the Repository**:
    ```bash
    git clone https://github.com/tokual/shekelbot.git
    cd shekelbot
    ```

2.  **Run Setup Script**:
    This will create a virtual environment and install dependencies.
    ```bash
    ./setup.sh
    ```

3.  **Configure Environment**:
    Rename `.env.example` to `.env` and fill in your bot token and admin IDs.
    ```bash
    mv .env.example .env
    nano .env
    ```

4.  **Run the Bot**:
    ```bash
    source venv/bin/activate
    python -m shekkle_bot.main
    ```

## Commands

### User Commands
- `/start` - Join and check balance.
- `/daily` - Claim daily reward.
- `/balance` - Check current balance.
- `/createbet` - Start a conversation to create a new bet.
- `/bets` - List all open bets.
- `/wager <bet_id> <A/B> <amount>` - manually place a wager (or use inline buttons).

### Admin Commands
- `/resolve <bet_id> <A/B>` - Resolve a bet (A wins or B wins).
- `/give <user_id> <amount>` - Manually add/remove funds to a user.

## Deployment (Raspberry Pi / Linux)

A systemd service file is included (`shekkle-bot.service`).

1. Edit the service file to match your paths.
2. Copy to `/etc/systemd/system/`.
3. Enable and start:
   ```bash
   sudo systemctl enable shekkle-bot
   sudo systemctl start shekkle-bot
   ```
