import logging
import os
from telegram import BotCommand, BotCommandScopeChat, BotCommandScopeDefault
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler
from shekkle_bot.config import TOKEN, ADMIN_IDS
from shekkle_bot.database import init_db
from shekkle_bot.handlers import general, betting, admin, leaderboard
from shekkle_bot import jobs

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
async def post_init(application):
    user_commands = [
        BotCommand("start", "Join"),
        BotCommand("daily", "Claim reward"),
        BotCommand("balance", "Check funds"),
        BotCommand("createbet", "New bet"),
        BotCommand("bets", "List open bets"),
        BotCommand("leaderboard", "Top winners"),
        BotCommand("loserboard", "Top losers"),
    ]
    
    admin_commands = user_commands + [
        BotCommand("resolve", "Settle bet (Admin)"),
        BotCommand("give", "Add funds (Admin)"),
    ]
    
    # Set commands for general users (default scope)
    await application.bot.set_my_commands(user_commands, scope=BotCommandScopeDefault())
    
    # Set commands for admins specifically in their private chat
    for admin_id in ADMIN_IDS:
        try:
            await application.bot.set_my_commands(admin_commands, scope=BotCommandScopeChat(chat_id=admin_id))
        except Exception as e:
            logging.warning(f"Could not set commands for admin {admin_id}: {e}")


def main():
    if not TOKEN:
        raise ValueError("No TOKEN provided in .env file.")

    # Initialize the database
    init_db()

    # Build the application
    application = ApplicationBuilder().token(TOKEN).post_init(post_init).build()

    # Add General Handlers
    application.add_handler(CommandHandler("start", general.start))
    application.add_handler(CommandHandler("balance", general.balance))
    application.add_handler(CommandHandler("daily", general.daily))
    
    # Add Leaderboard Handlers
    application.add_handler(CommandHandler("leaderboard", leaderboard.show_leaderboard))
    application.add_handler(CommandHandler("loserboard", leaderboard.show_loserboard))

    # Add Betting Handlers
    application.add_handler(betting.createbet_conv_handler)
    application.add_handler(CommandHandler("bets", betting.list_bets))

    application.add_handler(CommandHandler("wager", betting.wager))
    application.add_handler(CallbackQueryHandler(betting.wager_button, pattern='^wager:'))
    application.add_handler(CallbackQueryHandler(betting.view_bets_button, pattern='^view_bets:'))

    # Add Admin Handlers
    application.add_handler(CommandHandler("resolve", admin.resolve))
    application.add_handler(CommandHandler("give", admin.add_funds))

    # Job Queue
    if application.job_queue:
        application.job_queue.run_repeating(jobs.check_deadlines, interval=60, first=10)

    # Run the bot
    print("Bot is running...")
    application.run_polling()

if __name__ == '__main__':
    main()
