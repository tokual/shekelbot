import logging
import datetime
from telegram.ext import ContextTypes
from shekkle_bot.database import get_expired_open_bets, update_bet_status
from shekkle_bot.config import ADMIN_IDS

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def check_deadlines(context: ContextTypes.DEFAULT_TYPE):
    """
    Job to check for betting deadlines.
    """
    try:
        # Use datetime.now().isoformat() directly as string comparison works for ISO8601
        now_iso = datetime.datetime.now().isoformat()
        expired_bets = get_expired_open_bets(now_iso)

        if not expired_bets:
            return

        for bet in expired_bets:
            # bet is a dict: {'id': ..., 'description': ...}
            bet_id = bet['id']
            description = bet['description']
            
            # Update status to PENDING
            update_bet_status(bet_id, 'PENDING_RESOLUTION')
            logger.info(f"Bet {bet_id} expired. Status updated to PENDING_RESOLUTION.")
            
            # Notify Admins
            message = (
                f"🚨 *Bet Expired!* 🚨\n\n"
                f"ID: `{bet_id}`\n"
                f"Desc: {description}\n\n"
                f"Please resolve using:\n"
                f"`/resolve {bet_id} A`\n"
                f"`/resolve {bet_id} B`\n"
                f"Or refund with:\n"
                f"`/resolve {bet_id} REFUND`"
            )
            
            for admin_id in ADMIN_IDS:
                try:
                    await context.bot.send_message(chat_id=admin_id, text=message, parse_mode='Markdown')
                except Exception as e:
                    logger.error(f"Failed to notify admin {admin_id}: {e}")

    except Exception as e:
        logger.error(f"Error in check_deadlines: {e}")
