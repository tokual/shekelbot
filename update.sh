#!/bin/bash

# Configuration
SERVICE_NAME="shekkle-bot"
BRANCH="main"

echo "Started update process..."

# 1. Pull latest changes
echo "Fetching changes from git..."
git fetch origin
git reset --hard origin/$BRANCH

# 2. Update dependencies (just in case requirements.txt changed)
if [ -f "requirements.txt" ]; then
    echo "Updating Python dependencies..."
    source venv/bin/activate
    pip install -r requirements.txt
fi

# 3. Restart Service
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    if systemctl is-active --quiet $SERVICE_NAME; then
        echo "Restarting $SERVICE_NAME service..."
        sudo systemctl restart $SERVICE_NAME
        sudo systemctl status $SERVICE_NAME --no-pager
    else
        echo "Service $SERVICE_NAME is not active or installed. Skipping restart."
        echo "You may need to run ./setup.sh first or run the bot manually."
    fi
else
    echo "Not on Linux/Systemd. Please restart the bot manually."
fi

echo "Update complete!"
