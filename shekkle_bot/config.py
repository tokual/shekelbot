import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Bot Configuration
TOKEN = os.getenv("TOKEN")
# Default to a file in the parent directory if not specified
DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(os.path.dirname(__file__)), "shekkle.db"))

# Admin Configuration
_admin_ids_str = os.getenv("ADMIN_IDS", "")
ADMIN_IDS = [int(id_str.strip()) for id_str in _admin_ids_str.split(",") if id_str.strip().isdigit()]

# Economy Settings
INITIAL_BALANCE = 100
DAILY_REWARD = 50
DEFAULT_WAGER_AMOUNT = 50
CURRENCY_NAME = "Shekel"
