import logging
import datetime
import html
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
        now_iso = datetime.datetime.now().isoformat()
        expired_bets = get_expired_open_bets(now_iso)

        if not expired_bets:
            return

        for bet in expired_bets:
            bet_id = bet['id']
            description = html.escape(bet['description'])
            
            # Send notification BEFORE changing status
            if ADMIN_IDS:
                message = (
                    f"🚨 <b>Bet Expired!</b> 🚨\n\n"
                    f"ID: <code>{bet_id}</code>\n"
                    f"Desc: {description}\n\n"
                    f"Please resolve using:\n"
                    f"<code>/resolve {bet_id} A</code>\n"
                    f"<code>/resolve {bet_id} B</code>\n"
                )
                
                for admin_id in ADMIN_IDS:
                    try:
                        await context.bot.send_message(
                            chat_id=int(admin_id), 
                            text=message, 
                            parse_mode='HTML'
                        )
                    except Exception as e:
                        logger.warning(f"Failed to notify admin {admin_id}: {e}")

            # Update status to LOCKED
            update_bet_status(bet_id, 'LOCKED')
            logger.info(f"Bet {bet_id} expired. Status updated to LOCKED and admins notified.")
            
    except Exception as e:
        logger.error(f"Error in check_deadlines job: {e}")