from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import shekkle_bot.database as db
from shekkle_bot.config import CURRENCY_NAME
import html
import math

PAGE_SIZE = 5

def build_board_message(users, page, is_losers, user_id):
    if is_losers:
        users = [u for u in users if u['net_profit'] < 0]

    if not users:
        return "No stats available yet." if not is_losers else "No one is in the red yet! 🎉", None
        
    total_pages = max(1, math.ceil(len(users) / PAGE_SIZE))
    page = max(0, min(page, total_pages - 1))
    
    start_idx = page * PAGE_SIZE
    end_idx = start_idx + PAGE_SIZE
    page_users = users[start_idx:end_idx]
    
    title = f"📉 <b>Top Losers</b> 📉\n\n" if is_losers else f"🏆 <b>Top Winners</b> 🏆\n\n"
    msg = title
    
    my_rank = None
    for i, user in enumerate(users, 1):
        if user['user_id'] == user_id:
            my_rank = (i, user)
            break
            
    for i, user in enumerate(page_users, start_idx + 1):
        username = html.escape(user['username']) if user['username'] else "Unknown"
        profit = user['net_profit']
        
        if not is_losers:
            medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, f"{i}.")
            msg += f"{medal} <b>{username}</b>: {profit}\n"
        else:
            msg += f"{i}. <b>{username}</b>: {profit}\n"
            
    if my_rank and (my_rank[0] <= start_idx or my_rank[0] > end_idx):
        msg += f"\n...\n<b>{my_rank[0]}. YOU</b>: {my_rank[1]['net_profit']}\n"

    # Pagination buttons
    keyboard = []
    nav_row = []
    board_str = 'losers' if is_losers else 'winners'
    
    if page > 0:
        nav_row.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"page_board_{board_str}_{page-1}"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton("Next ➡️", callback_data=f"page_board_{board_str}_{page+1}"))
        
    if nav_row:
        keyboard.append(nav_row)
        
    reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
    return msg, reply_markup

async def show_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows the top winners."""
    winners, _ = db.get_leaderboard_data()
    msg, reply_markup = build_board_message(winners, 0, False, update.effective_user.id)
    await update.message.reply_text(msg, parse_mode='HTML', reply_markup=reply_markup)

async def show_loserboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows the top losers."""
    _, losers = db.get_leaderboard_data()
    msg, reply_markup = build_board_message(losers, 0, True, update.effective_user.id)
    await update.message.reply_text(msg, parse_mode='HTML', reply_markup=reply_markup)

async def board_page_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles callback for navigating board pages."""
    query = update.callback_query
    await query.answer()
    
    # Callback data format: page_board_{type}_{page}
    parts = query.data.split('_')
    board_type = parts[2]
    page = int(parts[3])
    is_losers = (board_type == 'losers')
    
    winners, losers = db.get_leaderboard_data()
    users = losers if is_losers else winners
    
    msg, reply_markup = build_board_message(users, page, is_losers, update.effective_user.id)
    
    # Avoid telegram errors if message text hasn't changed
    if query.message.text_html != msg:
        await query.edit_message_text(text=msg, parse_mode='HTML', reply_markup=reply_markup)