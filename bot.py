import logging
import os
from telegram import Update, BotCommand, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, ConversationHandler
from datetime import datetime, timedelta
import sqlite3
from dotenv import load_dotenv
import re

# Load environment variables from .env file
load_dotenv()
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
ADMIN_CHAT_ID = 5485465524  # Set your numeric chat ID here

# Configure logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize database
conn = sqlite3.connect('airdrop.db')
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS users
             (user_id INTEGER PRIMARY KEY, wallet TEXT, balance INTEGER DEFAULT 0, last_claim TIMESTAMP, last_withdraw TIMESTAMP, invites INTEGER DEFAULT 0)''')
conn.commit()

# Define constants
DAILY_LIMIT = 500
TOKEN_INCREASE_PER_INVITE = 5
WITHDRAW_INTERVAL_DAYS = 30

# IPFS URL of the welcome image
WELCOME_IMAGE_URL = 'https://ipfs.eth.aragon.network/ipfs/bafybeif4v3shyyhnzogi6bhcij2fnpnzvlembg3gbflyqq6kh2q2xcxium'

# Stages for conversation handler
WALLET, AMOUNT, CONFIRM = range(3)

def get_main_keyboard():
    keyboard = [
        [KeyboardButton("/start"), KeyboardButton("/claim")],
        [KeyboardButton("/invite"), KeyboardButton("/request_withdraw")],
        [KeyboardButton("/balance"), KeyboardButton("/referrals"), KeyboardButton("/cancel")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def start(update: Update, context: CallbackContext) -> None:
    logger.info(f"Start command received from user {update.message.from_user.id}")
    chat_id = update.message.chat_id
    await context.bot.send_photo(chat_id=chat_id, photo=WELCOME_IMAGE_URL)
    await update.message.reply_text(
        'Welcome to the Sync Meme token Airdrop Bot! Please click the [claim] button to claim your daily share of tokens. Visit our official X handle to stay informed: https://x.com/syncprotocol_',
        reply_markup=get_main_keyboard()
    )

async def claim(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    now = datetime.now()
    
    c.execute('SELECT balance, last_claim, invites FROM users WHERE user_id=?', (user_id,))
    row = c.fetchone()

    if row:
        balance, last_claim, invites = row

        if last_claim is None or now - datetime.strptime(last_claim, '%Y-%m-%d %H:%M:%S') > timedelta(days=1):
            claim_amount = DAILY_LIMIT + invites * TOKEN_INCREASE_PER_INVITE
            new_balance = balance + claim_amount
            c.execute('UPDATE users SET balance=?, last_claim=? WHERE user_id=?', (new_balance, now.strftime('%Y-%m-%d %H:%M:%S'), user_id))
            conn.commit()
            await update.message.reply_text(f'You have claimed {claim_amount} tokens! Your new balance is {new_balance} tokens.')
        else:
            await update.message.reply_text('You have already claimed your tokens today. Please try again tomorrow.')
    else:
        claim_amount = DAILY_LIMIT
        new_balance = claim_amount
        c.execute('INSERT INTO users (user_id, balance, last_claim) VALUES (?, ?, ?)', (user_id, new_balance, now.strftime('%Y-%m-%d %H:%M:%S')))
        conn.commit()
        await update.message.reply_text(f'You have claimed {claim_amount} tokens! Your new balance is {new_balance} tokens.')

async def invite(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    invite_link = f"https://t.me/{context.bot.username}?start={user_id}"
    await update.message.reply_text(f'Share this link to invite your friends: {invite_link}')

async def handle_new_user(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    inviter_id = context.args[0] if context.args else None
    if inviter_id:
        c.execute('UPDATE users SET invites = invites + 1 WHERE user_id=?', (inviter_id,))
        conn.commit()
        await update.message.reply_text('Thank you for joining via an invite!')

async def request_withdraw(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    c.execute('SELECT last_withdraw, balance FROM users WHERE user_id=?', (user_id,))
    row = c.fetchone()

    if row:
        last_withdraw, balance = row
        now = datetime.now()

        if last_withdraw is None or now - datetime.strptime(last_withdraw, '%Y-%m-%d %H:%M:%S') > timedelta(days=WITHDRAW_INTERVAL_DAYS):
            await update.message.reply_text('Please provide your Solana wallet address for the withdrawal request:')
            return WALLET
        else:
            await update.message.reply_text('You have already requested a withdrawal in the past 30 days. Please try again later.')
            return ConversationHandler.END
    else:
        await update.message.reply_text('An error occurred. Please try again.')
        return ConversationHandler.END

async def wallet_input(update: Update, context: CallbackContext) -> None:
    context.user_data['withdraw_wallet'] = update.message.text.split()[-1]
    await update.message.reply_text(f'You have entered {context.user_data["withdraw_wallet"]}. How many tokens do you wish to withdraw?')
    return AMOUNT

async def amount_input(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    withdraw_amount = int(update.message.text)
    c.execute('SELECT balance FROM users WHERE user_id=?', (user_id,))
    row = c.fetchone()

    if row:
        balance = row[0]
        if withdraw_amount > balance:
            await update.message.reply_text(f'Insufficient balance. Your current balance is {balance} tokens.')
            return ConversationHandler.END
        else:
            context.user_data['withdraw_amount'] = withdraw_amount
            await update.message.reply_text(f'You have requested to withdraw {withdraw_amount} tokens. Please confirm by typing "confirm".')
            return CONFIRM
    else:
        await update.message.reply_text('An error occurred. Please try again.')
        return ConversationHandler.END

async def confirm_withdraw(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    wallet = context.user_data['withdraw_wallet']
    withdraw_amount = context.user_data['withdraw_amount']
    now = datetime.now()
    try:
        c.execute('SELECT balance FROM users WHERE user_id=?', (user_id,))
        row = c.fetchone()
        if row:
            balance = row[0]
            new_balance = balance - withdraw_amount
            c.execute('UPDATE users SET balance=?, last_withdraw=? WHERE user_id=?', (new_balance, now.strftime('%Y-%m-%d %H:%M:%S'), user_id))
            conn.commit()
            await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"User ID: {user_id}\nWallet: {wallet}\nRequested withdrawal: {withdraw_amount} tokens")
            await update.message.reply_text(f'Your withdrawal request for {withdraw_amount} tokens has been sent. It will be processed within 7 working days. If not received, please contact support via Telegram @syncprotocol {ADMIN_CHAT_ID}.')
        else:
            await update.message.reply_text('An error occurred. Please try again.')
    except Exception as e:
        logger.error(f"Error processing withdrawal: {e}")
        await update.message.reply_text(f'An error occurred. Please try again. Error details: {e}')
    return ConversationHandler.END

async def check_balance(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    c.execute('SELECT balance FROM users WHERE user_id=?', (user_id,))
    row = c.fetchone()
    if row:
        balance = row[0]
        await update.message.reply_text(f'Your current balance is {balance} tokens.')
    else:
        await update.message.reply_text('You need to claim tokens first using /claim.')

async def check_referrals(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    c.execute('SELECT invites FROM users WHERE user_id=?', (user_id,))
    row = c.fetchone()
    if row:
        invites = row[0]
        await update.message.reply_text(f'You have {invites} referrals.')
    else:
        await update.message.reply_text('You are not registered yet. Please use /start to register.')

async def cancel(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text('Withdrawal request canceled.')
    return ConversationHandler.END

def main() -> None:
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Set bot commands
    commands = [
        BotCommand("start", "Start the bot"),
        BotCommand("claim", "Claim your daily SMEME tokens"),
        BotCommand("invite", "Get your invite link"),
        BotCommand("request_withdraw", "Request a token withdrawal"),
        BotCommand("balance", "Check your token balance"),
        BotCommand("referrals", "Check your referral count"),
        BotCommand("cancel", "Cancel the current operation")
    ]
    application.bot.set_my_commands(commands)

    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("claim", claim))
    application.add_handler(CommandHandler("invite", invite))
    application.add_handler(CommandHandler("balance", check_balance))
    application.add_handler(CommandHandler("referrals", check_referrals))
    application.add_handler(CommandHandler("cancel", cancel))

    # Conversation handler for withdraw requests
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('request_withdraw', request_withdraw)],
        states={
            WALLET: [MessageHandler(filters.TEXT & ~filters.COMMAND, wallet_input)],
            AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, amount_input)],
            CONFIRM: [MessageHandler(filters.Regex(re.compile('^confirm$', re.IGNORECASE)), confirm_withdraw)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    application.add_handler(conv_handler)

    application.run_polling()

if __name__ == '__main__':
    main()