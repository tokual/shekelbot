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

echo "Setup complete. Don't forget to edit .env and activate venv."
