import logging
import html
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, ForceReply, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler,
)
import shekkle_bot.database as db
from shekkle_bot.config import CURRENCY_NAME, DEFAULT_WAGER_AMOUNT

# Enable logging
logger = logging.getLogger(__name__)

# Stages
DESCRIPTION, DEADLINE, OPTION_A, OPTION_B = range(4)

async def create_bet_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Starts the conversation and asks for the bet description."""
    await update.message.reply_text(
        "Let's create a new bet. What is the description/question for the bet?\n"
        "Send /cancel to stop.",
        reply_markup=ForceReply(selective=True),
    )
    return DESCRIPTION

async def receive_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stores the description and asks for the deadline."""
    text = update.message.text
    context.user_data['description'] = text
    await update.message.reply_text(
        f"Got it: '{text}'.\n\n"
        "When does betting close for this bet? (Format: YYYY-MM-DD HH:MM)\n"
        "Example: 2026-02-19 18:00",
        reply_markup=ForceReply(selective=True),
    )
    return DEADLINE

async def receive_deadline(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stores the deadline and asks for Option A."""
    text = update.message.text
    try:
        # Validate date format
        dt = datetime.strptime(text, "%Y-%m-%d %H:%M")
        if dt < datetime.now():
            await update.message.reply_text(
                "The deadline must be in the future. Please try again (YYYY-MM-DD HH:MM).",
                reply_markup=ForceReply(selective=True)
            )
            return DEADLINE
        
        context.user_data['deadline'] = dt
        await update.message.reply_text(
            "Deadline set. Now, what is Option A? (e.g. Yes, Red)",
            reply_markup=ForceReply(selective=True)
        )
        return OPTION_A
    except ValueError:
        await update.message.reply_text(
            "Invalid date format. Please use YYYY-MM-DD HH:MM\n"
            "Example: 2026-02-19 18:00",
            reply_markup=ForceReply(selective=True)
        )
        return DEADLINE

async def receive_option_a(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stores Option A and asks for Option B."""
    context.user_data['option_a'] = update.message.text
    await update.message.reply_text(
        "Option A saved. What is Option B? (e.g. No, Blue)",
        reply_markup=ForceReply(selective=True)
    )
    return OPTION_B

async def receive_option_b(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stores Option B and creates the bet."""
    option_b = update.message.text
    context.user_data['option_b'] = option_b
    
    # Create bet in DB
    user = update.effective_user
    # Ensure deadline is stored as ISO format string for consistency
    deadline_val = context.user_data['deadline']
    if isinstance(deadline_val, datetime):
        deadline_str = deadline_val.isoformat()
    else:
        deadline_str = str(deadline_val)

    new_id = db.create_bet(
        user.id,
        context.user_data['description'],
        deadline_str,
        context.user_data['option_a'],
        context.user_data['option_b']
    )
    
    if new_id:
        keyboard = [
            [
                InlineKeyboardButton(f"Bet {DEFAULT_WAGER_AMOUNT} {CURRENCY_NAME} on {context.user_data['option_a']}", callback_data=f"wager:{new_id}:A"),
                InlineKeyboardButton(f"Bet {DEFAULT_WAGER_AMOUNT} {CURRENCY_NAME} on {context.user_data['option_b']}", callback_data=f"wager:{new_id}:B"),
            ],
            [
                InlineKeyboardButton("View Bets", callback_data=f"view_bets:{new_id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Escape user provided content for HTML
        desc = html.escape(context.user_data['description'])
        opt_a = html.escape(context.user_data['option_a'])
        opt_b = html.escape(context.user_data['option_b'])

        await update.message.reply_text(
            f"✅ New Bet Created! #{new_id}\n\n"
            f"📝 {desc}\n"
            f"⏰ Deadline: {context.user_data['deadline']}\n"
            f"🅰️ {opt_a}\n"
            f"🅱️ {opt_b}\n\n"
            f"To wager custom amount use:\n"
            f"<code>/wager {new_id} A [amount]</code> or <code>/wager {new_id} B [amount]</code>",
            parse_mode='HTML',
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text("❌ Error creating bet. Please try again.")

    context.user_data.clear()
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancels and ends the conversation."""
    await update.message.reply_text(
        "Bet creation cancelled.", reply_markup=ReplyKeyboardRemove()
    )
    context.user_data.clear()
    return ConversationHandler.END

async def list_bets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lists all open bets with pagination."""
    bets = db.get_open_bets()
    if not bets:
        await update.message.reply_text("There are currently no open bets.")
        return

    # Call the helper to show the first bet (index 0)
    await send_bet_page(update.message.reply_text, bets, 0)

async def send_bet_page(send_method, bets, index):
    bet = bets[index]
    
    try:
        d_str = bet['deadline']
        if 'T' in d_str:
            d_str = d_str.replace('T', ' ')
    except:
        d_str = str(bet['deadline'])

    # Build navigation buttons at the top or bottom
    nav_buttons = []
    if index > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"page_bet:{index-1}"))
    nav_buttons.append(InlineKeyboardButton(f"{index+1}/{len(bets)}", callback_data="ignore"))
    if index < len(bets) - 1:
        nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"page_bet:{index+1}"))

    keyboard = [
        nav_buttons,
        [
            InlineKeyboardButton(f"Bet {DEFAULT_WAGER_AMOUNT} {CURRENCY_NAME} on {bet['option_a']}", callback_data=f"wager:{bet['id']}:A"),
            InlineKeyboardButton(f"Bet {DEFAULT_WAGER_AMOUNT} {CURRENCY_NAME} on {bet['option_b']}", callback_data=f"wager:{bet['id']}:B"),
        ],
        [
            InlineKeyboardButton("View Bets", callback_data=f"view_bets:{bet['id']}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    desc = html.escape(bet['description'])
    opt_a = html.escape(bet['option_a'])
    opt_b = html.escape(bet['option_b'])

    msg = (
        f"📢 <b>#{bet['id']}</b>: {desc}\n"
        f"🅰️ {opt_a} vs 🅱️ {opt_b}\n"
        f"⏰ Deadline: {d_str}\n"
        f"Use <code>/wager {bet['id']} A [amount]</code> to bet custom amount!"
    )

    await send_method(msg, parse_mode='HTML', reply_markup=reply_markup)

async def bet_page_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles pagination buttons for open bets."""
    query = update.callback_query
    if query.data == "ignore":
        await query.answer()
        return
        
    _, index_str = query.data.split(':')
    index = int(index_str)
    
    bets = db.get_open_bets()
    if not bets:
        await query.edit_message_text("There are currently no open bets.")
        return

    # Bound check
    if index < 0 or index >= len(bets):
        index = 0
        
    await query.answer()
    await send_bet_page(query.edit_message_text, bets, index)

async def wager_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles wager button clicks."""
    query = update.callback_query
    # Split the data formatted as wager:{bet_id}:{choice}
    _, bet_id_str, choice = query.data.split(':')
    bet_id = int(bet_id_str)
    user = update.effective_user

    # Ensure user exists
    if not db.get_user(user.id):
        db.add_user(user.id, user.username)

    success, message = db.place_wager(user.id, bet_id, choice, DEFAULT_WAGER_AMOUNT)

    if success:
        await query.answer(f"✅ Wagered {DEFAULT_WAGER_AMOUNT} {CURRENCY_NAME} on #{bet_id} Choice {choice}.")
    else:
        await query.answer(f"❌ {message}", show_alert=True)


async def wager(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Places a wager on a bet."""
    user = update.effective_user
    if not context.args or len(context.args) < 3:
        await update.message.reply_text("Usage: /wager <bet_id> <A/B> <amount>")
        return

    try:
        bet_id = int(context.args[0])
        choice = context.args[1].upper()
        amount = int(context.args[2])
    except ValueError:
        await update.message.reply_text("Invalid format. ID and Amount must be numbers.")
        return

    if choice not in ['A', 'B']:
        await update.message.reply_text("Choice must be 'A' or 'B'.")
        return
    
    if amount <= 0:
        await update.message.reply_text("Amount must be positive.")
        return

    # Ensure user exists (in case they haven't started user flow yet)
    if not db.get_user(user.id):
        db.add_user(user.id, user.username)

    success, message = db.place_wager(user.id, bet_id, choice, amount)
    
    if success:
        await update.message.reply_text(f"✅ {message}\nWagered {amount} {CURRENCY_NAME} on #{bet_id} Choice {choice}.")
    else:
        await update.message.reply_text(f"❌ {message}")

async def view_bets_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows the current bets and pool information for a bet."""
    query = update.callback_query
    # Split the data formatted as view_bets:{bet_id}
    try:
        _, bet_id_str = query.data.split(':')
        bet_id = int(bet_id_str)
    except ValueError:
        await query.answer("Invalid request.")
        return

    # Acknowledge callback immediately
    await query.answer()

    bet = db.get_bet(bet_id)
    if not bet:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Bet not found or deleted.")
        return

    wagers = db.get_bet_wagers(bet_id)
    
    # Organize wagers by choice
    pool_a_list = [w for w in wagers if w['choice'] == 'A']
    pool_b_list = [w for w in wagers if w['choice'] == 'B']
    
    amount_a = sum(w['amount'] for w in pool_a_list)
    amount_b = sum(w['amount'] for w in pool_b_list)
    total_pool = amount_a + amount_b

    # Calculate theoretical multipliers (Total / Side)
    # If side has 0, multiplier is technically N/A or Infinite. Let's show 0.00x
    mult_a = (total_pool / amount_a) if amount_a > 0 else 0.0
    mult_b = (total_pool / amount_b) if amount_b > 0 else 0.0

    # Format wagers list
    # We must escape names too as they can contain html chars
    def format_wager_list(w_list):
        if not w_list:
            return "None"
        formatted_entries = []
        for w in w_list:
            raw_name = w.get('username') or f"User {w['user_id']}"
            safe_name = html.escape(raw_name)
            # escape amount just in case? Numbers are safe though.
            formatted_entries.append(f"{safe_name} ({w['amount']})")
        return ", ".join(formatted_entries)

    bets_a_str = format_wager_list(pool_a_list)
    bets_b_str = format_wager_list(pool_b_list)

    # Escape bet details
    desc = html.escape(bet['description'])
    opt_a = html.escape(bet['option_a'])
    opt_b = html.escape(bet['option_b'])

    msg = (
        f"📊 <b>Bet #{bet_id} Status</b>\n"
        f"📝 {desc}\n\n"
        f"🅰️ <b>Option A</b>: {opt_a}\n"
        f"💰 Pool: {amount_a} {CURRENCY_NAME}\n"
        f"📈 Payout Ratio: {mult_a:.2f}x\n"
        f"👥 Bets: {bets_a_str}\n\n"
        f"🅱️ <b>Option B</b>: {opt_b}\n"
        f"💰 Pool: {amount_b} {CURRENCY_NAME}\n"
        f"📈 Payout Ratio: {mult_b:.2f}x\n"
        f"👥 Bets: {bets_b_str}\n\n"
        f"Total Pool: {total_pool} {CURRENCY_NAME}"
    )

    await context.bot.send_message(
        chat_id=update.effective_chat.id, 
        text=msg, 
        parse_mode='HTML'
    )


# Conversation Handler definition
createbet_conv_handler = ConversationHandler(
    entry_points=[CommandHandler("createbet", create_bet_start)],
    states={
        DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_description)],
        DEADLINE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_deadline)],
        OPTION_A: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_option_a)],
        OPTION_B: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_option_b)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)
