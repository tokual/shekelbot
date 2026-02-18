#!/bin/bash

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install requirements
pip install --upgrade pip
pip install -r requirements.txt

# Create empty .env if not exists
if [ ! -f .env ]; then
    cp .env.example .env
    echo "Created .env file. Please populate it with your credentials."
fi

# Make sure permissions are correct for execution
chmod +x setup.sh

# Service Setup (Linux only)
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "Detected Linux. Setting up systemd service..."
    
    SERVICE_FILE="shekkle-bot.service"
    CURRENT_USER=$(whoami)
    CURRENT_DIR=$(pwd)
    PYTHON_EXEC="$CURRENT_DIR/venv/bin/python"
    
    # Update service file with current paths and user
    sed -i "s|User=.*|User=$CURRENT_USER|g" $SERVICE_FILE
    sed -i "s|WorkingDirectory=.*|WorkingDirectory=$CURRENT_DIR|g" $SERVICE_FILE
    sed -i "s|ExecStart=.*|ExecStart=$PYTHON_EXEC -m shekkle_bot.main|g" $SERVICE_FILE
    
    echo "Service file updated with User=$CURRENT_USER and Path=$CURRENT_DIR"
    
    # Install and start service
    if sudo cp $SERVICE_FILE /etc/systemd/system/; then
        sudo systemctl daemon-reload
        sudo systemctl enable shekkle-bot
        sudo systemctl restart shekkle-bot
        echo "✅ Service installed and started!"
        sudo systemctl status shekkle-bot --no-pager
    else
        echo "❌ Failed to copy service file. Sudo access required."
    fi
else
    echo "Not on Linux. Skipping systemd setup."
fi

echo "Setup complete. Don't forget to edit .env if you haven't already."
